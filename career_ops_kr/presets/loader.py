"""Preset loader module for career-ops-kr.

Loads domain preset YAML bundles from ``<repo_root>/presets/`` and materializes
them into the ``config/*.yml`` user layer on ``career-ops init --preset <id>``.

A preset contains:
    - qualifier_rules (negative_patterns, positive_patterns, numeric_rules)
    - scoring_weights (dimensions dict with decimal weights summing to 1.00)
    - portals (list of portal definitions)
    - archetypes (domain archetype definitions)
    - profile_template (defaults for config/profile.yml and modes/_profile.md)

The loader splits the preset into the 4 target user-layer files:
    config/qualifier_rules.yml
    config/scoring_weights.yml
    config/portals.yml
    config/profile.yml  (scaffolded — still requires manual fill-in)

It also scaffolds ``modes/_profile.md`` from the preset's ``profile_template``.

All file I/O is UTF-8 explicit, uses ``pathlib.Path`` throughout, and refuses
to overwrite existing files unless ``overwrite=True``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────

REQUIRED_DIMENSIONS: tuple[str, ...] = (
    "role_fit",
    "eligibility_match",
    "compensation",
    "location",
    "growth",
    "brand",
    "portfolio_usefulness",
    "schedule_conflict",
    "deadline_urgency",
    "hitl_discretion",
)

WEIGHT_SUM_TOLERANCE = 0.01


# ────────────────────────────────────────────────────────────────────────────
# Exceptions
# ────────────────────────────────────────────────────────────────────────────


class PresetNotFound(Exception):
    """Raised when a requested preset_id cannot be resolved."""


class PresetValidationError(Exception):
    """Raised when a preset file fails pydantic validation."""


# ────────────────────────────────────────────────────────────────────────────
# Pydantic schema
# ────────────────────────────────────────────────────────────────────────────


class QualifierPattern(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    pattern: str
    weight: int
    reason: str
    action: str | None = None


class NumericRules(BaseModel):
    model_config = ConfigDict(extra="allow")
    min_semester_completed: int | None = None
    max_gpa_required: float | None = None
    max_years_experience_required: int | None = None


class QualifierRules(BaseModel):
    model_config = ConfigDict(extra="allow")
    negative_patterns: list[QualifierPattern] = Field(default_factory=list)
    positive_patterns: list[QualifierPattern] = Field(default_factory=list)
    numeric_rules: NumericRules | dict[str, Any] = Field(default_factory=dict)


class ScoringWeights(BaseModel):
    model_config = ConfigDict(extra="allow")
    dimensions: dict[str, float]
    modifiers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dimensions")
    @classmethod
    def _check_dimensions(cls, v: dict[str, float]) -> dict[str, float]:
        missing = [d for d in REQUIRED_DIMENSIONS if d not in v]
        if missing:
            raise ValueError(f"scoring_weights.dimensions missing keys: {missing}")
        total = sum(v.values())
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(
                f"scoring_weights.dimensions sum to {total:.4f}, expected 1.00 "
                f"(tolerance ±{WEIGHT_SUM_TOLERANCE})"
            )
        return v


class PortalEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    url: str
    backend: str
    tier: int
    login_required: bool = False
    enabled: bool = True
    filters: dict[str, list[str]] = Field(default_factory=dict)


class ProfileTemplate(BaseModel):
    model_config = ConfigDict(extra="allow")
    target_industries: list[str] = Field(default_factory=list)
    default_strengths: list[str] = Field(default_factory=list)
    default_constraints: list[str] = Field(default_factory=list)
    suggested_certifications: list[str] = Field(default_factory=list)


class Preset(BaseModel):
    model_config = ConfigDict(extra="allow")
    preset_id: str
    label_ko: str
    label_en: str
    description: str
    target_audience: str | None = None
    qualifier_rules: QualifierRules
    scoring_weights: ScoringWeights
    portals: list[PortalEntry]
    archetypes: dict[str, Any] = Field(default_factory=dict)
    profile_template: ProfileTemplate


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _default_presets_dir() -> Path:
    """Return the default ``<repo_root>/presets/`` directory."""
    return Path(__file__).resolve().parents[2] / "presets"


def _yaml_dump(data: dict[str, Any], path: Path) -> None:
    """Dump ``data`` to ``path`` as UTF-8 YAML with Korean characters preserved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
        )


def _yaml_load(path: Path) -> dict[str, Any]:
    """Load a UTF-8 YAML file to a dict. Returns ``{}`` on empty file."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise PresetValidationError(f"{path}: top-level YAML must be a mapping")
    return data


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────


def list_presets(presets_dir: Path | None = None) -> list[dict[str, str]]:
    """Convenience wrapper around ``PresetLoader.list_available``."""
    return PresetLoader(presets_dir).list_available()


class PresetLoader:
    """Loads and applies domain preset bundles."""

    def __init__(self, presets_dir: Path | None = None) -> None:
        self.presets_dir: Path = (
            Path(presets_dir) if presets_dir is not None else _default_presets_dir()
        )

    # ---- discovery ---------------------------------------------------------

    def list_available(self) -> list[dict[str, str]]:
        """Scan ``presets_dir`` for ``*.yml`` files and return metadata.

        Returns a list of dicts with keys: ``preset_id``, ``label_ko``,
        ``label_en``, ``description``. Invalid files are logged and skipped.
        """
        if not self.presets_dir.exists():
            logger.warning("presets directory not found: %s", self.presets_dir)
            return []

        results: list[dict[str, str]] = []
        for yml in sorted(self.presets_dir.glob("*.yml")):
            try:
                raw = _yaml_load(yml)
                results.append(
                    {
                        "preset_id": str(raw.get("preset_id", yml.stem)),
                        "label_ko": str(raw.get("label_ko", "")),
                        "label_en": str(raw.get("label_en", "")),
                        "description": str(raw.get("description", "")).strip(),
                        "path": str(yml),
                    }
                )
            except Exception as exc:
                logger.warning("skipping invalid preset %s: %s", yml, exc)
        return results

    # ---- load + validate ---------------------------------------------------

    def _path_for(self, preset_id: str) -> Path:
        candidate = self.presets_dir / f"{preset_id}.yml"
        if not candidate.exists():
            raise PresetNotFound(f"preset '{preset_id}' not found in {self.presets_dir}")
        return candidate

    def load(self, preset_id: str) -> dict[str, Any]:
        """Load a preset by id and return the validated raw dict."""
        path = self._path_for(preset_id)
        raw = _yaml_load(path)
        try:
            Preset.model_validate(raw)
        except ValidationError as exc:
            raise PresetValidationError(f"preset '{preset_id}' failed validation:\n{exc}") from exc
        return raw

    def validate(self, preset_id: str) -> list[str]:
        """Return a list of validation error messages (empty if valid)."""
        try:
            self.load(preset_id)
        except PresetNotFound as exc:
            return [str(exc)]
        except PresetValidationError as exc:
            return [str(exc)]
        return []

    # ---- materialize into config/ -----------------------------------------

    def apply_to(
        self,
        preset_id: str,
        target_config_dir: Path,
        overwrite: bool = False,
    ) -> dict[str, Path]:
        """Split the preset into ``config/*.yml`` files under ``target_config_dir``.

        Returns a dict mapping logical file names to their resolved paths.
        If ``overwrite=False`` and any target already exists, it is skipped
        (still present in the returned dict so callers know its location).
        Also scaffolds ``modes/_profile.md`` next to the config directory
        (sibling under the repo root).
        """
        preset = self.load(preset_id)
        target = Path(target_config_dir)
        target.mkdir(parents=True, exist_ok=True)

        created: dict[str, Path] = {
            "qualifier_rules": target / "qualifier_rules.yml",
            "scoring_weights": target / "scoring_weights.yml",
            "portals": target / "portals.yml",
            "profile": target / "profile.yml",
        }

        self._write_qualifier_rules(preset, created["qualifier_rules"], overwrite)
        self._write_scoring_weights(preset, created["scoring_weights"], overwrite)
        self._write_portals(preset, created["portals"], overwrite)
        self._write_profile(preset, created["profile"], overwrite)

        # Scaffold modes/_profile.md next to target_config_dir's parent
        modes_dir = target.parent / "modes"
        profile_md = modes_dir / "_profile.md"
        self._scaffold_profile_md(preset, profile_md, overwrite)
        created["profile_md"] = profile_md

        return created

    # ---- diff --------------------------------------------------------------

    def diff(self, preset_id: str, current_config_dir: Path) -> dict[str, Any]:
        """Compare preset defaults against the user's current config.

        Returns a dict with one entry per target file: ``{"status": ...,
        "would_change": [...]}``. Useful for a dry-run before ``apply_to``.
        """
        preset = self.load(preset_id)
        current = Path(current_config_dir)
        report: dict[str, Any] = {}

        targets = {
            "qualifier_rules.yml": self._build_qualifier_rules(preset),
            "scoring_weights.yml": self._build_scoring_weights(preset),
            "portals.yml": self._build_portals(preset),
            "profile.yml": self._build_profile(preset),
        }
        for name, new_data in targets.items():
            target_path = current / name
            if not target_path.exists():
                report[name] = {"status": "missing", "would_create": True}
                continue
            try:
                existing = _yaml_load(target_path)
            except Exception as exc:
                report[name] = {"status": "unreadable", "error": str(exc)}
                continue
            report[name] = {
                "status": "exists",
                "identical": existing == new_data,
                "existing_keys": sorted(existing.keys()),
                "preset_keys": sorted(new_data.keys()),
            }
        return report

    # ---- internal builders ------------------------------------------------

    @staticmethod
    def _build_qualifier_rules(preset: dict[str, Any]) -> dict[str, Any]:
        qr = preset.get("qualifier_rules", {})
        return {
            "negative_patterns": qr.get("negative_patterns", []),
            "positive_patterns": qr.get("positive_patterns", []),
            "numeric_rules": qr.get("numeric_rules", {}),
        }

    @staticmethod
    def _build_scoring_weights(preset: dict[str, Any]) -> dict[str, Any]:
        """Convert decimal dimensions dict to integer list form used by engine."""
        sw = preset.get("scoring_weights", {})
        dims = sw.get("dimensions", {})
        modifiers = sw.get("modifiers", {}) or {}
        out_dims: list[dict[str, Any]] = []
        total_int = 0
        for key in REQUIRED_DIMENSIONS:
            decimal = float(dims.get(key, 0))
            int_weight = round(decimal * 100)
            total_int += int_weight
            out_dims.append(
                {
                    "key": key,
                    "weight": int_weight,
                    "modifiers": modifiers.get(key, []),
                }
            )
        return {
            "grade_cuts": {"A": 85, "B": 70, "C": 55, "D": 40, "E": 25, "F": 0},
            "dimensions": out_dims,
            "sum_check": total_int,
        }

    @staticmethod
    def _build_portals(preset: dict[str, Any]) -> dict[str, Any]:
        return {"portals": preset.get("portals", [])}

    @staticmethod
    def _build_profile(preset: dict[str, Any]) -> dict[str, Any]:
        template = preset.get("profile_template", {}) or {}
        return {
            "preset": preset.get("preset_id"),
            "target_industries": template.get("target_industries", []),
            "strengths": template.get("default_strengths", []),
            "constraints": template.get("default_constraints", []),
            "certifications_planned": [
                {"name": c} for c in template.get("suggested_certifications", [])
            ],
        }

    # ---- internal writers -------------------------------------------------

    def _write_qualifier_rules(self, preset: dict[str, Any], path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            logger.info("skip existing %s (overwrite=False)", path)
            return
        _yaml_dump(self._build_qualifier_rules(preset), path)

    def _write_scoring_weights(self, preset: dict[str, Any], path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            logger.info("skip existing %s (overwrite=False)", path)
            return
        _yaml_dump(self._build_scoring_weights(preset), path)

    def _write_portals(self, preset: dict[str, Any], path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            logger.info("skip existing %s (overwrite=False)", path)
            return
        _yaml_dump(self._build_portals(preset), path)

    def _write_profile(self, preset: dict[str, Any], path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            logger.info("skip existing %s (overwrite=False)", path)
            return
        _yaml_dump(self._build_profile(preset), path)

    @staticmethod
    def _scaffold_profile_md(preset: dict[str, Any], path: Path, overwrite: bool) -> None:
        if path.exists() and not overwrite:
            logger.info("skip existing %s (overwrite=False)", path)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tpl = preset.get("profile_template", {}) or {}
        archetypes = preset.get("archetypes", {}) or {}

        lines: list[str] = [
            f"# _profile.md — {preset.get('label_ko', preset.get('preset_id', ''))}",
            "",
            f"> Preset: `{preset.get('preset_id')}` — {preset.get('description', '').strip()}",
            "",
            "## Target Industries",
            "",
        ]
        lines.extend(f"- {item}" for item in tpl.get("target_industries", []))
        lines.extend(["", "## Strengths", ""])
        lines.extend(f"- {item}" for item in tpl.get("default_strengths", []))
        lines.extend(["", "## Constraints", ""])
        lines.extend(f"- {item}" for item in tpl.get("default_constraints", []))
        lines.extend(["", "## Archetypes", ""])
        for key, val in archetypes.items():
            label = val.get("label", key) if isinstance(val, dict) else key
            lines.append(f"- **{key}** — {label}")
        lines.extend(["", "## Suggested Certifications", ""])
        lines.extend(f"- {item}" for item in tpl.get("suggested_certifications", []))
        lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
