"""증권사·선물사·생명보험·손해보험 채용 채널 — make_stub_channel_class 배치.

URL 정책:
    recruiter.co.kr 슬러그가 DNS 검증된 경우 → SPA (Playwright)
    그 외 → 회사 공식 채용 페이지 (requests + 범용 파서)

Tier 분류:
    3 = 증권사 / 선물사 / 보험사
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

# ---------------------------------------------------------------------------
# 증권사 (tier 3)
# ✅ recruiter.co.kr 슬러그 확인 → SPA
# ❌ DNS 실패 → 공식 채용 페이지
# ---------------------------------------------------------------------------

KyoboSecChannel = make_stub_channel_class(
    class_name="KyoboSecChannel",
    channel_name="kyobo_sec",
    channel_tier=3,
    listing_url="https://www.kyobosec.co.kr/recruit/main.do",
    org="교보증권",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaSecChannel = make_stub_channel_class(
    class_name="HanwhaSecChannel",
    channel_name="hanwha_sec",
    channel_tier=3,
    listing_url="https://www.hanwhainvestment.com/career",
    org="한화투자증권",
    location="서울",
    legitimacy_tier="T1",
)

YuantaSecChannel = make_stub_channel_class(
    class_name="YuantaSecChannel",
    channel_name="yuanta_sec",
    channel_tier=3,
    listing_url="https://www.yuanta.co.kr/contents/corporate/career/recruit.do",
    org="유안타증권",
    location="서울",
    legitimacy_tier="T1",
)

EugeneSecChannel = make_stub_channel_class(
    class_name="EugeneSecChannel",
    channel_name="eugene_sec",
    channel_tier=3,
    listing_url="https://eugenefn.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="유진투자증권",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiCarSecChannel = make_stub_channel_class(
    class_name="HyundaiCarSecChannel",
    channel_name="hyundai_car_sec",
    channel_tier=3,
    listing_url="https://www.hmcsec.com/about/recruit.do",
    org="현대차증권",
    location="서울",
    legitimacy_tier="T1",
)

HiSecChannel = make_stub_channel_class(
    class_name="HiSecChannel",
    channel_name="hi_sec",
    channel_tier=3,
    listing_url="https://www.hi-invest.co.kr/",
    org="하이투자증권",
    location="서울",
    legitimacy_tier="T1",
)

DbFiChannel = make_stub_channel_class(
    class_name="DbFiChannel",
    channel_name="db_fi",
    channel_tier=3,
    listing_url="https://www.dbfi.co.kr/",
    org="DB금융투자",
    location="서울",
    legitimacy_tier="T1",
)

SkSecChannel = make_stub_channel_class(
    class_name="SkSecChannel",
    channel_name="sk_sec",
    channel_tier=3,
    listing_url="https://www.sksec.com/",
    org="SK증권",
    location="서울",
    legitimacy_tier="T1",
)

ImSecChannel = make_stub_channel_class(
    class_name="ImSecChannel",
    channel_name="im_sec",
    channel_tier=3,
    listing_url="https://www.imsec.co.kr/",
    org="iM증권",
    location="서울",
    legitimacy_tier="T1",
)

CapeSecChannel = make_stub_channel_class(
    class_name="CapeSecChannel",
    channel_name="cape_sec",
    channel_tier=3,
    listing_url="https://www.cape.co.kr/",
    org="케이프투자증권",
    location="서울",
    legitimacy_tier="T1",
)

KoreafossSecChannel = make_stub_channel_class(
    class_name="KoreafossSecChannel",
    channel_name="koreafoss_sec",
    channel_tier=3,
    listing_url="https://www.koreafoss.co.kr/",
    org="한국포스증권",
    location="서울",
    legitimacy_tier="T1",
)

BookookSecChannel = make_stub_channel_class(
    class_name="BookookSecChannel",
    channel_name="bookook_sec",
    channel_tier=3,
    listing_url="https://www.bookook.co.kr/",
    org="부국증권",
    location="서울",
    legitimacy_tier="T1",
)

ShinyoungSecChannel = make_stub_channel_class(
    class_name="ShinyoungSecChannel",
    channel_name="shinyoung_sec",
    channel_tier=3,
    listing_url="https://www.shinyoung.com/",
    org="신영증권",
    location="서울",
    legitimacy_tier="T1",
)

HanyangSecChannel = make_stub_channel_class(
    class_name="HanyangSecChannel",
    channel_name="hanyang_sec",
    channel_tier=3,
    listing_url="https://www.hanyang.co.kr/",
    org="한양증권",
    location="서울",
    legitimacy_tier="T1",
)

YuhwaSecChannel = make_stub_channel_class(
    class_name="YuhwaSecChannel",
    channel_name="yuhwa_sec",
    channel_tier=3,
    listing_url="https://www.yuhwasec.co.kr/",
    org="유화증권",
    location="서울",
    legitimacy_tier="T1",
)

BnkSecChannel = make_stub_channel_class(
    class_name="BnkSecChannel",
    channel_name="bnk_sec",
    channel_tier=3,
    listing_url="https://www.bnkfn.co.kr/",
    org="BNK투자증권",
    location="부산",
    legitimacy_tier="T1",
)

HeungkukSecChannel = make_stub_channel_class(
    class_name="HeungkukSecChannel",
    channel_name="heungkuk_sec",
    channel_tier=3,
    listing_url="https://www.heungkuksec.co.kr/",
    org="흥국증권",
    location="서울",
    legitimacy_tier="T1",
)

DaolSecChannel = make_stub_channel_class(
    class_name="DaolSecChannel",
    channel_name="daol_sec",
    channel_tier=3,
    listing_url="https://www.daol.co.kr/",
    org="다올투자증권",
    location="서울",
    legitimacy_tier="T1",
)

LeadingSecChannel = make_stub_channel_class(
    class_name="LeadingSecChannel",
    channel_name="leading_sec",
    channel_tier=3,
    listing_url="https://leading.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="리딩투자증권",
    location="서울",
    legitimacy_tier="T1",
)

KoreaAssetSecChannel = make_stub_channel_class(
    class_name="KoreaAssetSecChannel",
    channel_name="korea_asset_sec",
    channel_tier=3,
    listing_url="https://www.koreaasset.co.kr/",
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
    listing_url="https://www.samsungfutures.co.kr/",
    org="삼성선물",
    location="서울",
    legitimacy_tier="T1",
)

NhFuturesChannel = make_stub_channel_class(
    class_name="NhFuturesChannel",
    channel_name="nh_futures",
    channel_tier=3,
    listing_url="https://www.nhfutures.co.kr/",
    org="NH선물",
    location="서울",
    legitimacy_tier="T1",
)

HanaFuturesChannel = make_stub_channel_class(
    class_name="HanaFuturesChannel",
    channel_name="hana_futures",
    channel_tier=3,
    listing_url="https://www.hanafutures.co.kr/",
    org="하나선물",
    location="서울",
    legitimacy_tier="T1",
)

KiwoomFuturesChannel = make_stub_channel_class(
    class_name="KiwoomFuturesChannel",
    channel_name="kiwoom_futures",
    channel_tier=3,
    listing_url="https://futures.kiwoom.com/",
    org="키움선물",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanFuturesChannel = make_stub_channel_class(
    class_name="ShinhanFuturesChannel",
    channel_name="shinhan_futures",
    channel_tier=3,
    listing_url="https://www.shinhansec.com/siw/user/employ/PC/list.do",
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
    listing_url="https://hanwhalife.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="한화생명",
    location="서울",
    legitimacy_tier="T1",
)

KyoboLifeChannel = make_stub_channel_class(
    class_name="KyoboLifeChannel",
    channel_name="kyobo_life",
    channel_tier=3,
    listing_url="https://www.kyobolife.co.kr/kl/recruit/main.do",
    org="교보생명",
    location="서울",
    legitimacy_tier="T1",
)

ShinhanLifeChannel = make_stub_channel_class(
    class_name="ShinhanLifeChannel",
    channel_name="shinhan_life",
    channel_tier=3,
    listing_url="https://shinhanlife.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="신한라이프",
    location="서울",
    legitimacy_tier="T1",
)

NhLifeChannel = make_stub_channel_class(
    class_name="NhLifeChannel",
    channel_name="nh_life",
    channel_tier=3,
    listing_url="https://www.nhlife.com.co.kr/recruit/",
    org="NH농협생명",
    location="서울",
    legitimacy_tier="T1",
)

HanaLifeChannel = make_stub_channel_class(
    class_name="HanaLifeChannel",
    channel_name="hana_life",
    channel_tier=3,
    listing_url="https://hanalife.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="하나생명",
    location="서울",
    legitimacy_tier="T1",
)

KbLifeChannel = make_stub_channel_class(
    class_name="KbLifeChannel",
    channel_name="kb_life",
    channel_tier=3,
    listing_url="https://kblife.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="KB라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

DongyangLifeChannel = make_stub_channel_class(
    class_name="DongyangLifeChannel",
    channel_name="dongyang_life",
    channel_tier=3,
    listing_url="https://www.dynl.com/",
    org="동양생명",
    location="서울",
    legitimacy_tier="T1",
)

MiraeassetLifeChannel = make_stub_channel_class(
    class_name="MiraeassetLifeChannel",
    channel_name="miraeasset_life",
    channel_tier=3,
    listing_url="https://career.miraeasset.com/",
    org="미래에셋생명",
    location="서울",
    legitimacy_tier="T1",
)

AblLifeChannel = make_stub_channel_class(
    class_name="AblLifeChannel",
    channel_name="abl_life",
    channel_tier=3,
    listing_url="https://www.abllife.co.kr/",
    org="ABL생명",
    location="서울",
    legitimacy_tier="T1",
)

MetlifeChannel = make_stub_channel_class(
    class_name="MetlifeChannel",
    channel_name="metlife",
    channel_tier=3,
    listing_url="https://metlife.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="메트라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

AiaLifeChannel = make_stub_channel_class(
    class_name="AiaLifeChannel",
    channel_name="aia_life",
    channel_tier=3,
    listing_url="https://www.aia.co.kr/ko/about-aia/careers.html",
    org="AIA생명",
    location="서울",
    legitimacy_tier="T1",
)

ChubbLifeChannel = make_stub_channel_class(
    class_name="ChubbLifeChannel",
    channel_name="chubb_life",
    channel_tier=3,
    listing_url="https://www.chubblife.co.kr/",
    org="처브라이프생명",
    location="서울",
    legitimacy_tier="T1",
)

FubonLifeChannel = make_stub_channel_class(
    class_name="FubonLifeChannel",
    channel_name="fubon_life",
    channel_tier=3,
    listing_url="https://www.fubonhyundai.co.kr/",
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
    listing_url="https://www.samsungfire.com/career/",
    org="삼성화재",
    location="서울",
    legitimacy_tier="T1",
)

HyundaiMarineChannel = make_stub_channel_class(
    class_name="HyundaiMarineChannel",
    channel_name="hyundai_marine",
    channel_tier=3,
    listing_url="https://www.hiins.co.kr/",
    org="현대해상",
    location="서울",
    legitimacy_tier="T1",
)

DbInsChannel = make_stub_channel_class(
    class_name="DbInsChannel",
    channel_name="db_ins",
    channel_tier=3,
    listing_url="https://www.dbins.co.kr/",
    org="DB손해보험",
    location="서울",
    legitimacy_tier="T1",
)

KbInsChannel = make_stub_channel_class(
    class_name="KbInsChannel",
    channel_name="kb_ins",
    channel_tier=3,
    listing_url="https://kbinsure.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
    org="KB손해보험",
    location="서울",
    legitimacy_tier="T1",
)

MeritzFireChannel = make_stub_channel_class(
    class_name="MeritzFireChannel",
    channel_name="meritz_fire",
    channel_tier=3,
    listing_url="https://www.meritzfire.com/",
    org="메리츠화재",
    location="서울",
    legitimacy_tier="T1",
)

HanwhaInsChannel = make_stub_channel_class(
    class_name="HanwhaInsChannel",
    channel_name="hanwha_ins",
    channel_tier=3,
    listing_url="https://www.hanwhageneral.com/",
    org="한화손해보험",
    location="서울",
    legitimacy_tier="T1",
)

LotteInsChannel = make_stub_channel_class(
    class_name="LotteInsChannel",
    channel_name="lotte_ins",
    channel_tier=3,
    listing_url="https://lotteins.recruiter.co.kr/career/home",  # ✅ HEAD 200
    org="롯데손해보험",
    location="서울",
    legitimacy_tier="T1",
)

HeungkukFireChannel = make_stub_channel_class(
    class_name="HeungkukFireChannel",
    channel_name="heungkuk_fire",
    channel_tier=3,
    listing_url="https://www.heungkukfire.co.kr/",
    org="흥국화재",
    location="서울",
    legitimacy_tier="T1",
)

MgInsChannel = make_stub_channel_class(
    class_name="MgInsChannel",
    channel_name="mg_ins",
    channel_tier=3,
    listing_url="https://www.mghfi.com/",
    org="MG손해보험",
    location="서울",
    legitimacy_tier="T1",
)

NhFireChannel = make_stub_channel_class(
    class_name="NhFireChannel",
    channel_name="nh_fire",
    channel_tier=3,
    listing_url="https://www.nhfire.co.kr/",
    org="농협손해보험",
    location="서울",
    legitimacy_tier="T1",
)

ThekInsChannel = make_stub_channel_class(
    class_name="ThekInsChannel",
    channel_name="thek_ins",
    channel_tier=3,
    listing_url="https://www.thekfire.co.kr/",
    org="더케이손해보험",
    location="서울",
    legitimacy_tier="T1",
)

HanaInsChannel = make_stub_channel_class(
    class_name="HanaInsChannel",
    channel_name="hana_ins",
    channel_tier=3,
    listing_url="https://hanafire.recruiter.co.kr/career/home",  # ✅ HEAD 200 (other)
    org="하나손해보험",
    location="서울",
    legitimacy_tier="T1",
)

CarrotInsChannel = make_stub_channel_class(
    class_name="CarrotInsChannel",
    channel_name="carrot_ins",
    channel_tier=3,
    listing_url="https://carrotins.recruiter.co.kr/career/home",  # ✅ 유효 슬러그
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
