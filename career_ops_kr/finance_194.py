"""
한국 금융권 194개 기관 쿼리 모듈.

Data source: `data/finance-194.json` (gitignored — 개인 적합도 평가 포함).
Generated from: 금융권_194개_전수조사_취업전략.xlsx (찬희 수기 정리본).

Public API
----------
- load_institutions()           : 전체 row 반환
- by_fit_grade(grade)           : S/A/B/C/D 등급 필터
- plan_a_targets()              : S+A 등급만 (Plan A 집중공략 대상)
- by_sector(sector)             : 섹터 이름으로 필터
- search(query)                 : 기관명·특징 전문검색
- sector_counts()               : {sector: count} 집계
- pick_top(limit, by='fit_grade'): 정렬 후 상위 N개

데이터는 공개 repo에 포함되지 않는다 (personal fit_grade 포함).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

__all__ = [
    "Institution",
    "load_institutions",
    "by_fit_grade",
    "plan_a_targets",
    "by_sector",
    "search",
    "sector_counts",
    "pick_top",
    "DATA_PATH",
]

# `career_ops_kr/finance_194.py` → 프로젝트 루트의 `data/finance-194.json`
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "finance-194.json"

Institution = dict[str, str | None]

FIT_GRADE_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}


class FinanceDataMissingError(FileNotFoundError):
    """data/finance-194.json 이 아직 배치되지 않았을 때."""


@lru_cache(maxsize=1)
def load_institutions() -> list[Institution]:
    """전체 194 기관 row 반환. 없으면 친절한 에러."""
    if not DATA_PATH.exists():
        raise FinanceDataMissingError(
            f"{DATA_PATH} 가 없습니다. "
            "Margin repo scripts/parse-finance-194.py 로 생성 후 "
            "data/finance-194.json 경로에 배치하세요."
        )
    with DATA_PATH.open(encoding="utf-8") as f:
        payload = json.load(f)
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("Unexpected data shape: rows must be a list.")
    return rows


def by_fit_grade(grade: str) -> list[Institution]:
    """적합도 등급(S/A/B/C/D) 필터."""
    normalized = grade.strip().upper()
    return [r for r in load_institutions() if r.get("fit_grade") == normalized]


def plan_a_targets() -> list[Institution]:
    """Plan A 집중공략 대상 (S + A, 약 30개)."""
    rows = load_institutions()
    hits = [r for r in rows if r.get("fit_grade") in ("S", "A")]
    hits.sort(key=_fit_sort_key)
    return hits


def by_sector(sector: str) -> list[Institution]:
    """섹터 이름 부분일치 필터."""
    q = sector.strip()
    return [r for r in load_institutions() if q in (r.get("sector") or "")]


def search(query: str) -> list[Institution]:
    """기관명·특징 부분일치 검색."""
    q = query.strip().lower()
    if not q:
        return []
    out: list[Institution] = []
    for r in load_institutions():
        blob = " ".join(
            [
                r.get("name") or "",
                r.get("sector") or "",
                r.get("features") or "",
            ]
        ).lower()
        if q in blob:
            out.append(r)
    return out


def sector_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in load_institutions():
        s = r.get("sector")
        if not s:
            continue
        counts[s] = counts.get(s, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _fit_sort_key(r: Institution) -> tuple[int, int]:
    grade = r.get("fit_grade") or "D"
    g_order = FIT_GRADE_ORDER.get(grade, 99)
    try:
        no = int(r.get("no") or 999)
    except (TypeError, ValueError):
        no = 999
    return (g_order, no)


def pick_top(
    limit: int = 10,
    by: str = "fit_grade",
    rows: Iterable[Institution] | None = None,
) -> list[Institution]:
    """정렬 키로 상위 N개 뽑기. 기본: fit_grade 오름차순(S→D)."""
    src = list(rows) if rows is not None else load_institutions()
    if by == "fit_grade":
        src.sort(key=_fit_sort_key)
    else:
        src.sort(key=lambda r: (r.get(by) or ""))
    return src[:limit]


if __name__ == "__main__":
    # Quick smoke: print Plan A summary
    try:
        targets = plan_a_targets()
    except FinanceDataMissingError as e:
        print(f"[finance_194] {e}")
        raise SystemExit(1)
    print(f"Plan A 대상: {len(targets)} 개 (S+A)")
    for r in targets:
        print(
            f"  [{r.get('fit_grade')}] {r.get('name'):<18} "
            f"· {r.get('sector'):<22} · {r.get('avg_salary')}"
        )
    print()
    print("섹터별 분포:")
    for s, n in sector_counts().items():
        print(f"  {n:3d}  {s}")
