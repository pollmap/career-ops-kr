"""career-ops history — 과거 마감 공고 수집 (채용 패턴 분석용).

잡코리아/사람인에서 마감 포함 검색으로 과거 공고를 수집.
기관별 채용 패턴(언제 공고 내는지)을 학습하는 데이터 확보 목적.
"""

from __future__ import annotations

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import click
import requests
from bs4 import BeautifulSoup
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from career_ops_kr.channels.base import BaseChannel, JobRecord
from career_ops_kr.commands._shared import CONFIG_DIR, DATA_DIR, console

UA = "Mozilla/5.0 career-ops-kr/0.2"


def _search_jobkorea_closed(query: str, pages: int = 3) -> list[dict[str, str]]:
    """잡코리아에서 마감 포함 검색."""
    results = []
    seen = set()
    for page in range(1, pages + 1):
        url = (
            f"https://www.jobkorea.co.kr/Search/"
            f"?stext={requests.utils.quote(query)}&tabType=recruit"
            f"&Page_No={page}&Recruit_Done=1"
        )
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
            if resp.status_code != 200:
                break
        except Exception:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a[href*='/Recruit/GI_Read']"):
            title = a.get_text(" ", strip=True)
            href = a.get("href", "")
            if not title or len(title) < 4 or not href:
                continue
            if href.startswith("/"):
                href = "https://www.jobkorea.co.kr" + href
            if href in seen:
                continue
            seen.add(href)
            results.append({"title": title, "url": href, "source": "jobkorea"})
        time.sleep(0.5)
    return results


def _search_saramin_closed(query: str, pages: int = 3) -> list[dict[str, str]]:
    """사람인에서 마감 포함 검색."""
    results = []
    seen = set()
    for page in range(1, pages + 1):
        url = (
            f"https://www.saramin.co.kr/zf_user/search"
            f"?searchword={requests.utils.quote(query)}&searchType=search"
            f"&recruitPage={page}&recruitSort=relation&recruitPageCount=40"
            f"&inner_com_type=&company_cd=0%2C1%2C2%2C3%2C4%2C5%2C6%2C7%2C9%2C10"
            f"&show_applied=&quick_apply=&except_read=&ai_head_498="
        )
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=10)
            if resp.status_code != 200:
                break
        except Exception:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a[href*='/zf_user/jobs/relay']"):
            title = a.get_text(" ", strip=True)
            href = a.get("href", "")
            if not title or len(title) < 4 or not href:
                continue
            if href.startswith("/"):
                href = "https://www.saramin.co.kr" + href
            if href in seen:
                continue
            seen.add(href)
            results.append({"title": title, "url": href, "source": "saramin"})
        time.sleep(0.5)
    return results


@click.command("history")
@click.option("--query", "-q", multiple=True, default=None, help="검색 키워드 (여러 개 가능)")
@click.option("--pages", type=int, default=3, help="페이지 수 (기본 3)")
@click.option("--top", type=int, default=30, help="상위 N건 표시")
def history_cmd(query: tuple[str, ...], pages: int, top: int) -> None:
    """과거 마감 공고 수집 — 채용 패턴 분석용.

    잡코리아/사람인에서 마감 포함 검색. 기관별 채용 시기 패턴 학습.
    """
    queries = list(query) if query else [
        "공기업 인턴",
        "금융 인턴",
        "체험형 인턴",
        "공공기관 채용",
        "NCS 채용",
    ]

    console.print(f"[green]history[/green] {len(queries)}개 키워드 × 2 aggregator (마감 포함)")

    all_results: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as prog:
        task = prog.add_task("[cyan]수집[/cyan]", total=len(queries) * 2)

        for q in queries:
            for results in [
                _search_jobkorea_closed(q, pages),
                _search_saramin_closed(q, pages),
            ]:
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        all_results.append(r)
                prog.advance(task)

    console.print(f"\n[green]수집 완료[/green] {len(all_results)}건 (마감 포함, 중복 제거)")

    # 결과 테이블
    if all_results:
        table = Table(title=f"과거+현재 공고 Top {min(top, len(all_results))}")
        table.add_column("#", justify="right")
        table.add_column("소스", style="dim")
        table.add_column("제목")
        for i, r in enumerate(all_results[:top], 1):
            table.add_row(str(i), r["source"], r["title"][:60])
        console.print(table)

    # SQLite 저장
    try:
        from career_ops_kr.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(DATA_DIR / "jobs.db")
        saved = 0
        now = datetime.now()
        for r in all_results:
            try:
                job = JobRecord(
                    id=BaseChannel._make_id(r["url"], r["title"][:120]),
                    source_url=r["url"],
                    source_channel=f"history_{r['source']}",
                    source_tier=3,
                    org="(과거공고)",
                    title=r["title"][:200],
                    description=r["title"],
                    legitimacy_tier="T3",
                    scanned_at=now,
                )
                store.upsert(job)
                saved += 1
            except Exception:
                continue
        console.print(f"[green]SQLite 저장[/green] {saved}건 (누적)")
    except Exception as exc:
        console.print(f"[yellow]저장 실패[/yellow]: {exc}")
