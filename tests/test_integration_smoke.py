"""End-to-end integration smoke test for career-ops-kr.

Exercises the full pipeline with REAL classes — no mocks, no network:

    preset  →  archetype  →  qualifier  →  fit score  →  sqlite upsert
            →  query      →  vault note  →  ics export →  state move

Invariants enforced:
    * UTF-8 file I/O, pathlib.Path only
    * No fabricated portal data — ONE in-memory sample JD (marked as such)
    * No network calls
    * Idempotent (safe to run repeatedly)
    * Must complete in < 30 seconds
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from career_ops_kr.archetype import Archetype, ArchetypeClassifier
from career_ops_kr.calendar import CalendarExporter
from career_ops_kr.channels.base import JobRecord
from career_ops_kr.presets import PresetLoader
from career_ops_kr.qualifier import QualifierEngine, Verdict
from career_ops_kr.scorer import FitGrade, FitScorer
from career_ops_kr.storage import SQLiteStore, VaultSync

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PRESETS_DIR = REPO_ROOT / "presets"
ARCHETYPES_YML = REPO_ROOT / "config" / "archetypes.yml"

# Sample JD for smoke testing — plausible structure, not copied from a real posting.
# This is an IN-MEMORY sample used only to exercise the pipeline; it is NOT
# fabricated portal data and is NEVER written to the real data store.
SAMPLE_JD_TITLE = "블록체인부 체험형 인턴 모집"
SAMPLE_JD_ORG = "신한투자증권"
SAMPLE_JD_TEXT = """
[신한투자증권] 블록체인부 체험형 인턴 모집

신한투자증권 블록체인부에서 체험형 인턴을 모집합니다.
- 업무: 디지털자산 관련 리서치, STO/토큰증권 프로젝트 지원, API 연동 검증,
        스마트컨트랙트 기본 분석, Python 데이터 파이프라인 보조
- 자격: 4년제 재학생 또는 휴학생 가능, 학력무관 전공무관
- 기간: 3개월 (2026.05~07)
- 근무지: 서울 여의도
- 급여: 월 210만원
- 우대사항: Python 경험, 스마트컨트랙트 이해, 블록체인 기본 지식, SQL/데이터 분석

지원 마감: 2026-05-15
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_job_record() -> JobRecord:
    """Build a JobRecord from the in-memory sample JD.

    Marked explicitly as an in-memory smoke-test sample — not portal data.
    """
    url = "https://careers.shinhansec.com/smoke/blockchain-intern-2026"
    return JobRecord(
        id="smoke000000000a1",  # stable 16-char id for smoke test
        source_url=url,
        source_channel="smoke_test",
        source_tier=1,
        org=SAMPLE_JD_ORG,
        title=SAMPLE_JD_TITLE,
        archetype=None,  # classifier fills this in
        deadline=date(2026, 5, 15),
        posted_at=date(2026, 4, 1),
        location="서울 여의도",
        description=SAMPLE_JD_TEXT,
        legitimacy_tier="T1",
        scanned_at=datetime(2026, 4, 11, 9, 0, 0),
        fetch_errors=[],
    )


class _FitAdapter:
    """Adapter: expose ScoreBreakdown to SQLiteStore's expected shape."""

    def __init__(self, grade: str, score: float, eligible: bool) -> None:
        self.grade = grade
        self.score = score
        self.eligible = eligible


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_end_to_end_pipeline(tmp_path: Path, sample_job_record: JobRecord) -> None:
    """Full pipeline smoke: preset → classify → qualify → score → persist → export."""

    # Defensive skip if the repo's baseline config files vanished.
    if not (PRESETS_DIR / "finance.yml").exists():
        pytest.skip(f"missing preset fixture: {PRESETS_DIR / 'finance.yml'}")
    if not ARCHETYPES_YML.exists():
        pytest.skip(f"missing archetypes yaml: {ARCHETYPES_YML}")

    # ---------- Step 1: Preset materialization -----------------------------
    loader = PresetLoader(presets_dir=PRESETS_DIR)
    available = loader.list_available()
    assert any(p["preset_id"] == "finance" for p in available)

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    created = loader.apply_to("finance", config_dir, overwrite=True)

    assert len(created) >= 4
    for key in ("qualifier_rules", "scoring_weights", "portals", "profile"):
        assert created[key].exists(), f"preset did not create {key}"
        # Every yml should be non-empty UTF-8.
        text = created[key].read_text(encoding="utf-8")
        assert len(text) > 0

    profile_md = created.get("profile_md")
    assert profile_md is not None and profile_md.exists()
    assert "target_industries" not in profile_md.read_text(
        encoding="utf-8"
    ).lower() or "Target Industries" in profile_md.read_text(encoding="utf-8")

    # ---------- Step 2: Archetype classification ---------------------------
    classifier = ArchetypeClassifier(config_path=ARCHETYPES_YML)
    archetype, confidence = classifier.classify(SAMPLE_JD_TEXT)
    assert archetype == Archetype.BLOCKCHAIN, f"expected BLOCKCHAIN got {archetype}"
    assert confidence > 0.3, f"low confidence: {confidence}"

    # ---------- Step 3: Qualifier verdict ----------------------------------
    qualifier = QualifierEngine()
    verdict_result = qualifier.evaluate(SAMPLE_JD_TEXT)
    assert verdict_result.verdict == Verdict.PASS, (
        f"expected PASS got {verdict_result.verdict} reasons={verdict_result.reasons}"
    )
    assert len(verdict_result.reasons) >= 1

    # ---------- Step 4: Fit scoring ----------------------------------------
    scorer = FitScorer()
    job_dict: dict[str, Any] = {
        "name": SAMPLE_JD_TITLE,
        "org": SAMPLE_JD_ORG,
        "description": SAMPLE_JD_TEXT,
        "notes": "",
        "location": "서울 여의도",
        "compensation": 210,
        "deadline": "2026-05-15",
        "source_url": str(sample_job_record.source_url),
    }
    score = scorer.score(
        job=job_dict,
        qualifier_result=verdict_result,
        archetype=archetype,
        today=date(2026, 4, 11),
    )
    assert score.grade in (FitGrade.A, FitGrade.B), (
        f"expected A or B, got {score.grade} total={score.total} breakdown={score.dimension_scores}"
    )
    assert score.total >= 80.0

    # Fill in archetype on the record so downstream sees it.
    sample_job_record.archetype = archetype.value

    # ---------- Step 5: SQLite upsert --------------------------------------
    db_path = tmp_path / "jobs.db"
    store = SQLiteStore(db_path=db_path)
    assert db_path.exists(), "SQLiteStore did not create db file"

    fit_adapter = _FitAdapter(
        grade=score.grade.value,
        score=float(score.total),
        eligible=verdict_result.verdict == Verdict.PASS,
    )
    is_new = store.upsert(sample_job_record, fit=fit_adapter)
    assert is_new is True

    # Idempotent: a second upsert of the same record should NOT be "new".
    is_new_again = store.upsert(sample_job_record, fit=fit_adapter)
    assert is_new_again is False

    # ---------- Step 6: Query by grade -------------------------------------
    target_grade = score.grade.value
    rows = store.list_by_grade(target_grade)
    assert len(rows) >= 1, f"list_by_grade({target_grade}) returned nothing"
    assert any(r["id"] == sample_job_record.id for r in rows)
    # Verify row payload round-tripped intact.
    row = next(r for r in rows if r["id"] == sample_job_record.id)
    assert row["org"] == SAMPLE_JD_ORG
    assert row["title"] == SAMPLE_JD_TITLE
    assert row["archetype"] == Archetype.BLOCKCHAIN.value
    assert row["status"] == "inbox"
    assert row["fit_grade"] == target_grade

    # ---------- Step 7: Vault sync -----------------------------------------
    vault_root = tmp_path / "vault"
    vault = VaultSync(vault_root=vault_root)
    assert vault.vault_root.exists()
    # Every required bucket folder should exist.
    for folder in ("0-inbox", "1-eligible", "2-watchlist", "3-rejected", "4-applied"):
        assert (vault.vault_root / folder).is_dir()

    fit_payload = {
        "grade": score.grade.value,
        "score": float(score.total),
        "eligible": True,
    }
    note_path = vault.upsert_note(sample_job_record, folder="0-inbox", fit=fit_payload)
    assert note_path.exists()
    note_text = note_path.read_text(encoding="utf-8")
    assert note_text.startswith("---\n")
    # Required frontmatter fields.
    for required in (
        f"id: {sample_job_record.id}",
        "archetype: BLOCKCHAIN",
        f"fit_grade: {score.grade.value}",
        "status: inbox",
    ):
        assert required in note_text, f"missing frontmatter field: {required}"
    assert SAMPLE_JD_TITLE in note_text
    assert SAMPLE_JD_ORG in note_text

    # ---------- Step 8: Calendar export ------------------------------------
    ics_path = tmp_path / "cal.ics"
    ics_payload = [
        {
            "id": sample_job_record.id,
            "org": SAMPLE_JD_ORG,
            "title": SAMPLE_JD_TITLE,
            "deadline": "2026-05-15",
            "archetype": Archetype.BLOCKCHAIN.value,
            "fit_grade": score.grade.value,
            "url": str(sample_job_record.source_url),
        }
    ]
    exporter = CalendarExporter()
    out = exporter.from_jobs(ics_payload, ics_path)
    assert out == ics_path
    assert ics_path.exists()
    ics_bytes = ics_path.read_bytes()
    # Basic ICS structural invariants.
    assert b"BEGIN:VCALENDAR" in ics_bytes
    assert b"END:VCALENDAR" in ics_bytes
    assert ics_bytes.count(b"BEGIN:VEVENT") == 1
    assert ics_bytes.count(b"END:VEVENT") == 1
    # Alarm block should exist (24h reminder is default for all jobs).
    assert b"BEGIN:VALARM" in ics_bytes

    # ---------- Step 9: State transition: inbox → eligible ------------------
    assert store.set_status(sample_job_record.id, "eligible") is True
    moved = vault.move_note(sample_job_record.id, "0-inbox", "1-eligible")
    assert moved is not None and moved.exists()
    assert not note_path.exists(), "source note should have been moved"
    assert moved.parent.name == "1-eligible"

    # Double-check SQLite status persisted.
    search_hits = store.search(SAMPLE_JD_ORG)
    assert any(r["id"] == sample_job_record.id and r["status"] == "eligible" for r in search_hits)

    # ---------- Extras: scan log + stats ------------------------------------
    store.log_scan("smoke_test", count=1, errors=[])
    stats = store.get_stats()
    assert stats["total"] >= 1
    assert stats["by_grade"].get(score.grade.value, 0) >= 1


@pytest.mark.integration
def test_end_to_end_pipeline_idempotent(tmp_path: Path, sample_job_record: JobRecord) -> None:
    """Running the core flow twice on the same tmp_path must stay consistent.

    Catches hidden mutable-state bugs — unique constraints, file races,
    doubled calendar events.
    """
    if not (PRESETS_DIR / "finance.yml").exists():
        pytest.skip("finance preset missing")
    if not ARCHETYPES_YML.exists():
        pytest.skip("archetypes.yml missing")

    classifier = ArchetypeClassifier(config_path=ARCHETYPES_YML)
    qualifier = QualifierEngine()
    scorer = FitScorer()
    store = SQLiteStore(db_path=tmp_path / "jobs.db")
    vault = VaultSync(vault_root=tmp_path / "vault")

    arch, _ = classifier.classify(SAMPLE_JD_TEXT)
    verdict_result = qualifier.evaluate(SAMPLE_JD_TEXT)
    job_dict: dict[str, Any] = {
        "name": SAMPLE_JD_TITLE,
        "org": SAMPLE_JD_ORG,
        "description": SAMPLE_JD_TEXT,
        "location": "서울 여의도",
        "compensation": 210,
        "deadline": (date.today() + timedelta(days=10)).isoformat(),
    }
    score = scorer.score(job_dict, verdict_result, arch)

    sample_job_record.archetype = arch.value
    fit = _FitAdapter(score.grade.value, float(score.total), True)

    # Run the same operations twice — should be idempotent.
    for _ in range(2):
        store.upsert(sample_job_record, fit=fit)
        vault.upsert_note(
            sample_job_record,
            folder="0-inbox",
            fit={
                "grade": score.grade.value,
                "score": float(score.total),
                "eligible": True,
            },
        )

    # Only one row per id regardless of upsert count.
    rows = store.list_by_grade(score.grade.value)
    matching = [r for r in rows if r["id"] == sample_job_record.id]
    assert len(matching) == 1

    # Only one vault note in the inbox for this id.
    notes = list((tmp_path / "vault" / "0-inbox").glob(f"{sample_job_record.id}_*.md"))
    assert len(notes) == 1
