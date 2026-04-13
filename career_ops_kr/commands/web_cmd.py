"""career-ops web — Streamlit 대시보드 실행 커맨드."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click


@click.command("web")
@click.option("--port", default=8501, show_default=True, help="Streamlit 서버 포트")
@click.option("--no-browser", is_flag=True, help="브라우저 자동 오픈 안 함")
def web_cmd(port: int, no_browser: bool) -> None:
    """Streamlit 대시보드를 브라우저에서 열기.

    실행:
        career-ops web
        career-ops web --port 8502
        career-ops web --no-browser
    """
    dashboard = Path(__file__).parents[1] / "web" / "dashboard.py"
    if not dashboard.exists():
        click.echo(f"[ERROR] 대시보드 파일이 없습니다: {dashboard}", err=True)
        raise SystemExit(1)

    args = [
        sys.executable, "-m", "streamlit", "run", str(dashboard),
        f"--server.port={port}",
        "--server.headless=false" if not no_browser else "--server.headless=true",
    ]
    click.echo(f"dashboard: http://localhost:{port}")
    subprocess.run(args, check=True)
