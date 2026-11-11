"""Native dashboard loads this file by absolute path; no sys.path changes."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "bootstrap.py"
_spec = importlib.util.spec_from_file_location("_repager_bootstrap", _path)
if _spec is None or _spec.loader is None:
    raise ImportError("Cannot load repager bootstrap")
_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_loader)
_runtime = _loader.runtime_module()
_api = __import__(_runtime.__package__ + ".api", fromlist=["create_router"])
router = _api.create_router()
