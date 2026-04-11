"""KOFIA (한국금융투자협회) certification exam notice channel.

Source: https://license.kofia.or.kr/

The exam schedules for 금융투자분석사(금투사) / 투자운용사(투운사) / 파생상품투자권유자문인력 etc.
are published as PDF attachments on the 공지사항 board. We fetch the board
(via Scrapling DynamicFetcher when available, else Playwright), grab PDF
links, download them, extract text with ``pdfplumber``, parse the exam
dates, and emit :class:`JobRecord`s with ``archetype="CERTIFICATION"``.

On any failure we return ``[]`` and log — we NEVER synthesize exam dates.
"""

from __future__ import annotations

import logging
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser

logger = logging.getLogger(__name__)


BASE_URL = "https://license.kofia.or.kr/"
NOTICE_URL = "https://license.kofia.or.kr/customer/notice/noticeList.do"
ORG = "한국금융투자협회"

EXAM_KEYWORDS: tuple[str, ...] = (
    "시험일정",
    "시험 일정",
    "금융투자분석사",
    "투자운용사",
    "투자자산운용사",
    "파생상품",
    "증권투자권유자문인력",
    "펀드투자권유자문인력",
    "접수",
    "원서접수",
)


# ---------------------------------------------------------------------------
# Shared helpers — backend-agnostic
# ---------------------------------------------------------------------------


def _extract_notice_links(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        text = (anchor.get_text(" ", strip=True) or "").strip()
        if not text:
            continue
        if not any(kw in text for kw in EXAM_KEYWORDS):
            continue
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.startswith("javascript"):
            continue
        url = urljoin(NOTICE_URL, href)
        if url in seen:
            continue
        seen.add(url)
        found.append((text[:200], url))
    return found


def _extract_pdf_urls(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a"):
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if ".pdf" in href.lower():
            urls.append(urljoin(base, href))
    return urls


def _pick_deadline(text: str) -> date | None:
    if not text:
        return None
    candidates = re.findall(r"\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}", text)
    for candidate in reversed(candidates):
        parsed = deadline_parser(candidate)
        if parsed is not None:
            return parsed
    return deadline_parser(text)


def _download_pdf_sync(pdf_url: str) -> bytes | None:
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(pdf_url)
        if resp.status_code >= 400:
            logger.warning("kofia: PDF HTTP %d for %s", resp.status_code, pdf_url)
            return None
        return resp.content
    except Exception as exc:
        logger.warning("kofia: PDF download failed %s: %s", pdf_url, exc)
        return None


async def _download_pdf_async(pdf_url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(pdf_url)
        if resp.status_code >= 400:
            logger.warning("kofia: PDF HTTP %d for %s", resp.status_code, pdf_url)
            return None
        return resp.content
    except Exception as exc:
        logger.warning("kofia: PDF download failed %s: %s", pdf_url, exc)
        return None


def _pdf_bytes_to_text(content: bytes) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        logger.warning("kofia: pdfplumber not installed — skipping PDF parse")
        return None
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / "notice.pdf"
        tmp_path.write_bytes(content)
        try:
            with pdfplumber.open(tmp_path) as pdf:
                text_parts = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(text_parts)
        except Exception as exc:
            logger.warning("kofia: pdfplumber failed: %s", exc)
            return None


def _record_from_notice(title: str, notice_url: str, html: str, make_id: Any) -> JobRecord:
    body = BeautifulSoup(html, "html.parser").get_text(" ", strip=True) if html else title
    return JobRecord(
        id=make_id(notice_url, title),
        source_url=notice_url,  # type: ignore[arg-type]
        source_channel="kofia",
        source_tier=2,
        org=ORG,
        title=title,
        archetype="CERTIFICATION",
        deadline=_pick_deadline(body),
        description=body[:5000],
        raw_html=None,
        legitimacy_tier="T2",
    )


def _record_from_pdf(pdf_url: str, notice_title: str, text: str, make_id: Any) -> JobRecord:
    title = notice_title or "금투협 자격시험 공지"
    return JobRecord(
        id=make_id(pdf_url, title),
        source_url=pdf_url,  # type: ignore[arg-type]
        source_channel="kofia",
        source_tier=2,
        org=ORG,
        title=title,
        archetype="CERTIFICATION",
        deadline=_pick_deadline(text),
        description=text[:5000],
        raw_html=None,
        legitimacy_tier="T2",
    )


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


try:
    from career_ops_kr.channels._scrapling_base import (
        SCRAPLING_AVAILABLE,
        ScraplingChannel,
    )
except ImportError:  # pragma: no cover
    SCRAPLING_AVAILABLE = False


if SCRAPLING_AVAILABLE:

    class KofiaChannel(ScraplingChannel):
        """금투협 공지사항 PDF 파싱 기반 자격시험 수집기 (Scrapling backend)."""

        name = "kofia"
        tier = 2
        default_legitimacy_tier = "T2"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="kofia",
                tier=2,
                login_url=NOTICE_URL,
                # Notice board is JS-heavy — DynamicFetcher renders properly.
                fetcher_mode="dynamic",
                **kwargs,
            )

        def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            board = self.fetch_page(NOTICE_URL)
            if board is None:
                self.logger.warning("kofia: notice board fetch failed")
                return []
            notice_links = _extract_notice_links(board["html"])
            if not notice_links:
                self.logger.info("kofia: no matching notices found")
                return []

            jobs: list[JobRecord] = []
            for title, notice_url in notice_links[:10]:
                detail = self.fetch_page(notice_url)
                if detail is None:
                    continue
                pdf_urls = _extract_pdf_urls(detail["html"], notice_url)
                if not pdf_urls:
                    jobs.append(
                        _record_from_notice(title, notice_url, detail["html"], self._make_id)
                    )
                    continue
                for pdf_url in pdf_urls:
                    content = _download_pdf_sync(pdf_url)
                    if content is None:
                        continue
                    text = _pdf_bytes_to_text(content)
                    if text is None:
                        jobs.append(
                            _record_from_notice(title, notice_url, detail["html"], self._make_id)
                        )
                        continue
                    jobs.append(_record_from_pdf(pdf_url, title, text, self._make_id))
            return jobs

        def get_detail(self, url: str) -> JobRecord | None:
            detail = self.fetch_page(url)
            if detail is None:
                return None
            try:
                return _record_from_notice(url, url, detail["html"], self._make_id)
            except Exception as exc:
                self.logger.warning("kofia: detail parse failed %s: %s", url, exc)
                return None

else:
    from career_ops_kr.channels._playwright_base import PlaywrightChannel

    class KofiaChannel(PlaywrightChannel):  # type: ignore[no-redef]
        """금투협 공지사항 PDF 파싱 기반 자격시험 수집기 (Playwright fallback)."""

        name = "kofia"
        tier = 2
        default_legitimacy_tier = "T2"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="kofia",
                tier=2,
                login_url=NOTICE_URL,
                requires_login=False,
                **kwargs,
            )

        async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            html = await self.fetch_html(NOTICE_URL, wait_selector="body")
            if html is None:
                self.logger.warning("kofia: notice board fetch failed")
                await self.close()
                return []

            notice_links = _extract_notice_links(html)
            if not notice_links:
                self.logger.info("kofia: no matching notices found")
                await self.close()
                return []

            jobs: list[JobRecord] = []
            for title, notice_url in notice_links[:10]:
                detail_html = await self.fetch_html(notice_url)
                if detail_html is None:
                    continue
                pdf_urls = _extract_pdf_urls(detail_html, notice_url)
                if not pdf_urls:
                    jobs.append(_record_from_notice(title, notice_url, detail_html, self._make_id))
                    continue
                for pdf_url in pdf_urls:
                    content = await _download_pdf_async(pdf_url)
                    if content is None:
                        continue
                    text = _pdf_bytes_to_text(content)
                    if text is None:
                        jobs.append(
                            _record_from_notice(title, notice_url, detail_html, self._make_id)
                        )
                        continue
                    jobs.append(_record_from_pdf(pdf_url, title, text, self._make_id))

            await self.close()
            return jobs

        async def _async_get_detail(self, url: str) -> JobRecord | None:
            html = await self.fetch_html(url)
            await self.close()
            if html is None:
                return None
            return _record_from_notice(url, url, html, self._make_id)
