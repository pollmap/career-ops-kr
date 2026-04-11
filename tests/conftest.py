"""Shared pytest fixtures for career-ops-kr tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Minimal career-ops-kr project skeleton under tmp_path."""
    root = tmp_path / "career-ops-kr"
    (root / "config").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "modes").mkdir()
    (root / "templates").mkdir()
    (root / "output").mkdir()
    (root / "scripts").mkdir()

    (root / "config" / "profile.yml").write_text(
        "name: 이찬희\ntarget_industries:\n  - 금융\n",
        encoding="utf-8",
    )
    (root / "modes" / "_profile.md").write_text(
        "# Profile\n\n(test fixture)\n",
        encoding="utf-8",
    )
    (root / "cv.md").write_text("# 이찬희 이력서\n", encoding="utf-8")
    return root


@pytest.fixture
def sample_jobs() -> list[dict[str, Any]]:
    """Five realistic JobRecord dicts."""
    return [
        {
            "id": "krx-2026-001",
            "org": "한국거래소",
            "title": "디지털자산 시장감시 전문인력",
            "url": "https://job.krx.co.kr/2026/001",
            "archetype": "블록체인",
            "fit_grade": "A",
            "deadline": date(2026, 4, 17),
            "legitimacy": "T1",
            "status": "inbox",
        },
        {
            "id": "dunamu-2026-02",
            "org": "두나무",
            "title": "블록체인 리서치",
            "url": "https://dunamu.com/careers/02",
            "archetype": "블록체인",
            "fit_grade": "A",
            "deadline": date(2026, 4, 25),
            "legitimacy": "T1",
            "status": "inbox",
        },
        {
            "id": "toss-2026-07",
            "org": "토스",
            "title": "핀테크 프로덕트 애널리스트",
            "url": "https://toss.im/careers/07",
            "archetype": "핀테크",
            "fit_grade": "B",
            "deadline": date(2026, 5, 1),
            "legitimacy": "T1",
            "status": "inbox",
        },
        {
            "id": "fnguide-2026-03",
            "org": "에프앤가이드",
            "title": "금융데이터 주니어",
            "url": "https://fnguide.com/jobs/03",
            "archetype": "금융IT",
            "fit_grade": "C",
            "deadline": None,  # missing deadline → skipped by calendar
            "legitimacy": "T2",
            "status": "inbox",
        },
        {
            "id": "bok-2026-11",
            "org": "한국은행",
            "title": "리서치 어시스턴트",
            "url": "https://bok.or.kr/careers/11",
            "archetype": "공공",
            "fit_grade": "A",
            "deadline": date(2026, 6, 10),
            "legitimacy": "T1",
            "status": "inbox",
        },
    ]


@pytest.fixture
def mock_profile() -> dict[str, Any]:
    """찬희 profile dict."""
    return {
        "name": "이찬희",
        "school": "충북대학교 경영학부",
        "year": 3,
        "semester": 1,
        "status": "재학",
        "target_industries": ["금융", "핀테크", "블록체인", "공공"],
        "deal_breakers": ["토요일 근무", "학력차별"],
        "strengths": ["DART API", "퀀트 백테스트", "CUFA 회장"],
    }
