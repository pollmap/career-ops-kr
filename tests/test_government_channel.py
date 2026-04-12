"""Tests for GovernmentChannel (config-driven multi-agency)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_government_channel_import():
    """GovernmentChannel imports cleanly."""
    from career_ops_kr.channels.government import GovernmentChannel
    assert GovernmentChannel.name == "government"
    assert GovernmentChannel.tier == 1


def test_government_channel_builtin_portals():
    """Builtin portals loaded when no YAML config exists."""
    from career_ops_kr.channels.government import GovernmentChannel, _BUILTIN_PORTALS
    ch = GovernmentChannel()
    assert len(ch._portals) == len(_BUILTIN_PORTALS)
    assert ch._portals[0]["org"] == "국가정보원"


def test_government_channel_check():
    """check() returns True when portals exist."""
    from career_ops_kr.channels.government import GovernmentChannel
    ch = GovernmentChannel()
    assert ch.check() is True


def test_government_channel_list_jobs_handles_failure():
    """list_jobs() returns empty list on network failure, never raises."""
    from career_ops_kr.channels.government import GovernmentChannel

    ch = GovernmentChannel()
    with patch("career_ops_kr.channels.government.requests.get", side_effect=Exception("network")):
        jobs = ch.list_jobs()
    assert isinstance(jobs, list)


def test_government_channel_scrape_portal_parses_html():
    """_scrape_portal extracts jobs from HTML with anchor tags."""
    from career_ops_kr.channels.government import GovernmentChannel

    html = """
    <html><body>
    <table>
        <tr><td><a href="/recruit/123">2026년 상반기 채용 공고</a></td></tr>
        <tr><td><a href="/recruit/456">인턴 모집 안내</a></td></tr>
    </table>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html

    ch = GovernmentChannel()
    with patch.object(ch, "_retry", return_value=mock_resp):
        jobs = ch._scrape_portal({
            "name": "test_agency",
            "org": "테스트기관",
            "url": "https://test.go.kr/recruit/",
            "tier": 1,
            "legitimacy": "T1",
        })

    assert len(jobs) == 2
    assert jobs[0].org == "테스트기관"
    assert "채용" in jobs[0].title
    assert jobs[0].source_channel == "gov_test_agency"


def test_government_channel_keyword_fallback():
    """Keyword anchor fallback works when table selectors miss."""
    from career_ops_kr.channels.government import GovernmentChannel

    html = """
    <html><body>
    <div>
        <a href="/notice/1">일반 공지사항</a>
        <a href="/careers/2">2026 신입 채용 공고</a>
        <a href="/notice/3">시스템 점검 안내</a>
    </div>
    </body></html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html

    ch = GovernmentChannel()
    with patch.object(ch, "_retry", return_value=mock_resp):
        jobs = ch._scrape_portal({
            "name": "fallback_test",
            "org": "폴백기관",
            "url": "https://fallback.go.kr/",
            "tier": 1,
            "legitimacy": "T1",
        })

    assert len(jobs) >= 1
    assert any("채용" in j.title for j in jobs)
