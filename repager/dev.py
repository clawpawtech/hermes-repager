"""Explicit local browser shell, reached through the host's registered CLI command."""
import os
import secrets
from pathlib import Path


def setup_cli(parser):
    parser.add_argument("--port", type=int, default=9197)
    parser.add_argument("--doctor", action="store_true", help="Print non-secret browser configuration without calling a model")
    parser.add_argument("--probe-url", help="With --doctor: run a real public capture; no model call")
    parser.add_argument("--token-file", type=Path, help="New trusted local file for the generated access token; never committed")


def serve(args):
    from .api import create_dev_app
    from .runtime import get_runtime
    if args.doctor:
        import json
        browser = get_runtime().service.browser
        scratch = os.getenv("TMPDIR", "")
        print(json.dumps({"chromium_path": browser.executable_path, "allow_no_sandbox": browser.allow_no_sandbox, "timeout": browser.timeout, "scratch": scratch, "socket_path_warning": len(scratch.encode()) > 50}, indent=2))
        if args.probe_url:
            if len(scratch.encode()) > 50:
                raise ValueError("Chromium's Unix socket path may exceed the OS limit. Use a shorter trusted Hermes scratch/profile path; do not disable the browser network policy.")
            import tempfile
            from concurrent.futures import ThreadPoolExecutor
            with tempfile.TemporaryDirectory(prefix="repager-doctor-") as output:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(browser.capture, args.probe_url, Path(output)).result()
                    print(json.dumps({"captured_title": result["title"], "viewports": [v["name"] for v in result["viewports"]]}))
        return
    if args.token_file is None:
        raise ValueError("--token-file is required to open the development server")
    token = secrets.token_urlsafe(32)
    args.token_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token)
    app = create_dev_app(get_runtime, token=token)
    print(f"Local repager: http://127.0.0.1:{args.port}; access token saved to {args.token_file}. No public listener.", flush=True)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
