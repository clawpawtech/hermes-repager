"""Authenticated host API + local-only development app; no I/O at import."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from .runtime import get_runtime, check_model_policy
from .service import ServiceError

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

class CaptureInput(Input):
    url: str = Field(min_length=1, max_length=2000)
    audience: str = Field(default="", max_length=400)
    goal: str = Field(default="", max_length=400)

class ApproveInput(Input):
    finding_id: str = Field(min_length=1, max_length=200)
    preserve_copy: StrictBool
    preserve_destination: StrictBool
    cta_id: str = Field(min_length=1, max_length=200)
    scope_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    expected_version: StrictInt = Field(ge=1)

class GenerateInput(Input):
    instruction: str = Field(default="", max_length=500)

class DesignChanges(Input):
    layout: Literal['stack', 'split', 'editorial', 'spotlight'] | None = None
    alignment: Literal['left', 'center'] | None = None
    spacing: Literal['compact', 'comfortable'] | None = None
    background: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    foreground: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    accent: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    button_text: str | None = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')

class RemixInput(Input):
    base_revision: StrictInt = Field(ge=1, le=50)
    artifact_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    changes: DesignChanges
    from_revision: StrictInt | None = Field(default=None, ge=1, le=50)

class DecisionInput(Input):
    verification_signature: str = Field(pattern=r'^[0-9a-f]{64}$')
    revision: StrictInt = Field(ge=1, le=50)
    artifact_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    verdict: Literal['prefer', 'reject', 'undecided']
    reason: str = Field(min_length=1, max_length=500)

class EmptyInput(Input):
    pass


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ServiceError as exc:
        raise HTTPException(409, str(exc)[:1200]) from None
    except ValueError as exc:
        code = 404 if str(exc).lower().startswith(("unknown review", "unknown job")) else 400
        raise HTTPException(code, str(exc)[:1200]) from None


async def same_origin(request: Request):
    if request.method not in {"GET", "HEAD"}:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            raise HTTPException(415, "Use application/json for changes.")
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            raise HTTPException(403, "Cross-origin changes are not allowed.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site changes are not allowed.")
    # Keep model/context requests bounded even if Content-Length is absent.
    if request.method not in {"GET", "HEAD"} and len(await request.body()) > 10000:
        raise HTTPException(413, "repager request is too large.")


def artifact_path(service, rid, filename):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", filename):
        raise ValueError("Invalid artifact basename")
    record = service.get_review(rid)
    allowed = {v["screenshot"] for v in (record.get("source") or {}).get("viewports", [])}
    allowed.update(r["html_file"] for r in record.get("revisions", []))
    allowed.update(v["screenshot"] for v in (record.get("verification") or {}).get("viewports", []))
    allowed.update(name for e in record.get('review_events', []) if e['kind'] == 'verification' for name in e['payload']['image_hashes'])
    if filename not in allowed:
        raise ValueError("Artifact is not in this review's controlled manifest")
    root = service.store.run_dir(rid).resolve()
    path = root / filename
    if path.is_symlink() or path.resolve().parent != root or not path.is_file():
        raise ValueError("Artifact is missing or not a regular local file")
    return path


def create_router(runtime_provider: Callable = get_runtime):
    router = APIRouter(dependencies=[Depends(same_origin)])

    def runtime():
        return _call(runtime_provider)

    @router.get("/health")
    def health():
        rt = runtime()
        browser = rt.service.browser
        executable = getattr(browser, "executable_path", None)
        import shutil
        browser_ready = bool(shutil.which("node") and (Path(executable).is_file() if executable else False))
        reason = None
        model_ready = rt.service.llm is not None
        ctx = getattr(rt.service.llm, "ctx", None)
        if ctx:
            try:
                if not ctx.get_config("allow_model_calls", False):
                    raise ServiceError("Model-data consent is off in repager settings.")
                from hermes_cli.config import load_config_readonly
                check_model_policy(load_config_readonly() or {})
            except ServiceError as exc:
                model_ready, reason = False, str(exc)
        return {"status": "ok", "model_ready": model_ready, "browser_ready": browser_ready,
                "model_note": reason, "note": "Readiness is a configuration check, not proof of quota or a successful browser/model call."}

    @router.get("/reviews")
    def list_reviews():
        return {"reviews": _call(runtime().service.list_reviews)}

    @router.get("/reviews/{rid}")
    def get_review(rid: str):
        return {"review": _call(runtime().service.get_review, rid)}

    @router.get("/reviews/{rid}/scope")
    def preview_scope(rid: str):
        return {"scope": _call(runtime().service.preview_scope, rid)}

    @router.post("/reviews", status_code=202)
    def capture(body: CaptureInput):
        rt = runtime()
        return {"job": _call(rt.submit, rt.service.create_review, **body.model_dump())}

    @router.post("/reviews/{rid}/approve")
    def approve(rid: str, body: ApproveInput):
        return {"review": _call(runtime().service.approve, rid, **body.model_dump())}

    @router.post("/reviews/{rid}/generate", status_code=202)
    def generate(rid: str, body: GenerateInput):
        rt = runtime()
        _call(rt.service.get_review, rid)
        return {"job": _call(rt.submit, rt.service.generate, rid, review_id=rid, **body.model_dump())}

    @router.post("/reviews/{rid}/verify", status_code=202)
    def verify(rid: str, body: EmptyInput):
        rt = runtime()
        _call(rt.service.get_review, rid)
        return {"job": _call(rt.submit, rt.service.verify, rid, review_id=rid)}

    @router.post('/reviews/{rid}/remix', status_code=202)
    def remix(rid: str, body: RemixInput):
        rt = runtime()
        _call(rt.service.get_review, rid)
        return {'job': _call(rt.submit, rt.service.remix, rid, review_id=rid, **body.model_dump(exclude_unset=True))}

    @router.post('/reviews/{rid}/decision')
    def decision(rid: str, body: DecisionInput):
        return {'review': _call(runtime().service.decide, rid, **body.model_dump())}

    @router.get('/jobs')
    def jobs():
        return {'jobs': _call(runtime().jobs)}

    @router.get("/jobs/{jid}")
    def get_job(jid: str):
        return {"job": _call(runtime().job, jid)}

    @router.get("/reviews/{rid}/artifacts/{filename}")
    def artifact(rid: str, filename: str):
        path = _call(artifact_path, runtime().service, rid, filename)
        is_html = path.suffix == ".html"
        media = "text/html" if is_html else "image/png"
        data = _call(runtime().service.read_artifact, rid, filename)
        return Response(data, media_type=media, headers={
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'",
        })

    @router.get('/reviews/{rid}/report')
    def report(rid: str):
        data = _call(runtime().service.report, rid)
        return Response(data, media_type='text/html', headers={
            'Content-Disposition': f'attachment; filename="repager-{rid}-review.html"',
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'"})

    @router.get("/reviews/{rid}/export")
    def export(rid: str):
        service = runtime().service
        with service.store.record_lock(rid):
            path = _call(service.export, rid)
            payload = path.read_bytes()
        return Response(payload, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="repager-{rid}.zip"', "Cache-Control": "no-store"})

    return router


def create_dev_app(runtime_provider: Callable, *, token: str):
    """Explicit local development only. Token auth is required, including binary artifacts."""
    if not token or len(token) < 24:
        raise ValueError("Development token must have at least 24 characters")
    import secrets
    app = FastAPI(title="repager local workbench", docs_url=None, redoc_url=None, openapi_url=None)
    assets = Path(__file__).resolve().parents[1] / "dashboard"

    @app.middleware("http")
    async def protect(request, call_next):
        host = (request.url.hostname or "").lower()
        if host not in {"127.0.0.1", "localhost", "[::1]", "::1", "testserver"}:
            return Response("Unrecognised development host", status_code=403)
        cookie = request.cookies.get("repager_dev", "")
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        if request.url.path.startswith("/api/") and not (secrets.compare_digest(cookie, token) or secrets.compare_digest(supplied, token)):
            return Response("Authentication required", status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(create_router(runtime_provider), prefix="/api/plugins/repager")

    @app.post("/dev/login")
    async def login(request: Request):
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
            raise HTTPException(403, "Cross-origin login refused")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site login refused")
        if len(await request.body()) > 1000:
            raise HTTPException(413, "Request too large")
        try:
            candidate = (await request.json()).get("token", "")
        except Exception:
            candidate = ""
        if not isinstance(candidate, str) or not secrets.compare_digest(candidate, token):
            raise HTTPException(401, "Incorrect development token")
        response = Response(status_code=204)
        response.set_cookie("repager_dev", token, httponly=True, samesite="strict", path="/", max_age=28800)
        return response

    @app.get("/")
    def index():
        return FileResponse(assets / "index.html")

    @app.get("/canvas.js")
    def canvas():
        return FileResponse(assets / "dist" / "index.js", media_type="text/javascript")

    return app
