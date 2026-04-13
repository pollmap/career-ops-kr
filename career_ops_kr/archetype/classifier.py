"""Keyword-weighted archetype classifier for Korean job postings.

Seven canonical archetypes target user's job-hunt map:

    * BLOCKCHAIN       — 블록체인·STO·DID·크립토 개발/기획
    * DIGITAL_ASSET    — 암호화폐 거래소·수탁·커스터디
    * FINANCIAL_IT     — 금융사 IT / 코어뱅킹 / 디지털 인턴
    * RESEARCH         — 리서치 / 이코노미스트 / 퀀트 분석
    * FINTECH_PRODUCT  — 핀테크 서비스/프로덕트 (토스/카카오페이 계열)
    * PUBLIC_FINANCE   — 공공 금융기관 인턴/서포터즈
    * CERTIFICATION    — 자격시험 (ADsP/SQLD/금투사/투운사/한국사)

Classification = weighted keyword matches per bucket, argmax + confidence.

Keyword tables are loaded from ``config/archetypes.yml`` (🔶 USER layer) so
that non-finance domains can be supported by copying
``templates/archetypes.example.yml``.  If the YAML file is missing or
malformed, the classifier falls back to a set of embedded defaults so that
existing tests and callers keep working.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class Archetype(str, Enum):
    """Job archetype buckets for 사용자 fit scoring.

    The Enum members are intentionally **static** — they form the public API
    consumed by tests, reports, and downstream scoring code.  New archetypes
    can still be added by editing this Enum and updating
    ``config/archetypes.yml``; archetypes referenced only by YAML that are
    missing from the Enum are dropped at load time with a warning.
    """

    BLOCKCHAIN = "BLOCKCHAIN"
    DIGITAL_ASSET = "DIGITAL_ASSET"
    FINANCIAL_IT = "FINANCIAL_IT"
    RESEARCH = "RESEARCH"
    FINTECH_PRODUCT = "FINTECH_PRODUCT"
    PUBLIC_FINANCE = "PUBLIC_FINANCE"
    CERTIFICATION = "CERTIFICATION"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Embedded fallback keyword table.
# Used when ``config/archetypes.yml`` is unavailable — preserves backwards
# compatibility with tests/test_archetype.py before the YAML externalization.
# ---------------------------------------------------------------------------

_FALLBACK_KEYWORDS: dict[Archetype, list[tuple[str, int]]] = {
    Archetype.BLOCKCHAIN: [
        ("블록체인", 3),
        ("STO", 3),
        ("토큰증권", 3),
        ("토큰 증권", 3),
        ("DID", 2),
        ("스마트컨트랙트", 3),
        ("스마트 컨트랙트", 3),
        ("Web3", 3),
        ("web3", 3),
        ("Lambda256", 3),
        ("Hashed", 3),
        ("온체인", 2),
        ("이더리움", 2),
        ("솔라나", 2),
        ("디파이", 2),
        ("NFT", 2),
        ("블록체인부", 3),
        ("블록체인스크럼", 3),
        ("블록체인 스크럼", 3),
    ],
    Archetype.DIGITAL_ASSET: [
        ("디지털자산", 3),
        ("디지털 자산", 3),
        ("가상자산", 3),
        ("암호화폐", 3),
        ("크립토", 2),
        ("거래소", 2),
        ("수탁", 2),
        ("커스터디", 3),
        ("업비트", 3),
        ("빗썸", 3),
        ("코인원", 3),
        ("두나무", 3),
        ("UpTo", 2),
        ("마이닝", 2),
    ],
    Archetype.FINANCIAL_IT: [
        ("금융 IT", 3),
        ("금융IT", 3),
        ("IT/Digital", 2),
        ("코어뱅킹", 3),
        ("마이데이터", 2),
        ("API 게이트웨이", 2),
        ("결제 시스템", 2),
        ("핀테크 인프라", 2),
        ("디지털 전환", 2),
        ("디지털 인턴", 2),
        ("데이터 부트캠프", 2),
        ("금융데이터", 2),
        ("KDA", 2),
        ("데이터분석가", 2),
        ("부트캠프", 2),
        ("하나로", 2),
        ("디지털 하나로", 3),
        ("FISA", 2),
        ("에이블스쿨", 2),
        ("부스트캠프", 2),
        ("SW마에스트로", 2),
        ("SW 마에스트로", 2),
        ("카카오테크", 2),
        ("멀티캠퍼스", 2),
        ("신한DS", 2),
        ("우리FISA", 2),
        ("하나저축은행", 2),
        ("FITI", 1),
        ("하나금융융합기술원", 2),
        ("체험형 인턴", 1),
        ("체험형 청년인턴", 1),
        ("ICT 학점연계", 2),
        ("학점연계 인턴", 1),
        ("KB IT", 2),
        ("IT's Your Life", 2),
        ("미래내일", 2),
        ("미래 내일", 2),
        ("일경험", 2),
        ("일 경험", 2),
        ("인턴형", 1),
        ("데이터 청년 캠퍼스", 3),
        ("청년 캠퍼스", 2),
        ("데이터분석 인턴", 2),
    ],
    Archetype.RESEARCH: [
        ("리서치", 3),
        ("이코노미스트", 3),
        ("기업분석", 2),
        ("투자전략", 2),
        ("퀀트", 3),
        ("Quant", 2),
        ("애널리스트", 2),
        ("Equity Research", 3),
        ("ESG 리서치", 3),
        ("ESG리서치", 3),
        ("통화정책 경시대회", 3),
        ("경시대회", 2),
    ],
    Archetype.FINTECH_PRODUCT: [
        ("토스", 3),
        ("카카오페이", 3),
        ("뱅크샐러드", 3),
        ("인슈어테크", 3),
        ("간편결제", 2),
        ("핀다", 3),
        ("페이히어", 3),
        ("8percent", 3),
        ("에잇퍼센트", 3),
        ("렌딧", 2),
        ("핀테크 프로덕트", 2),
        ("창업패키지", 2),
        ("예비창업", 2),
        ("창업유망팀", 2),
        ("창업중심대학", 2),
        ("금융위원회 핀테크", 3),
        ("금융위 핀테크", 3),
    ],
    Archetype.PUBLIC_FINANCE: [
        ("한국은행", 3),
        ("신용보증기금", 3),
        ("기술보증기금", 3),
        ("주택금융공사", 3),
        ("한국주택금융공사", 3),
        ("예탁결제원", 3),
        ("예금보험공사", 3),
        ("금융감독원", 3),
        ("금감원", 3),
        ("금융위원회", 2),
        ("한국거래소", 3),
        ("자산관리공사", 3),
        ("캠코", 3),
        ("한국연구재단", 3),
        ("공공기관", 2),
        ("체험형 인턴", 1),
        ("대학생 서포터즈", 2),
        ("서포터즈", 1),
    ],
    Archetype.CERTIFICATION: [
        ("자격시험", 3),
        ("ADsP", 3),
        ("SQLD", 3),
        ("금투사", 3),
        ("투운사", 3),
        ("투자자산운용사", 3),
        ("증권투자상담사", 2),
        ("한국사능력검정", 3),
        ("한국사", 2),
        ("회차", 1),
        ("정기시험", 2),
    ],
    Archetype.UNKNOWN: [],
}

_FALLBACK_PRIORITY: list[Archetype] = [
    Archetype.BLOCKCHAIN,
    Archetype.CERTIFICATION,
    Archetype.PUBLIC_FINANCE,
    Archetype.DIGITAL_ASSET,
    Archetype.FINTECH_PRODUCT,
    Archetype.RESEARCH,
    Archetype.FINANCIAL_IT,
    Archetype.UNKNOWN,
]

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "archetypes.yml"


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------


class ArchetypeKeywords(BaseModel):
    """Keyword lists bucketed by signal strength."""

    strong: list[str] = Field(default_factory=list)
    medium: list[str] = Field(default_factory=list)
    weak: list[str] = Field(default_factory=list)


class ArchetypeDefinition(BaseModel):
    """Single archetype entry loaded from YAML."""

    label_ko: str = ""
    label_en: str = ""
    keywords: ArchetypeKeywords = Field(default_factory=ArchetypeKeywords)
    org_patterns: list[str] = Field(default_factory=list)


class ArchetypeConfig(BaseModel):
    """Top-level archetype classifier configuration."""

    version: int = 1
    domain: str = "unknown"
    description: str = ""
    tiebreak_priority: list[str] = Field(default_factory=list)
    archetypes: dict[str, ArchetypeDefinition] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


class ArchetypeClassifier:
    """Weighted keyword classifier producing (Archetype, confidence)."""

    _WEIGHT_STRONG = 3
    _WEIGHT_MEDIUM = 2
    _WEIGHT_WEAK = 1
    _ORG_BONUS = 1

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path is not None else _DEFAULT_CONFIG_PATH
        self._domain = "finance_kr"
        self._table: dict[Archetype, list[tuple[str, int]]] = {}
        self._org_patterns: dict[Archetype, list[str]] = {}
        self._priority: list[Archetype] = []
        self._labels_ko: dict[Archetype, str] = {}
        self._load(self._config_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self, path: Path) -> None:
        """Load keyword tables from YAML, falling back to embedded defaults."""
        if not path.exists():
            logger.warning(
                "archetypes.yml not found at %s — using embedded defaults",
                path,
            )
            self._install_fallback()
            return

        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            logger.warning(
                "Failed to read archetypes.yml (%s) — using embedded defaults",
                exc,
            )
            self._install_fallback()
            return

        if not isinstance(raw, dict):
            logger.warning("archetypes.yml root must be a mapping — using embedded defaults")
            self._install_fallback()
            return

        try:
            config = ArchetypeConfig.model_validate(raw)
        except ValidationError as exc:
            logger.warning(
                "archetypes.yml failed validation (%s) — using embedded defaults",
                exc,
            )
            self._install_fallback()
            return

        self._install_from_config(config)

    def _install_fallback(self) -> None:
        self._domain = "finance_kr"
        self._table = {
            arch: [(kw.lower(), w) for kw, w in kws] for arch, kws in _FALLBACK_KEYWORDS.items()
        }
        self._org_patterns = {arch: [] for arch in _FALLBACK_KEYWORDS}
        self._priority = list(_FALLBACK_PRIORITY)
        self._labels_ko = {arch: arch.value for arch in _FALLBACK_KEYWORDS}

    def _install_from_config(self, config: ArchetypeConfig) -> None:
        self._domain = config.domain
        table: dict[Archetype, list[tuple[str, int]]] = {}
        org_patterns: dict[Archetype, list[str]] = {}
        labels_ko: dict[Archetype, str] = {}

        valid_codes = {a.value for a in Archetype}
        for code, definition in config.archetypes.items():
            if code not in valid_codes:
                logger.warning("archetypes.yml: unknown archetype code %r — skipped", code)
                continue
            arch = Archetype(code)
            entries: list[tuple[str, int]] = []
            for kw in definition.keywords.strong:
                entries.append((kw.lower(), self._WEIGHT_STRONG))
            for kw in definition.keywords.medium:
                entries.append((kw.lower(), self._WEIGHT_MEDIUM))
            for kw in definition.keywords.weak:
                entries.append((kw.lower(), self._WEIGHT_WEAK))
            table[arch] = entries
            org_patterns[arch] = [p.lower() for p in definition.org_patterns]
            labels_ko[arch] = definition.label_ko or arch.value

        # Ensure every Enum member has an entry so downstream code is safe.
        for arch in Archetype:
            table.setdefault(arch, [])
            org_patterns.setdefault(arch, [])
            labels_ko.setdefault(arch, arch.value)

        priority: list[Archetype] = []
        for code in config.tiebreak_priority:
            if code in valid_codes:
                arch = Archetype(code)
                if arch not in priority:
                    priority.append(arch)
        # Append any missing archetypes at the end (deterministic).
        for arch in Archetype:
            if arch not in priority:
                priority.append(arch)

        self._table = table
        self._org_patterns = org_patterns
        self._priority = priority
        self._labels_ko = labels_ko

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_archetypes(self) -> list[str]:
        """Return archetype codes that have at least one keyword defined."""
        return [
            arch.value
            for arch in Archetype
            if self._table.get(arch) or self._org_patterns.get(arch)
        ]

    @property
    def domain(self) -> str:
        return self._domain

    def label_ko(self, archetype: Archetype) -> str:
        return self._labels_ko.get(archetype, archetype.value)

    def classify(self, text: str) -> tuple[Archetype, float]:
        """Classify ``text`` into an archetype with confidence ∈ [0, 1]."""
        if not text or not text.strip():
            return Archetype.UNKNOWN, 0.0

        lowered = text.lower()
        scores: dict[Archetype, int] = {}
        for arch, kws in self._table.items():
            if arch is Archetype.UNKNOWN:
                continue
            total = 0
            for kw, weight in kws:
                if kw and kw in lowered:
                    total += weight
            for org in self._org_patterns.get(arch, []):
                if org and org in lowered:
                    total += self._ORG_BONUS
            if total > 0:
                scores[arch] = total

        if not scores:
            return Archetype.UNKNOWN, 0.0

        top_score = max(scores.values())
        top_arches = [a for a, s in scores.items() if s == top_score]

        winner = self._break_tie(top_arches)

        total_points = sum(scores.values())
        confidence = min(1.0, top_score / max(total_points, 1))
        # Floor confidence to avoid 0 when clearly matched.
        confidence = max(confidence, 0.5 if top_score >= 2 else 0.35)
        return winner, round(confidence, 3)

    def _break_tie(self, candidates: list[Archetype]) -> Archetype:
        """Apply configured tiebreak priority; fall back to first candidate."""
        if len(candidates) == 1:
            return candidates[0]
        for arch in self._priority:
            if arch in candidates:
                return arch
        return candidates[0]


def load_config(path: Path | None = None) -> ArchetypeConfig:
    """Utility loader used by tests and tooling.

    Returns a validated ``ArchetypeConfig`` or raises ``FileNotFoundError``
    if ``path`` does not exist.
    """
    target = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not target.exists():
        raise FileNotFoundError(target)
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8"))
    return ArchetypeConfig.model_validate(raw)
