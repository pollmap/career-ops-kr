"""Sector inference — 채널명/org/title → 금융/공공/안보/핀테크/기타.

212개 채널 레지스트리를 sector 그룹으로 분류. aggregator 채널
(saramin/wanted/linkareer 등)은 source_channel만으로 판정 불가하므로
org + title 키워드로 fallback.

Used by:
    * ``career_ops_kr.web.dashboard`` — Streamlit 대시보드 sector 필터
    * ``career_ops_kr.cli.list_cmd`` — ``--sector`` CLI 옵션
"""

from __future__ import annotations

SECTOR_CHOICES: tuple[str, ...] = ("금융", "공공", "안보", "핀테크", "기타")


_FINANCE_CHANNELS: frozenset[str] = frozenset({
    # 은행
    "kb_bank", "shinhan_bank", "hana_bank", "woori_bank", "nh_bank",
    "busan_bank", "knb", "im_bank", "kwangju_bank", "jb_bank", "jeju_bank",
    "sh_bank", "kakao_bank", "toss_bank", "k_bank", "sc_bank", "citi_bank",
    "kdb_bank", "exim_bank", "ibk_bank",
    # 증권
    "shinhan_sec", "mirae_asset", "kb_sec", "hana_sec", "nh_sec",
    "samsung_sec", "korea_invest_sec", "ibk_sec", "daishin_sec",
    "kyobo_sec", "hanwha_sec", "yuanta_sec", "eugene_sec",
    "hyundai_car_sec", "hi_sec", "db_fi", "sk_sec", "im_sec",
    "cape_sec", "koreafoss_sec", "bookook_sec", "shinyoung_sec",
    "hanyang_sec", "yuhwa_sec", "bnk_sec", "heungkuk_sec", "daol_sec",
    "leading_sec", "korea_asset_sec", "meritz_sec", "miraeasset_sec",
    "kiwoom_kda", "kiwoomda",
    # 선물
    "samsung_futures", "nh_futures", "hana_futures", "kiwoom_futures",
    "shinhan_futures",
    # 생명보험
    "samsung_life", "hanwha_life", "kyobo_life", "shinhan_life",
    "nh_life", "hana_life", "kb_life", "dongyang_life", "miraeasset_life",
    "abl_life", "metlife", "aia_life", "chubb_life", "fubon_life", "kdb_life",
    # 손해보험
    "samsung_fire", "hyundai_marine", "db_ins", "kb_ins", "meritz_fire",
    "hanwha_ins", "lotte_ins", "heungkuk_fire", "mg_ins", "nh_fire",
    "thek_ins", "hana_ins", "carrot_ins", "korean_re",
    # 카드
    "shinhan_card", "samsung_card", "kb_card", "hyundai_card", "lotte_card",
    "woori_card", "bc_card", "hana_card",
    # 캐피탈
    "kb_capital", "hana_capital", "shinhan_capital", "woori_capital",
    "aju_capital", "lotte_capital", "bnk_capital", "jb_woori_capital",
    "nh_capital", "dgb_capital", "kdb_capital", "meritz_capital",
    "hyundai_capital",
    # 저축은행
    "sbi_savings", "ok_savings", "welcome_savings", "kiwoom_yes_savings",
    "pepper_savings", "aquon_savings", "kit_savings", "jt_savings",
    "osb_savings", "thek_savings",
    # 자산운용
    "miraeasset_am", "kit_am", "samsung_am", "kb_am", "shinhan_am",
    "hanwha_am", "nh_amundi_am", "kiwoom_am", "shinyoung_am",
    "kyobo_axa_am", "eastspring_am", "timefolio_am", "truston_am",
    "vi_am", "lazard_am", "ab_am",
    # 금융 인프라·협회·규제
    "kic", "kobc", "koscom", "smbs", "apfs",
    "kfb", "kofia", "knia", "klia", "crefia", "fsb", "cu_central",
    "kfcc", "krx", "ksfc", "ksd", "kftc", "fsec", "kcredit",
    "kfmb", "krca", "kodit", "kibo", "hf", "kamco", "kdic",
    "ksure", "hug", "sgi", "kinfa", "fsc", "fss",
})

_SECURITY_CHANNELS: frozenset[str] = frozenset({
    "nis", "mnd", "mofa", "police", "customs", "dapa", "kisa", "government",
})

_PUBLIC_CHANNELS: frozenset[str] = frozenset({
    "apply_bok", "jobalio", "gojobs", "yw_work24", "dataq",
    "mirae_naeil", "mjob", "ktcu", "mac", "poba", "loginet",
    "cgc", "special_cgc", "firefighter_fund", "sema", "sw_fund",
    "kofic_fund", "kvic", "kgf",
})

_FINTECH_CHANNELS: frozenset[str] = frozenset({
    "toss", "kakao_pay", "banksalad", "finda", "naver_pay",
    "eight_percent", "payco", "dunamu", "bithumb", "lambda256",
    "coinone", "kakao_inv", "lb_inv", "mbk", "hahn_co", "imm",
    "stic", "skylake", "daol_inv", "kit_partners",
})

_FINANCE_KW: tuple[str, ...] = (
    "은행", "증권", "보험", "카드", "캐피탈", "저축", "자산운용", "투자",
    "금융", "선물", "파생", "운용사", "신탁", "펀드", "리츠", "금감원",
    "금융위", "예탁", "결제원", "거래소", "KRX", "KIC", "산업은행",
    "수출입은행", "기업은행", "신용보증", "주택금융", "예금보험",
)
# 블록체인/디지털자산은 사용자 도메인(핀테크 카테고리로 병합)
_FINTECH_KW: tuple[str, ...] = (
    "블록체인", "Web3", "web3", "크립토", "암호화폐", "가상자산", "디지털자산",
    "토큰증권", "STO", "스마트컨트랙트", "NFT", "디파이", "DeFi",
    "온체인", "수탁", "커스터디", "Lambda256", "해시드", "업비트", "빗썸",
    "코인원", "두나무", "간편결제", "핀테크",
)
_SECURITY_KW: tuple[str, ...] = (
    "국정원", "안보", "국방", "국가정보", "방위사업", "외교부", "경찰",
    "관세", "KISA", "정보보호", "사이버", "군", "보안",
)
_PUBLIC_KW: tuple[str, ...] = (
    "공사", "공단", "공기업", "공공기관", "청", "처", "원", "연구원",
    "한국은행", "한국거래소", "한국투자공사", "공제회", "중앙회",
)


def infer_sector(channel: str | None, org: str | None, title: str | None) -> str:
    """Return sector label: 금융 / 공공 / 안보 / 핀테크 / 기타.

    채널명 매칭이 가장 확실한 신호. aggregator 채널(saramin/wanted 등)은
    source_channel만으로 구분 불가 → org + title 키워드로 fallback.
    """
    ch = (channel or "").lower()
    if ch in _FINANCE_CHANNELS:
        return "금융"
    if ch in _SECURITY_CHANNELS:
        return "안보"
    if ch in _PUBLIC_CHANNELS:
        return "공공"
    if ch in _FINTECH_CHANNELS:
        return "핀테크"
    combined = f"{org or ''} {title or ''}"
    if any(kw in combined for kw in _SECURITY_KW):
        return "안보"
    if any(kw in combined for kw in _FINTECH_KW):
        return "핀테크"
    if any(kw in combined for kw in _FINANCE_KW):
        return "금융"
    if any(kw in combined for kw in _PUBLIC_KW):
        return "공공"
    return "기타"
