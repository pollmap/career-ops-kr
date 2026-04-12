"""career-ops vault-sync — SQLite → Obsidian Vault 동기화.

jobs DB에서 전체 공고를 읽어서 Obsidian 마크다운 노트로 내보낸다.
folder 매핑: status → vault folder (inbox→0-inbox, applying→4-applied 등).
"""

from __future__ import annotations

import click
from rich.table import Table

from career_ops_kr.commands._shared import console, get_store


_STATUS_TO_FOLDER: dict[str, str] = {
    "inbox": "0-inbox",
    "eligible": "1-eligible",
    "graded": "1-eligible",
    "applying": "4-applied",
    "rejected": "3-rejected",
    "archived": "3-rejected",
}


@click.command("vault-sync")
@click.option("--path", type=click.Path(), default=None, help="Vault 루트 경로 (기본: ~/obsidian-vault/career-ops)")
@click.option("--dry-run", "dry_run", is_flag=True, help="실제 파일 생성 없이 미리보기")
@click.option("--index", "write_idx", is_flag=True, help="_index.md 생성")
def vault_sync_cmd(path: str | None, dry_run: bool, write_idx: bool) -> None:
    """SQLite DB → Obsidian Vault 마크다운 노트 동기화."""
    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음[/yellow] — career-ops scan 먼저 실행하세요.")
        return

    try:
        all_jobs = store.search(keyword="")
    except Exception as exc:
        console.print(f"[red]DB 조회 실패[/red]: {exc}")
        return

    if not all_jobs:
        console.print("[yellow]DB에 공고 없음[/yellow]")
        return

    if dry_run:
        table = Table(title="Vault Sync 미리보기", show_lines=False)
        table.add_column("status", style="cyan")
        table.add_column("folder", style="green")
        table.add_column("org")
        table.add_column("title")
        for job in all_jobs[:20]:
            status = job.get("status") or "inbox"
            folder = _STATUS_TO_FOLDER.get(status, "0-inbox")
            table.add_row(
                status,
                folder,
                str(job.get("org", ""))[:20],
                str(job.get("title", ""))[:40],
            )
        console.print(table)
        if len(all_jobs) > 20:
            console.print(f"[dim]... +{len(all_jobs) - 20}건 더[/dim]")
        console.print(f"\n[cyan]총 {len(all_jobs)}건[/cyan] 동기화 대상 (--dry-run)")
        return

    # 실제 동기화
    try:
        from career_ops_kr.storage.vault_sync import VaultSync
        from career_ops_kr.channels.base import JobRecord
    except ImportError as exc:
        console.print(f"[red]VaultSync import 실패[/red]: {exc}")
        return

    vault = VaultSync(vault_root=path)
    synced = 0
    for job_dict in all_jobs:
        status = job_dict.get("status") or "inbox"
        folder = _STATUS_TO_FOLDER.get(status, "0-inbox")
        try:
            record = JobRecord(
                id=job_dict["id"],
                source_url=job_dict["source_url"],
                source_channel=job_dict.get("source_channel", "unknown"),
                source_tier=int(job_dict.get("source_tier", 5)),
                org=job_dict.get("org", ""),
                title=job_dict.get("title", ""),
                archetype=job_dict.get("archetype"),
                location=job_dict.get("location"),
                description=job_dict.get("description", ""),
                legitimacy_tier=job_dict.get("legitimacy_tier", "T5"),
            )
        except Exception:
            continue

        fit = {
            "grade": job_dict.get("fit_grade", ""),
            "score": job_dict.get("fit_score", ""),
            "eligible": job_dict.get("eligible") == "true",
        }
        vault.upsert_note(record, folder=folder, fit=fit)
        synced += 1

    console.print(f"[green]Vault 동기화 완료[/green] {synced}/{len(all_jobs)}건 → {vault.vault_root}")

    if write_idx:
        idx_path = vault.write_index()
        console.print(f"[green]_index.md 생성[/green] → {idx_path}")
