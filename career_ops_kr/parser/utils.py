"""Parser utility functions — pure, side-effect-free normalization helpers.

한국 구직 포털에서 수집된 원시 데이터(HTML/텍스트/날짜 문자열)를
정규화된 Job dict 필드로 변환하는 순수 함수 모음. 프로젝트 전역
**single source of truth** — 다른 모듈은 이 파일의 함수만 호출하며
자체 사본을 두지 않는다.

모든 함수는 실패 시 빈 값 또는 ``None``을 반환하고 예외를 던지지 않는다.
상위 레이어(channel / JobNormalizer / FitScorer)가 결과를 보고 스킵·재시도
결정을 내린다.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from html import unescape
from typing import Any

__all__ = [
    "clean_html",
    "coerce_to_date",
    "extract_eligibility_keywords",
    "generate_job_id",
    "parse_korean_date",
]


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 2026.04.17 / 2026-04-17 / 2026/04/17 / 26.04.17
    re.compile(r"(?P<y>\d{2,4})[.\-/](?P<m>\d{1,2})[.\-/](?P<d>\d{1,2})"),
    # 2026년 4월 17일 (공백 optional)
    re.compile(r"(?P<y>\d{4})\s*년\s*(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"),
    # 4/17(금) or 4/17
    re.compile(r"(?P<m>\d{1,2})/(?P<d>\d{1,2})(?:\s*\([월화수목금토일]\))?"),
    # 4월 17일
    re.compile(r"(?P<m>\d{1,2})\s*월\s*(?P<d>\d{1,2})\s*일"),
)


def parse_korean_date(raw: str, *, default_year: int | None = None) -> date | None:
    """한국식 날짜 표기를 ``date`` 객체로 파싱.

    지원 포맷:
        - ``2026.04.17`` / ``2026-04-17`` / ``2026/04/17``
        - ``26.04.17`` (2자리 연도는 20xx로 자동 확장)
        - ``2026년 4월 17일``
        - ``4/17(금)`` / ``4/17``
        - ``4월 17일``

    Args:
        raw: 원본 문자열. None/빈문자열/파싱 불가 시 ``None``.
        default_year: 연도 미포함 포맷에 사용할 기본값.
            ``None`` 이면 ``datetime.now().year`` 로 동적 계산.

    Returns:
        파싱된 ``date`` 또는 ``None``. 예외를 던지지 않는다.
    """
    if not raw:
        return None
    text = raw.strip()
    if default_year is None:
        default_year = datetime.now().year
    for pat in _DATE_PATTERNS:
        match = pat.search(text)
        if match is None:
            continue
        parts = match.groupdict()
        year_raw = parts.get("y")
        if year_raw is None:
            year = default_year
        else:
            year = int(year_raw)
            if year < 100:
                year += 2000
        try:
            return date(year, int(parts["m"]), int(parts["d"]))
        except ValueError:
            return None
    return None


_ISO_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d")


def coerce_to_date(value: Any) -> date | None:
    """Coerce any reasonable value (date/datetime/str) to ``date``.

    Fast-path:
        - ``None`` → ``None``
        - ``datetime`` → ``.date()``
        - ``date`` (not datetime) → returned as-is

    String path:
        - ISO-ish: ``%Y-%m-%d`` / ``%Y.%m.%d`` / ``%Y/%m/%d``
        - Korean: any format from :func:`parse_korean_date`

    Returns ``None`` on any failure — never raises.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        for fmt in _ISO_FORMATS:
            try:
                return datetime.strptime(stripped[:10], fmt).date()
            except ValueError:
                continue
        return parse_korean_date(stripped)
    return None


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_html(raw: str) -> str:
    """HTML 문자열에서 script/style 블록 + 태그 + 엔티티 제거.

    1. ``<script>`` / ``<style>`` 블록 완전 제거 (내용 포함)
    2. 남은 HTML 태그 제거
    3. HTML 엔티티(``&amp;``, ``&nbsp;`` 등) 디코딩
    4. 연속 공백을 단일 공백으로 정규화

    가벼운 fragment 용도. raw HTML 대형 document 는 BeautifulSoup 권장.
    """
    if not raw:
        return ""
    text = _SCRIPT_RE.sub("", raw)
    text = _STYLE_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Job ID generation — project-wide single source of truth
# ---------------------------------------------------------------------------


def generate_job_id(
    url: str | dict[str, Any],
    title: str | None = None,
    *,
    org: str = "",
) -> str:
    """결정적(deterministic) 16-char SHA-256 job ID 생성.

    호출 방식 2가지 모두 지원:
        - **positional**: ``generate_job_id(url, title, org="...")``
        - **dict**:       ``generate_job_id({"url": ..., "title": ..., "org": ...})``

    Seed 포맷:
        - ``org`` 없음: ``f"{url}||{title}"`` — 구 ``BaseChannel._make_id`` 와
          **동일 해시** ⇒ 기존 저장된 id 와 호환.
        - ``org`` 있음: ``f"{url}||{title}||{org}"`` — 추가 entropy.

    충돌 확률: 10K jobs 기준 ~1e-9 (16-char hex prefix of SHA-256).
    """
    if isinstance(url, dict):
        job = url
        url_str = str(job.get("url") or "")
        title_str = str(job.get("title") or "")
        org_str = str(job.get("org") or "")
    else:
        url_str = str(url)
        title_str = str(title or "")
        org_str = org
    # url/title intentionally NOT normalized so the resulting hash is
    # byte-identical to the pre-refactor ``BaseChannel._make_id``
    # (``sha256("url||title")``). This preserves every existing stored id
    # regardless of casing/whitespace. Only the optional ``org`` component
    # is normalized since it was introduced in this refactor and has no
    # legacy hashes to protect.
    org_n = org_str.strip().lower()
    seed = f"{url_str}||{title_str}||{org_n}" if org_n else f"{url_str}||{title_str}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return digest[:16]


# ---------------------------------------------------------------------------
# Eligibility keywords — merged set (23) across utils + legacy normalizer
# ---------------------------------------------------------------------------


_ELIGIBILITY_KEYWORDS: tuple[str, ...] = (
    # 학력 단계
    "졸업자",
    "졸업예정",
    "졸업예정자",
    "재학생",
    "휴학생",
    "학부생",
    "대학원생",
    "전학년",
    "고졸",
    "대졸",
    "석사",
    "박사",
    # 전공/경력 제한
    "학력무관",
    "전공무관",
    "경력무관",
    # 채용 유형
    "인턴",
    "신입",
    "경력",
    # 정책 대상
    "청년",
    "만39세",
    "보훈",
    "장애인",
    "병역특례",
)


def extract_eligibility_keywords(text: str) -> list[str]:
    """자격 관련 키워드를 텍스트에서 추출 (중복 제거, 정의 순서 유지).

    사전 정의된 23개 키워드 중 텍스트에 등장한 것만 반환.

    Args:
        text: 검색 대상 텍스트.

    Returns:
        발견된 키워드 리스트. 비어있으면 ``[]``.
    """
    if not text:
        return []
    return [kw for kw in _ELIGIBILITY_KEYWORDS if kw in text]
