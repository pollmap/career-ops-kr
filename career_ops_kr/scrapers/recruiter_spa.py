"""Playwright 기반 recruiter.co.kr SPA 스크레이퍼.

recruiter.co.kr은 React SPA라 requests로 접근하면 빈 껍데기만 반환.
Playwright(headless Chromium)로 JS 렌더링 후 공고 추출.

URL 패턴:
    https://{slug}.recruiter.co.kr/career/home
    공고 상세: https://{slug}.recruiter.co.kr/career/jobs/{id}

사용:
    from career_ops_kr.scrapers.recruiter_spa import fetch_recruiter_jobs
    jobs = fetch_recruiter_jobs("https://shinhan.recruiter.co.kr/career/home", ...)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

if TYPE_CHECKING:
    from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)

# recruiter.co.kr 공고 href 패턴
_JOB_HREF_RE = re.compile(r"/career/jobs/(\d+)")

# 마감일 패턴 (공고 텍스트에서)
_DEADLINE_RE = re.compile(
    r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})"
)

_DEADLINE_KEYWORDS = ("마감", "접수", "~", "까지")


def _extract_deadline(text: str) -> str | None:
    """텍스트에서 마감일 추출."""
    matches = _DEADLINE_RE.findall(text)
    if not matches:
        return None
    # 가장 마지막 날짜가 마감일일 가능성 높음
    y, m, d = matches[-1]
    try:
        dt = datetime(int(y), int(m), int(d))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _extract_status(text: str) -> str | None:
    """접수중 / 접수마감 추출."""
    if "접수중" in text:
        return "open"
    if "접수마감" in text or "마감" in text:
        return "closed"
    return None


def fetch_recruiter_jobs(
    listing_url: str,
    *,
    channel_name: str,
    channel_tier: int,
    org: str,
    location: str | None,
    legitimacy_tier: str,
    make_id,  # callable(url, title) -> str
    timeout_ms: int = 30_000,
    open_only: bool = True,
) -> list[JobRecord]:
    """recruiter.co.kr SPA에서 공고 목록 추출.

    Args:
        listing_url: https://{slug}.recruiter.co.kr/career/home
        channel_name: 채널 이름 (JobRecord.source_channel)
        channel_tier: 채널 tier
        org: 기관명
        location: 지역
        legitimacy_tier: T1/T2 등
        make_id: BaseChannel._make_id 메서드
        timeout_ms: 페이지 로드 타임아웃 (ms)
        open_only: True면 '접수중' 공고만 수집

    Returns:
        list[JobRecord] — 실패 시 []
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("recruiter_spa: playwright not installed — returning []")
        return []

    try:
        from career_ops_kr.channels.base import JobRecord, deadline_parser
    except ImportError:
        logger.error("recruiter_spa: cannot import JobRecord")
        return []

    base = "{0.scheme}://{0.netloc}".format(urlparse(listing_url))

    jobs: list[JobRecord] = []
    now = datetime.now()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                ],
            )
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36 career-ops-kr/0.2.0"
                ),
                locale="ko-KR",
            )
            page = ctx.new_page()

            try:
                page.goto(
                    listing_url,
                    timeout=timeout_ms,
                    wait_until="networkidle",
                )
            except PWTimeout:
                # networkidle 타임아웃 → domcontentloaded로 재시도
                try:
                    page.goto(
                        listing_url,
                        timeout=timeout_ms,
                        wait_until="domcontentloaded",
                    )
                    page.wait_for_timeout(3000)  # 추가 렌더링 대기
                except Exception as e2:
                    logger.warning("recruiter_spa %s: goto failed: %s", channel_name, e2)
                    browser.close()
                    return []

            html = page.content()
            browser.close()

    except Exception as exc:
        logger.error("recruiter_spa %s: playwright error: %s", channel_name, exc)
        return []

    # --- HTML 파싱 ---
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("recruiter_spa: bs4 not installed")
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not _JOB_HREF_RE.search(href):
            continue

        url = urljoin(base, href)
        if url in seen:
            continue
        seen.add(url)

        # 컨테이너 (li / article / div) 에서 더 풍부한 텍스트 추출
        container = anchor.find_parent(["li", "article", "div", "tr"])
        body_text = (
            container.get_text(" ", strip=True) if container else anchor.get_text(" ", strip=True)
        )

        # 접수중 필터
        status = _extract_status(body_text)
        if open_only and status == "closed":
            continue

        # 타이틀: anchor 텍스트에서 날짜/상태 prefix·suffix 제거
        raw_title = anchor.get_text(" ", strip=True)
        clean_title = raw_title
        # prefix: "접수마감", "접수중", "D-Day" 제거
        clean_title = re.sub(r"^(접수마감|접수중|마감|D-Day|D-\d+)\s*", "", clean_title).strip()
        # suffix: 날짜 범위 "2026.03.23 ~2026.04.03 14:00공채" 제거
        clean_title = re.sub(r"\s*\d{4}[.\-]\d{1,2}[.\-]\d{1,2}.*$", "", clean_title).strip()
        # D-Day 라벨 제거
        clean_title = re.sub(r"\s*D-Day\s*$", "", clean_title).strip()
        clean_title = re.sub(r"\s*D-\d+\s*$", "", clean_title).strip()
        # 남은 채용유형 suffix (공채/상시 등) 는 유지
        if not clean_title or len(clean_title) < 3:
            clean_title = org + " 채용"

        deadline_str = _extract_deadline(body_text)
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d") if deadline_str else None
        except ValueError:
            deadline = None

        try:
            record = JobRecord(
                id=make_id(url, clean_title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=channel_name,
                source_tier=channel_tier,
                org=org[:100],
                title=clean_title[:200],
                archetype=_infer_archetype(clean_title),
                deadline=deadline,
                location=location,
                description=body_text[:2000],
                legitimacy_tier=legitimacy_tier,
                scanned_at=now,
            )
            jobs.append(record)
        except Exception as exc:
            logger.warning("recruiter_spa %s: skip bad record: %s", channel_name, exc)
            continue

    logger.info(
        "recruiter_spa %s: %d jobs from %s (open_only=%s)",
        channel_name, len(jobs), listing_url, open_only,
    )
    return jobs


def _infer_archetype(title: str) -> str | None:
    """타이틀에서 archetype 추론."""
    if not title:
        return None
    t = title.lower()
    if "인턴" in t or "intern" in t:
        return "INTERN"
    if "신입" in t:
        return "ENTRY"
    if "경력" in t:
        return "EXPERIENCED"
    if any(k in t for k in ("공채", "정기채용")):
        return "ENTRY"
    if any(k in t for k in ("it", "개발", "엔지니어", "데이터", "디지털", "sw", "ai")):
        return "IT"
    return None
