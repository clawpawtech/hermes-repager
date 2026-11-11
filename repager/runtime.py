"""Lazy, profile-scoped runtime shared by native tools and the dashboard API."""
from __future__ import annotations

import contextvars
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .browser import BrowserAdapter
from .service import ReviewService, ServiceError
from .store import ReviewStore
from .models import now_iso

_CONTEXTS = {}
_RUNTIMES = {}
_LOCK = threading.RLock()
TASK = "repager_layout"


def profile_home():
    from hermes_constants import get_hermes_home
    return Path(get_hermes_home()).resolve()


def check_model_policy(config):
    """Require explicit task routing; never infer model pricing or credentials."""
    import re
    main = config.get('model') or {}
    task = (config.get('auxiliary') or {}).get(TASK) or {}
    if not isinstance(main, dict) or not isinstance(task, dict):
        raise ServiceError('Model configuration must contain explicit provider/model objects')
    fallbacks = config.get('fallback_providers', [])
    legacy = config.get('fallback_model', {})
    chain = task.get('fallback_chain')
    if not (type(fallbacks) is list and not fallbacks
            and (legacy is None or (type(legacy) is dict and not legacy))
            and type(chain) is list and not chain):
        raise ServiceError('repager inference requires fallback_providers: [], fallback_model: {} (or null), and auxiliary.repager_layout.fallback_chain: []. No fallback or automatic route is permitted; host configuration was not changed.')
    for item in (main, task):
        for value in (item.get('model'), item.get('default')):
            if re.search(r'(^|[:/_.-])free($|[:/_.-])', str(value or ''), re.I):
                raise ServiceError('No-free-model policy: free/router aliases are refused before inference. Host configuration was not changed.')
    provider = str(task.get('provider') or '').strip()
    model = str(task.get('model') or task.get('default') or '').strip()
    if (not provider or provider.lower() in {'auto', 'default', 'free'} or not model
            or model.lower() in {'auto', 'default', 'free', 'openrouter/auto'}):
        raise ServiceError('Configure auxiliary.repager_layout with BOTH an explicit provider and model and fallback_chain: []. Main-model inheritance and automatic routing are refused.')
    return {'provider': provider, 'model': model}


class HostLlm:
    def __init__(self, ctx):
        self.ctx = ctx

    def complete_structured(self, **kwargs):
        if not self.ctx.get_config("allow_model_calls", False):
            raise ServiceError("Model calls are disabled. Enable repager's allow_model_calls setting after reviewing the data disclosure.")
        from hermes_cli.config import load_config_readonly
        route = check_model_policy(load_config_readonly() or {})
        kwargs["task"] = TASK
        result = self.ctx.llm.complete_structured(**kwargs)
        if (getattr(result, 'provider', None) != route['provider']
                or getattr(result, 'model', None) != route['model']):
            raise ServiceError('Host returned an unexpected model route; result discarded. This audit cannot undo inference.')
        return result


class Runtime:
    """At most two active jobs, bounded history; worker context preserves host profile scope."""
    def __init__(self, root, browser, llm=None):
        self.service = ReviewService(ReviewStore(Path(root)), browser, llm)
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="repager")
        self._lock = threading.Lock()
        self._jobs = {}
        self._active = set()

    def _reserve(self, review_id=None):
        import uuid
        with self._lock:
            if len(self._active) >= 2:
                raise ServiceError("Two repager jobs are already running. Wait for one to finish.")
            if review_id and any(self._jobs[j].get("review_id") == review_id for j in self._active):
                raise ServiceError("This review already has a running job.")
            if len(self._jobs) >= 100:
                for key in list(self._jobs):
                    if key not in self._active:
                        del self._jobs[key]
                        break
            jid = uuid.uuid4().hex
            job = {"id": jid, "state": "pending", "review_id": review_id, "error": None, "created_at": now_iso()}
            self._jobs[jid] = job
            self._active.add(jid)
            return jid, dict(job)

    def submit(self, operation: Callable, *args, review_id=None, **kwargs):
        jid, job = self._reserve(review_id)
        scope = contextvars.copy_context()
        try:
            self._pool.submit(scope.run, self._run, jid, operation, args, kwargs)
        except Exception:
            with self._lock:
                self._active.discard(jid)
                self._jobs.pop(jid, None)
            raise
        return job

    def run_sync(self, operation: Callable, *args, admission_review_id=None, **kwargs):
        """Native synchronous tools share dashboard admission and per-review slots."""
        jid, _ = self._reserve(admission_review_id)
        return self._run(jid, operation, args, kwargs, propagate=True)

    def _run(self, jid, operation, args, kwargs, propagate=False):
        with self._lock:
            self._jobs[jid]["state"] = "running"
        try:
            record = operation(*args, **kwargs)
            with self._lock:
                self._jobs[jid]["review_id"] = record["id"]
            if record.get("status") == "failed" and not record.get("revisions"):
                raise ServiceError(record.get("error") or "Capture did not produce a supported source.")
            with self._lock:
                self._jobs[jid].update(state="completed", review_id=record["id"])
            return record
        except Exception as exc:
            # Errors returned by service/adapter are already bounded. Never expose a traceback.
            with self._lock:
                self._jobs[jid].update(state="failed", error=str(exc)[:1200])
            if propagate:
                raise
        finally:
            with self._lock:
                self._jobs[jid]["finished_at"] = now_iso()
                self._active.discard(jid)

    def jobs(self):
        with self._lock:
            return [dict(job) for job in self._jobs.values()]

    def job(self, jid):
        with self._lock:
            if jid not in self._jobs:
                raise ValueError("Unknown job. Job history is process-local; reopen the saved review after a server restart.")
            return dict(self._jobs[jid])

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)


def bind_context(ctx):
    with _LOCK:
        _CONTEXTS[str(profile_home())] = ctx


def get_runtime():
    home = profile_home()
    key = str(home)
    with _LOCK:
        ctx = _CONTEXTS.get(key)
        if ctx is None:
            raise ServiceError("repager is not enabled in this Hermes process. Enable the native plugin before opening its canvas.")
        if key not in _RUNTIMES:
            browser = BrowserAdapter(executable_path=ctx.get_config("chromium_path", "") or None,
                                     allow_no_sandbox=ctx.get_config("allow_no_sandbox", False),
                                     temp_dir=ctx.get_config("browser_temp_dir", "") or None)
            _RUNTIMES[key] = Runtime(home / "plugin-data" / "repager" / "reviews", browser, HostLlm(ctx))
        return _RUNTIMES[key]


def register_plugin(ctx):
    bind_context(ctx)
    # A plugin-owned auxiliary task, no cross-provider fallback chain by default.
    ctx.register_auxiliary_task(TASK, display_name="repager layout", description="Bounded text-only section layout from an approved review", defaults={"fallback_chain": []})
    operations = {
        "capture": ("Capture a public landing page at desktop/mobile sizes. Sends no model request.", {"url": {"type": "string"}, "audience": {"type": "string"}, "goal": {"type": "string"}}, ["url"]),
        "scope": ("Inspect the exact proposed copy and supported CTA choices BEFORE asking the user to approve a change.", {"review_id": {"type": "string"}}, ["review_id"]),
        "get": ("Read a saved evidence review and exact revision/check metadata.", {"review_id": {"type": "string"}}, ["review_id"]),
        "list": ("List local saved repager reviews for this profile.", {}, []),
        "approve": ("Approve ONE finding and explicit selected hero-copy/CTA preservation contract. Only call after user approval.", {"review_id": {"type": "string"}, "finding_id": {"type": "string"}, "cta_id": {"type": "string"}, "scope_hash": {"type": "string"}, "expected_version": {"type": "integer"}, "preserve_copy": {"type": "boolean"}, "preserve_destination": {"type": "boolean"}}, ["review_id", "finding_id", "cta_id", "scope_hash", "expected_version", "preserve_copy", "preserve_destination"]),
        "generate": ("Generate a bounded layout using host ctx.llm after an approved contract. Original site unchanged; model consent required.", {"review_id": {"type": "string"}, "instruction": {"type": "string"}}, ["review_id"]),
        "remix": ("Create a NEW revision using bounded layout/colors only, with no inference. Requires the current baseline revision/hash. Original approved copy and destination cannot change; fresh checks required.", {"review_id": {"type": "string"}, "base_revision": {"type": "integer"}, "artifact_hash": {"type": "string"}, "from_revision": {"type": "integer"}, "changes": {"type": "object", "properties": {"layout": {"type": "string", "enum": ["stack", "split", "editorial", "spotlight"]}, "alignment": {"type": "string", "enum": ["left", "center"]}, "spacing": {"type": "string", "enum": ["compact", "comfortable"]}, **{k: {"type": "string"} for k in ("background", "foreground", "accent", "button_text")}}, "additionalProperties": False}}, ["review_id", "base_revision", "artifact_hash", "changes"]),
        "decide": ("Record the user's explicit prefer/reject/undecided choice and reason for the current checked artifact. Never invent preference or treat it as deployment permission.", {"review_id": {"type": "string"}, "revision": {"type": "integer"}, "artifact_hash": {"type": "string"}, "verification_signature": {"type": "string"}, "verdict": {"type": "string", "enum": ["prefer", "reject", "undecided"]}, "reason": {"type": "string"}}, ["review_id", "revision", "artifact_hash", "verification_signature", "verdict", "reason"]),
        "verify": ("Run a real isolated browser against the exact current artifact revision, not the original website.", {"review_id": {"type": "string"}}, ["review_id"]),
        "export": ("Create ZIP handoff only for a current verified revision with no failed checks. Returns local path.", {"review_id": {"type": "string"}}, ["review_id"]),
    }
    for action, (description, properties, required) in operations.items():
        def handler(args, _action=action, **_kw):
            try:
                runtime = get_runtime()
                service = runtime.service
                method = {"capture": "create_review", "get": "get_review", "list": "list_reviews", "scope": "preview_scope"}.get(_action, _action)
                if _action in {"capture", "generate", "remix", "verify"}:
                    result = runtime.run_sync(getattr(service, method), admission_review_id=args.get("review_id"), **args)
                else:
                    result = getattr(service, method)(**args)
                key = "reviews" if _action == "list" else "path" if _action == "export" else "scope" if _action == "scope" else "review"
                return json.dumps({key: str(result) if _action == "export" else result})
            except Exception as exc:
                return json.dumps({"error": str(exc)[:1200]})
        name = "repager_" + action
        ctx.register_tool(name=name, toolset="repager", schema={"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False}}, handler=handler)
    from .dev import setup_cli, serve
    ctx.register_cli_command("repager", help="Open the local repager browser workbench", setup_fn=setup_cli, handler_fn=serve)
    ctx.register_skill("workbench", Path(__file__).resolve().parents[1] / "skills" / "workbench" / "SKILL.md")
    def cleanup():
        key = str(profile_home())
        with _LOCK:
            runtime = _RUNTIMES.pop(key, None)
            _CONTEXTS.pop(key, None)
        if runtime:
            runtime.close()
    ctx.on_unload(cleanup)
