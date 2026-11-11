"""Load this plugin's local package without changing sys.path or shadowing another repager."""
import hashlib
import importlib
import importlib.util
import sys
import threading
from pathlib import Path

_LOCK = threading.RLock()

def runtime_module():
    root = Path(__file__).resolve().parent / "repager"
    name = "_hermes_repager_" + hashlib.sha256(str(root).encode()).hexdigest()[:16]
    with _LOCK:
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, root / "__init__.py", submodule_search_locations=[str(root)])
            if spec is None or spec.loader is None:
                raise ImportError("Cannot load the local repager package")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(name, None)
                raise
        return importlib.import_module(name + ".runtime")
