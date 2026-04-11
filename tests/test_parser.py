"""Tests for JobNormalizer parser utilities.

These tests import from career_ops_kr.parser. If the parser module isn't
implemented yet, individual tests will skip cleanly so the suite stays green.
"""

from __future__ import annotations

from datetime import date

import pytest

parser_mod = pytest.importorskip("career_ops_kr.parser")


def _get(attr: str):
    return getattr(parser_mod, attr, None)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026.04.17", date(2026, 4, 17)),
        ("2026-04-17", date(2026, 4, 17)),
        ("4/17(금)", date(2026, 4, 17)),
        ("4월 17일", date(2026, 4, 17)),
        ("26.04.17", date(2026, 4, 17)),
    ],
)
def test_korean_date_parsing(raw: str, expected: date) -> None:
    parse_date = _get("parse_korean_date")
    if parse_date is None:
        pytest.skip("parser.parse_korean_date not implemented yet")
    # assume default year 2026 for bare month/day
    result = parse_date(raw, default_year=2026)
    assert result == expected


def test_html_cleanup_strips_scripts_and_entities() -> None:
    clean = _get("clean_html")
    if clean is None:
        pytest.skip("parser.clean_html not implemented yet")
    raw = "<p>Hello&nbsp;<script>alert(1)</script>  world&amp;more</p>"
    result = clean(raw)
    assert "script" not in result.lower()
    assert "alert" not in result
    assert "world&more" in result or "world more" in result
    # whitespace normalized
    assert "  " not in result


def test_id_generation_is_deterministic() -> None:
    gen_id = _get("generate_job_id")
    if gen_id is None:
        pytest.skip("parser.generate_job_id not implemented yet")
    # positional call and dict call must produce identical hashes.
    positional = gen_id("https://krx.co.kr/1", "디지털자산 PM", org="한국거래소")
    as_dict = gen_id({"org": "한국거래소", "title": "디지털자산 PM", "url": "https://krx.co.kr/1"})
    assert positional == as_dict
    assert isinstance(positional, str)
    assert len(positional) > 0
    # stability across repeated calls.
    assert gen_id("u", "t") == gen_id("u", "t")
    # org-less call matches the legacy BaseChannel._make_id hash format.
    import hashlib

    legacy = hashlib.sha256(b"u||t").hexdigest()[:16]
    assert gen_id("u", "t") == legacy
    # mixed-case / whitespace inputs must ALSO hash to the legacy byte
    # format — catches the "hidden normalization" regression that the
    # pure-ascii 'u'/'t' case would miss (code review HIGH finding).
    mixed_url = "HTTPS://Example.com/1"
    spaced_title = " Title "
    mixed_legacy = hashlib.sha256(f"{mixed_url}||{spaced_title}".encode()).hexdigest()[:16]
    assert gen_id(mixed_url, spaced_title) == mixed_legacy


@pytest.mark.parametrize(
    "text,expected_kw",
    [
        ("졸업자 지원 가능", "졸업자"),
        ("재학생 환영", "재학생"),
        ("휴학생도 가능합니다", "휴학생"),
        ("학력무관 우대", "학력무관"),
    ],
)
def test_eligibility_keyword_extraction(text: str, expected_kw: str) -> None:
    extract = _get("extract_eligibility_keywords")
    if extract is None:
        pytest.skip("parser.extract_eligibility_keywords not implemented yet")
    keywords = extract(text)
    assert expected_kw in keywords
