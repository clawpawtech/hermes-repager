"""Native Hermes entry point. Registration is lazy: no browser, state directory or model call."""
import importlib.util
from pathlib import Path

def register(ctx):
    path = Path(__file__).resolve().parent / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("_repager_bootstrap", path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load repager bootstrap")
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    loader.runtime_module().register_plugin(ctx)
