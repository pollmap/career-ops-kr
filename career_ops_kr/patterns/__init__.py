"""career-ops-kr patterns 서브패키지.

이 패키지가 존재하면 mcp_server.py의 _safe_import("career_ops_kr.patterns")가
tool_run_patterns MCP 도구를 자동 활성화한다.
"""

from career_ops_kr.patterns.analyzer import analyze

__all__ = ["analyze"]
