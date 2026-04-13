"""Channel package — one module per portal.

Each channel subclasses :class:`career_ops_kr.channels.base.BaseChannel` and
is registered in :data:`CHANNEL_REGISTRY` so the orchestrator can dispatch
by name.

:class:`NotTunedYetError` lives in :mod:`career_ops_kr.channels._stub_errors`
to avoid circular imports: Tier 3-4 stub channels need to import the
exception at module load time, and putting it in this package's
``__init__.py`` would create a cycle. It is re-exported here for
convenience.

**Product Reach Tiers** (사용자 재정의 Sprint 5):
    - **General Major (T1)**: Linkareer, Wanted, JobKorea, Incruit,
      JobPlanet, Jasoseol, Saramin — the public-product backbone. These
      are what any user gets out of the box regardless of preset.
    - **Public Agency (T1)**: Jobalio, ApplyBok, YwWork24, Kiwoomda, DataQ —
      government / state-owned enterprise feeds.
    - **Tier 3 Securities**: Korean brokerage firms — domain-specific.
    - **Tier 4 Crypto/Fintech**: exchanges and lendtech — domain-specific.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_errors import NotTunedYetError
from career_ops_kr.channels.apply_bok import ApplyBokChannel
from career_ops_kr.channels.banksalad import BanksaladChannel
from career_ops_kr.channels.coinone import CoinoneChannel
from career_ops_kr.channels.customs import CustomsChannel
from career_ops_kr.channels.dapa import DapaChannel
from career_ops_kr.channels.government import GovernmentChannel
from career_ops_kr.channels.base import (
    BaseChannel,
    Channel,
    ChannelError,
    JobRecord,
    deadline_parser,
)
from career_ops_kr.channels.bithumb import BithumbChannel
from career_ops_kr.channels.catch import CatchChannel
from career_ops_kr.channels.daishin_sec import DaishinSecChannel
from career_ops_kr.channels.dataq import DataqChannel
from career_ops_kr.channels.dunamu import DunamuChannel
from career_ops_kr.channels.finda import FindaChannel
from career_ops_kr.channels.fsc import FscChannel
from career_ops_kr.channels.fss import FssChannel
from career_ops_kr.channels.gojobs import GoJobsChannel
from career_ops_kr.channels.hana_sec import HanaSecChannel
from career_ops_kr.channels.ibk_sec import IbkSecChannel
from career_ops_kr.channels.incruit import IncruitChannel
from career_ops_kr.channels.jasoseol import JasoseolChannel
from career_ops_kr.channels.jobalio import JobalioChannel
from career_ops_kr.channels.jobkorea import JobKoreaChannel
from career_ops_kr.channels.kisa import KisaChannel
from career_ops_kr.channels.jobplanet import JobPlanetChannel
from career_ops_kr.channels.kakao_bank import KakaoBankChannel
from career_ops_kr.channels.kakao_pay import KakaoPayChannel
from career_ops_kr.channels.kb_sec import KbSecChannel
from career_ops_kr.channels.kiwoom_kda import KiwoomKdaChannel
from career_ops_kr.channels.korea_invest_sec import KoreaInvestSecChannel
from career_ops_kr.channels.kiwoomda import KiwoomdaChannel
from career_ops_kr.channels.lambda256 import Lambda256Channel
from career_ops_kr.channels.linkareer import LinkareerChannel
from career_ops_kr.channels.mnd import MndChannel
from career_ops_kr.channels.mofa import MofaChannel
from career_ops_kr.channels.mirae_asset import MiraeAssetChannel
from career_ops_kr.channels.mirae_naeil import MiraeNaeilChannel
from career_ops_kr.channels.mjob import MjobChannel
from career_ops_kr.channels.nis import NisChannel
from career_ops_kr.channels.nh_sec import NhSecChannel
from career_ops_kr.channels.samsung_sec import SamsungSecChannel
from career_ops_kr.channels.police import PoliceChannel
from career_ops_kr.channels.saramin import SaraminChannel
from career_ops_kr.channels.shinhan_sec import ShinhanSecChannel
from career_ops_kr.channels.toss import TossChannel
from career_ops_kr.channels.universal import UniversalChannel
from career_ops_kr.channels.wanted import WantedChannel
from career_ops_kr.channels.yw_work24 import YwWork24Channel
from career_ops_kr.channels.institutions_public import (
    KfbChannel,
    KofiaChannel,
    KniaChannel,
    KliaChannel,
    CrefiaChannel,
    FsbChannel,
    CuCentralChannel,
    KfccChannel,
    KrxChannel,
    KsfcChannel,
    KsdChannel,
    KftcChannel,
    FsecChannel,
    KcreditChannel,
    KfmbChannel,
    KrcaChannel,
    KtcuChannel,
    MacChannel,
    PobaChannel,
    LoginetChannel,
    CgcChannel,
    SpecialCgcChannel,
    FirefighterFundChannel,
    SemaChannel,
    SwFundChannel,
    KoficFundChannel,
    IbkBankChannel,
    KoditChannel,
    KiboChannel,
    HfChannel,
    KamcoChannel,
    KdicChannel,
    KsureChannel,
    HugChannel,
    SgiChannel,
    KinfaChannel,
    KbBankChannel,
    WooriBankChannel,
    NhBankChannel,
    ImBankChannel,
    KwangjuBankChannel,
    ShBankChannel,
    CitiBankChannel,
)
from career_ops_kr.channels.institutions_securities import (
    KyoboSecChannel,
    HanwhaSecChannel,
    YuantaSecChannel,
    EugeneSecChannel,
    HyundaiCarSecChannel,
    HiSecChannel,
    DbFiChannel,
    SkSecChannel,
    ImSecChannel,
    CapeSecChannel,
    KoreafossSecChannel,
    BookookSecChannel,
    ShinyoungSecChannel,
    HanyangSecChannel,
    YuhwaSecChannel,
    BnkSecChannel,
    HeungkukSecChannel,
    DaolSecChannel,
    LeadingSecChannel,
    KoreaAssetSecChannel,
    SamsungFuturesChannel,
    NhFuturesChannel,
    HanaFuturesChannel,
    KiwoomFuturesChannel,
    ShinhanFuturesChannel,
    SamsungLifeChannel,
    HanwhaLifeChannel,
    KyoboLifeChannel,
    ShinhanLifeChannel,
    NhLifeChannel,
    HanaLifeChannel,
    KbLifeChannel,
    DongyangLifeChannel,
    MiraeassetLifeChannel,
    AblLifeChannel,
    MetlifeChannel,
    AiaLifeChannel,
    ChubbLifeChannel,
    FubonLifeChannel,
    SamsungFireChannel,
    HyundaiMarineChannel,
    DbInsChannel,
    KbInsChannel,
    MeritzFireChannel,
    HanwhaInsChannel,
    LotteInsChannel,
    HeungkukFireChannel,
    MgInsChannel,
    NhFireChannel,
    ThekInsChannel,
    HanaInsChannel,
    CarrotInsChannel,
)
from career_ops_kr.channels.institutions_finops import (
    ShinhanCardChannel,
    SamsungCardChannel,
    KbCardChannel,
    HyundaiCardChannel,
    LotteCardChannel,
    WooriCardChannel,
    BcCardChannel,
    HanaCardChannel,
    KbCapitalChannel,
    HanaCapitalChannel,
    ShinhanCapitalChannel,
    WooriCapitalChannel,
    AjuCapitalChannel,
    LotteCapitalChannel,
    BnkCapitalChannel,
    JbWooriCapitalChannel,
    NhCapitalChannel,
    DgbCapitalChannel,
    KdbCapitalChannel,
    KiwoomYesSavingsChannel,
    PepperSavingsChannel,
    AquonSavingsChannel,
    KitSavingsChannel,
    JtSavingsChannel,
    OsbSavingsChannel,
    ThekSavingsChannel,
    MiraeassetAmChannel,
    KitAmChannel,
    SamsungAmChannel,
    KbAmChannel,
    ShinhanAmChannel,
    HanwhaAmChannel,
    NhAmundiAmChannel,
    KiwoomAmChannel,
    ShinyoungAmChannel,
    KyoboAxaAmChannel,
    EastspringAmChannel,
    TimefolioAmChannel,
    TrustonAmChannel,
    ViAmChannel,
    LazardAmChannel,
    AbAmChannel,
    KvicChannel,
    KgfChannel,
    MbkChannel,
    HahnCoChannel,
    ImmChannel,
    SticChannel,
    SkylakeChannel,
    DaolInvChannel,
    KitPartnersChannel,
    KakaoInvChannel,
    LbInvChannel,
    NaverPayChannel,
    EightPercentChannel,
    PaycoChannel,
)
from career_ops_kr.channels.institutions import (
    ApfsChannel,
    BusanBankChannel,
    EximBankChannel,
    HanaBankChannel,
    HyundaiCapitalChannel,
    JbBankChannel,
    JejuBankChannel,
    KBankChannel,
    KdbBankChannel,
    KdbLifeChannel,
    KicChannel,
    KnbChannel,
    KobcChannel,
    KoreanReChannel,
    KoscomChannel,
    MeritzCapitalChannel,
    MeritzSecChannel,
    MiraeassetSecChannel,
    OkSavingsChannel,
    SbiSavingsChannel,
    ScBankChannel,
    ShinhanBankChannel,
    SmbsChannel,
    TossBankChannel,
    WelcomeSavingsChannel,
)

CHANNEL_REGISTRY: dict[str, type[BaseChannel]] = {
    # --- General major portals (Tier 1) — product backbone, 8 channels ---
    LinkareerChannel.name: LinkareerChannel,  # 링커리어 (인턴/대외활동)
    CatchChannel.name: CatchChannel,  # 캐치 (대학생 특화)
    WantedChannel.name: WantedChannel,  # 원티드 (핀테크/IT)
    JobKoreaChannel.name: JobKoreaChannel,  # 잡코리아
    IncruitChannel.name: IncruitChannel,  # 인크루트
    JobPlanetChannel.name: JobPlanetChannel,  # 잡플래닛
    JasoseolChannel.name: JasoseolChannel,  # 자소설닷컴
    SaraminChannel.name: SaraminChannel,  # 사람인
    # --- Public-agency portals (Tier 1-2), 7 channels ---
    JobalioChannel.name: JobalioChannel,  # 잡알리오 (공공기관)
    ApplyBokChannel.name: ApplyBokChannel,  # 한국은행
    YwWork24Channel.name: YwWork24Channel,  # 청년일경험포털
    KiwoomdaChannel.name: KiwoomdaChannel,  # 키움DA
    DataqChannel.name: DataqChannel,  # 데이터큐
    MiraeNaeilChannel.name: MiraeNaeilChannel,  # 미래내일 일경험
    MjobChannel.name: MjobChannel,  # 중소기��진흥공단 일자리
    GoJobsChannel.name: GoJobsChannel,  # 나라일터 (정부일자리 통합포털)
    # --- Government unified (10 agencies in 1 channel) ---
    GovernmentChannel.name: GovernmentChannel,  # 국정원/경찰/국방/외교/관세/금융위/금감원/방사청/KISA/나라일터
    # --- Target-specific (사용자 우선순위 P0), 1 channel ---
    KiwoomKdaChannel.name: KiwoomKdaChannel,  # 키움 KDA (recruit.kiwoom.com)
    # --- Tier 3 securities (Korean brokerage), 6 channels ---
    ShinhanSecChannel.name: ShinhanSecChannel,  # 신한투자증권 (requests 재작성)
    MiraeAssetChannel.name: MiraeAssetChannel,
    KbSecChannel.name: KbSecChannel,
    HanaSecChannel.name: HanaSecChannel,
    NhSecChannel.name: NhSecChannel,
    SamsungSecChannel.name: SamsungSecChannel,
    KoreaInvestSecChannel.name: KoreaInvestSecChannel,  # 한국투자증권
    IbkSecChannel.name: IbkSecChannel,  # IBK투자증권
    DaishinSecChannel.name: DaishinSecChannel,  # 대신증권
    # --- Tier 3 fintech direct (company careers pages), 2 channels ---
    KakaoPayChannel.name: KakaoPayChannel,  # 카카오페이
    KakaoBankChannel.name: KakaoBankChannel,  # 카카오뱅크
    # --- Tier 4 crypto/fintech, 4 channels ---
    DunamuChannel.name: DunamuChannel,
    BithumbChannel.name: BithumbChannel,
    TossChannel.name: TossChannel,
    Lambda256Channel.name: Lambda256Channel,
    BanksaladChannel.name: BanksaladChannel,  # 뱅크샐러드
    FindaChannel.name: FindaChannel,  # 핀다
    CoinoneChannel.name: CoinoneChannel,  # 코인원
    # NOTE: UniversalChannel removed (redundant with institutions CLI cmd)
    # --- Tier 2 규제/협회 (institutions_public.py) ---
    KfbChannel.name: KfbChannel,
    KofiaChannel.name: KofiaChannel,
    KniaChannel.name: KniaChannel,
    KliaChannel.name: KliaChannel,
    CrefiaChannel.name: CrefiaChannel,
    FsbChannel.name: FsbChannel,
    CuCentralChannel.name: CuCentralChannel,
    KfccChannel.name: KfccChannel,
    KrxChannel.name: KrxChannel,
    KsfcChannel.name: KsfcChannel,
    KsdChannel.name: KsdChannel,
    KftcChannel.name: KftcChannel,
    FsecChannel.name: FsecChannel,
    KcreditChannel.name: KcreditChannel,
    KfmbChannel.name: KfmbChannel,
    KrcaChannel.name: KrcaChannel,
    # --- Tier 2 공제회 ---
    KtcuChannel.name: KtcuChannel,
    MacChannel.name: MacChannel,
    PobaChannel.name: PobaChannel,
    LoginetChannel.name: LoginetChannel,
    CgcChannel.name: CgcChannel,
    SpecialCgcChannel.name: SpecialCgcChannel,
    FirefighterFundChannel.name: FirefighterFundChannel,
    SemaChannel.name: SemaChannel,
    SwFundChannel.name: SwFundChannel,
    KoficFundChannel.name: KoficFundChannel,
    # --- Tier 2 정책금융 ---
    IbkBankChannel.name: IbkBankChannel,
    KoditChannel.name: KoditChannel,
    KiboChannel.name: KiboChannel,
    HfChannel.name: HfChannel,
    KamcoChannel.name: KamcoChannel,
    KdicChannel.name: KdicChannel,
    KsureChannel.name: KsureChannel,
    HugChannel.name: HugChannel,
    SgiChannel.name: SgiChannel,
    KinfaChannel.name: KinfaChannel,
    # --- Tier 3 시중은행 ---
    KbBankChannel.name: KbBankChannel,
    WooriBankChannel.name: WooriBankChannel,
    NhBankChannel.name: NhBankChannel,
    ImBankChannel.name: ImBankChannel,
    KwangjuBankChannel.name: KwangjuBankChannel,
    ShBankChannel.name: ShBankChannel,
    CitiBankChannel.name: CitiBankChannel,
    # --- Tier 3 증권사 추가 ---
    KyoboSecChannel.name: KyoboSecChannel,
    HanwhaSecChannel.name: HanwhaSecChannel,
    YuantaSecChannel.name: YuantaSecChannel,
    EugeneSecChannel.name: EugeneSecChannel,
    HyundaiCarSecChannel.name: HyundaiCarSecChannel,
    HiSecChannel.name: HiSecChannel,
    DbFiChannel.name: DbFiChannel,
    SkSecChannel.name: SkSecChannel,
    ImSecChannel.name: ImSecChannel,
    CapeSecChannel.name: CapeSecChannel,
    KoreafossSecChannel.name: KoreafossSecChannel,
    BookookSecChannel.name: BookookSecChannel,
    ShinyoungSecChannel.name: ShinyoungSecChannel,
    HanyangSecChannel.name: HanyangSecChannel,
    YuhwaSecChannel.name: YuhwaSecChannel,
    BnkSecChannel.name: BnkSecChannel,
    HeungkukSecChannel.name: HeungkukSecChannel,
    DaolSecChannel.name: DaolSecChannel,
    LeadingSecChannel.name: LeadingSecChannel,
    KoreaAssetSecChannel.name: KoreaAssetSecChannel,
    # --- Tier 3 선물사 ---
    SamsungFuturesChannel.name: SamsungFuturesChannel,
    NhFuturesChannel.name: NhFuturesChannel,
    HanaFuturesChannel.name: HanaFuturesChannel,
    KiwoomFuturesChannel.name: KiwoomFuturesChannel,
    ShinhanFuturesChannel.name: ShinhanFuturesChannel,
    # --- Tier 3 생명보험 ---
    SamsungLifeChannel.name: SamsungLifeChannel,
    HanwhaLifeChannel.name: HanwhaLifeChannel,
    KyoboLifeChannel.name: KyoboLifeChannel,
    ShinhanLifeChannel.name: ShinhanLifeChannel,
    NhLifeChannel.name: NhLifeChannel,
    HanaLifeChannel.name: HanaLifeChannel,
    KbLifeChannel.name: KbLifeChannel,
    DongyangLifeChannel.name: DongyangLifeChannel,
    MiraeassetLifeChannel.name: MiraeassetLifeChannel,
    AblLifeChannel.name: AblLifeChannel,
    MetlifeChannel.name: MetlifeChannel,
    AiaLifeChannel.name: AiaLifeChannel,
    ChubbLifeChannel.name: ChubbLifeChannel,
    FubonLifeChannel.name: FubonLifeChannel,
    # --- Tier 3 손해보험 ---
    SamsungFireChannel.name: SamsungFireChannel,
    HyundaiMarineChannel.name: HyundaiMarineChannel,
    DbInsChannel.name: DbInsChannel,
    KbInsChannel.name: KbInsChannel,
    MeritzFireChannel.name: MeritzFireChannel,
    HanwhaInsChannel.name: HanwhaInsChannel,
    LotteInsChannel.name: LotteInsChannel,
    HeungkukFireChannel.name: HeungkukFireChannel,
    MgInsChannel.name: MgInsChannel,
    NhFireChannel.name: NhFireChannel,
    ThekInsChannel.name: ThekInsChannel,
    HanaInsChannel.name: HanaInsChannel,
    CarrotInsChannel.name: CarrotInsChannel,
    # --- Tier 3 카드사 ---
    ShinhanCardChannel.name: ShinhanCardChannel,
    SamsungCardChannel.name: SamsungCardChannel,
    KbCardChannel.name: KbCardChannel,
    HyundaiCardChannel.name: HyundaiCardChannel,
    LotteCardChannel.name: LotteCardChannel,
    WooriCardChannel.name: WooriCardChannel,
    BcCardChannel.name: BcCardChannel,
    HanaCardChannel.name: HanaCardChannel,
    # --- Tier 3 자산운용 ---
    MiraeassetAmChannel.name: MiraeassetAmChannel,
    KitAmChannel.name: KitAmChannel,
    SamsungAmChannel.name: SamsungAmChannel,
    KbAmChannel.name: KbAmChannel,
    ShinhanAmChannel.name: ShinhanAmChannel,
    HanwhaAmChannel.name: HanwhaAmChannel,
    NhAmundiAmChannel.name: NhAmundiAmChannel,
    KiwoomAmChannel.name: KiwoomAmChannel,
    ShinyoungAmChannel.name: ShinyoungAmChannel,
    KyoboAxaAmChannel.name: KyoboAxaAmChannel,
    EastspringAmChannel.name: EastspringAmChannel,
    TimefolioAmChannel.name: TimefolioAmChannel,
    TrustonAmChannel.name: TrustonAmChannel,
    ViAmChannel.name: ViAmChannel,
    LazardAmChannel.name: LazardAmChannel,
    AbAmChannel.name: AbAmChannel,
    # --- Tier 4 캐피탈 ---
    KbCapitalChannel.name: KbCapitalChannel,
    HanaCapitalChannel.name: HanaCapitalChannel,
    ShinhanCapitalChannel.name: ShinhanCapitalChannel,
    WooriCapitalChannel.name: WooriCapitalChannel,
    AjuCapitalChannel.name: AjuCapitalChannel,
    LotteCapitalChannel.name: LotteCapitalChannel,
    BnkCapitalChannel.name: BnkCapitalChannel,
    JbWooriCapitalChannel.name: JbWooriCapitalChannel,
    NhCapitalChannel.name: NhCapitalChannel,
    DgbCapitalChannel.name: DgbCapitalChannel,
    KdbCapitalChannel.name: KdbCapitalChannel,
    # --- Tier 4 저축은행 ---
    KiwoomYesSavingsChannel.name: KiwoomYesSavingsChannel,
    PepperSavingsChannel.name: PepperSavingsChannel,
    AquonSavingsChannel.name: AquonSavingsChannel,
    KitSavingsChannel.name: KitSavingsChannel,
    JtSavingsChannel.name: JtSavingsChannel,
    OsbSavingsChannel.name: OsbSavingsChannel,
    ThekSavingsChannel.name: ThekSavingsChannel,
    # --- Tier 4 PE/VC ---
    KvicChannel.name: KvicChannel,
    KgfChannel.name: KgfChannel,
    MbkChannel.name: MbkChannel,
    HahnCoChannel.name: HahnCoChannel,
    ImmChannel.name: ImmChannel,
    SticChannel.name: SticChannel,
    SkylakeChannel.name: SkylakeChannel,
    DaolInvChannel.name: DaolInvChannel,
    KitPartnersChannel.name: KitPartnersChannel,
    KakaoInvChannel.name: KakaoInvChannel,
    LbInvChannel.name: LbInvChannel,
    # --- Tier 4 핀테크 추가 ---
    NaverPayChannel.name: NaverPayChannel,
    EightPercentChannel.name: EightPercentChannel,
    PaycoChannel.name: PaycoChannel,
    # --- Tier 2 정책금융/공공기관 (institutions.py stub batch) ---
    KicChannel.name: KicChannel,  # 한국투자공사
    KdbBankChannel.name: KdbBankChannel,  # 한국산업은행
    EximBankChannel.name: EximBankChannel,  # 한국수출입은행
    KobcChannel.name: KobcChannel,  # 한국해양진흥공사
    KoscomChannel.name: KoscomChannel,  # 코스콤
    ApfsChannel.name: ApfsChannel,  # 농업정책보험금융원
    SmbsChannel.name: SmbsChannel,  # 서울외국환중개
    # --- Tier 3 시중은행/지방은행 ---
    ShinhanBankChannel.name: ShinhanBankChannel,  # 신한은행
    HanaBankChannel.name: HanaBankChannel,  # 하나은행
    BusanBankChannel.name: BusanBankChannel,  # 부산은행(BNK)
    KnbChannel.name: KnbChannel,  # 경남은행(BNK)
    JbBankChannel.name: JbBankChannel,  # 전북은행(JB)
    JejuBankChannel.name: JejuBankChannel,  # 제주은행
    KBankChannel.name: KBankChannel,  # 케이뱅크
    ScBankChannel.name: ScBankChannel,  # SC제일은행
    # --- Tier 3 증권사 ---
    MiraeassetSecChannel.name: MiraeassetSecChannel,  # 미래에셋증권
    MeritzSecChannel.name: MeritzSecChannel,  # 메리츠증권
    # --- Tier 3 보험사 ---
    KdbLifeChannel.name: KdbLifeChannel,  # KDB생명
    KoreanReChannel.name: KoreanReChannel,  # 코리안리
    # --- Tier 4 캐피탈 ---
    MeritzCapitalChannel.name: MeritzCapitalChannel,  # 메리츠캐피탈
    HyundaiCapitalChannel.name: HyundaiCapitalChannel,  # 현대캐피탈
    # --- Tier 4 저축은행 ---
    SbiSavingsChannel.name: SbiSavingsChannel,  # SBI저축은행
    OkSavingsChannel.name: OkSavingsChannel,  # OK저축은행
    WelcomeSavingsChannel.name: WelcomeSavingsChannel,  # 웰컴저축은행
    # --- Tier 4 핀테크/인터넷은행 ---
    TossBankChannel.name: TossBankChannel,  # 토스뱅크
}

__all__ = [
    "CHANNEL_REGISTRY",
    "ApplyBokChannel",
    "BanksaladChannel",
    "BaseChannel",
    "BithumbChannel",
    "CoinoneChannel",
    "CatchChannel",
    "Channel",
    "ChannelError",
    "CustomsChannel",
    "DapaChannel",
    "DaishinSecChannel",
    "DataqChannel",
    "DunamuChannel",
    "FindaChannel",
    "FscChannel",
    "FssChannel",
    "GoJobsChannel",
    "GovernmentChannel",
    "HanaSecChannel",
    "IbkSecChannel",
    "IncruitChannel",
    "JasoseolChannel",
    "JobKoreaChannel",
    "JobPlanetChannel",
    "JobRecord",
    "JobalioChannel",
    "KisaChannel",
    "KakaoBankChannel",
    "KakaoPayChannel",
    "KbSecChannel",
    "KiwoomKdaChannel",
    "KiwoomdaChannel",
    "KoreaInvestSecChannel",
    "Lambda256Channel",
    "LinkareerChannel",
    "MndChannel",
    "MofaChannel",
    "MiraeAssetChannel",
    "MiraeNaeilChannel",
    "MjobChannel",
    "NisChannel",
    "NhSecChannel",
    "NotTunedYetError",
    "PoliceChannel",
    "SamsungSecChannel",
    "SaraminChannel",
    "ShinhanSecChannel",
    "TossChannel",
    "UniversalChannel",
    "WantedChannel",
    "YwWork24Channel",
    "deadline_parser",
    # institutions.py stub batch
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
