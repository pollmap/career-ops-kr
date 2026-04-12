"""career-ops auto-pipeline — 전체 채널 수집 + AI 채점 자동 파이프라인.

CHANNEL_REGISTRY를 직접 순회해서 JobRecord 목록을 수집한다.
(tool_scan_jobs()는 count만 반환하므로 URL 목록 추출 불가)
G4 게이트: 5건 이상이면 샘플 1건 확인 후 진행.
"""

from __future__ import annotations

import sys

import click
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm

from career_ops_kr.commands._shared import (
    CONFIG_DIR,
    DATA_DIR,
    console,
    get_store,
    grade_ge,
    load_profile,
    print_standard_report,
)

_PROGRESS_COLS = (
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
)


@click.command("auto-pipeline")
@click.option("--tier", type=int, default=None, help="채널 Tier 필터 (1~6)")
@click.option("--site", type=str, default=None, help="특정 사이트만 (예: linkareer)")
@click.option("--limit", type=int, default=50, show_default=True, help="최대 채점 건수")
@click.option(
    "--grade",
    "min_grade",
    type=str,
    default="B",
    show_default=True,
    help="저장 최소 등급 (A/B/C/D/F)",
)
@click.option("--notify", is_flag=True, help="Discord 알림 전송")
@click.option("--dry-run", "dry_run", is_flag=True, help="설정 검증만, 네트워크 없음")
@click.option(
    "--source",
    type=click.Choice(["channels", "institutions", "both"]),
    default="both",
    show_default=True,
    help="수�� 소스: channels(45채널), institutions(194기관 aggregator), both",
)
@click.option("--ai-score", "ai_score", is_flag=True, help="Ollama/OpenRouter AI 채점 활성화")
@click.option("--concurrency", type=int, default=6, help="institutions 검색 동시성")
def auto_pipeline_cmd(
    tier: int | None,
    site: str | None,
    limit: int,
    min_grade: str,
    notify: bool,
    dry_run: bool,
    source: str,
    ai_score: bool,
    concurrency: int,
) -> None:
    """전체 수집 + 채점 → SQLiteStore 저장 → 알림. 소스: channels/institutions/both."""
    if dry_run:
        console.print("[cyan]dry-run[/cyan] 모드: 설정 검증만 수행")
        console.print(
            f"  source={source}  tier={tier}  site={site}  limit={limit}  "
            f"min_grade={min_grade}  notify={notify}  ai_score={ai_score}"
        )
        console.print(f"  CONFIG_DIR: {CONFIG_DIR}")
        console.print(f"  DATA_DIR: {DATA_DIR}")
        return

    all_jobs = []

    # --- Source 1: channels ---
    if source in ("channels", "both"):
        try:
            from career_ops_kr.channels import CHANNEL_REGISTRY
        except Exception as exc:
            console.print(f"[red]channels import 실패[/red]: {exc}")
            sys.exit(1)

        console.print("[cyan]채널 순회 중...[/cyan]")
        for name, cls in CHANNEL_REGISTRY.items():
            if name == "universal":
                continue  # redundant with institutions
            if site and name != site:
                continue
            if tier is not None and getattr(cls, "tier", None) != tier:
                continue
            try:
                jobs = cls().list_jobs() or []
                if jobs:
                    all_jobs.extend(jobs)
                    console.print(f"  [dim]{name}[/dim]: {len(jobs)}건")
            except Exception as exc:
                console.print(f"  [yellow]{name}[/yellow] 실패: {exc}")

    # --- Source 2: institutions (aggregator search) ---
    if source in ("institutions", "both"):
        console.print("[cyan]institutions 기관 검색 중...[/cyan]")
        try:
            from career_ops_kr.channels.universal import _load_institutions
            from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser
            import re
            import time as _time
            import requests as _req
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from datetime import datetime

            insts = _load_institutions()
            if not insts:
                console.print("[yellow]institutions.yml 없음[/yellow]")
            else:
                ua = "Mozilla/5.0 career-ops-kr/0.2"
                inst_jobs: list = []

                def _search_inst(inst: dict) -> list:
                    name = re.sub(r"\(.*?\)", "", inst.get("name", "")).strip()
                    if len(name) < 2:
                        return []
                    from urllib.parse import quote
                    url = (
                        f"https://www.wanted.co.kr/api/v4/jobs"
                        f"?query={quote(name)}&country=kr&job_sort=job.latest_order"
                        f"&years=-1&limit=5&offset=0"
                    )
                    try:
                        resp = _req.get(url, headers={"User-Agent": ua}, timeout=8)
                        if resp.status_code != 200:
                            return []
                        items = resp.json().get("data", [])
                    except Exception:
                        return []
                    results = []
                    now = datetime.now()
                    for item in items[:5]:
                        try:
                            jid = str(item.get("id", ""))
                            co = item.get("company", {}).get("name", "")
                            title = item.get("position", "") or item.get("title", "")
                            jurl = f"https://www.wanted.co.kr/wd/{jid}"
                            if not title:
                                continue
                            # fuzzy match
                            if name not in co and co not in name:
                                try:
                                    from fuzzywuzzy import fuzz
                                    if fuzz.partial_ratio(name, co) < 60:
                                        continue
                                except ImportError:
                                    if name.lower() not in co.lower():
                                        continue
                            results.append(JobRecord(
                                id=BaseChannel._make_id(jurl, title[:120]),
                                source_url=jurl, source_channel="wanted",
                                source_tier=1, org=co or name, title=title[:200],
                                description=title, legitimacy_tier="T1", scanned_at=now,
                            ))
                        except Exception:
                            continue
                    return results

                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures = {pool.submit(_search_inst, i): i["name"] for i in insts}
                    for f in as_completed(futures):
                        try:
                            jobs = f.result()
                            inst_jobs.extend(jobs)
                        except Exception:
                            pass

                all_jobs.extend(inst_jobs)
                console.print(f"  [dim]institutions[/dim]: {len(inst_jobs)}건")
        except Exception as exc:
            console.print(f"[yellow]institutions 검색 실패[/yellow]: {exc}")

    # 중복 제거
    seen_ids: set[str] = set()
    unique_jobs = []
    for j in all_jobs:
        if j.id not in seen_ids:
            seen_ids.add(j.id)
            unique_jobs.append(j)
    all_jobs = unique_jobs

    console.print(f"[green]수집 완료[/green] 총 {len(all_jobs)}건 (중복 제거)")

    if not all_jobs:
        console.print("[yellow]수집된 공고 없음[/yellow]")
        return

    # G4 게이트 — 5건 이상
    if len(all_jobs) >= 5:
        console.print(f"[yellow]G4 게이트[/yellow]: {len(all_jobs)}건 채점 예정")
        if not Confirm.ask("���속 진행?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return

    target = min(limit, len(all_jobs))
    store = get_store()
    saved = 0

    # --- AI 채점 (Ollama/OpenRouter) ---
    if ai_score:
        client, model = get_ai_client_or_fallback()
        if client is None:
            console.print("[yellow]AI 비활성화 — rule-based 채점으로 대체[/yellow]")
            ai_score = False
        else:
            console.print(f"[green]AI 채점 활성화[/green] model={model}")

    if ai_score and client is not None:
        # Ollama/OpenRouter AI scoring path
        from career_ops_kr.ai.scorer import score_jobs_batch
        from career_ops_kr.ai.summarizer import summarize_jobs_batch

        profile = load_profile()
        target_jobs = all_jobs[:target]

        console.print(f"[cyan]요약 중...[/cyan] {len(target_jobs)}건")
        summaries = summarize_jobs_batch(target_jobs, client, model)

        console.print(f"[cyan]AI 채점 중...[/cyan] {len(target_jobs)}건")
        scores = score_jobs_batch(
            target_jobs, summaries, profile, client, model,
            request_delay=0.5,
            on_progress=lambda done, total: None,
        )

        for job, (score, reason) in zip(target_jobs, scores):
            grade_letter = (
                "A" if score >= 85 else "B" if score >= 70
                else "C" if score >= 55 else "D" if score >= 40 else "F"
            )
            if grade_ge(grade_letter, min_grade) and store is not None:
                try:
                    store.upsert(job, fit={
                        "grade": grade_letter,
                        "total_score": score,
                        "reasons": [reason],
                    })
                    saved += 1
                except Exception:
                    pass
    else:
        # Rule-based scoring (mcp.tool_score_job)
        try:
            from career_ops_kr import mcp_server as mcp
        except Exception as exc:
            console.print(f"[red]mcp_server import 실패[/red]: {exc}")
            sys.exit(1)

        with Progress(*_PROGRESS_COLS, console=console, transient=True) as prog:
            task = prog.add_task("[cyan]채점[/cyan]", total=target)
            for job in all_jobs[:target]:
                url = str(job.source_url)
                try:
                    result = mcp.tool_score_job(url=url)
                    if isinstance(result, dict) and "error" not in result:
                        if grade_ge(result.get("grade") or "", min_grade) and store is not None:
                            try:
                                store.upsert(job, fit=result)
                                saved += 1
                            except Exception:
                                pass
                except Exception:
                    pass
                prog.advance(task)

    console.print(
        f"[green]완료[/green] 채점 {target}건 → {min_grade}+ 등급 저장 {saved}건"
    )

    if notify and store is not None:
        _send_notification(store, load_profile())


def _run_sample(url: str) -> None:
    """샘플 1건 채점 후 표준 리포트 출력."""
    try:
        from career_ops_kr import mcp_server as mcp

        result = mcp.tool_score_job(url=url)
        if isinstance(result, dict) and "error" not in result:
            print_standard_report(result, console)
    except Exception as exc:
        console.print(f"[yellow]샘플 채점 실패[/yellow]: {exc}")


def _send_notification(store: object, profile: dict) -> None:
    """Discord 배치 요약 알림 전송."""
    try:
        from career_ops_kr.notifier.discord_push import DiscordNotifier

        webhook = (profile.get("discord") or {}).get("webhook_url")
        notifier = DiscordNotifier(webhook_url=webhook)
        stats = store.get_stats()  # type: ignore[union-attr]
        notifier.notify_batch_summary(stats)
        console.print("[green]Discord 알림 전송 완료[/green]")
    except Exception as exc:
        console.print(f"[yellow]Discord 알림 실패[/yellow]: {exc}")
