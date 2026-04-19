import compileall
import importlib
import pkgutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import backend


def test_backend_compiles():
    backend_dir = Path(backend.__file__).resolve().parent
    assert compileall.compile_dir(
        str(backend_dir),
        quiet=1,
    ), "Python compile check failed for backend package"


def test_backend_imports():
    failures = []
    for module_info in pkgutil.walk_packages(backend.__path__, backend.__name__ + "."):
        module_name = module_info.name
        if module_name.startswith("backend.tests"):
            continue
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            failures.append((module_name, exc))

    assert not failures, "Import failures:\n" + "\n".join(
        f"- {name}: {exc}" for name, exc in failures
    )
