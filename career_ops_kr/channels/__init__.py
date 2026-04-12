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
from career_ops_kr.channels.base import (
    BaseChannel,
    Channel,
    ChannelError,
    JobRecord,
    deadline_parser,
)
from career_ops_kr.channels.bithumb import BithumbChannel
from career_ops_kr.channels.catch import CatchChannel
from career_ops_kr.channels.dataq import DataqChannel
from career_ops_kr.channels.dunamu import DunamuChannel
from career_ops_kr.channels.hana_sec import HanaSecChannel
from career_ops_kr.channels.incruit import IncruitChannel
from career_ops_kr.channels.jasoseol import JasoseolChannel
from career_ops_kr.channels.jobalio import JobalioChannel
from career_ops_kr.channels.jobkorea import JobKoreaChannel
from career_ops_kr.channels.jobplanet import JobPlanetChannel
from career_ops_kr.channels.kb_sec import KbSecChannel
from career_ops_kr.channels.kiwoom_kda import KiwoomKdaChannel
from career_ops_kr.channels.kiwoomda import KiwoomdaChannel
from career_ops_kr.channels.lambda256 import Lambda256Channel
from career_ops_kr.channels.linkareer import LinkareerChannel
from career_ops_kr.channels.mirae_asset import MiraeAssetChannel
from career_ops_kr.channels.mirae_naeil import MiraeNaeilChannel
from career_ops_kr.channels.mjob import MjobChannel
from career_ops_kr.channels.nh_sec import NhSecChannel
from career_ops_kr.channels.samsung_sec import SamsungSecChannel
from career_ops_kr.channels.saramin import SaraminChannel
from career_ops_kr.channels.shinhan_sec import ShinhanSecChannel
from career_ops_kr.channels.toss import TossChannel
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
    MjobChannel.name: MjobChannel,  # 중소기업진흥공단 일자리
    # --- Target-specific (찬희 우선순위 P0), 1 channel ---
    KiwoomKdaChannel.name: KiwoomKdaChannel,  # 키움 KDA (recruit.kiwoom.com)
    # --- Tier 3 securities (Korean brokerage), 6 channels ---
    ShinhanSecChannel.name: ShinhanSecChannel,  # 신한투자증권 (requests 재작성)
    MiraeAssetChannel.name: MiraeAssetChannel,
    KbSecChannel.name: KbSecChannel,
    HanaSecChannel.name: HanaSecChannel,
    NhSecChannel.name: NhSecChannel,
    SamsungSecChannel.name: SamsungSecChannel,
    # --- Tier 4 crypto/fintech, 4 channels ---
    DunamuChannel.name: DunamuChannel,
    BithumbChannel.name: BithumbChannel,
    TossChannel.name: TossChannel,
    Lambda256Channel.name: Lambda256Channel,
}

__all__ = [
    "CHANNEL_REGISTRY",
    "ApplyBokChannel",
    "BaseChannel",
    "BithumbChannel",
    "CatchChannel",
    "Channel",
    "ChannelError",
    "DataqChannel",
    "DunamuChannel",
    "HanaSecChannel",
    "IncruitChannel",
    "JasoseolChannel",
    "JobKoreaChannel",
    "JobPlanetChannel",
    "JobRecord",
    "JobalioChannel",
    "KbSecChannel",
    "KiwoomKdaChannel",
    "KiwoomdaChannel",
    "Lambda256Channel",
    "LinkareerChannel",
    "MiraeAssetChannel",
    "MiraeNaeilChannel",
    "MjobChannel",
    "NhSecChannel",
    "NotTunedYetError",
    "SamsungSecChannel",
    "SaraminChannel",
    "ShinhanSecChannel",
    "TossChannel",
    "WantedChannel",
    "YwWork24Channel",
    "deadline_parser",
]
