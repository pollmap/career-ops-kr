"""증권사·선물사·생명보험·손해보험 채용 채널 — make_stub_channel_class 배치.

Tier 분류:
    3 = 증권사 / 선물사 / 보험사
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

# ---------------------------------------------------------------------------
# 증권사 추가 (tier 3) — KB증권/하나증권/NH증권/삼성증권/신한투자증권/한국투자증권/IBK증권/대신증권은 별도 채널 파일 있음
# ---------------------------------------------------------------------------

KyoboSecChannel = make_stub_channel_class(
    class_name="KyoboSecChannel",
    channel_name="kyobo_sec",
    channel_tier=3,
    listing_url="https://kyobosec.recruiter.co.kr/career/home",
    org="교보증권",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaSecChannel = make_stub_channel_class(
    class_name="HanwhaSecChannel",
    channel_name="hanwha_sec",
    channel_tier=3,
    listing_url="https://hanwhasec.recruiter.co.kr/career/home",
    org="한화투자증권",
    location="서울",
    legitimacy_tier="T1",
)

YuantaSecChannel = make_stub_channel_class(
    class_name="YuantaSecChannel",
    channel_name="yuanta_sec",
    channel_tier=3,
    listing_url="https://yuanta.recruiter.co.kr/career/home",
    org="유안타증권",
    location="서울",
    legitimacy_tier="T1",
)

EugeneSecChannel = make_stub_channel_class(
    class_name="EugeneSecChannel",
    channel_name="eugene_sec",
    channel_tier=3,
    listing_url="https://eugenefn.recruiter.co.kr/career/home",
    org="유진투자증권",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiCarSecChannel = make_stub_channel_class(
    class_name="HyundaiCarSecChannel",
    channel_name="hyundai_car_sec",
    channel_tier=3,
    listing_url="https://hmcsec.recruiter.co.kr/career/home",
    org="현대차증권",
    location="서울",
    legitimacy_tier="T1",
)

HiSecChannel = make_stub_channel_class(
    class_name="HiSecChannel",
    channel_name="hi_sec",
    channel_tier=3,
    listing_url="https://hiinvest.recruiter.co.kr/career/home",
    org="하이투자증권",
    location="서울",
    legitimacy_tier="T1",
)

DbFiChannel = make_stub_channel_class(
    class_name="DbFiChannel",
    channel_name="db_fi",
    channel_tier=3,
    listing_url="https://dbfi.recruiter.co.kr/career/home",
    org="DB금융투자",
    location="서울",
    legitimacy_tier="T1",
)

SkSecChannel = make_stub_channel_class(
    class_name="SkSecChannel",
    channel_name="sk_sec",
    channel_tier=3,
    listing_url="https://sksec.recruiter.co.kr/career/home",
    org="SK증권",
    location="서울",
    legitimacy_tier="T1",
)

ImSecChannel = make_stub_channel_class(
    class_name="ImSecChannel",
    channel_name="im_sec",
    channel_tier=3,
    listing_url="https://imsec.recruiter.co.kr/career/home",
    org="iM증권",
    location="서울",
    legitimacy_tier="T1",
)

CapeSecChannel = make_stub_channel_class(
    class_name="CapeSecChannel",
    channel_name="cape_sec",
    channel_tier=3,
    listing_url="https://cape.recruiter.co.kr/career/home",
    org="케이프투자증권",
    location="서울",
    legitimacy_tier="T1",
)

KoreafossSecChannel = make_stub_channel_class(
    class_name="KoreafossSecChannel",
    channel_name="koreafoss_sec",
    channel_tier=3,
    listing_url="https://koreafoss.recruiter.co.kr/career/home",
    org="한국포스증권",
    location="서울",
    legitimacy_tier="T1",
)

BookookSecChannel = make_stub_channel_class(
    class_name="BookookSecChannel",
    channel_name="bookook_sec",
    channel_tier=3,
    listing_url="https://bookook.recruiter.co.kr/career/home",
    org="부국증권",
    location="서울",
    legitimacy_tier="T1",
)

ShinyoungSecChannel = make_stub_channel_class(
    class_name="ShinyoungSecChannel",
    channel_name="shinyoung_sec",
    channel_tier=3,
    listing_url="https://shinyoung.recruiter.co.kr/career/home",
    org="신영증권",
    location="서울",
    legitimacy_tier="T1",
)

HanyangSecChannel = make_stub_channel_class(
    class_name="HanyangSecChannel",
    channel_name="hanyang_sec",
    channel_tier=3,
    listing_url="https://hanyang.recruiter.co.kr/career/home",
    org="한양증권",
    location="서울",
    legitimacy_tier="T1",
)

YuhwaSecChannel = make_stub_channel_class(
    class_name="YuhwaSecChannel",
    channel_name="yuhwa_sec",
    channel_tier=3,
    listing_url="https://yuhwa.recruiter.co.kr/career/home",
    org="유화증권",
    location="서울",
    legitimacy_tier="T1",
)

BnkSecChannel = make_stub_channel_class(
    class_name="BnkSecChannel",
    channel_name="bnk_sec",
    channel_tier=3,
    listing_url="https://bnkis.recruiter.co.kr/career/home",
    org="BNK투자증권",
    location="부산",
    legitimacy_tier="T1",
)

HeungkukSecChannel = make_stub_channel_class(
    class_name="HeungkukSecChannel",
    channel_name="heungkuk_sec",
    channel_tier=3,
    listing_url="https://heungkuksec.recruiter.co.kr/career/home",
    org="흥국증권",
    location="서울",
    legitimacy_tier="T1",
)

DaolSecChannel = make_stub_channel_class(
    class_name="DaolSecChannel",
    channel_name="daol_sec",
    channel_tier=3,
    listing_url="https://daol.recruiter.co.kr/career/home",
    org="다올투자증권",
    location="서울",
    legitimacy_tier="T1",
)

LeadingSecChannel = make_stub_channel_class(
    class_name="LeadingSecChannel",
    channel_name="leading_sec",
    channel_tier=3,
    listing_url="https://leading.recruiter.co.kr/career/home",
    org="리딩투자증권",
    location="서울",
    legitimacy_tier="T1",
)

KoreaAssetSecChannel = make_stub_channel_class(
    class_name="KoreaAssetSecChannel",
    channel_name="korea_asset_sec",
    channel_tier=3,
    listing_url="https://koreaasset.recruiter.co.kr/career/home",
    org="코리아에셋투자증권",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 선물사 (tier 3)
# ---------------------------------------------------------------------------

SamsungFuturesChannel = make_stub_channel_class(
    class_name="SamsungFuturesChannel",
    channel_name="samsung_futures",
    channel_tier=3,
    listing_url="https://samsungfutures.recruiter.co.kr/career/home",
    org="삼성선물",
    location="서울",
    legitimacy_tier="T1",
)

NhFuturesChannel = make_stub_channel_class(
    class_name="NhFuturesChannel",
    channel_name="nh_futures",
    channel_tier=3,
    listing_url="https://nhfutures.recruiter.co.kr/career/home",
    org="NH선물",
    location="서울",
    legitimacy_tier="T1",
)

HanaFuturesChannel = make_stub_channel_class(
    class_name="HanaFuturesChannel",
    channel_name="hana_futures",
    channel_tier=3,
    listing_url="https://hanafutures.recruiter.co.kr/career/home",
    org="하나선물",
    location="서울",
    legitimacy_tier="T1",
)

KiwoomFuturesChannel = make_stub_channel_class(
    class_name="KiwoomFuturesChannel",
    channel_name="kiwoom_futures",
    channel_tier=3,
    listing_url="https://kiwoomfutures.recruiter.co.kr/career/home",
    org="키움선물",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanFuturesChannel = make_stub_channel_class(
    class_name="ShinhanFuturesChannel",
    channel_name="shinhan_futures",
    channel_tier=3,
    listing_url="https://shinhanfutures.recruiter.co.kr/career/home",
    org="신한선물",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 생명보험사 (tier 3)
# ---------------------------------------------------------------------------

SamsungLifeChannel = make_stub_channel_class(
    class_name="SamsungLifeChannel",
    channel_name="samsung_life",
    channel_tier=3,
    listing_url="https://recruit.samsunglife.com/recruit/",
    org="삼성생명",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaLifeChannel = make_stub_channel_class(
    class_name="HanwhaLifeChannel",
    channel_name="hanwha_life",
    channel_tier=3,
    listing_url="https://hanwhalife.recruiter.co.kr/career/home",
    org="한화생명",
    location="서울",
    legitimacy_tier="T1",
)

KyoboLifeChannel = make_stub_channel_class(
    class_name="KyoboLifeChannel",
    channel_name="kyobo_life",
    channel_tier=3,
    listing_url="https://kyobogen.recruiter.co.kr/career/home",
    org="교보생명",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanLifeChannel = make_stub_channel_class(
    class_name="ShinhanLifeChannel",
    channel_name="shinhan_life",
    channel_tier=3,
    listing_url="https://shinhanlife.recruiter.co.kr/career/home",
    org="신한라이프",
    location="서울",
    legitimacy_tier="T1",
)

NhLifeChannel = make_stub_channel_class(
    class_name="NhLifeChannel",
    channel_name="nh_life",
    channel_tier=3,
    listing_url="https://nhlife.recruiter.co.kr/career/home",
    org="NH농협생명",
    location="서울",
    legitimacy_tier="T1",
)

HanaLifeChannel = make_stub_channel_class(
    class_name="HanaLifeChannel",
    channel_name="hana_life",
    channel_tier=3,
    listing_url="https://hanalife.recruiter.co.kr/career/home",
    org="하나생명",
    location="서울",
    legitimacy_tier="T1",
)

KbLifeChannel = make_stub_channel_class(
    class_name="KbLifeChannel",
    channel_name="kb_life",
    channel_tier=3,
    listing_url="https://kblife.recruiter.co.kr/career/home",
    org="KB라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

DongyangLifeChannel = make_stub_channel_class(
    class_name="DongyangLifeChannel",
    channel_name="dongyang_life",
    channel_tier=3,
    listing_url="https://dylife.recruiter.co.kr/career/home",
    org="동양생명",
    location="서울",
    legitimacy_tier="T1",
)

MiraeassetLifeChannel = make_stub_channel_class(
    class_name="MiraeassetLifeChannel",
    channel_name="miraeasset_life",
    channel_tier=3,
    listing_url="https://miraeassetlife.recruiter.co.kr/career/home",
    org="미래에셋생명",
    location="서울",
    legitimacy_tier="T1",
)

AblLifeChannel = make_stub_channel_class(
    class_name="AblLifeChannel",
    channel_name="abl_life",
    channel_tier=3,
    listing_url="https://abllife.recruiter.co.kr/career/home",
    org="ABL생명",
    location="서울",
    legitimacy_tier="T1",
)

MetlifeChannel = make_stub_channel_class(
    class_name="MetlifeChannel",
    channel_name="metlife",
    channel_tier=3,
    listing_url="https://metlife.recruiter.co.kr/career/home",
    org="메트라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

AiaLifeChannel = make_stub_channel_class(
    class_name="AiaLifeChannel",
    channel_name="aia_life",
    channel_tier=3,
    listing_url="https://aia.recruiter.co.kr/career/home",
    org="AIA생명",
    location="서울",
    legitimacy_tier="T1",
)

ChubbLifeChannel = make_stub_channel_class(
    class_name="ChubbLifeChannel",
    channel_name="chubb_life",
    channel_tier=3,
    listing_url="https://chubb.recruiter.co.kr/career/home",
    org="처브라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

FubonLifeChannel = make_stub_channel_class(
    class_name="FubonLifeChannel",
    channel_name="fubon_life",
    channel_tier=3,
    listing_url="https://fubon.recruiter.co.kr/career/home",
    org="푸본현대생명",
    location="서울",
    legitimacy_tier="T1",
)

# ---------------------------------------------------------------------------
# 손해보험사 (tier 3)
# ---------------------------------------------------------------------------

SamsungFireChannel = make_stub_channel_class(
    class_name="SamsungFireChannel",
    channel_name="samsung_fire",
    channel_tier=3,
    listing_url="https://samsungfire.recruiter.co.kr/career/home",
    org="삼성화재",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiMarineChannel = make_stub_channel_class(
    class_name="HyundaiMarineChannel",
    channel_name="hyundai_marine",
    channel_tier=3,
    listing_url="https://hiins.recruiter.co.kr/career/home",
    org="현대해상",
    location="서울",
    legitimacy_tier="T1",
)

DbInsChannel = make_stub_channel_class(
    class_name="DbInsChannel",
    channel_name="db_ins",
    channel_tier=3,
    listing_url="https://dbins.recruiter.co.kr/career/home",
    org="DB손해보험",
    location="서울",
    legitimacy_tier="T1",
)

KbInsChannel = make_stub_channel_class(
    class_name="KbInsChannel",
    channel_name="kb_ins",
    channel_tier=3,
    listing_url="https://kbinsure.recruiter.co.kr/career/home",
    org="KB손해보험",
    location="서울",
    legitimacy_tier="T1",
)

MeritzFireChannel = make_stub_channel_class(
    class_name="MeritzFireChannel",
    channel_name="meritz_fire",
    channel_tier=3,
    listing_url="https://meritzfire.recruiter.co.kr/career/home",
    org="메리츠화재",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaInsChannel = make_stub_channel_class(
    class_name="HanwhaInsChannel",
    channel_name="hanwha_ins",
    channel_tier=3,
    listing_url="https://hanwhageneral.recruiter.co.kr/career/home",
    org="한화손해보험",
    location="서울",
    legitimacy_tier="T1",
)

LotteInsChannel = make_stub_channel_class(
    class_name="LotteInsChannel",
    channel_name="lotte_ins",
    channel_tier=3,
    listing_url="https://lotteins.recruiter.co.kr/career/home",
    org="롯데손해보험",
    location="서울",
    legitimacy_tier="T1",
)

HeungkukFireChannel = make_stub_channel_class(
    class_name="HeungkukFireChannel",
    channel_name="heungkuk_fire",
    channel_tier=3,
    listing_url="https://heungkukfire.recruiter.co.kr/career/home",
    org="흥국화재",
    location="서울",
    legitimacy_tier="T1",
)

MgInsChannel = make_stub_channel_class(
    class_name="MgInsChannel",
    channel_name="mg_ins",
    channel_tier=3,
    listing_url="https://mgfire.recruiter.co.kr/career/home",
    org="MG손해보험",
    location="서울",
    legitimacy_tier="T1",
)

NhFireChannel = make_stub_channel_class(
    class_name="NhFireChannel",
    channel_name="nh_fire",
    channel_tier=3,
    listing_url="https://nhfire.recruiter.co.kr/career/home",
    org="농협손해보험",
    location="서울",
    legitimacy_tier="T1",
)

ThekInsChannel = make_stub_channel_class(
    class_name="ThekInsChannel",
    channel_name="thek_ins",
    channel_tier=3,
    listing_url="https://thekfire.recruiter.co.kr/career/home",
    org="더케이손해보험",
    location="서울",
    legitimacy_tier="T1",
)

HanaInsChannel = make_stub_channel_class(
    class_name="HanaInsChannel",
    channel_name="hana_ins",
    channel_tier=3,
    listing_url="https://hanafire.recruiter.co.kr/career/home",
    org="하나손해보험",
    location="서울",
    legitimacy_tier="T1",
)

CarrotInsChannel = make_stub_channel_class(
    class_name="CarrotInsChannel",
    channel_name="carrot_ins",
    channel_tier=3,
    listing_url="https://carrotins.recruiter.co.kr/career/home",
    org="캐롯손해보험",
    location="서울",
    legitimacy_tier="T1",
)

__all__ = [
    # 증권사
    "KyoboSecChannel",
    "HanwhaSecChannel",
    "YuantaSecChannel",
    "EugeneSecChannel",
    "HyundaiCarSecChannel",
    "HiSecChannel",
    "DbFiChannel",
    "SkSecChannel",
    "ImSecChannel",
    "CapeSecChannel",
    "KoreafossSecChannel",
    "BookookSecChannel",
    "ShinyoungSecChannel",
    "HanyangSecChannel",
    "YuhwaSecChannel",
    "BnkSecChannel",
    "HeungkukSecChannel",
    "DaolSecChannel",
    "LeadingSecChannel",
    "KoreaAssetSecChannel",
    # 선물사
    "SamsungFuturesChannel",
    "NhFuturesChannel",
    "HanaFuturesChannel",
    "KiwoomFuturesChannel",
    "ShinhanFuturesChannel",
    # 생명보험
    "SamsungLifeChannel",
    "HanwhaLifeChannel",
    "KyoboLifeChannel",
    "ShinhanLifeChannel",
    "NhLifeChannel",
    "HanaLifeChannel",
    "KbLifeChannel",
    "DongyangLifeChannel",
    "MiraeassetLifeChannel",
    "AblLifeChannel",
    "MetlifeChannel",
    "AiaLifeChannel",
    "ChubbLifeChannel",
    "FubonLifeChannel",
    # 손해보험
    "SamsungFireChannel",
    "HyundaiMarineChannel",
    "DbInsChannel",
    "KbInsChannel",
    "MeritzFireChannel",
    "HanwhaInsChannel",
    "LotteInsChannel",
    "HeungkukFireChannel",
    "MgInsChannel",
    "NhFireChannel",
    "ThekInsChannel",
    "HanaInsChannel",
    "CarrotInsChannel",
]
