"""금융기관 채용 채널 배치 — 확인된 URL 기반 stub 모음.

2026-04-13: URL 프로빙으로 확인된 27개 기관 채용 페이지.
모두 make_stub_channel_class 기반 stub. 추후 tune으로 selector 정밀화 가능.

Tier 분류:
    2 = 정책금융/공공기관
    3 = 시중은행/지방은행/증권/보험/카드
    4 = 핀테크/저축은행/캐피탈
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

# ---------------------------------------------------------------------------
# 정책금융 / 공공기관 (tier 2)
# ---------------------------------------------------------------------------

KicChannel = make_stub_channel_class(
    class_name="KicChannel",
    channel_name="kic",
    channel_tier=2,
    listing_url="https://recruit.kic.com/",
    org="한국투자공사(KIC)",
    location="서울",
    legitimacy_tier="T1",
)

KdbBankChannel = make_stub_channel_class(
    class_name="KdbBankChannel",
    channel_name="kdb_bank",
    channel_tier=2,
    listing_url="https://recruit.kdb.co.kr/",
    org="한국산업은행",
    location="서울",
    legitimacy_tier="T1",
)

EximBankChannel = make_stub_channel_class(
    class_name="EximBankChannel",
    channel_name="exim_bank",
    channel_tier=2,
    listing_url="https://recruit.koreaexim.go.kr/",
    org="한국수출입은행",
    location="서울",
    legitimacy_tier="T1",
)

KobcChannel = make_stub_channel_class(
    class_name="KobcChannel",
    channel_name="kobc",
    channel_tier=2,
    listing_url="https://www.kobc.or.kr/hmpg/cont/recrt/List.do",
    org="한국해양진흥공사",
    location="부산",
    legitimacy_tier="T1",
)

KoscomChannel = make_stub_channel_class(
    class_name="KoscomChannel",
    channel_name="koscom",
    channel_tier=2,
    listing_url="https://recruit.koscom.com/",
    org="코스콤",
    location="서울",
    legitimacy_tier="T1",
)

ApfsChannel = make_stub_channel_class(
    class_name="ApfsChannel",
    channel_name="apfs",
    channel_tier=2,
    listing_url="https://apfs.recruiter.co.kr/career/home",
    org="농업정책보험금융원",
    location="서울",
    legitimacy_tier="T1",
)

SmbsChannel = make_stub_channel_class(
    class_name="SmbsChannel",
    channel_name="smbs",
    channel_tier=2,
    listing_url="https://smbs.recruiter.co.kr/career/home",
    org="서울외국환중개",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 시중은행 / 지방은행 (tier 3)
# ---------------------------------------------------------------------------

ShinhanBankChannel = make_stub_channel_class(
    class_name="ShinhanBankChannel",
    channel_name="shinhan_bank",
    channel_tier=3,
    listing_url="https://shinhan.recruiter.co.kr/career/home",
    org="신한은행",
    location="서울",
    legitimacy_tier="T1",
)

HanaBankChannel = make_stub_channel_class(
    class_name="HanaBankChannel",
    channel_name="hana_bank",
    channel_tier=3,
    listing_url="https://hanabank.recruiter.co.kr/career/home",
    org="하나은행",
    location="서울",
    legitimacy_tier="T1",
)

BusanBankChannel = make_stub_channel_class(
    class_name="BusanBankChannel",
    channel_name="busan_bank",
    channel_tier=3,
    listing_url="https://busanbank.recruiter.co.kr/career/home",
    org="부산은행(BNK)",
    location="부산",
    legitimacy_tier="T1",
)

KnbChannel = make_stub_channel_class(
    class_name="KnbChannel",
    channel_name="knb",
    channel_tier=3,
    listing_url="https://knbank.recruiter.co.kr/career/home",
    org="경남은행(BNK)",
    location="창원",
    legitimacy_tier="T1",
)

JbBankChannel = make_stub_channel_class(
    class_name="JbBankChannel",
    channel_name="jb_bank",
    channel_tier=3,
    listing_url="https://jbbank.recruiter.co.kr/career/home",
    org="전북은행(JB)",
    location="전주",
    legitimacy_tier="T1",
)

JejuBankChannel = make_stub_channel_class(
    class_name="JejuBankChannel",
    channel_name="jeju_bank",
    channel_tier=3,
    listing_url="https://jejubank.recruiter.co.kr/career/home",
    org="제주은행",
    location="제주",
    legitimacy_tier="T1",
)

KBankChannel = make_stub_channel_class(
    class_name="KBankChannel",
    channel_name="k_bank",
    channel_tier=3,
    listing_url="https://www.kbanknow.com/ib20/mnu/FPFLT0000005",
    org="케이뱅크",
    location="서울",
    legitimacy_tier="T1",
)

ScBankChannel = make_stub_channel_class(
    class_name="ScBankChannel",
    channel_name="sc_bank",
    channel_tier=3,
    listing_url="https://www.standardchartered.co.kr/np/kr/pmc/aboutsc/CareerMain.jsp",
    org="SC제일은행",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 증권사 (tier 3)
# ---------------------------------------------------------------------------

MiraeassetSecChannel = make_stub_channel_class(
    class_name="MiraeassetSecChannel",
    channel_name="miraeasset_sec",
    channel_tier=3,
    listing_url="https://career.miraeasset.com/",
    org="미래에셋증권",
    location="서울",
    legitimacy_tier="T1",
)


MeritzSecChannel = make_stub_channel_class(
    class_name="MeritzSecChannel",
    channel_name="meritz_sec",
    channel_tier=3,
    listing_url="https://meritz.recruiter.co.kr/career/home",
    org="메리츠증권",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 보험사 (tier 3)
# ---------------------------------------------------------------------------

KdbLifeChannel = make_stub_channel_class(
    class_name="KdbLifeChannel",
    channel_name="kdb_life",
    channel_tier=3,
    listing_url="https://kdblife.recruiter.co.kr/career/home",
    org="KDB생명",
    location="서울",
    legitimacy_tier="T1",
)

KoreanReChannel = make_stub_channel_class(
    class_name="KoreanReChannel",
    channel_name="korean_re",
    channel_tier=3,
    listing_url="https://koreanre.recruiter.co.kr/career/home",
    org="코리안리",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 캐피탈 (tier 4)
# ---------------------------------------------------------------------------

MeritzCapitalChannel = make_stub_channel_class(
    class_name="MeritzCapitalChannel",
    channel_name="meritz_capital",
    channel_tier=4,
    listing_url="https://meritzcapital.recruiter.co.kr/career/home",
    org="메리츠캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiCapitalChannel = make_stub_channel_class(
    class_name="HyundaiCapitalChannel",
    channel_name="hyundai_capital",
    channel_tier=4,
    listing_url="https://career.hyundaicapital.com/",
    org="현대캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 저축은행 (tier 4)
# ---------------------------------------------------------------------------

SbiSavingsChannel = make_stub_channel_class(
    class_name="SbiSavingsChannel",
    channel_name="sbi_savings",
    channel_tier=4,
    listing_url="https://sbisb.recruiter.co.kr/career/home",
    org="SBI저축은행",
    location="서울",
    legitimacy_tier="T1",
)

OkSavingsChannel = make_stub_channel_class(
    class_name="OkSavingsChannel",
    channel_name="ok_savings",
    channel_tier=4,
    listing_url="https://www.oksavingsbank.com/company/talent/index.do",
    org="OK저축은행",
    location="서울",
    legitimacy_tier="T1",
)

WelcomeSavingsChannel = make_stub_channel_class(
    class_name="WelcomeSavingsChannel",
    channel_name="welcome_savings",
    channel_tier=4,
    listing_url="https://www.welcomebank.co.kr/ib20/mnu/WB0000007",
    org="웰컴저축은행",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 핀테크 / 인터넷은행 (tier 4)
# ---------------------------------------------------------------------------

TossBankChannel = make_stub_channel_class(
    class_name="TossBankChannel",
    channel_name="toss_bank",
    channel_tier=4,
    listing_url="https://recruit.tossbank.com/",
    org="토스뱅크",
    location="서울",
    legitimacy_tier="T1",
)

__all__ = [
    "ApfsChannel",
    "BusanBankChannel",
    "EximBankChannel",
    "HanaBankChannel",
    "HyundaiCapitalChannel",
    "JbBankChannel",
    "JejuBankChannel",
    "KBankChannel",
    "KdbBankChannel",
    "KdbLifeChannel",
    "KicChannel",
    "KnbChannel",
    "KobcChannel",
    "KoreanReChannel",
    "KoscomChannel",
    "MeritzCapitalChannel",
    "MeritzSecChannel",
    "MiraeassetSecChannel",
    "OkSavingsChannel",
    "SbiSavingsChannel",
    "ScBankChannel",
    "ShinhanBankChannel",
    "SmbsChannel",
    "TossBankChannel",
    "WelcomeSavingsChannel",
]
