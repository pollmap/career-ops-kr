"""Global constants for career-ops-kr — user-facing strings centralized here.

범용 배포를 위해 하드코딩된 author/repo URL을 환경변수로 오버라이드 가능하게
한 곳에 모아둔 모듈. 포크해서 쓰는 사용자는 ``CAREER_OPS_HOMEPAGE``,
``CAREER_OPS_USER_AGENT`` 등 환경변수로 본인 repo/버전을 지정할 수 있다.
"""

from __future__ import annotations

import os

# 버전은 pyproject.toml 단일 소스 — 여기선 기본값만
try:
    from importlib.metadata import version as _pkg_version
    _DEFAULT_VERSION = _pkg_version("career-ops-kr")
except Exception:
    _DEFAULT_VERSION = "1.0.0"

APP_NAME = "career-ops-kr"
APP_VERSION = os.environ.get("CAREER_OPS_VERSION", _DEFAULT_VERSION)

# 포크 사용자가 본인 repo URL로 덮어쓸 수 있게 환경변수 지원
APP_HOMEPAGE = os.environ.get(
    "CAREER_OPS_HOMEPAGE",
    "https://github.com/pollmap/career-ops-kr",
)

# User-Agent — 모든 채널 크롤러 공통 사용
DEFAULT_USER_AGENT = os.environ.get(
    "CAREER_OPS_USER_AGENT",
    f"{APP_NAME}/{APP_VERSION} (+{APP_HOMEPAGE})",
)

# ICS 일정 UID 도메인 — 범용 placeholder
ICS_UID_DOMAIN = os.environ.get(
    "CAREER_OPS_ICS_DOMAIN",
    "career-ops-kr.local",
)
