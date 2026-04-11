"""Channel package — one module per portal.

Each channel subclasses :class:`career_ops_kr.channels.base.BaseChannel` and
is registered in :data:`CHANNEL_REGISTRY` so the orchestrator can dispatch
by name.

:class:`NotTunedYetError` lives in :mod:`career_ops_kr.channels._stub_errors`
to avoid circular imports: Tier 3-4 stub channels need to import the
exception at module load time, and putting it in this package's
``__init__.py`` would create a cycle. It is re-exported here for
convenience.
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
from career_ops_kr.channels.dataq import DataqChannel
from career_ops_kr.channels.dunamu import DunamuChannel
from career_ops_kr.channels.hana_sec import HanaSecChannel
from career_ops_kr.channels.jobalio import JobalioChannel
from career_ops_kr.channels.kb_sec import KbSecChannel
from career_ops_kr.channels.kiwoomda import KiwoomdaChannel
from career_ops_kr.channels.lambda256 import Lambda256Channel
from career_ops_kr.channels.mirae_asset import MiraeAssetChannel
from career_ops_kr.channels.nh_sec import NhSecChannel
from career_ops_kr.channels.samsung_sec import SamsungSecChannel
from career_ops_kr.channels.toss import TossChannel
from career_ops_kr.channels.yw_work24 import YwWork24Channel

CHANNEL_REGISTRY: dict[str, type[BaseChannel]] = {
    JobalioChannel.name: JobalioChannel,
    YwWork24Channel.name: YwWork24Channel,
    ApplyBokChannel.name: ApplyBokChannel,
    KiwoomdaChannel.name: KiwoomdaChannel,
    DataqChannel.name: DataqChannel,
    # Tier 3 securities
    MiraeAssetChannel.name: MiraeAssetChannel,
    KbSecChannel.name: KbSecChannel,
    HanaSecChannel.name: HanaSecChannel,
    NhSecChannel.name: NhSecChannel,
    SamsungSecChannel.name: SamsungSecChannel,
    # Tier 4 crypto/fintech
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
    "Channel",
    "ChannelError",
    "DataqChannel",
    "DunamuChannel",
    "HanaSecChannel",
    "JobRecord",
    "JobalioChannel",
    "KbSecChannel",
    "KiwoomdaChannel",
    "Lambda256Channel",
    "MiraeAssetChannel",
    "NhSecChannel",
    "NotTunedYetError",
    "SamsungSecChannel",
    "TossChannel",
    "YwWork24Channel",
    "deadline_parser",
]
