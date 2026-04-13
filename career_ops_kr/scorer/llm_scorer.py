"""LLM-backed 2nd-pass scorer for ambiguous (B/C/D) fit scores.

Complements :mod:`career_ops_kr.scorer.fit_score`. When the rule-based
:class:`FitScorer` returns a score in the 60–89 range (grades ``D``–``B``),
this module asks an LLM to re-read the JD + 사용자 profile summary + the
rule-based breakdown and return an adjusted score with reasoning.

Design principles
-----------------
1. **Optional**: if the ``anthropic`` SDK is missing, no API key is set,
   or the HTTP call fails, :meth:`LLMScorer.score` returns ``None`` and
   the caller keeps the rule-based verdict. It must NEVER raise upward.
2. **Narrow invocation window**: only called for ``60 <= rule_score < 90``.
   A/F cases stay rule-based — the LLM adds no value and just costs money.
3. **No fabrication**: the prompt forbids the model from inventing facts
   that aren't in the JD. We also filter the returned ``key_match_points``
   by keyword presence in the raw JD text before trusting them.
4. **Rate limited**: max 10 calls per rolling 60 seconds. Over the limit
   we return ``None`` rather than blocking.
5. **API key precedence**: constructor arg → ``ANTHROPIC_API_KEY`` env var
   → ``config/profile.yml > llm.api_key`` → ``None``.

Cost model
----------
Haiku 4.5 is ~$1/M input, $5/M output tokens. A typical call is
~1.5k in + ~400 out ≈ $0.0035 per ambiguous job. If the rule-based
scorer flags ~30 % of scans as ambiguous and 사용자 scans ~50 jobs/day,
that's roughly $0.05/day — effectively free, but the kill-switch above
still caps runaway usage.

File I/O uses ``encoding='utf-8'`` throughout. Py 3.11+.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from career_ops_kr.archetype import Archetype
from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def _load_applicant_summary() -> str:
    """config/profile.yml에서 지원자 프로필 요약 생성 (LLM 프롬프트용).

    개인정보 하드코딩 금지 — 사용자별 프로필을 동적으로 읽는다.
    프로필 미설정 시 범용 placeholder 반환.
    """
    try:
        from career_ops_kr.commands._shared import load_profile
        p = load_profile()
    except Exception:
        p = {}
    if not p:
        return "- (프로필 미설정 — `career-ops init` 으로 config/profile.yml 생성 권장)"

    lines: list[str] = []
    name = (p.get("name") or {}).get("ko") or (p.get("name") or {}).get("en")
    age = (p.get("birth") or {}).get("age")
    if name:
        lines.append(f"- {name}{f', {age}세' if age else ''}")

    uni = (p.get("university") or {}).get("name")
    year = p.get("year") or {}
    status = p.get("status")
    if uni:
        year_str = year.get("completed") or (f"{year.get('grade', '')}학년" if year.get("grade") else "")
        lines.append(
            f"- {uni}{f' {year_str}' if year_str else ''}{f' ({status})' if status else ''}"
        )

    major = (p.get("major") or {}).get("field")
    if major:
        is_target = (p.get("major") or {}).get("is_target_field")
        note = "" if is_target is None else (" (전공)" if is_target else " (비전공)")
        lines.append(f"- 전공: {major}{note}")

    targets = p.get("target_industries") or p.get("archetype_priority")
    if isinstance(targets, list) and targets:
        lines.append(f"- 타겟 산업: {' > '.join(str(x) for x in targets[:6])}")

    skills = p.get("skills") or p.get("strengths")
    if isinstance(skills, list) and skills:
        lines.append(f"- 강점/스킬: {', '.join(str(x) for x in skills[:8])}")

    locations = p.get("locations") or p.get("commute")
    if isinstance(locations, list) and locations:
        lines.append(f"- 통근 가능 지역: {', '.join(str(x) for x in locations[:5])}")

    return "\n".join(lines) if lines else "- (프로필 yml 존재하나 주요 필드 비어있음)"


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class LLMScoreResponse(BaseModel):
    """Validated JSON envelope returned by the LLM 2nd-pass scorer.

    Attributes:
        adjusted_score: Integer in 0..100 — may equal the rule-based score.
        reasoning: 1–3 sentences (Korean) explaining the adjustment.
        key_match_points: Up to 5 short phrases that the LLM believes
            are strong match signals, filtered against the JD keywords
            before the caller trusts them.
        concerns: Up to 5 short phrases flagging risks or mismatches.
    """

    adjusted_score: int = Field(ge=0, le=100)
    reasoning: str = Field(max_length=600)
    key_match_points: list[str] = Field(default_factory=list, max_length=5)
    concerns: list[str] = Field(default_factory=list, max_length=5)


# ---------------------------------------------------------------------------
# LLMScorer
# ---------------------------------------------------------------------------


_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_LOWER_BOUND = 60.0  # inclusive
_UPPER_BOUND = 90.0  # exclusive
_RATE_LIMIT = 10  # max calls
_RATE_WINDOW = 60.0  # seconds
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class LLMScorer:
    """LLM 2nd-pass scorer — graceful no-op when not configured."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        profile_path: Path | None = None,
        max_tokens: int = 600,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.profile_path = profile_path
        self.api_key = self._resolve_api_key(api_key, profile_path)
        self._call_times: deque[float] = deque(maxlen=_RATE_LIMIT)

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------
    @staticmethod
    def should_invoke(rule_score: float) -> bool:
        """Return ``True`` iff ``60 <= rule_score < 90``."""
        return _LOWER_BOUND <= rule_score < _UPPER_BOUND

    async def score(
        self,
        job: JobRecord,
        archetype: Archetype,
        rule_based_breakdown: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Run a 2nd-pass LLM scoring call.

        Returns a plain dict with the four :class:`LLMScoreResponse` fields,
        or ``None`` if the call is skipped / fails. The caller should treat
        ``None`` as "keep the rule-based score".
        """
        rule_total = float(rule_based_breakdown.get("total", 0.0))
        if not self.should_invoke(rule_total):
            logger.debug("LLMScorer.skip: score %.1f out of 60–90 window", rule_total)
            return None
        if not self.api_key:
            logger.info("LLMScorer.skip: no API key configured")
            return None
        if not self._rate_limit_ok():
            logger.warning("LLMScorer.skip: rate limit hit")
            return None

        prompt = self._build_prompt(job, archetype, rule_based_breakdown)
        raw = await self._call_anthropic(prompt)
        if raw is None:
            return None

        parsed = self._parse_response(raw)
        if parsed is None:
            return None

        # No-fabrication filter: drop match points whose keywords aren't in the JD.
        jd_text = f"{job.title} {job.description} {job.org}".lower()
        parsed.key_match_points = [
            p for p in parsed.key_match_points if self._keyword_in_jd(p, jd_text)
        ]
        return parsed.model_dump()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve_api_key(self, explicit: str | None, profile_path: Path | None) -> str | None:
        if explicit:
            return explicit
        env = os.environ.get("ANTHROPIC_API_KEY")
        if env:
            return env
        if profile_path and profile_path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
                llm_cfg = data.get("llm") or {}
                key = llm_cfg.get("api_key")
                if isinstance(key, str) and key.strip():
                    return key.strip()
            except (OSError, ValueError) as exc:
                logger.debug("LLMScorer: profile read failed: %s", exc)
        return None

    def _rate_limit_ok(self) -> bool:
        now = time.monotonic()
        while self._call_times and now - self._call_times[0] > _RATE_WINDOW:
            self._call_times.popleft()
        if len(self._call_times) >= _RATE_LIMIT:
            return False
        self._call_times.append(now)
        return True

    def _build_prompt(
        self,
        job: JobRecord,
        archetype: Archetype,
        rule_based_breakdown: dict[str, Any],
    ) -> str:
        jd_snippet = (job.description or "")[:3000]
        applicant_summary = _load_applicant_summary()
        return (
            "너는 한국 금융/디지털 채용 공고를 평가하는 보조 스코어러다.\n"
            "규칙 기반 스코어러가 이미 1차 평가를 했고, 애매한 구간(60~89)만 너한테 온다.\n\n"
            f"## 지원자 요약\n{applicant_summary}\n\n"
            "## 평가할 공고\n"
            f"회사: {job.org}\n"
            f"직무: {job.title}\n"
            f"아키타입(1차 분류): {archetype.value if hasattr(archetype, 'value') else archetype}\n"
            f"지역: {job.location or '미상'}\n"
            f"마감: {job.deadline or '미상'}\n"
            f"---\n{jd_snippet}\n---\n\n"
            "## 규칙 기반 breakdown (0~100)\n"
            f"{json.dumps(rule_based_breakdown, ensure_ascii=False, indent=2)}\n\n"
            "## 지시\n"
            "1) breakdown을 재검토하고, JD에 **실제로 존재하는 표현**을 근거로 0~100 점수 한 개를 내놔.\n"
            "2) JD에 없는 사실을 지어내면 안 된다. 추측/'아마' 금지.\n"
            "3) 아래 JSON 스키마로만 답해라. 다른 텍스트 금지.\n\n"
            "```json\n"
            "{\n"
            '  "adjusted_score": <int 0-100>,\n'
            '  "reasoning": "<1~3문장, 한국어>",\n'
            '  "key_match_points": ["<짧은 구절>", ...],\n'
            '  "concerns": ["<짧은 구절>", ...]\n'
            "}\n"
            "```"
        )

    async def _call_anthropic(self, prompt: str) -> str | None:
        """Try the official SDK first, then fall back to raw httpx."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)
            msg = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            if msg.content and hasattr(msg.content[0], "text"):
                return msg.content[0].text  # type: ignore[no-any-return]
            return None
        except ImportError:
            logger.debug("LLMScorer: anthropic SDK not installed, trying httpx")
        except Exception as exc:
            logger.warning("LLMScorer: SDK call failed: %s", exc)
            return None

        # httpx fallback
        try:
            import httpx
        except ImportError:
            logger.info("LLMScorer: httpx missing → skip")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _ANTHROPIC_URL,
                    headers={
                        "x-api-key": self.api_key or "",
                        "anthropic-version": _API_VERSION,
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": self.max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
            if resp.status_code != 200:
                logger.warning("LLMScorer: httpx %s — %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            content = data.get("content") or []
            if content and isinstance(content, list):
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text")
            return None
        except Exception as exc:
            logger.warning("LLMScorer: httpx call failed: %s", exc)
            return None

    @staticmethod
    def _parse_response(raw: str) -> LLMScoreResponse | None:
        """Extract the first JSON object from ``raw`` and validate it."""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            logger.warning("LLMScorer: no JSON block in response")
            return None
        try:
            obj = json.loads(match.group(0))
            return LLMScoreResponse.model_validate(obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("LLMScorer: parse failed: %s", exc)
            return None

    @staticmethod
    def _keyword_in_jd(phrase: str, jd_text_lower: str) -> bool:
        """Conservative substring check — the phrase must share at least
        one token (len ≥ 2) with the JD."""
        tokens = [t for t in re.split(r"[\s,./()\[\]]+", phrase.lower()) if len(t) >= 2]
        if not tokens:
            return False
        return any(t in jd_text_lower for t in tokens)


# ---------------------------------------------------------------------------
# Convenience sync wrapper for CLI / tests
# ---------------------------------------------------------------------------


def score_sync(
    scorer: LLMScorer,
    job: JobRecord,
    archetype: Archetype,
    rule_based_breakdown: dict[str, Any],
) -> dict[str, Any] | None:
    """Run :meth:`LLMScorer.score` from a synchronous context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(scorer.score(job, archetype, rule_based_breakdown))
