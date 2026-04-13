"""career-ops ncs — NCS 준비 상태 대시보드.

NCS 10개 영역 중 필수 3개(의사소통/수리/문제해결) 중심으로
공부 상태와 리소스를 추적.
"""

from __future__ import annotations

import click
from rich.table import Table

from career_ops_kr.commands._shared import CONFIG_DIR, console


# NCS 10개 영역 (필수 3개 + 선택 7개)
NCS_DOMAINS = [
    {"id": "communication", "name": "의사소통능력", "required": True,
     "note": "공문서 이해/작성, 비즈니스 문서", "user_strength": "중"},
    {"id": "math", "name": "수리능력", "required": True,
     "note": "도표/통계 해석, 비율/증감률", "user_strength": "강"},
    {"id": "problem_solving", "name": "문제해결능력", "required": True,
     "note": "논리 추론, 원인 분석, 대안 평가", "user_strength": "강"},
    {"id": "self_development", "name": "자기개발능력", "required": False,
     "note": "자기관리, 경력개발", "user_strength": "중"},
    {"id": "resource_mgmt", "name": "자원관리능력", "required": False,
     "note": "시간/예산/인적자원 관리", "user_strength": "중"},
    {"id": "interpersonal", "name": "대인관계능력", "required": False,
     "note": "팀워크, 리더십, 갈등관리", "user_strength": "중"},
    {"id": "information", "name": "정보능력", "required": False,
     "note": "컴퓨터 활용, 정보 처리", "user_strength": "최강"},
    {"id": "technical", "name": "기술능력", "required": False,
     "note": "기술 이해/선택/적용", "user_strength": "강"},
    {"id": "organization", "name": "조직이해능력", "required": False,
     "note": "조직 구조, 경영이해, 업무이해", "user_strength": "중"},
    {"id": "work_ethics", "name": "직업윤리", "required": False,
     "note": "근로윤리, 공동체윤리", "user_strength": "중"},
]

NCS_RESOURCES = [
    {"name": "NCS 공식 사이트", "url": "https://www.ncs.go.kr"},
    {"name": "에듀윌 NCS 무료강의", "url": "https://www.eduwill.net/ncs"},
    {"name": "잡알리오 NCS 기출", "url": "https://job.alio.go.kr"},
    {"name": "공기출 (기출문제)", "url": "https://www.gongkichul.com"},
    {"name": "해커스 NCS", "url": "https://ncs.hackers.com"},
]


@click.command("ncs")
def ncs_cmd() -> None:
    """NCS 준비 상태 대시보드 — 10영역 + 리소스."""
    console.print("\n[bold cyan]NCS 직업기초능력 대시보드[/bold cyan]\n")

    # 영역 테이블
    table = Table(title="10개 영역 (필수 3개 ★)")
    table.add_column("#", justify="right")
    table.add_column("영역", style="cyan")
    table.add_column("필수", justify="center")
    table.add_column("사용자 강점", justify="center")
    table.add_column("설명", style="dim")

    for i, d in enumerate(NCS_DOMAINS, 1):
        req = "[red bold]★[/red bold]" if d["required"] else ""
        strength = d["user_strength"]
        if strength == "최강":
            s_color = "[green bold]최강[/green bold]"
        elif strength == "강":
            s_color = "[green]강[/green]"
        else:
            s_color = "[yellow]중[/yellow]"
        table.add_row(str(i), d["name"], req, s_color, d["note"])

    console.print(table)

    # 전략
    console.print("\n[bold]NCS 전략[/bold]")
    console.print("  필수 3개(의사소통+수리+문제해결) = 전체의 80% 커버")
    console.print("  수리+문제해결 = 사용자 강점 → 의사소통(공문서)만 집중 보완")
    console.print("  정보능력 = 364개 도구 만든 사람 → NCS에서 가장 쉬움")
    console.print()

    # 리소스 테이블
    res_table = Table(title="NCS 학습 리소스")
    res_table.add_column("사이트")
    res_table.add_column("URL", style="dim")
    for r in NCS_RESOURCES:
        res_table.add_row(r["name"], r["url"])
    console.print(res_table)

    console.print("\n[dim]하루 30분 × 3개월 = NCS 필기 합격 가능 (7월 빅시즌 대비)[/dim]\n")
