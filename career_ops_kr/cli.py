"""career-ops-kr CLI entry point.

Click-based command-line interface. Provides commands for scan/score/pipeline/list
and graceful fallbacks when subpackage imports fail.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

# Project root assumed to be CWD; avoid ~/.career-ops/config.yml
PROJECT_ROOT = Path.cwd()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
MODES_DIR = PROJECT_ROOT / "modes"


def _fallback_import(module_name: str, what_for: str) -> Any:
    """Import with graceful error. Returns module or None and prints fix."""
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as exc:
        console.print(
            f"[red]ERROR[/red] cannot import [bold]{module_name}[/bold] "
            f"(needed for {what_for}): {exc}"
        )
        console.print(
            "[yellow]Fix:[/yellow] run [bold]pip install -e .[dev][/bold] "
            "from the project root, and verify package layout under career_ops_kr/."
        )
        return None


def _ensure_project_dirs() -> None:
    for d in (CONFIG_DIR, DATA_DIR, MODES_DIR):
        d.mkdir(parents=True, exist_ok=True)


@click.group(help="career-ops-kr — 한국형 구직 자동화 CLI (Luxon AI)")
@click.version_option("0.2.0", prog_name="career-ops")
def cli() -> None:
    """Root group."""
    _ensure_project_dirs()


def _load_preset_loader() -> Any:
    """Import PresetLoader with graceful fallback.

    Returns the PresetLoader class or None if unavailable.
    Printed message guides the user to install the presets module
    (which is delivered by a parallel implementation track).
    """
    try:
        from career_ops_kr.presets.loader import PresetLoader

        return PresetLoader
    except Exception as exc:
        console.print(
            "[yellow]preset 기능을 사용하려면 career_ops_kr.presets 모듈이 필요합니다[/yellow]"
        )
        console.print(f"[dim]import error: {exc}[/dim]")
        console.print(
            "[dim]docs/presets.md 참조 — 해당 모듈이 아직 배포되지 않았다면 "
            "interactive 모드(`career-ops init`)를 사용하세요.[/dim]"
        )
        return None


def _show_preset_list() -> int:
    """Print rich table of available presets. Returns exit code."""
    loader_cls = _load_preset_loader()
    if loader_cls is None:
        return 2
    try:
        loader = loader_cls()
        presets = loader.list_available()
    except Exception as exc:
        console.print(f"[red]preset 목록 조회 실패[/red] {exc}")
        return 2

    table = Table(title="사용 가능한 프리셋")
    table.add_column("preset_id", style="cyan")
    table.add_column("label_ko")
    table.add_column("description", style="dim")
    for p in presets:
        table.add_row(
            str(p.get("preset_id", "")),
            str(p.get("label_ko", "")),
            str(p.get("description", "")),
        )
    console.print(table)
    console.print("[dim]사용법: [bold]career-ops init --preset <preset_id>[/bold][/dim]")
    return 0


def _apply_preset(preset_id: str, force: bool) -> int:
    """Apply a preset to config/ + modes/_profile.md with HITL G1 gate.

    Returns exit code.
    """
    loader_cls = _load_preset_loader()
    if loader_cls is None:
        return 2
    try:
        loader = loader_cls()
        preset = loader.load(preset_id)
    except Exception as exc:
        console.print(f"[red]preset '{preset_id}' 로드 실패[/red] {exc}")
        return 2

    label = preset.get("label_ko", preset_id) if isinstance(preset, dict) else preset_id
    console.print(
        Panel.fit(
            f"[bold]{preset_id}[/bold] — {label}\n"
            f"[dim]대상 디렉토리: {CONFIG_DIR}[/dim]\n"
            f"[dim]overwrite: {force}[/dim]",
            title="preset apply plan",
            border_style="cyan",
        )
    )

    existing: list[Path] = []
    for name in (
        "profile.yml",
        "portals.yml",
        "qualifier_rules.yml",
        "scoring_weights.yml",
    ):
        p = CONFIG_DIR / name
        if p.exists():
            existing.append(p)
    if (MODES_DIR / "_profile.md").exists():
        existing.append(MODES_DIR / "_profile.md")

    if existing and not force:
        console.print("[yellow]다음 파일이 이미 존재합니다 (덮어쓰지 않음):[/yellow]")
        for p in existing:
            console.print(f"  - {p}")
        console.print("[dim]덮어쓰려면 --force 플래그를 사용하세요.[/dim]")

    # HITL G1: always confirm before writing
    if not Confirm.ask(f"프리셋 [bold cyan]{preset_id}[/bold cyan]을(를) 적용할까?", default=True):
        console.print("[yellow]aborted[/yellow]")
        return 0

    try:
        written = loader.apply_to(preset_id, CONFIG_DIR, overwrite=force)
    except Exception as exc:
        console.print(f"[red]preset 적용 실패[/red] {exc}")
        return 2

    console.print(
        Panel.fit(
            "\n".join(f"[green]created[/green] {k}: {v}" for k, v in written.items())
            or "[dim](no files written)[/dim]",
            title=f"preset '{preset_id}' applied",
            border_style="green",
        )
    )
    console.print(
        "[dim]다음: [bold]career-ops init[/bold] (인터뷰 모드)로 cv.md를 마저 채우거나, "
        "docs/presets.md 에서 프리셋별 세부 지침을 확인하세요.[/dim]"
    )
    return 0


@cli.command("init", help="G1 온보딩 — 누락 유저 파일 생성 (cv.md / config.yml / _profile.md)")
@click.option(
    "--preset",
    "preset",
    type=str,
    default=None,
    help="도메인 프리셋: finance|dev|design|marketing|research|public|edu",
)
@click.option(
    "--list-presets",
    "list_presets",
    is_flag=True,
    help="사용 가능한 프리셋 목록 표시 후 종료",
)
@click.option(
    "--force",
    "force",
    is_flag=True,
    help="기존 config 덮어쓰기",
)
def init_cmd(preset: str | None, list_presets: bool, force: bool) -> None:
    # 1) preset 목록 표시
    if list_presets:
        code = _show_preset_list()
        if code != 0:
            sys.exit(code)
        return

    # 2) preset 적용 (HITL G1 gate)
    if preset:
        code = _apply_preset(preset, force=force)
        if code != 0:
            sys.exit(code)
        return

    # 3) 기본(기존) 인터랙티브 플로우 — 하위 호환
    cv = PROJECT_ROOT / "cv.md"
    profile_yml = CONFIG_DIR / "profile.yml"
    profile_md = MODES_DIR / "_profile.md"

    missing: list[str] = []
    if not cv.exists():
        missing.append("cv.md")
    if not profile_yml.exists():
        missing.append("config/profile.yml")
    if not profile_md.exists():
        missing.append("modes/_profile.md")

    if not missing:
        console.print("[green]OK[/green] onboarding complete — all user files present")
        return

    console.print(f"[yellow]G1 onboarding[/yellow] missing: {', '.join(missing)}")
    if not Confirm.ask("대화형 인터뷰로 생성할까?", default=True):
        console.print("[yellow]skipped[/yellow]")
        return

    if "cv.md" in missing:
        name = Prompt.ask("이름", default="이찬희")
        cv.write_text(f"# {name} 이력서\n\n(채워주세요)\n", encoding="utf-8")
        console.print(f"[green]created[/green] {cv}")

    if "config/profile.yml" in missing:
        profile_yml.write_text(
            "name: 이찬희\ntarget_industries:\n  - 금융\n  - 핀테크\n  - 블록체인\n",
            encoding="utf-8",
        )
        console.print(f"[green]created[/green] {profile_yml}")

    if "modes/_profile.md" in missing:
        tmpl = MODES_DIR / "_profile.template.md"
        if tmpl.exists():
            profile_md.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            profile_md.write_text("# Profile\n\n(placeholder)\n", encoding="utf-8")
        console.print(f"[green]created[/green] {profile_md}")


@cli.command("scan", help="스캔 모드 — 포털 크롤링 + 신규 공고 수집")
@click.option("--tier", type=int, default=None, help="특정 tier만 스캔 (1~5)")
@click.option("--site", type=str, default=None, help="특정 사이트 이름")
@click.option("--all", "all_sites", is_flag=True, help="모든 포털 스캔")
@click.option("--dry-run", is_flag=True, help="네트워크 호출 없이 설정만 검증")
def scan_cmd(tier: int | None, site: str | None, all_sites: bool, dry_run: bool) -> None:
    if dry_run:
        console.print("[cyan]dry-run[/cyan] scan config OK — no network calls")
        table = Table(title="Scan plan")
        table.add_column("filter")
        table.add_column("value")
        table.add_row("tier", str(tier) if tier else "(any)")
        table.add_row("site", site or "(any)")
        table.add_row("all", str(all_sites))
        console.print(table)
        return

    mcp = _fallback_import("career_ops_kr.mcp_server", "scan mode")
    if mcp is None:
        sys.exit(2)

    console.print(f"[green]scan[/green] tier={tier} site={site} all={all_sites}")
    try:
        result = mcp.tool_scan_jobs(tier=tier, site=site)
    except Exception as exc:
        console.print(f"[red]scan failed[/red] {exc}")
        sys.exit(1)

    if isinstance(result, dict) and "error" in result:
        console.print(f"[red]scan error[/red] {result['error']}")
        hint = result.get("hint")
        if hint:
            console.print(f"[dim]hint: {hint}[/dim]")
        sys.exit(1)

    table = Table(title=f"Scan results (total={result.get('total', 0)})")
    table.add_column("channel", style="cyan")
    table.add_column("tier", justify="right")
    table.add_column("backend", style="dim")
    table.add_column("count", justify="right")
    table.add_column("error", style="red")

    channels_summary: dict[str, Any] = result.get("channels", {}) or {}
    for ch_name, info in channels_summary.items():
        info = info or {}
        table.add_row(
            ch_name,
            str(info.get("tier", "")),
            str(info.get("backend", "")),
            str(info.get("count", 0)),
            str(info.get("error", "") or ""),
        )
    console.print(table)


@cli.command("score", help="단일 URL 평가 — markdown 리포트 출력")
@click.argument("url")
def score_cmd(url: str) -> None:
    if "://" not in url or url.startswith("invalid"):
        console.print(f"[red]invalid URL[/red] {url}")
        sys.exit(1)

    mcp = _fallback_import("career_ops_kr.mcp_server", "score mode")
    if mcp is None:
        sys.exit(2)

    console.print(f"[green]scoring[/green] {url}")
    try:
        result = mcp.tool_score_job(url=url)
    except Exception as exc:
        console.print(f"[red]score failed[/red] {exc}")
        sys.exit(1)

    if isinstance(result, dict) and "error" in result:
        console.print(f"[red]score error[/red] {result['error']}")
        hint = result.get("hint")
        if hint:
            console.print(f"[dim]hint: {hint}[/dim]")
        sys.exit(1)

    url_out = result.get("url", url)
    legitimacy = result.get("legitimacy") or "T5 미확인"
    archetype = result.get("archetype") or "(미판정)"
    grade = result.get("grade") or "(미평가)"
    total = result.get("total_score")
    fit_grade_line = f"{grade}" + (f" ({total})" if total is not None else "")
    eligibility = result.get("qualifier_verdict") or "(미판정)"
    deadline = result.get("deadline") or "(미상)"
    org = result.get("org") or ""
    title = result.get("title") or ""
    reasons = result.get("reasons") or []

    lines = [
        f"**URL:** {url_out}",
        f"**Legitimacy:** {legitimacy}",
        f"**Archetype:** {archetype}",
        f"**Fit Grade:** {fit_grade_line}",
        f"**Eligibility:** {eligibility}",
        f"**Deadline:** {deadline}",
    ]
    if org or title:
        lines.append(f"**Org / Title:** {org} / {title}")
    if reasons:
        lines.append("")
        lines.append("**Reasons:**")
        for r in reasons:
            lines.append(f"- {r}")

    console.print(
        Panel.fit(
            "\n".join(lines),
            title="score report",
            border_style="green",
        )
    )


@cli.command("pipeline", help="배치 평가 — inbox 전체 (G4 게이트)")
@click.option("--limit", type=int, default=10)
def pipeline_cmd(limit: int) -> None:
    if limit >= 5:
        console.print(f"[yellow]G4 batch gate[/yellow] {limit}건 일괄 평가 예정")
        if not Confirm.ask("샘플 1건 후 계속 진행?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return
    console.print(f"[green]pipeline[/green] processing up to {limit} items")

    db = DATA_DIR / "jobs.db"
    if not db.exists():
        console.print(
            "[yellow]inbox empty[/yellow] (no jobs.db — run [bold]career-ops scan[/bold] first)"
        )
        return

    mcp = _fallback_import("career_ops_kr.mcp_server", "pipeline mode")
    store_mod = _fallback_import("career_ops_kr.storage.sqlite_store", "pipeline mode")
    if mcp is None or store_mod is None:
        sys.exit(2)

    try:
        store = store_mod.SQLiteStore(db)
    except Exception as exc:
        console.print(f"[red]SQLiteStore init failed[/red] {exc}")
        sys.exit(1)

    # Pull inbox-status jobs (ungraded) — use search() with empty keyword.
    try:
        inbox = store.search(keyword="")
    except Exception as exc:
        console.print(f"[red]inbox query failed[/red] {exc}")
        sys.exit(1)

    inbox = [j for j in inbox if (j.get("status") or "inbox") == "inbox"]
    if not inbox:
        console.print("[yellow]no inbox items[/yellow]")
        return

    table = Table(title=f"pipeline results ({min(limit, len(inbox))}/{len(inbox)})")
    table.add_column("org", style="cyan")
    table.add_column("title")
    table.add_column("grade", justify="center")
    table.add_column("score", justify="right")
    table.add_column("error", style="red")

    processed = 0
    for job in inbox[:limit]:
        url = job.get("source_url") or ""
        if not url:
            continue
        try:
            result = mcp.tool_score_job(url=url)
        except Exception as exc:
            table.add_row(str(job.get("org") or ""), str(job.get("title") or ""), "", "", str(exc))
            processed += 1
            continue

        if isinstance(result, dict) and "error" in result:
            table.add_row(
                str(job.get("org") or ""),
                str(job.get("title") or ""),
                "",
                "",
                str(result.get("error", "")),
            )
        else:
            table.add_row(
                str(result.get("org") or ""),
                str(result.get("title") or ""),
                str(result.get("grade") or ""),
                str(result.get("total_score") or ""),
                "",
            )
        processed += 1

    console.print(table)
    console.print(f"[dim]processed {processed} item(s)[/dim]")


@cli.command("list", help="SQLite 조회 — 저장된 공고 테이블 출력")
@click.option("--grade", type=str, default=None)
@click.option("--status", type=str, default=None)
@click.option("--archetype", type=str, default=None)
def list_cmd(grade: str | None, status: str | None, archetype: str | None) -> None:
    db = DATA_DIR / "jobs.db"
    if not db.exists():
        console.print("[yellow]no jobs found[/yellow] (empty DB)")
        return

    store_mod = _fallback_import("career_ops_kr.storage.sqlite_store", "list mode")
    if store_mod is None:
        sys.exit(2)

    try:
        store = store_mod.SQLiteStore(db)
    except Exception as exc:
        console.print(f"[red]SQLiteStore init failed[/red] {exc}")
        sys.exit(1)

    try:
        if grade:
            jobs = store.list_by_grade(grade)
        elif archetype:
            jobs = store.search(keyword="", archetype=archetype)
        else:
            jobs = store.search(keyword="")
    except Exception as exc:
        console.print(f"[red]query failed[/red] {exc}")
        sys.exit(1)

    if status:
        jobs = [j for j in jobs if (j.get("status") or "") == status]

    if not jobs:
        console.print("[yellow]no jobs found[/yellow] (filter matched 0 rows)")
        console.print(f"[dim]filters: grade={grade} status={status} archetype={archetype}[/dim]")
        return

    table = Table(title=f"Jobs ({len(jobs)})")
    for col in ("id", "org", "title", "grade", "status", "deadline"):
        table.add_column(col)
    for job in jobs:
        table.add_row(
            str(job.get("id") or "")[:12],
            str(job.get("org") or ""),
            str(job.get("title") or ""),
            str(job.get("fit_grade") or ""),
            str(job.get("status") or ""),
            str(job.get("deadline") or ""),
        )
    console.print(table)
    console.print(f"[dim]filters: grade={grade} status={status} archetype={archetype}[/dim]")


@cli.command("sync-vault", help="SQLite → Obsidian Vault 동기화")
def sync_vault_cmd() -> None:
    storage = _fallback_import("career_ops_kr.storage", "vault sync")
    if storage is None:
        sys.exit(2)
    console.print("[green]sync-vault[/green] delegated to storage subpackage")


@cli.command("calendar", help=".ics 파일 생성 — 마감일 일정")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=PROJECT_ROOT / "output" / "deadlines.ics",
)
@click.option("--days", type=int, default=30, help="Deadline window in days")
def calendar_cmd(output: Path, days: int) -> None:
    try:
        from career_ops_kr.calendar.ics_export import CalendarExporter
    except Exception as exc:
        console.print(f"[red]calendar import failed[/red] {exc}")
        sys.exit(2)

    jobs: list[dict[str, Any]] = []
    db = DATA_DIR / "jobs.db"
    if db.exists():
        store_mod = _fallback_import("career_ops_kr.storage.sqlite_store", "calendar mode")
        if store_mod is not None:
            try:
                store = store_mod.SQLiteStore(db)
                jobs = list(store.list_upcoming_deadlines(days=days))
            except Exception as exc:
                console.print(
                    f"[yellow]deadline query failed — writing empty calendar[/yellow] {exc}"
                )
                jobs = []

    output.parent.mkdir(parents=True, exist_ok=True)
    exporter = CalendarExporter()
    path = exporter.from_jobs(jobs, output)
    console.print(f"[green]calendar[/green] written {path} ({len(jobs)} job(s))")


@cli.command("patterns", help="패턴 분석 모드 — N일치 잡 히스토리")
@click.option("--days", type=int, default=7)
def patterns_cmd(days: int) -> None:
    console.print(f"[green]patterns[/green] last {days} days")


@cli.command("verify", help="데이터 무결성 검증 — verify_pipeline.py")
def verify_cmd() -> None:
    script = PROJECT_ROOT / "scripts" / "verify_pipeline.py"
    if not script.exists():
        # Empty project counts as clean
        console.print("[green]verify[/green] clean (no pipeline script, nothing to verify)")
        return
    console.print(f"[green]verify[/green] {script}")


@cli.command("dedup", help="중복 제거 — dedup_tracker.py")
@click.option("--apply", is_flag=True, help="실제 적용 (기본은 dry-run)")
def dedup_cmd(apply: bool) -> None:
    mode = "apply" if apply else "dry-run"
    console.print(f"[green]dedup[/green] mode={mode}")


@cli.command("ui", help="TUI 대시보드 실행 — Textual 기반")
def ui_cmd() -> None:
    """TUI 대시보드 실행 — Textual 기반."""
    try:
        from career_ops_kr.tui.app import run_tui
    except ImportError as exc:
        console.print(
            "[red]textual 패키지가 필요합니다.[/red]\n"
            "설치: [bold]pip install 'career-ops-kr\\[tui]'[/bold]\n"
            f"[dim]import error: {exc}[/dim]"
        )
        sys.exit(1)
    run_tui()


@cli.command("login", help="Playwright 수동 로그인 — storage_state 저장")
@click.argument("site")
def login_cmd(site: str) -> None:
    console.print(f"[green]login[/green] {site} (Playwright UI will open)")
    state_dir = DATA_DIR / "auth"
    state_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[dim]storage_state will be saved to {state_dir / f'{site}.json'}[/dim]")


@cli.command("ai-rank", help="AI 적합도 채점 + 우선순위 랭킹 (OpenRouter 필요)")
@click.option("--site", type=str, default=None, help="특정 채널만 스캔 (기본: 전체)")
@click.option("--model", type=str, default=None, help="OpenRouter 모델 ID (기본: 환경변수 또는 gemini-flash-free)")
@click.option("--top", type=int, default=5, help="상위 N개 출력 (기본: 5)")
@click.option("--api-key", "api_key", type=str, default=None, help="OpenRouter API 키 (기본: OPENROUTER_API_KEY 환경변수)")
def ai_rank_cmd(
    site: str | None,
    model: str | None,
    top: int,
    api_key: str | None,
) -> None:
    """27개 채널 스캔 → AI 요약 → 적합도 채점 → Top N 우선순위 출력."""
    import yaml

    # --- 1. AI 모듈 + 채널 레지스트리 임포트 ---
    try:
        from career_ops_kr.ai.client import DEFAULT_MODEL, get_client
        from career_ops_kr.ai.ranker import rank_jobs
        from career_ops_kr.ai.scorer import score_jobs_batch
        from career_ops_kr.ai.summarizer import summarize_jobs_batch
        from career_ops_kr.channels import CHANNEL_REGISTRY
    except ImportError as exc:
        console.print(f"[red]import error[/red] {exc}")
        console.print("[dim]openai 설치: uv add openai[/dim]")
        sys.exit(2)

    # --- 2. OpenRouter 클라이언트 초기화 ---
    try:
        client = get_client(api_key)
        _model = model or DEFAULT_MODEL
    except ValueError as exc:
        console.print(f"[red]API 키 오류[/red] {exc}")
        sys.exit(1)

    console.print(f"[dim]model: {_model}[/dim]")

    # --- 3. 공고 수집 ---
    if site:
        if site not in CHANNEL_REGISTRY:
            console.print(f"[red]unknown channel[/red] {site}")
            console.print(f"[dim]사용 가능: {', '.join(CHANNEL_REGISTRY)}[/dim]")
            sys.exit(1)
        targets: dict = {site: CHANNEL_REGISTRY[site]}
    else:
        targets = dict(CHANNEL_REGISTRY)

    console.print(f"[green]스캔 시작[/green] {len(targets)}개 채널")
    all_jobs = []
    for ch_name, cls in targets.items():
        try:
            ch = cls()
            jobs = ch.list_jobs()
            all_jobs.extend(jobs)
            if jobs:
                console.print(f"  [cyan]{ch_name}[/cyan] {len(jobs)}개")
        except Exception as exc:
            console.print(f"  [dim]{ch_name}: {exc}[/dim]")

    if not all_jobs:
        console.print("[yellow]수집된 공고 없음[/yellow] (채널 접속 실패 또는 SPA 채널)")
        sys.exit(0)

    console.print(f"[green]총 {len(all_jobs)}개[/green] 수집 완료 → AI 분석 시작")

    # --- 4. AI 요약 ---
    console.print("[cyan]요약 중...[/cyan]", end=" ")
    summaries = summarize_jobs_batch(all_jobs, client, _model)
    console.print("[green]완료[/green]")

    # --- 5. profile.yml 로드 ---
    profile: dict = {}
    profile_path = CONFIG_DIR / "profile.yml"
    if profile_path.exists():
        try:
            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            console.print(f"[yellow]profile.yml 로드 실패 (채점 정확도 낮음)[/yellow] {exc}")
    else:
        console.print("[yellow]config/profile.yml 없음 — 기본 채점 적용[/yellow]")

    # --- 6. AI 채점 ---
    console.print("[cyan]채점 중...[/cyan]", end=" ")
    fit_scores = score_jobs_batch(all_jobs, summaries, profile, client, _model)
    console.print("[green]완료[/green]")

    # --- 7. 랭킹 ---
    ranked = rank_jobs(all_jobs, fit_scores, summaries, top_n=top)

    # --- 8. Rich 테이블 출력 ---
    table = Table(title=f"AI 추천 Top {len(ranked)} (전체 {len(all_jobs)}개 분석)")
    table.add_column("#", justify="right", style="bold")
    table.add_column("org", style="cyan")
    table.add_column("title")
    table.add_column("archetype", style="dim")
    table.add_column("fit", justify="right")
    table.add_column("total", justify="right", style="bold green")
    table.add_column("D-day", justify="right")
    table.add_column("이유", style="dim")

    for i, r in enumerate(ranked, 1):
        days = r.days_left
        if days is None:
            dday = "-"
        elif days < 0:
            dday = f"[red]D+{abs(days)}[/red]"
        elif days == 0:
            dday = "[red]오늘[/red]"
        elif days <= 3:
            dday = f"[red]D-{days}[/red]"
        elif days <= 7:
            dday = f"[yellow]D-{days}[/yellow]"
        else:
            dday = f"D-{days}"

        table.add_row(
            str(i),
            r.job.org[:20],
            r.job.title[:35],
            r.job.archetype or "-",
            str(r.fit_score),
            str(r.total_score),
            dday,
            r.fit_reason[:40] if r.fit_reason else "-",
        )

    console.print(table)
    console.print(
        f"[dim]모델: {_model} | "
        f"fit=AI채점(0~100) | total=fit+마감긴급도+archetype보너스[/dim]"
    )

    # --- 9. 상세 패널 (Top 3) ---
    for i, r in enumerate(ranked[:3], 1):
        summary_text = r.summary or "(요약 없음)"
        console.print(
            Panel.fit(
                f"[bold]{r.job.title}[/bold]  —  {r.job.org}\n"
                f"[dim]URL:[/dim] {r.job.source_url}\n"
                f"[dim]요약:[/dim] {summary_text}\n"
                f"[dim]이유:[/dim] {r.fit_reason}",
                title=f"#{i} total={r.total_score}",
                border_style="cyan" if i == 1 else "dim",
            )
        )


def main() -> None:
    """Entry point for [project.scripts] career-ops = cli:main."""
    try:
        cli(standalone_mode=True)
    except click.ClickException:
        raise
    except Exception as exc:
        console.print(f"[red]unexpected error[/red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
