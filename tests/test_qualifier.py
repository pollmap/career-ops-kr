"""Regression + unit tests for QualifierEngine.

Regression: iterate all entries in
``tests/fixtures/programs_verified_20260411.json`` and assert the engine's
verdict matches ``eligibility_expected``. Reports per-verdict accuracy.

Unit: parametrized tests for individual patterns that 찬희 hits daily.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_ops_kr.qualifier import QualifierEngine, Verdict

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "programs_verified_20260411.json"


def _load_programs() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    programs = data["programs"]
    assert len(programs) >= 50, f"fixture must have >=50 entries, got {len(programs)}"
    return programs


@pytest.fixture(scope="module")
def engine() -> QualifierEngine:
    return QualifierEngine()


@pytest.fixture(scope="module")
def programs() -> list[dict]:
    return _load_programs()


def _program_text(p: dict) -> str:
    return " ".join(str(p.get(k, "")) for k in ("name", "org", "notes"))


def test_fixture_size(programs: list[dict]) -> None:
    assert len(programs) >= 50


def test_fixture_expected_labels_valid(programs: list[dict]) -> None:
    valid = {v.value for v in Verdict}
    for p in programs:
        assert p["eligibility_expected"] in valid, p["id"]


def test_regression_accuracy(engine: QualifierEngine, programs: list[dict]) -> None:
    """Regression: verdict should match expected on >=95% of programs."""
    total = len(programs)
    matches = 0
    mismatches: list[str] = []
    per_verdict: dict[str, tuple[int, int]] = {}

    for p in programs:
        text = _program_text(p)
        result = engine.evaluate(text)
        expected = p["eligibility_expected"]
        actual = result.verdict.value
        ok = actual == expected
        if ok:
            matches += 1
        else:
            mismatches.append(
                f"{p['id']}: expected={expected} actual={actual} reasons={result.reasons[:2]}"
            )
        hit, tot = per_verdict.get(expected, (0, 0))
        per_verdict[expected] = (hit + (1 if ok else 0), tot + 1)

    accuracy = matches / total
    report_lines = [
        "\n=== QualifierEngine regression ===",
        f"Total: {total}, Matches: {matches}, Accuracy: {accuracy:.1%}",
    ]
    for v, (hit, tot) in sorted(per_verdict.items()):
        report_lines.append(f"  {v:12s}: {hit}/{tot}")
    if mismatches:
        report_lines.append("Mismatches:")
        report_lines.extend(f"  - {m}" for m in mismatches[:20])
    print("\n".join(report_lines))

    assert accuracy >= 0.95, (
        f"accuracy {accuracy:.1%} below 95% target. Mismatches: {mismatches[:5]}"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("졸업예정자 대상 KB IT 인턴", Verdict.FAIL),
        ("졸업자 대상 채용형 인턴", Verdict.FAIL),
        ("4년제 대학 졸업 필수 공채", Verdict.FAIL),
        ("정보통신 관련학과 재학생", Verdict.FAIL),
        ("컴퓨터공학 전공 필수", Verdict.FAIL),
        ("학점 3.5 이상 요건", Verdict.FAIL),
        ("학력 무관, 전공 무관 인턴", Verdict.PASS),
        ("재학생 휴학생 지원 가능", Verdict.PASS),
        ("체험형 인턴 모집", Verdict.PASS),
        ("내일배움카드 활용 가능", Verdict.PASS),
        ("대학생 서포터즈 모집", Verdict.PASS),
        ("수시 채용, 경력 우대", Verdict.CONDITIONAL),
        ("", Verdict.CONDITIONAL),
    ],
)
def test_individual_patterns(engine: QualifierEngine, text: str, expected: Verdict) -> None:
    result = engine.evaluate(text)
    assert result.verdict == expected, (
        f"text={text!r}, got {result.verdict}, reasons={result.reasons}"
    )


def test_numeric_semester_rule(engine: QualifierEngine) -> None:
    fail = engine.evaluate("6학기 이상 수료자 대상 인턴")
    assert fail.verdict == Verdict.FAIL
    ok = engine.evaluate("4학기 이상 수료자 대상")
    assert ok.verdict == Verdict.PASS


def test_age_rule(engine: QualifierEngine) -> None:
    # 찬희 is 24세; 만 22세 이하 요건 → FAIL
    result = engine.evaluate("만 22세 이하 청년 인턴")
    assert result.verdict == Verdict.FAIL


def test_batch_evaluate(engine: QualifierEngine, programs: list[dict]) -> None:
    jobs = [
        {
            "name": p["name"],
            "description": p.get("notes", ""),
            "notes": p.get("notes", ""),
        }
        for p in programs[:10]
    ]
    results = engine.batch_evaluate(jobs)
    assert len(results) == 10
    assert all(r.verdict in set(Verdict) for r in results)
