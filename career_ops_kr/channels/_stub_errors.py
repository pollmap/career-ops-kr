"""Shared stub-channel exception.

Defines :class:`NotTunedYetError`, raised by Tier 3-4 stub channels when
their selectors have not yet been tuned against live HTML.

Why a separate module?
----------------------
Placing this inside ``career_ops_kr/channels/__init__.py`` would create a
circular import: each concrete stub channel (``mirae_asset``, ``dunamu``,
etc.) needs to import ``NotTunedYetError`` at module-load time, but
``__init__.py`` imports those same channels. Extracting the error into its
own zero-dependency module (only imports :mod:`career_ops_kr.channels.base`
for ``ChannelError``) breaks the cycle.

Stub-channel contract
---------------------
Stub channels MUST still fulfil the :class:`BaseChannel` contract:

* They are importable without network access.
* Their constructors raise no exceptions.
* ``check()`` probes reachability (and returns ``False`` on failure rather
  than raising).
* ``list_jobs()`` returns ``[]`` on any failure — parse errors, network
  errors, and :class:`NotTunedYetError` are all caught internally and
  converted to empty lists. The exception is logged so 사용자 knows exactly
  which channel needs tuning.
* ``get_detail()`` returns ``None`` on any failure.

No stub channel is allowed to fabricate a :class:`JobRecord`. The 실데이터
invariant is absolute.
"""

from __future__ import annotations

from career_ops_kr.channels.base import ChannelError

__all__ = ["NotTunedYetError"]


class NotTunedYetError(ChannelError):
    """Raised when stub channel selectors have not yet been tuned.

    Carries the channel name so the caller (typically the channel's own
    ``list_jobs`` method) can log a helpful message pointing 사용자 at the
    tuning CLI. The message always includes the exact command to run.
    """

    def __init__(self, channel_name: str, detail: str | None = None) -> None:
        msg = (
            f"Channel '{channel_name}' selectors not yet tuned against live HTML. "
            f"Run `career-ops channels tune {channel_name}` to capture a sample "
            f"and auto-generate selectors."
        )
        if detail:
            msg = f"{msg} [{detail}]"
        super().__init__(msg)
        self.channel_name = channel_name
