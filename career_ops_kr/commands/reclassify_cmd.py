"""`career-ops reclassify` — 공고 archetype 일괄 재분류.

채널들이 채용공고 수집 시 `archetype`을 비워두거나 (``None``) 로컬 임시
문자열(``"INTERN"``, ``"GENERAL"`` 등)로 채운다. 이 커맨드는
:class:`ArchetypeClassifier`를 전체 DB에 일괄 적용해 ``Archetype`` enum
값(``FINANCIAL_IT``, ``PUBLIC_FINANCE`` 등)으로 정규화한다.

Usage::

    career-ops reclassify               # 미분류(NULL/UNKNOWN/비정규값)만
    career-ops reclassify --all         # 전체 재분류 (기존값 덮어쓰기)
    career-ops reclassify --dry-run     # 실제 UPDATE 없이 집계만
"""

from __future__ import annotations

import click

from career_ops_kr.archetype.classifier import Archetype, ArchetypeClassifier
from career_ops_kr.commands._shared import console, get_store


_VALID_ARCHETYPES: frozenset[str] = frozenset(a.value for a in Archetype)


@click.command("reclassify", help="공고 archetype 일괄 재분류 (classifier 적용)")
@click.option(
    "--all",
    "reclassify_all",
    is_flag=True,
    help="전체 재분류 (기본: NULL/비정규값만)",
)
@click.option("--dry-run", is_flag=True, help="실제 UPDATE 없이 분류 결과만 집계")
@click.option(
    "--min-confidence",
    type=float,
    default=0.35,
    show_default=True,
    help="최소 confidence (미만이면 UNKNOWN 유지)",
)
def reclassify_cmd(reclassify_all: bool, dry_run: bool, min_confidence: float) -> None:
    """Reclassify job archetypes using the central ArchetypeClassifier."""
    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음 — career-ops scan 먼저 실행[/yellow]")
        return

    classifier = ArchetypeClassifier()

    with store._connect() as conn:  # type: ignore[attr-defined]
        rows = conn.execute(
            "SELECT id, archetype, title, description, org FROM jobs"
        ).fetchall()

    targets: list[dict] = []
    for row in rows:
        d = dict(row)
        current = d.get("archetype")
        needs_reclassify = (
            reclassify_all
            or current is None
            or current == ""
            or current not in _VALID_ARCHETYPES
        )
        if needs_reclassify:
            targets.append(d)

    console.print(
        f"[cyan]총 공고[/cyan] {len(rows)} | [cyan]재분류 대상[/cyan] {len(targets)}"
    )

    if not targets:
        console.print("[green]재분류할 공고 없음[/green]")
        return

    updates: list[tuple[str | None, str]] = []
    dist: dict[str, int] = {}
    for row in targets:
        text_parts = [
            row.get("title") or "",
            row.get("description") or "",
            row.get("org") or "",
        ]
        text = " ".join(p for p in text_parts if p)
        archetype, conf = classifier.classify(text)
        if archetype is Archetype.UNKNOWN or conf < min_confidence:
            new_value: str | None = None
            dist["UNKNOWN"] = dist.get("UNKNOWN", 0) + 1
        else:
            new_value = archetype.value
            dist[new_value] = dist.get(new_value, 0) + 1
        updates.append((new_value, str(row["id"])))

    console.print("\n[bold]분류 결과 분포:[/bold]")
    for code, count in sorted(dist.items(), key=lambda x: -x[1]):
        pct = count * 100.0 / len(targets)
        console.print(f"  {code:<18} {count:>4}  ({pct:5.1f}%)")

    if dry_run:
        console.print("\n[cyan]dry-run[/cyan] — UPDATE 건너뜀")
        return

    with store._connect() as conn:  # type: ignore[attr-defined]
        conn.executemany(
            "UPDATE jobs SET archetype = ? WHERE id = ?",
            updates,
        )
        conn.commit()

    classified = len(targets) - dist.get("UNKNOWN", 0)
    console.print(
        f"\n[green]완료[/green] {len(updates)}건 UPDATE "
        f"(분류됨 {classified}, UNKNOWN {dist.get('UNKNOWN', 0)})"
    )
