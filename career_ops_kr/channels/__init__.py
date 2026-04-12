"""Channel package — one module per portal.

Each channel subclasses :class:`career_ops_kr.channels.base.BaseChannel` and
is registered in :data:`CHANNEL_REGISTRY` so the orchestrator can dispatch
by name.

:class:`NotTunedYetError` lives in :mod:`career_ops_kr.channels._stub_errors`
to avoid circular imports: Tier 3-4 stub channels need to import the
exception at module load time, and putting it in this package's
``__init__.py`` would create a cycle. It is re-exported here for
convenience.

**Product Reach Tiers** (찬희 재정의 Sprint 5):
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
    # --- Security / Intelligence / Defense (T1), 4 channels ---
    NisChannel.name: NisChannel,  # 국가정보원
    PoliceChannel.name: PoliceChannel,  # 경찰청
    MndChannel.name: MndChannel,  # 국방부
    DapaChannel.name: DapaChannel,  # 방위사업청
    # --- Diplomacy / Trade / Finance regulation (T1), 4 channels ---
    MofaChannel.name: MofaChannel,  # 외교부
    CustomsChannel.name: CustomsChannel,  # ���세청
    FscChannel.name: FscChannel,  # 금융위원회
    FssChannel.name: FssChannel,  # 금융감독원
    # --- Cyber security quasi-gov (T2), 1 channel ---
    KisaChannel.name: KisaChannel,  # 한국인터넷��흥원 (KISA)
    # --- Target-specific (찬희 우선순위 P0), 1 channel ---
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
    # --- Universal DB scanner (institutions.yml, 194+ institutions) ---
    UniversalChannel.name: UniversalChannel,  # 전체 기관 일괄 크롤링
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
]
