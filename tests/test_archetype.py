"""Regression + unit tests for ArchetypeClassifier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from career_ops_kr.archetype import Archetype, ArchetypeClassifier

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "programs_verified_20260411.json"


def _load_programs() -> list[dict]:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["programs"]


@pytest.fixture(scope="module")
def classifier() -> ArchetypeClassifier:
    return ArchetypeClassifier()


@pytest.fixture(scope="module")
def programs() -> list[dict]:
    return _load_programs()


def _program_text(p: dict) -> str:
    return " ".join(str(p.get(k, "")) for k in ("name", "org", "notes"))


def test_fixture_archetype_labels_valid(programs: list[dict]) -> None:
    valid = {a.value for a in Archetype}
    for p in programs:
        assert p["archetype_expected"] in valid, f"{p['id']}: {p['archetype_expected']}"


def test_regression_accuracy(classifier: ArchetypeClassifier, programs: list[dict]) -> None:
    total = len(programs)
    matches = 0
    mismatches: list[str] = []

    for p in programs:
        text = _program_text(p)
        archetype, confidence = classifier.classify(text)
        expected = p["archetype_expected"]
        ok = archetype.value == expected and confidence >= 0.5
        if ok:
            matches += 1
        else:
            mismatches.append(
                f"{p['id']}: expected={expected} actual={archetype.value} conf={confidence}"
            )

    accuracy = matches / total
    print(
        f"\n=== ArchetypeClassifier regression ===\n"
        f"Total: {total}, Matches: {matches}, Accuracy: {accuracy:.1%}"
    )
    if mismatches:
        print("Mismatches (first 15):")
        for m in mismatches[:15]:
            print(f"  - {m}")

    assert accuracy >= 0.85, f"archetype accuracy {accuracy:.1%} below 85% target"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("블록체인부 STO 토큰증권 인턴", Archetype.BLOCKCHAIN),
        ("스마트컨트랙트 개발 Web3", Archetype.BLOCKCHAIN),
        ("업비트 UpTo 서포터즈", Archetype.DIGITAL_ASSET),
        ("빗썸 커스터디 담당", Archetype.DIGITAL_ASSET),
        ("디지털 하나로 채용 연계", Archetype.FINANCIAL_IT),
        ("신한은행 체험형 청년인턴", Archetype.FINANCIAL_IT),
        ("Equity Research 애널리스트", Archetype.RESEARCH),
        ("한국은행 통화정책 경시대회", Archetype.RESEARCH),
        ("토스 인턴 간편결제", Archetype.FINTECH_PRODUCT),
        ("뱅크샐러드 인턴", Archetype.FINTECH_PRODUCT),
        ("한국은행 체험형 인턴", Archetype.PUBLIC_FINANCE),
        ("신용보증기금 인턴", Archetype.PUBLIC_FINANCE),
        ("금융감독원 대학생 서포터즈", Archetype.PUBLIC_FINANCE),
        ("ADsP 49회 정기시험", Archetype.CERTIFICATION),
        ("SQLD 61회 자격시험", Archetype.CERTIFICATION),
    ],
)
def test_individual_classifications(
    classifier: ArchetypeClassifier, text: str, expected: Archetype
) -> None:
    arch, conf = classifier.classify(text)
    assert arch == expected, f"text={text!r} → {arch} (expected {expected})"
    assert conf >= 0.5, f"confidence {conf} too low for {text!r}"


def test_empty_text_returns_unknown(
    classifier: ArchetypeClassifier,
) -> None:
    arch, conf = classifier.classify("")
    assert arch == Archetype.UNKNOWN
    assert conf == 0.0


def test_blockchain_beats_digital_asset_tie(
    classifier: ArchetypeClassifier,
) -> None:
    """When both 블록체인 and 거래소 present, BLOCKCHAIN should win."""
    arch, _ = classifier.classify("블록체인 거래소 STO 토큰증권 개발")
    assert arch == Archetype.BLOCKCHAIN


_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "archetypes.yml"


def test_loads_from_yml() -> None:
    """Explicit YAML path — round-trip a known program."""
    assert _CONFIG_PATH.exists(), f"missing config: {_CONFIG_PATH}"
    clf = ArchetypeClassifier(config_path=_CONFIG_PATH)
    assert clf.domain == "finance_kr"
    arch, conf = clf.classify("신한투자증권 블록체인부 STO 토큰증권 인턴")
    assert arch == Archetype.BLOCKCHAIN
    assert conf >= 0.5
    # All 8 enum members should round-trip through list_archetypes or labels.
    assert "BLOCKCHAIN" in clf.list_archetypes()


def test_missing_yml_fallback(tmp_path: Path) -> None:
    """Non-existent yml path falls back to embedded defaults."""
    missing = tmp_path / "does-not-exist.yml"
    clf = ArchetypeClassifier(config_path=missing)
    # Embedded fallback should still classify canonical samples correctly.
    samples = [
        ("블록체인부 STO 토큰증권 인턴", Archetype.BLOCKCHAIN),
        ("업비트 UpTo 서포터즈", Archetype.DIGITAL_ASSET),
        ("ADsP 49회 정기시험", Archetype.CERTIFICATION),
        ("한국은행 체험형 인턴", Archetype.PUBLIC_FINANCE),
    ]
    for text, expected in samples:
        arch, conf = clf.classify(text)
        assert arch == expected, f"{text!r} → {arch}"
        assert conf >= 0.5
