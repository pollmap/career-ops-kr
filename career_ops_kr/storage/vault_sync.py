"""Obsidian Vault sync for career-ops-kr.

Writes one markdown note per :class:`JobRecord` into a bucket folder under
the vault root (default: ``~/obsidian-vault/career-ops/``).  Each note has
YAML frontmatter so Obsidian Dataview / Bases can query the corpus.

Graceful fallback: if the configured vault root does not exist we fall back
to ``<repo>/data/vault_fallback/`` so the pipeline never fails on a missing
Obsidian install.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)


VAULT_FOLDERS: tuple[str, ...] = (
    "0-inbox",
    "1-eligible",
    "2-watchlist",
    "3-rejected",
    "4-applied",
)

_SAFE_CHAR_RE = re.compile(r"[^0-9A-Za-z가-힣_\- ]+")


def _default_vault_root() -> Path:
    env = os.environ.get("CAREER_OPS_VAULT")
    if env:
        return Path(env).expanduser()
    return Path.home() / "obsidian-vault" / "career-ops"


def _repo_fallback() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "vault_fallback"


def _sanitize(name: str, max_len: int = 80) -> str:
    cleaned = _SAFE_CHAR_RE.sub(" ", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_len] or "untitled"


def _iso(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return value.isoformat()


def _yaml_escape(value: Any) -> str:
    if value is None:
        return '""'
    text = str(value)
    if any(ch in text for ch in ':"\n') or text.strip() != text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        return f'"{escaped}"'
    return text


class VaultSync:
    """Write JobRecords to Obsidian markdown notes."""

    def __init__(self, vault_root: Path | str | None = None) -> None:
        requested = Path(vault_root).expanduser() if vault_root else _default_vault_root()
        self.vault_root = requested
        try:
            self.vault_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "VaultSync: could not create vault root %s (%s) — using fallback",
                requested,
                exc,
            )
            self.vault_root = _repo_fallback()
            self.vault_root.mkdir(parents=True, exist_ok=True)

        for folder in VAULT_FOLDERS:
            (self.vault_root / folder).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def _folder_path(self, folder: str) -> Path:
        if folder not in VAULT_FOLDERS:
            logger.warning("VaultSync: unknown folder %r — forcing 0-inbox", folder)
            folder = "0-inbox"
        return self.vault_root / folder

    def _note_path(self, folder: str, job: JobRecord) -> Path:
        base = _sanitize(f"{job.org}-{job.title}")
        filename = f"{job.id}_{base}.md"
        return self._folder_path(folder) / filename

    def _find_note(self, job_id: str) -> tuple[str, Path] | None:
        for folder in VAULT_FOLDERS:
            for path in self._folder_path(folder).glob(f"{job_id}_*.md"):
                return folder, path
        return None

    # ------------------------------------------------------------------
    # Upsert note
    # ------------------------------------------------------------------

    def upsert_note(
        self,
        job: JobRecord,
        folder: str = "0-inbox",
        fit: dict[str, Any] | None = None,
    ) -> Path:
        path = self._note_path(folder, job)
        content = self._render_markdown(job, folder, fit or {})
        path.write_text(content, encoding="utf-8")
        logger.debug("VaultSync: wrote %s", path)
        return path

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_markdown(self, job: JobRecord, folder: str, fit: dict[str, Any]) -> str:
        status = folder.split("-", 1)[-1] if "-" in folder else folder
        eligible = fit.get("eligible")
        eligible_str = "true" if eligible is True else "false" if eligible is False else ""

        frontmatter_lines = [
            "---",
            f"id: {_yaml_escape(job.id)}",
            f"org: {_yaml_escape(job.org)}",
            f"title: {_yaml_escape(job.title)}",
            f"archetype: {_yaml_escape(job.archetype or '')}",
            f"deadline: {_yaml_escape(_iso(job.deadline))}",
            f"posted_at: {_yaml_escape(_iso(job.posted_at))}",
            f"location: {_yaml_escape(job.location or '')}",
            f"eligible: {_yaml_escape(eligible_str)}",
            f"fit_grade: {_yaml_escape(fit.get('grade', ''))}",
            f"fit_score: {_yaml_escape(fit.get('score', ''))}",
            f"legitimacy_tier: {_yaml_escape(job.legitimacy_tier)}",
            f"source_url: {_yaml_escape(str(job.source_url))}",
            f"source_channel: {_yaml_escape(job.source_channel)}",
            f"source_tier: {job.source_tier}",
            f"scanned_at: {_yaml_escape(_iso(job.scanned_at))}",
            f"status: {_yaml_escape(status)}",
            "tags: [career-ops-kr, " + job.source_channel + "]",
            "---",
            "",
        ]

        body_lines = [
            f"# {job.title}",
            "",
            f"**조직**: {job.org}",
            f"**URL**: {job.source_url}",
            f"**Legitimacy**: {job.legitimacy_tier}",
            f"**Archetype**: {job.archetype or '미분류'}",
            f"**Deadline**: {_iso(job.deadline) or '미정'}",
            "",
            "## Description",
            "",
            job.description or "_설명 없음_",
            "",
            "## Action Items",
            "",
            "- [ ] 공고 원문 정독",
            "- [ ] 자격요건 체크",
            "- [ ] 이력서 맞춤화",
            "- [ ] 지원 여부 결정 (HITL G5)",
            "",
        ]
        if job.fetch_errors:
            body_lines.extend(["## Fetch Errors", ""])
            body_lines.extend(f"- {e}" for e in job.fetch_errors)
            body_lines.append("")

        return "\n".join(frontmatter_lines + body_lines)

    # ------------------------------------------------------------------
    # Move / list
    # ------------------------------------------------------------------

    def move_note(self, job_id: str, from_folder: str, to_folder: str) -> Path | None:
        src_folder = self._folder_path(from_folder)
        dst_folder = self._folder_path(to_folder)
        for path in src_folder.glob(f"{job_id}_*.md"):
            target = dst_folder / path.name
            path.replace(target)
            logger.info("VaultSync: moved %s -> %s", path, target)
            return target
        logger.warning("VaultSync: move_note failed — %s not in %s", job_id, from_folder)
        return None

    def list_notes(self, folder: str) -> list[Path]:
        return sorted(self._folder_path(folder).glob("*.md"))

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------

    def write_index(self) -> Path:
        lines: list[str] = [
            "# career-ops-kr — Job Index",
            "",
            f"_생성: {datetime.now().isoformat(timespec='seconds')}_",
            "",
        ]
        for folder in VAULT_FOLDERS:
            notes = self.list_notes(folder)
            lines.append(f"## {folder} ({len(notes)})")
            lines.append("")
            if not notes:
                lines.append("_비어 있음_")
                lines.append("")
                continue
            lines.append("| 파일 | 조직 | 제목 |")
            lines.append("|------|------|------|")
            for path in notes:
                meta = self._read_frontmatter(path)
                lines.append(
                    f"| [[{path.stem}]] | {meta.get('org', '')} | {meta.get('title', '')} |"
                )
            lines.append("")
        index_path = self.vault_root / "_index.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
        return index_path

    @staticmethod
    def _read_frontmatter(path: Path) -> dict[str, str]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}
        if not text.startswith("---"):
            return {}
        end = text.find("\n---", 3)
        if end == -1:
            return {}
        raw = text[3:end].strip().splitlines()
        meta: dict[str, str] = {}
        for line in raw:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
        return meta
