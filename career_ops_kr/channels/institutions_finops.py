"""카드·캐피탈·저축은행·자산운용·PE/VC·핀테크 채용 채널 — make_stub_channel_class 배치.

Tier 분류:
    3 = 카드사 / 자산운용
    4 = 캐피탈 / 저축은행 / PE/VC / 핀테크
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

# ---------------------------------------------------------------------------
# 카드사 (tier 3)
# ---------------------------------------------------------------------------

ShinhanCardChannel = make_stub_channel_class(
    class_name="ShinhanCardChannel",
    channel_name="shinhan_card",
    channel_tier=3,
    listing_url="https://shinhancard.recruiter.co.kr/career/home",
    org="신한카드",
    location="서울",
    legitimacy_tier="T1",
)

SamsungCardChannel = make_stub_channel_class(
    class_name="SamsungCardChannel",
    channel_name="samsung_card",
    channel_tier=3,
    listing_url="https://samsungcard.recruiter.co.kr/career/home",
    org="삼성카드",
    location="서울",
    legitimacy_tier="T1",
)

KbCardChannel = make_stub_channel_class(
    class_name="KbCardChannel",
    channel_name="kb_card",
    channel_tier=3,
    listing_url="https://kbcard.recruiter.co.kr/career/home",
    org="KB국민카드",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiCardChannel = make_stub_channel_class(
    class_name="HyundaiCardChannel",
    channel_name="hyundai_card",
    channel_tier=3,
    listing_url="https://recruit.hyundaicard.com/",
    org="현대카드",
    location="서울",
    legitimacy_tier="T1",
)

LotteCardChannel = make_stub_channel_class(
    class_name="LotteCardChannel",
    channel_name="lotte_card",
    channel_tier=3,
    listing_url="https://lottecard.recruiter.co.kr/career/home",
    org="롯데카드",
    location="서울",
    legitimacy_tier="T1",
)

WooriCardChannel = make_stub_channel_class(
    class_name="WooriCardChannel",
    channel_name="woori_card",
    channel_tier=3,
    listing_url="https://wooricard.recruiter.co.kr/career/home",
    org="우리카드",
    location="서울",
    legitimacy_tier="T1",
)

BcCardChannel = make_stub_channel_class(
    class_name="BcCardChannel",
    channel_name="bc_card",
    channel_tier=3,
    listing_url="https://bccard.recruiter.co.kr/career/home",
    org="비씨카드",
    location="서울",
    legitimacy_tier="T1",
)

HanaCardChannel = make_stub_channel_class(
    class_name="HanaCardChannel",
    channel_name="hana_card",
    channel_tier=3,
    listing_url="https://hanacard.recruiter.co.kr/career/home",
    org="하나카드",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 캐피탈 추가 (tier 4) — 현대캐피탈/메리츠캐피탈은 institutions.py에 있음
# ---------------------------------------------------------------------------

KbCapitalChannel = make_stub_channel_class(
    class_name="KbCapitalChannel",
    channel_name="kb_capital",
    channel_tier=4,
    listing_url="https://kbcapital.recruiter.co.kr/career/home",
    org="KB캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

HanaCapitalChannel = make_stub_channel_class(
    class_name="HanaCapitalChannel",
    channel_name="hana_capital",
    channel_tier=4,
    listing_url="https://hanacapital.recruiter.co.kr/career/home",
    org="하나캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanCapitalChannel = make_stub_channel_class(
    class_name="ShinhanCapitalChannel",
    channel_name="shinhan_capital",
    channel_tier=4,
    listing_url="https://shinhancapital.recruiter.co.kr/career/home",
    org="신한캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

WooriCapitalChannel = make_stub_channel_class(
    class_name="WooriCapitalChannel",
    channel_name="woori_capital",
    channel_tier=4,
    listing_url="https://wooricapital.recruiter.co.kr/career/home",
    org="우리금융캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

AjuCapitalChannel = make_stub_channel_class(
    class_name="AjuCapitalChannel",
    channel_name="aju_capital",
    channel_tier=4,
    listing_url="https://ajucapital.recruiter.co.kr/career/home",
    org="아주캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

LotteCapitalChannel = make_stub_channel_class(
    class_name="LotteCapitalChannel",
    channel_name="lotte_capital",
    channel_tier=4,
    listing_url="https://lottecapital.recruiter.co.kr/career/home",
    org="롯데캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

BnkCapitalChannel = make_stub_channel_class(
    class_name="BnkCapitalChannel",
    channel_name="bnk_capital",
    channel_tier=4,
    listing_url="https://bnkcapital.recruiter.co.kr/career/home",
    org="BNK캐피탈",
    location="부산",
    legitimacy_tier="T1",
)

JbWooriCapitalChannel = make_stub_channel_class(
    class_name="JbWooriCapitalChannel",
    channel_name="jb_woori_capital",
    channel_tier=4,
    listing_url="https://jbwooricapital.recruiter.co.kr/career/home",
    org="JB우리캐피탈",
    location="광주",
    legitimacy_tier="T1",
)

NhCapitalChannel = make_stub_channel_class(
    class_name="NhCapitalChannel",
    channel_name="nh_capital",
    channel_tier=4,
    listing_url="https://nhcapital.recruiter.co.kr/career/home",
    org="NH농협캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

DgbCapitalChannel = make_stub_channel_class(
    class_name="DgbCapitalChannel",
    channel_name="dgb_capital",
    channel_tier=4,
    listing_url="https://dgbcapital.recruiter.co.kr/career/home",
    org="DGB캐피탈",
    location="대구",
    legitimacy_tier="T1",
)

KdbCapitalChannel = make_stub_channel_class(
    class_name="KdbCapitalChannel",
    channel_name="kdb_capital",
    channel_tier=4,
    listing_url="https://kdbc.recruiter.co.kr/career/home",
    org="산은캐피탈",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 저축은행 추가 (tier 4) — SBI/OK/웰컴은 institutions.py에 있음
# ---------------------------------------------------------------------------

KiwoomYesSavingsChannel = make_stub_channel_class(
    class_name="KiwoomYesSavingsChannel",
    channel_name="kiwoom_yes_savings",
    channel_tier=4,
    listing_url="https://kiwoomyes.recruiter.co.kr/career/home",
    org="키움YES저축은행",
    location="서울",
    legitimacy_tier="T1",
)

PepperSavingsChannel = make_stub_channel_class(
    class_name="PepperSavingsChannel",
    channel_name="pepper_savings",
    channel_tier=4,
    listing_url="https://pepperbank.recruiter.co.kr/career/home",
    org="페퍼저축은행",
    location="서울",
    legitimacy_tier="T1",
)

AquonSavingsChannel = make_stub_channel_class(
    class_name="AquonSavingsChannel",
    channel_name="aquon_savings",
    channel_tier=4,
    listing_url="https://aquon.recruiter.co.kr/career/home",
    org="애큐온저축은행",
    location="서울",
    legitimacy_tier="T1",
)

KitSavingsChannel = make_stub_channel_class(
    class_name="KitSavingsChannel",
    channel_name="kit_savings",
    channel_tier=4,
    listing_url="https://kitb.recruiter.co.kr/career/home",
    org="한국투자저축은행",
    location="서울",
    legitimacy_tier="T1",
)

JtSavingsChannel = make_stub_channel_class(
    class_name="JtSavingsChannel",
    channel_name="jt_savings",
    channel_tier=4,
    listing_url="https://jtsavings.recruiter.co.kr/career/home",
    org="JT저축은행",
    location="서울",
    legitimacy_tier="T1",
)

OsbSavingsChannel = make_stub_channel_class(
    class_name="OsbSavingsChannel",
    channel_name="osb_savings",
    channel_tier=4,
    listing_url="https://osb.recruiter.co.kr/career/home",
    org="OSB저축은행",
    location="서울",
    legitimacy_tier="T1",
)

ThekSavingsChannel = make_stub_channel_class(
    class_name="ThekSavingsChannel",
    channel_name="thek_savings",
    channel_tier=4,
    listing_url="https://thek.recruiter.co.kr/career/home",
    org="더케이저축은행",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 자산운용 (tier 3)
# ---------------------------------------------------------------------------

MiraeassetAmChannel = make_stub_channel_class(
    class_name="MiraeassetAmChannel",
    channel_name="miraeasset_am",
    channel_tier=3,
    listing_url="https://miraeassetam.recruiter.co.kr/career/home",
    org="미래에셋자산운용",
    location="서울",
    legitimacy_tier="T1",
)

KitAmChannel = make_stub_channel_class(
    class_name="KitAmChannel",
    channel_name="kit_am",
    channel_tier=3,
    listing_url="https://kitam.recruiter.co.kr/career/home",
    org="한국투자신탁운용",
    location="서울",
    legitimacy_tier="T1",
)

SamsungAmChannel = make_stub_channel_class(
    class_name="SamsungAmChannel",
    channel_name="samsung_am",
    channel_tier=3,
    listing_url="https://samsungam.recruiter.co.kr/career/home",
    org="삼성자산운용",
    location="서울",
    legitimacy_tier="T1",
)

KbAmChannel = make_stub_channel_class(
    class_name="KbAmChannel",
    channel_name="kb_am",
    channel_tier=3,
    listing_url="https://kbam.recruiter.co.kr/career/home",
    org="KB자산운용",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanAmChannel = make_stub_channel_class(
    class_name="ShinhanAmChannel",
    channel_name="shinhan_am",
    channel_tier=3,
    listing_url="https://shinhanam.recruiter.co.kr/career/home",
    org="신한자산운용",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaAmChannel = make_stub_channel_class(
    class_name="HanwhaAmChannel",
    channel_name="hanwha_am",
    channel_tier=3,
    listing_url="https://hanwaaim.recruiter.co.kr/career/home",
    org="한화자산운용",
    location="서울",
    legitimacy_tier="T1",
)

NhAmundiAmChannel = make_stub_channel_class(
    class_name="NhAmundiAmChannel",
    channel_name="nh_amundi_am",
    channel_tier=3,
    listing_url="https://nhamundi.recruiter.co.kr/career/home",
    org="NH-Amundi자산운용",
    location="서울",
    legitimacy_tier="T1",
)

KiwoomAmChannel = make_stub_channel_class(
    class_name="KiwoomAmChannel",
    channel_name="kiwoom_am",
    channel_tier=3,
    listing_url="https://kiwoomam.recruiter.co.kr/career/home",
    org="키움투자자산운용",
    location="서울",
    legitimacy_tier="T1",
)

ShinyoungAmChannel = make_stub_channel_class(
    class_name="ShinyoungAmChannel",
    channel_name="shinyoung_am",
    channel_tier=3,
    listing_url="https://shinyoungam.recruiter.co.kr/career/home",
    org="신영자산운용",
    location="서울",
    legitimacy_tier="T1",
)

KyoboAxaAmChannel = make_stub_channel_class(
    class_name="KyoboAxaAmChannel",
    channel_name="kyobo_axa_am",
    channel_tier=3,
    listing_url="https://kyoboaxa.recruiter.co.kr/career/home",
    org="교보악사자산운용",
    location="서울",
    legitimacy_tier="T1",
)

EastspringAmChannel = make_stub_channel_class(
    class_name="EastspringAmChannel",
    channel_name="eastspring_am",
    channel_tier=3,
    listing_url="https://eastspring.recruiter.co.kr/career/home",
    org="이스트스프링자산운용",
    location="서울",
    legitimacy_tier="T1",
)

TimefolioAmChannel = make_stub_channel_class(
    class_name="TimefolioAmChannel",
    channel_name="timefolio_am",
    channel_tier=3,
    listing_url="https://timefolio.recruiter.co.kr/career/home",
    org="타임폴리오자산운용",
    location="서울",
    legitimacy_tier="T1",
)

TrustonAmChannel = make_stub_channel_class(
    class_name="TrustonAmChannel",
    channel_name="truston_am",
    channel_tier=3,
    listing_url="https://truston.recruiter.co.kr/career/home",
    org="트러스톤자산운용",
    location="서울",
    legitimacy_tier="T1",
)

ViAmChannel = make_stub_channel_class(
    class_name="ViAmChannel",
    channel_name="vi_am",
    channel_tier=3,
    listing_url="https://vi.recruiter.co.kr/career/home",
    org="브이아이자산운용",
    location="서울",
    legitimacy_tier="T1",
)

LazardAmChannel = make_stub_channel_class(
    class_name="LazardAmChannel",
    channel_name="lazard_am",
    channel_tier=3,
    listing_url="https://lazard.recruiter.co.kr/career/home",
    org="라자드코리아자산운용",
    location="서울",
    legitimacy_tier="T1",
)

AbAmChannel = make_stub_channel_class(
    class_name="AbAmChannel",
    channel_name="ab_am",
    channel_tier=3,
    listing_url="https://alliancebernstein.recruiter.co.kr/career/home",
    org="얼라이언스번스틴",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# PE / VC (tier 4)
# ---------------------------------------------------------------------------

KvicChannel = make_stub_channel_class(
    class_name="KvicChannel",
    channel_name="kvic",
    channel_tier=4,
    listing_url="https://kvic.recruiter.co.kr/career/home",
    org="한국벤처투자(KVIC)",
    location="서울",
    legitimacy_tier="T1",
)

KgfChannel = make_stub_channel_class(
    class_name="KgfChannel",
    channel_name="kgf",
    channel_tier=4,
    listing_url="https://kgf.recruiter.co.kr/career/home",
    org="한국성장금융",
    location="서울",
    legitimacy_tier="T1",
)

MbkChannel = make_stub_channel_class(
    class_name="MbkChannel",
    channel_name="mbk",
    channel_tier=4,
    listing_url="https://www.mbkpartnersinvestment.com/en/careers",
    org="MBK파트너스",
    location="서울",
    legitimacy_tier="T1",
)

HahnCoChannel = make_stub_channel_class(
    class_name="HahnCoChannel",
    channel_name="hahn_co",
    channel_tier=4,
    listing_url="https://www.hahnco.com/careers",
    org="한앤컴퍼니",
    location="서울",
    legitimacy_tier="T1",
)

ImmChannel = make_stub_channel_class(
    class_name="ImmChannel",
    channel_name="imm",
    channel_tier=4,
    listing_url="https://www.immpe.com/en/careers",
    org="IMM인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

SticChannel = make_stub_channel_class(
    class_name="SticChannel",
    channel_name="stic",
    channel_tier=4,
    listing_url="https://www.stickvp.com/en/career",
    org="스틱인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

SkylakeChannel = make_stub_channel_class(
    class_name="SkylakeChannel",
    channel_name="skylake",
    channel_tier=4,
    listing_url="https://www.skylakeinc.com/en/careers",
    org="스카이레이크인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

DaolInvChannel = make_stub_channel_class(
    class_name="DaolInvChannel",
    channel_name="daol_inv",
    channel_tier=4,
    listing_url="https://daolins.recruiter.co.kr/career/home",
    org="다올인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

KitPartnersChannel = make_stub_channel_class(
    class_name="KitPartnersChannel",
    channel_name="kit_partners",
    channel_tier=4,
    listing_url="https://kitpartners.recruiter.co.kr/career/home",
    org="한국투자파트너스",
    location="서울",
    legitimacy_tier="T1",
)

KakaoInvChannel = make_stub_channel_class(
    class_name="KakaoInvChannel",
    channel_name="kakao_inv",
    channel_tier=4,
    listing_url="https://kakaoinvestment.career.greetinghr.com/",
    org="카카오인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

LbInvChannel = make_stub_channel_class(
    class_name="LbInvChannel",
    channel_name="lb_inv",
    channel_tier=4,
    listing_url="https://lbinvestment.recruiter.co.kr/career/home",
    org="LB인베스트먼트",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 핀테크 추가 (tier 4) — 토스/카카오페이/뱅크샐러드/핀다는 별도 채널 파일 있음
# ---------------------------------------------------------------------------

NaverPayChannel = make_stub_channel_class(
    class_name="NaverPayChannel",
    channel_name="naver_pay",
    channel_tier=4,
    listing_url="https://navercorp.recruiter.co.kr/career/home",
    org="네이버페이",
    location="성남",
    legitimacy_tier="T1",
)

EightPercentChannel = make_stub_channel_class(
    class_name="EightPercentChannel",
    channel_name="eight_percent",
    channel_tier=4,
    listing_url="https://8percent.kr/career/",
    org="8퍼센트",
    location="서울",
    legitimacy_tier="T1",
)

PaycoChannel = make_stub_channel_class(
    class_name="PaycoChannel",
    channel_name="payco",
    channel_tier=4,
    listing_url="https://payco.recruiter.co.kr/career/home",
    org="페이코(NHN)",
    location="성남",
    legitimacy_tier="T1",
)

__all__ = [
    # 카드사
    "ShinhanCardChannel",
    "SamsungCardChannel",
    "KbCardChannel",
    "HyundaiCardChannel",
    "LotteCardChannel",
    "WooriCardChannel",
    "BcCardChannel",
    "HanaCardChannel",
    # 캐피탈
    "KbCapitalChannel",
    "HanaCapitalChannel",
    "ShinhanCapitalChannel",
    "WooriCapitalChannel",
    "AjuCapitalChannel",
    "LotteCapitalChannel",
    "BnkCapitalChannel",
    "JbWooriCapitalChannel",
    "NhCapitalChannel",
    "DgbCapitalChannel",
    "KdbCapitalChannel",
    # 저축은행
    "KiwoomYesSavingsChannel",
    "PepperSavingsChannel",
    "AquonSavingsChannel",
    "KitSavingsChannel",
    "JtSavingsChannel",
    "OsbSavingsChannel",
    "ThekSavingsChannel",
    # 자산운용
    "MiraeassetAmChannel",
    "KitAmChannel",
    "SamsungAmChannel",
    "KbAmChannel",
    "ShinhanAmChannel",
    "HanwhaAmChannel",
    "NhAmundiAmChannel",
    "KiwoomAmChannel",
    "ShinyoungAmChannel",
    "KyoboAxaAmChannel",
    "EastspringAmChannel",
    "TimefolioAmChannel",
    "TrustonAmChannel",
    "ViAmChannel",
    "LazardAmChannel",
    "AbAmChannel",
    # PE/VC
    "KvicChannel",
    "KgfChannel",
    "MbkChannel",
    "HahnCoChannel",
    "ImmChannel",
    "SticChannel",
    "SkylakeChannel",
    "DaolInvChannel",
    "KitPartnersChannel",
    "KakaoInvChannel",
    "LbInvChannel",
    # 핀테크
    "NaverPayChannel",
    "EightPercentChannel",
    "PaycoChannel",
]
