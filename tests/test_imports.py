"""Import integrity audit for career_ops_kr.

Walks every public module under ``career_ops_kr.*`` and ``scripts.*`` and
imports it, asserting no exception is raised. Parametrized so pytest
reports each module individually.

Optional dependencies (textual for TUI, mcp for mcp_server) are handled
gracefully: when the optional package is missing, the test is skipped
rather than failed. All other modules MUST import cleanly.

No network, no file creation, no side effects — the test imports only.
"""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module discovery
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Ensure repo root is importable (so `import scripts.xxx` resolves even
# when the package has no __init__.py).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _iter_package_modules(package_name: str) -> list[str]:
    """Return the fully-qualified module names under ``package_name``."""
    try:
        package = importlib.import_module(package_name)
    except Exception:  # pragma: no cover - surfaced as a failing test elsewhere
        return [package_name]

    modules: list[str] = [package_name]
    if not hasattr(package, "__path__"):
        return modules

    for info in pkgutil.walk_packages(package.__path__, prefix=f"{package_name}."):
        modules.append(info.name)
    return modules


def _iter_script_modules() -> list[str]:
    """Return ``scripts.<stem>`` for every ``scripts/*.py`` file."""
    if not SCRIPTS_DIR.exists():
        return []
    return [
        f"scripts.{p.stem}" for p in sorted(SCRIPTS_DIR.glob("*.py")) if p.name != "__init__.py"
    ]


CAREER_OPS_MODULES = _iter_package_modules("career_ops_kr")
SCRIPT_MODULES = _iter_script_modules()

# Modules that require optional dependencies. If the dep is missing we
# pytest.skip instead of fail.
OPTIONAL_MODULE_DEPS: dict[str, str] = {
    "career_ops_kr.tui.app": "textual",
    "career_ops_kr.tui.screens": "textual",
    "career_ops_kr.tui.screens.calendar": "textual",
    "career_ops_kr.tui.screens.dashboard": "textual",
    "career_ops_kr.tui.screens.job_detail": "textual",
    "career_ops_kr.tui.screens.jobs_list": "textual",
}


# ---------------------------------------------------------------------------
# Parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", CAREER_OPS_MODULES)
def test_career_ops_module_imports(module_name: str) -> None:
    """Every ``career_ops_kr.*`` module imports without error."""
    optional_dep = OPTIONAL_MODULE_DEPS.get(module_name)
    if optional_dep is not None and importlib.util.find_spec(optional_dep) is None:
        pytest.skip(f"optional dependency missing: {optional_dep}")

    # mcp_server has a dependency-free fallback, but still guard the
    # optional ``mcp`` package to avoid false failures on minimal installs.
    if module_name == "career_ops_kr.mcp_server":
        # The module is designed to tolerate missing ``mcp`` — no skip needed.
        pass

    importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", SCRIPT_MODULES)
def test_script_module_imports(module_name: str) -> None:
    """Every ``scripts/*.py`` file imports as a module without executing main."""
    importlib.import_module(module_name)


# ---------------------------------------------------------------------------
# Targeted contract tests — registries and key symbols
# ---------------------------------------------------------------------------


def test_channel_registry_populated() -> None:
    """CHANNEL_REGISTRY exposes at least one channel and all values are BaseChannel subclasses."""
    from career_ops_kr.channels import CHANNEL_REGISTRY, BaseChannel

    assert CHANNEL_REGISTRY, "CHANNEL_REGISTRY is empty"
    for name, cls in CHANNEL_REGISTRY.items():
        assert isinstance(name, str) and name, f"invalid channel name: {name!r}"
        assert isinstance(cls, type), f"{name} registry value is not a class"
        assert issubclass(cls, BaseChannel), f"{name} -> {cls!r} is not a BaseChannel subclass"


def test_channel_classes_importable_directly() -> None:
    """Every class in CHANNEL_REGISTRY can be re-imported from its source module."""
    from career_ops_kr.channels import CHANNEL_REGISTRY

    for name, cls in CHANNEL_REGISTRY.items():
        mod = importlib.import_module(cls.__module__)
        assert getattr(mod, cls.__name__) is cls, (
            f"{name}: {cls.__module__}.{cls.__name__} does not round-trip"
        )


def test_preset_loader_importable() -> None:
    """PresetLoader and friends import cleanly from career_ops_kr.presets."""
    from career_ops_kr.presets import PresetLoader, PresetNotFound, list_presets

    assert callable(list_presets)
    assert isinstance(PresetLoader, type)
    assert issubclass(PresetNotFound, Exception)


def test_mcp_server_importable() -> None:
    """career_ops_kr.mcp_server imports (falls back to minimal JSON-RPC if mcp missing)."""
    mod = importlib.import_module("career_ops_kr.mcp_server")
    assert mod is not None


def test_tui_guarded_import() -> None:
    """career_ops_kr.tui always imports and exposes TEXTUAL_AVAILABLE."""
    mod = importlib.import_module("career_ops_kr.tui")
    assert hasattr(mod, "TEXTUAL_AVAILABLE")
    # When textual is installed the app module must import; when not, the
    # package must still be importable with TEXTUAL_AVAILABLE=False.
    if importlib.util.find_spec("textual") is not None:
        assert mod.TEXTUAL_AVAILABLE is True
        importlib.import_module("career_ops_kr.tui.app")
    else:  # pragma: no cover - env-dependent
        assert mod.TEXTUAL_AVAILABLE is False
