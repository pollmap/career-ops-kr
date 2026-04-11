"""career-ops-kr preset system.

Preset bundles are YAML files that materialize into ``config/*.yml`` on
``career-ops init --preset <id>``. A preset is a self-contained domain bundle:
qualifier rules, scoring weights, portals, archetypes, profile template.
"""

from __future__ import annotations

from career_ops_kr.presets.loader import PresetLoader, PresetNotFound, list_presets

__all__ = ["PresetLoader", "PresetNotFound", "__version__", "list_presets"]

__version__ = "0.1.0"
