"""공공·규제·정책금융·시중은행 채용 채널 — make_stub_channel_class 배치.

Tier 분류:
    2 = 규제기관/협회/공제회/정책금융
    3 = 시중은행/지방은행/인터넷은행
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

# ---------------------------------------------------------------------------
# 규제·감독 기관 (tier 2)
# ---------------------------------------------------------------------------

KfbChannel = make_stub_channel_class(
    class_name="KfbChannel",
    channel_name="kfb",
    channel_tier=2,
    listing_url="https://kfb.recruiter.co.kr/career/home",
    org="전국은행연합회",
    location="서울",
    legitimacy_tier="T1",
)

KofiaChannel = make_stub_channel_class(
    class_name="KofiaChannel",
    channel_name="kofia",
    channel_tier=2,
    listing_url="https://www.kofia.or.kr/brd/m_73/list.do",
    org="금융투자협회",
    location="서울",
    legitimacy_tier="T1",
)

KniaChannel = make_stub_channel_class(
    class_name="KniaChannel",
    channel_name="knia",
    channel_tier=2,
    listing_url="https://knia.recruiter.co.kr/career/home",
    org="손해보험협회",
    location="서울",
    legitimacy_tier="T1",
)

KliaChannel = make_stub_channel_class(
    class_name="KliaChannel",
    channel_name="klia",
    channel_tier=2,
    listing_url="https://klia.recruiter.co.kr/career/home",
    org="생명보험협회",
    location="서울",
    legitimacy_tier="T1",
)

CrefiaChannel = make_stub_channel_class(
    class_name="CrefiaChannel",
    channel_name="crefia",
    channel_tier=2,
    listing_url="https://crefia.recruiter.co.kr/career/home",
    org="여신금융협회",
    location="서울",
    legitimacy_tier="T1",
)

FsbChannel = make_stub_channel_class(
    class_name="FsbChannel",
    channel_name="fsb",
    channel_tier=2,
    listing_url="https://fsb.recruiter.co.kr/career/home",
    org="저축은행중앙회",
    location="서울",
    legitimacy_tier="T1",
)

CuCentralChannel = make_stub_channel_class(
    class_name="CuCentralChannel",
    channel_name="cu_central",
    channel_tier=2,
    listing_url="https://cu.recruiter.co.kr/career/home",
    org="신용협동조합중앙회",
    location="서울",
    legitimacy_tier="T1",
)

KfccChannel = make_stub_channel_class(
    class_name="KfccChannel",
    channel_name="kfcc",
    channel_tier=2,
    listing_url="https://kfcc.recruiter.co.kr/career/home",
    org="새마을금고중앙회",
    location="서울",
    legitimacy_tier="T1",
)

KrxChannel = make_stub_channel_class(
    class_name="KrxChannel",
    channel_name="krx",
    channel_tier=2,
    listing_url="https://recruit.krx.co.kr/",
    org="한국거래소(KRX)",
    location="부산",
    legitimacy_tier="T1",
)

KsfcChannel = make_stub_channel_class(
    class_name="KsfcChannel",
    channel_name="ksfc",
    channel_tier=2,
    listing_url="https://ksfc.recruiter.co.kr/career/home",
    org="한국증권금융",
    location="서울",
    legitimacy_tier="T1",
)

KsdChannel = make_stub_channel_class(
    class_name="KsdChannel",
    channel_name="ksd",
    channel_tier=2,
    listing_url="https://ksd.recruiter.co.kr/career/home",
    org="한국예탁결제원",
    location="부산",
    legitimacy_tier="T1",
)

KftcChannel = make_stub_channel_class(
    class_name="KftcChannel",
    channel_name="kftc",
    channel_tier=2,
    listing_url="https://kftc.recruiter.co.kr/career/home",
    org="금융결제원",
    location="서울",
    legitimacy_tier="T1",
)

FsecChannel = make_stub_channel_class(
    class_name="FsecChannel",
    channel_name="fsec",
    channel_tier=2,
    listing_url="https://fsec.recruiter.co.kr/career/home",
    org="금융보안원",
    location="서울",
    legitimacy_tier="T1",
)

KcreditChannel = make_stub_channel_class(
    class_name="KcreditChannel",
    channel_name="kcredit",
    channel_tier=2,
    listing_url="https://kcredit.recruiter.co.kr/career/home",
    org="한국신용정보원",
    location="서울",
    legitimacy_tier="T1",
)

KfmbChannel = make_stub_channel_class(
    class_name="KfmbChannel",
    channel_name="kfmb",
    channel_tier=2,
    listing_url="https://kfb2.recruiter.co.kr/career/home",
    org="한국자금중개",
    location="서울",
    legitimacy_tier="T1",
)

KrcaChannel = make_stub_channel_class(
    class_name="KrcaChannel",
    channel_name="krca",
    channel_tier=2,
    listing_url="https://krca.recruiter.co.kr/career/home",
    org="신용정보협회",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 공제회 (tier 2)
# ---------------------------------------------------------------------------

KtcuChannel = make_stub_channel_class(
    class_name="KtcuChannel",
    channel_name="ktcu",
    channel_tier=2,
    listing_url="https://ktcu.recruiter.co.kr/career/home",
    org="한국교직원공제회",
    location="서울",
    legitimacy_tier="T1",
)

MacChannel = make_stub_channel_class(
    class_name="MacChannel",
    channel_name="mac",
    channel_tier=2,
    listing_url="https://mac.recruiter.co.kr/career/home",
    org="군인공제회",
    location="서울",
    legitimacy_tier="T1",
)

PobaChannel = make_stub_channel_class(
    class_name="PobaChannel",
    channel_name="poba",
    channel_tier=2,
    listing_url="https://poba.recruiter.co.kr/career/home",
    org="경찰공제회",
    location="서울",
    legitimacy_tier="T1",
)

LoginetChannel = make_stub_channel_class(
    class_name="LoginetChannel",
    channel_name="loginet",
    channel_tier=2,
    listing_url="https://loginet.recruiter.co.kr/career/home",
    org="대한지방행정공제회",
    location="서울",
    legitimacy_tier="T1",
)

CgcChannel = make_stub_channel_class(
    class_name="CgcChannel",
    channel_name="cgc",
    channel_tier=2,
    listing_url="https://cgc.recruiter.co.kr/career/home",
    org="건설공제조합",
    location="서울",
    legitimacy_tier="T1",
)

SpecialCgcChannel = make_stub_channel_class(
    class_name="SpecialCgcChannel",
    channel_name="special_cgc",
    channel_tier=2,
    listing_url="https://www.cak.or.kr/board/recruit/list.do",
    org="전문건설공제조합",
    location="서울",
    legitimacy_tier="T1",
)

FirefighterFundChannel = make_stub_channel_class(
    class_name="FirefighterFundChannel",
    channel_name="firefighter_fund",
    channel_tier=2,
    listing_url="https://www.foremutual.or.kr/user/main/main.do",
    org="대한소방공제회",
    location="서울",
    legitimacy_tier="T1",
)

SemaChannel = make_stub_channel_class(
    class_name="SemaChannel",
    channel_name="sema",
    channel_tier=2,
    listing_url="https://sema.recruiter.co.kr/career/home",
    org="과학기술인공제회",
    location="서울",
    legitimacy_tier="T1",
)

SwFundChannel = make_stub_channel_class(
    class_name="SwFundChannel",
    channel_name="sw_fund",
    channel_tier=2,
    listing_url="https://www.swfund.or.kr/board/noticelist.do",
    org="소프트웨어공제조합",
    location="서울",
    legitimacy_tier="T1",
)

KoficFundChannel = make_stub_channel_class(
    class_name="KoficFundChannel",
    channel_name="kofic_fund",
    channel_tier=2,
    listing_url="https://www.kfcm.co.kr/html/members/notice.do",
    org="영화인공제회",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 정책금융 (tier 2)
# ---------------------------------------------------------------------------

IbkBankChannel = make_stub_channel_class(
    class_name="IbkBankChannel",
    channel_name="ibk_bank",
    channel_tier=2,
    listing_url="https://ibk.recruiter.co.kr/career/home",
    org="중소기업은행(IBK)",
    location="서울",
    legitimacy_tier="T1",
)

KoditChannel = make_stub_channel_class(
    class_name="KoditChannel",
    channel_name="kodit",
    channel_tier=2,
    listing_url="https://kodit.recruiter.co.kr/career/home",
    org="신용보증기금",
    location="대구",
    legitimacy_tier="T1",
)

KiboChannel = make_stub_channel_class(
    class_name="KiboChannel",
    channel_name="kibo",
    channel_tier=2,
    listing_url="https://kibo.recruiter.co.kr/career/home",
    org="기술보증기금",
    location="부산",
    legitimacy_tier="T1",
)

HfChannel = make_stub_channel_class(
    class_name="HfChannel",
    channel_name="hf",
    channel_tier=2,
    listing_url="https://hf.recruiter.co.kr/career/home",
    org="한국주택금융공사",
    location="부산",
    legitimacy_tier="T1",
)

KamcoChannel = make_stub_channel_class(
    class_name="KamcoChannel",
    channel_name="kamco",
    channel_tier=2,
    listing_url="https://kamco.recruiter.co.kr/career/home",
    org="한국자산관리공사",
    location="부산",
    legitimacy_tier="T1",
)

KdicChannel = make_stub_channel_class(
    class_name="KdicChannel",
    channel_name="kdic",
    channel_tier=2,
    listing_url="https://kdic.recruiter.co.kr/career/home",
    org="예금보험공사",
    location="서울",
    legitimacy_tier="T1",
)

KsureChannel = make_stub_channel_class(
    class_name="KsureChannel",
    channel_name="ksure",
    channel_tier=2,
    listing_url="https://ksure.recruiter.co.kr/career/home",
    org="한국무역보험공사",
    location="서울",
    legitimacy_tier="T1",
)

HugChannel = make_stub_channel_class(
    class_name="HugChannel",
    channel_name="hug",
    channel_tier=2,
    listing_url="https://hug.recruiter.co.kr/career/home",
    org="주택도시보증공사",
    location="부산",
    legitimacy_tier="T1",
)

SgiChannel = make_stub_channel_class(
    class_name="SgiChannel",
    channel_name="sgi",
    channel_tier=2,
    listing_url="https://sgi.recruiter.co.kr/career/home",
    org="서울보증보험",
    location="서울",
    legitimacy_tier="T1",
)

KinfaChannel = make_stub_channel_class(
    class_name="KinfaChannel",
    channel_name="kinfa",
    channel_tier=2,
    listing_url="https://kinfa.recruiter.co.kr/career/home",
    org="서민금융진흥원",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 시중은행 / 지방은행 / 인터넷은행 (tier 3)
# ---------------------------------------------------------------------------

KbBankChannel = make_stub_channel_class(
    class_name="KbBankChannel",
    channel_name="kb_bank",
    channel_tier=3,
    listing_url="https://kbstar.recruiter.co.kr/career/home",
    org="KB국민은행",
    location="서울",
    legitimacy_tier="T1",
)

WooriBankChannel = make_stub_channel_class(
    class_name="WooriBankChannel",
    channel_name="woori_bank",
    channel_tier=3,
    listing_url="https://wooribank.recruiter.co.kr/career/home",
    org="우리은행",
    location="서울",
    legitimacy_tier="T1",
)

NhBankChannel = make_stub_channel_class(
    class_name="NhBankChannel",
    channel_name="nh_bank",
    channel_tier=3,
    listing_url="https://nhrecruit.co.kr/",
    org="NH농협은행",
    location="서울",
    legitimacy_tier="T1",
)

ImBankChannel = make_stub_channel_class(
    class_name="ImBankChannel",
    channel_name="im_bank",
    channel_tier=3,
    listing_url="https://imbank.recruiter.co.kr/career/home",
    org="iM뱅크(DGB)",
    location="대구",
    legitimacy_tier="T1",
)

KwangjuBankChannel = make_stub_channel_class(
    class_name="KwangjuBankChannel",
    channel_name="kwangju_bank",
    channel_tier=3,
    listing_url="https://kjbank.recruiter.co.kr/career/home",
    org="광주은행(JB)",
    location="광주",
    legitimacy_tier="T1",
)

ShBankChannel = make_stub_channel_class(
    class_name="ShBankChannel",
    channel_name="sh_bank",
    channel_tier=3,
    listing_url="https://shbank.recruiter.co.kr/career/home",
    org="Sh수협은행",
    location="서울",
    legitimacy_tier="T1",
)

CitiBankChannel = make_stub_channel_class(
    class_name="CitiBankChannel",
    channel_name="citi_bank",
    channel_tier=3,
    listing_url="https://citibank.recruiter.co.kr/career/home",
    org="한국씨티은행",
    location="서울",
    legitimacy_tier="T1",
)

__all__ = [
    # 규제/협회
    "KfbChannel",
    "KofiaChannel",
    "KniaChannel",
    "KliaChannel",
    "CrefiaChannel",
    "FsbChannel",
    "CuCentralChannel",
    "KfccChannel",
    "KrxChannel",
    "KsfcChannel",
    "KsdChannel",
    "KftcChannel",
    "FsecChannel",
    "KcreditChannel",
    "KfmbChannel",
    "KrcaChannel",
    # 공제회
    "KtcuChannel",
    "MacChannel",
    "PobaChannel",
    "LoginetChannel",
    "CgcChannel",
    "SpecialCgcChannel",
    "FirefighterFundChannel",
    "SemaChannel",
    "SwFundChannel",
    "KoficFundChannel",
    # 정책금융
    "IbkBankChannel",
    "KoditChannel",
    "KiboChannel",
    "HfChannel",
    "KamcoChannel",
    "KdicChannel",
    "KsureChannel",
    "HugChannel",
    "SgiChannel",
    "KinfaChannel",
    # 시중은행
    "KbBankChannel",
    "WooriBankChannel",
    "NhBankChannel",
    "ImBankChannel",
    "KwangjuBankChannel",
    "ShBankChannel",
    "CitiBankChannel",
]
