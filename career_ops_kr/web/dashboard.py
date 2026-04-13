"""career-ops-kr Streamlit 웹 대시보드 — Linkareer 디자인 시스템.

링커리어(linkareer.com) 레이아웃/색상/컴포넌트를 그대로 재현.

색상 팔레트 (실측):
    #01A0FF  — 프라이머리 블루 (rgb 1,160,255)
    #F8F8FA  — 페이지 배경
    #FFFFFF  — 카드/행 배경
    #333333  — 본문 텍스트
    #666666  — 서브 텍스트
    #EF2929  — 마감임박 (red)
    #F2FAFF  — 호버 배경

실행:
    python -m streamlit run career_ops_kr/web/dashboard.py --server.port 8501
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

DB_PATH = Path(__file__).parents[2] / "data" / "jobs.db"
REPO_ROOT = Path(__file__).parents[2]

STATUS_LABELS = {
    "inbox": "Inbox",
    "applied": "지원함",
    "passed": "합격",
    "rejected": "탈락",
}

STATUS_COLORS = {
    "inbox": "#6b7280",
    "applied": "#01A0FF",
    "passed": "#22c55e",
    "rejected": "#ef4444",
}

ARCHETYPE_LABELS = {
    "INTERN": "인턴",
    "ENTRY": "신입",
    "EXPERIENCED": "경력",
    "IT": "IT",
}

# ---------------------------------------------------------------------------
# CSS — Linkareer 디자인 시스템
# ---------------------------------------------------------------------------
LINKAREER_CSS = """
<style>
:root {
  --bg-base:    #070B14;
  --bg-surface: #0C1525;
  --bg-elev:    #111D30;
  --border:     #1C2E47;
  --border-hi:  #0057A8;
  --accent:     #0094FF;
  --accent-dim: rgba(0,148,255,0.10);
  --accent-glo: rgba(0,148,255,0.22);
  --green:      #00C87A;
  --green-dim:  rgba(0,200,122,0.10);
  --amber:      #F5A623;
  --amber-dim:  rgba(245,166,35,0.10);
  --red:        #F43F5E;
  --red-dim:    rgba(244,63,94,0.10);
  --purple:     #A78BFA;
  --purple-dim: rgba(167,139,250,0.10);
  --txt:        #DDE6F5;
  --txt-sec:    #8AABCC;
  --txt-mute:   #4A6585;
  --ff-disp:    'Oxanium', monospace;
  --ff-body:    'DM Sans', -apple-system, sans-serif;
  --ff-mono:    'JetBrains Mono', monospace;
}

/* ── 전역 ── */
html, body, [class*="css"] {
  font-family: var(--ff-body) !important;
  background-color: var(--bg-base) !important;
  color: var(--txt) !important;
}
.stApp { background-color: var(--bg-base) !important; }
.stApp > header { background: var(--bg-base) !important; border-bottom: 1px solid var(--border) !important; }
section[data-testid="stSidebar"] { background: var(--bg-surface) !important; border-right: 1px solid var(--border) !important; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
p, .stMarkdown p { color: var(--txt) !important; }
hr { border-color: var(--border) !important; }

/* ── 반응형 중앙 정렬 ── */
.block-container {
  max-width: 1240px !important;
  padding: 0 2rem 2rem !important;
  margin: 0 auto !important;
}
@media (max-width: 768px) {
  .block-container { padding: 0 1rem 1rem !important; }
  .lk-stat-row { grid-template-columns: repeat(2,1fr) !important; }
  .td-title { max-width: 160px; }
}

/* ── 헤더 ── */
.lk-header {
  background: linear-gradient(120deg, var(--bg-surface) 60%, var(--bg-elev) 100%);
  border: 1px solid var(--border);
  border-top: 2px solid var(--accent);
  padding: 16px 28px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  border-radius: 0 0 10px 10px;
  position: relative;
  overflow: hidden;
}
.lk-header::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,148,255,0.015) 2px, rgba(0,148,255,0.015) 4px);
  pointer-events: none;
}
.lk-logo {
  font-family: var(--ff-disp);
  font-size: 18px;
  font-weight: 800;
  color: var(--accent);
  letter-spacing: 2px;
  text-transform: uppercase;
}
.lk-subtitle {
  font-family: var(--ff-mono);
  font-size: 11px;
  color: var(--txt-mute);
  margin-left: auto;
}
.co-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  animation: blink 2s ease infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-surface) !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important; padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: var(--ff-body) !important;
  font-size: 13px !important; font-weight: 600 !important;
  color: var(--txt-sec) !important;
  padding: 12px 20px !important;
  border-bottom: 2px solid transparent !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  background: var(--accent-dim) !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 16px !important; }

/* ── 통계 카드 그리드 ── */
.lk-stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 28px;
}
.lk-stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
  padding: 16px 18px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.lk-stat-card:hover { box-shadow: 0 0 18px var(--accent-glo); border-color: var(--border-hi); }
.lk-stat-card.green  { border-left-color: var(--green); }
.lk-stat-card.amber  { border-left-color: var(--amber); }
.lk-stat-card.red    { border-left-color: var(--red); }
.lk-stat-card.purple { border-left-color: var(--purple); }
.lk-stat-num {
  font-family: var(--ff-mono);
  font-size: 26px; font-weight: 600;
  color: var(--accent);
  line-height: 1; margin-bottom: 4px;
}
.lk-stat-num.green  { color: var(--green); }
.lk-stat-num.amber  { color: var(--amber); }
.lk-stat-num.red    { color: var(--red); }
.lk-stat-num.purple { color: var(--purple); }
.lk-stat-num.muted  { color: var(--txt-sec); }
.lk-stat-label {
  font-family: var(--ff-mono);
  font-size: 10px; color: var(--txt-mute);
  text-transform: uppercase; letter-spacing: 0.8px;
}

/* ── 섹션 헤더 ── */
.lk-section-title {
  font-family: var(--ff-disp);
  font-size: 11px; font-weight: 700;
  color: var(--txt-sec);
  text-transform: uppercase; letter-spacing: 2px;
  margin: 24px 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  display: block;
}
.lk-section-title::before { display: none !important; }

/* ── Streamlit 네이티브 다크 오버라이드 ── */
.stTextInput input,
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {
  background: var(--bg-elev) !important;
  color: var(--txt) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
}
.stTextInput input::placeholder { color: var(--txt-mute) !important; }
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.stCheckbox label span, .stRadio label span, [data-testid="stWidgetLabel"] {
  color: var(--txt-sec) !important;
  font-size: 12px !important;
}
[data-baseweb="menu"], [data-baseweb="popover"] {
  background: var(--bg-elev) !important;
  border: 1px solid var(--border) !important;
}
[data-baseweb="option"] { color: var(--txt) !important; background: transparent !important; }
[data-baseweb="option"]:hover { background: var(--accent-dim) !important; }
[data-baseweb="tag"] { background: var(--accent-dim) !important; color: var(--accent) !important; }
.stButton button {
  background: var(--accent) !important; color: #fff !important;
  border: none !important; border-radius: 6px !important;
  font-weight: 600 !important; font-size: 13px !important;
  transition: box-shadow 0.2s !important;
}
.stButton button:hover { box-shadow: 0 0 18px var(--accent-glo) !important; }
[data-testid="stExpander"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: var(--txt-sec) !important; }
[data-testid="stExpander"] summary:hover { color: var(--txt) !important; }
[data-testid="stNotification"] { background: var(--bg-elev) !important; border: 1px solid var(--border) !important; }
div[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: var(--ff-mono) !important; font-weight: 600 !important; }
.stRadio div[role="radiogroup"] label span { color: var(--txt) !important; }
</style>
"""

# ---------------------------------------------------------------------------
# 테이블 전용 CSS (st.html iframe embed — 다크 터미널 테마)
# ---------------------------------------------------------------------------
_TABLE_STYLE = """
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',-apple-system,sans-serif;font-size:13px;color:#DDE6F5;background:#070B14}
.lk-table-wrap{background:#0C1525;border:1px solid #1C2E47;border-radius:8px;overflow:hidden}
.lk-table{width:100%;border-collapse:collapse;font-size:13px}
.lk-table thead th{background:#070B14;color:#5A7899;font-family:'JetBrains Mono',monospace;font-weight:600;font-size:10px;padding:10px 14px;border-bottom:1px solid #1C2E47;text-align:left;white-space:nowrap;text-transform:uppercase;letter-spacing:.8px}
.lk-table tbody tr{border-bottom:1px solid #1C2E47;transition:background .12s}
.lk-table tbody tr:hover{background:#0F1F38}
.lk-table tbody tr:last-child{border-bottom:none}
.lk-table td{padding:12px 14px;vertical-align:middle}
.td-company{min-width:110px}
.company-name{font-size:11px;color:#8AABCC;display:block;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.td-title{min-width:200px;max-width:360px}
.recruit-name{font-size:13px;font-weight:600;color:#DDE6F5;display:block;line-height:1.4}
.recruit-name a{color:#DDE6F5!important;text-decoration:none}
.recruit-name a:hover{color:#0094FF!important}
.recruit-category{font-size:11px;color:#4A6585;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:320px;display:block}
.short-info{font-size:11px;color:#8AABCC;white-space:nowrap}
.badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;white-space:nowrap;font-family:'JetBrains Mono',monospace}
.badge-intern{background:rgba(0,148,255,.12);color:#0094FF}
.badge-entry{background:rgba(0,200,122,.12);color:#00C87A}
.badge-exp{background:rgba(245,166,35,.12);color:#F5A623}
.badge-it{background:rgba(167,139,250,.12);color:#A78BFA}
.badge-default{background:rgba(44,64,96,.3);color:#6B87A8}
.grade-badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:11px;min-width:32px;text-align:center;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:.5px}
.grade-A{background:rgba(0,200,122,.15);color:#00C87A;border:1px solid rgba(0,200,122,.3)}
.grade-B{background:rgba(0,148,255,.15);color:#0094FF;border:1px solid rgba(0,148,255,.3)}
.grade-C{background:rgba(245,166,35,.15);color:#F5A623;border:1px solid rgba(245,166,35,.3)}
.grade-D{background:rgba(244,63,94,.12);color:#F43F5E;border:1px solid rgba(244,63,94,.2)}
.grade-F{background:rgba(44,64,96,.2);color:#6B87A8;border:1px solid rgba(44,64,96,.3)}
.dday-label{font-size:11px;font-weight:600;white-space:nowrap;font-family:'JetBrains Mono',monospace}
.dday-urgent{color:#F43F5E}
.dday-soon{color:#F5A623}
.dday-ok{color:#0094FF}
.dday-closed{color:#4A6585}
.status-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;font-family:'JetBrains Mono',monospace}
.status-inbox{background:rgba(44,64,96,.3);color:#6B87A8}
.status-applied{background:rgba(0,148,255,.12);color:#0094FF}
.status-passed{background:rgba(0,200,122,.12);color:#00C87A}
.status-rejected{background:rgba(244,63,94,.12);color:#F43F5E}
.lk-log-row{background:#0C1525;border:1px solid #1C2E47;border-radius:6px;padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:12px;font-size:12px}
.log-channel{font-family:'JetBrains Mono',monospace;font-weight:600;color:#DDE6F5;min-width:150px}
.log-count{color:#0094FF;font-weight:600;font-family:'JetBrains Mono',monospace}
.log-time{color:#4A6585;margin-left:auto;font-family:'JetBrains Mono',monospace}
.log-error{color:#F43F5E}
</style>
"""

# ---------------------------------------------------------------------------
# 통계 카드 전용 CSS (st.html iframe embed)
# ---------------------------------------------------------------------------
_STAT_STYLE = """
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'DM Sans',sans-serif;background:#070B14;color:#DDE6F5}
.lk-stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:4px 0 16px}
.lk-stat-card{background:#0C1525;border:1px solid #1C2E47;border-left:3px solid #0094FF;border-radius:8px;padding:16px 18px}
.lk-stat-card.green{border-left-color:#00C87A}
.lk-stat-card.amber{border-left-color:#F5A623}
.lk-stat-card.red{border-left-color:#F43F5E}
.lk-stat-card.purple{border-left-color:#A78BFA}
.lk-stat-num{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:600;color:#0094FF;line-height:1;margin-bottom:4px}
.lk-stat-num.green{color:#00C87A}
.lk-stat-num.amber{color:#F5A623}
.lk-stat-num.red{color:#F43F5E}
.lk-stat-num.purple{color:#A78BFA}
.lk-stat-num.muted{color:#8AABCC}
.lk-stat-label{font-family:'JetBrains Mono',monospace;font-size:10px;color:#4A6585;text-transform:uppercase;letter-spacing:.8px}
@media(max-width:700px){.lk-stat-row{grid-template-columns:repeat(2,1fr)}}
</style>
"""

# ---------------------------------------------------------------------------
# 섹션 타이틀 전용 CSS (st.html iframe embed)
# ---------------------------------------------------------------------------
_SECTION_STYLE = """
<link href="https://fonts.googleapis.com/css2?family=Oxanium:wght@700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070B14;color:#DDE6F5}
.lk-section-title{font-family:'Oxanium',monospace;font-size:11px;font-weight:700;color:#8AABCC;text-transform:uppercase;letter-spacing:2px;padding:4px 0 8px;border-bottom:1px solid #1C2E47;display:block;margin:0}
</style>
"""

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=30)
def load_jobs() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM jobs", conn)
    return df


@st.cache_data(ttl=30)
def load_scan_log() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM scan_log ORDER BY timestamp DESC LIMIT 300", conn
        )
    return df


def update_status(job_id: str, new_status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (new_status, job_id))
        conn.commit()
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def parse_deadline(value: Any) -> datetime | None:
    if not value or pd.isna(value):
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def dday_delta(deadline: Any) -> int | None:
    dt = parse_deadline(deadline)
    if dt is None:
        return None
    return (dt.date() - datetime.now().date()).days


def dday_html(deadline: Any) -> str:
    """링커리어 스타일 마감 표시 HTML."""
    delta = dday_delta(deadline)
    if delta is None:
        return '<span class="dday-label dday-closed">—</span>'
    dt = parse_deadline(deadline)
    date_str = f"~ {dt.month:02d}.{dt.day:02d}" if dt else ""
    if delta < 0:
        return f'<span class="dday-label dday-closed">마감</span>'
    if delta == 0:
        return f'<span class="dday-label dday-urgent">D-DAY</span>'
    if delta <= 3:
        return f'<span class="dday-label dday-urgent">{date_str}<br>D-{delta}</span>'
    if delta <= 7:
        return f'<span class="dday-label dday-soon">{date_str}<br>D-{delta}</span>'
    return f'<span class="dday-label dday-ok">{date_str}<br>D-{delta}</span>'


def archetype_badge(archetype: Any) -> str:
    if not archetype or pd.isna(archetype):
        return '<span class="badge badge-default">—</span>'
    a = str(archetype).upper()
    label = ARCHETYPE_LABELS.get(a, archetype)
    cls = {
        "INTERN": "badge-intern",
        "ENTRY": "badge-entry",
        "EXPERIENCED": "badge-exp",
        "IT": "badge-it",
    }.get(a, "badge-default")
    return f'<span class="badge {cls}">{label}</span>'


def grade_badge(grade: Any) -> str:
    """적합도 등급 뱃지 — A(초록)~F(빨강) 컬러 코딩."""
    if not grade or pd.isna(grade):
        return '<span class="badge badge-default">—</span>'
    g = str(grade).upper()
    return f'<span class="badge grade-badge grade-{g}">{g}</span>'


def status_badge(status: Any) -> str:
    s = str(status) if status else "inbox"
    label = STATUS_LABELS.get(s, s)
    return f'<span class="status-badge status-{s}">{label}</span>'


def safe_str(v: Any, maxlen: int = 60) -> str:
    if not v or pd.isna(v):
        return "—"
    s = str(v).strip()
    return (s[:maxlen] + "…") if len(s) > maxlen else s


# ---------------------------------------------------------------------------
# HTML 공고 테이블
# ---------------------------------------------------------------------------
def render_job_table(filtered: pd.DataFrame) -> None:
    """링커리어 스타일 HTML 공고 테이블 렌더링."""
    if filtered.empty:
        st.info("해당 조건의 공고가 없습니다.")
        return

    rows_html = ""
    for _, row in filtered.iterrows():
        title = safe_str(row.get("title"), 70)
        org = safe_str(row.get("org"), 20)
        category = safe_str(row.get("description"), 50) if row.get("archetype") is None else ""
        url = row.get("source_url", "#") or "#"
        channel = safe_str(row.get("source_channel"), 20)
        location = safe_str(row.get("location"), 12)
        if location == "—":
            location = "전국"
        fit_score = row.get("fit_score")
        score_html = (
            f'<span style="color:#0094FF;font-weight:700;font-family:\'JetBrains Mono\',monospace;">{int(fit_score)}</span>'
            if fit_score is not None and not pd.isna(fit_score)
            else "—"
        )

        rows_html += f"""
        <tr>
          <td class="td-company">
            <span class="company-name" title="{org}">{org}</span>
            <span class="short-info">{channel}</span>
          </td>
          <td class="td-title">
            <div class="recruit-name">
              <a href="{url}" target="_blank" rel="noopener">{title}</a>
            </div>
            <span class="recruit-category">{category}</span>
          </td>
          <td>{archetype_badge(row.get("archetype"))}</td>
          <td style="text-align:center;">{grade_badge(row.get("fit_grade"))}</td>
          <td style="text-align:center;">{score_html}</td>
          <td><span class="short-info">{location}</span></td>
          <td>{dday_html(row.get("deadline"))}</td>
          <td>{status_badge(row.get("status"))}</td>
        </tr>
        """

    html = f"""
    <div class="lk-table-wrap">
      <table class="lk-table">
        <thead>
          <tr>
            <th>기업/채널</th>
            <th>공고명</th>
            <th>유형</th>
            <th style="text-align:center;">등급</th>
            <th style="text-align:center;">점수</th>
            <th>지역</th>
            <th>마감</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
    """
    st.html(_TABLE_STYLE + html)


# ---------------------------------------------------------------------------
# 통계 카드
# ---------------------------------------------------------------------------
def render_stat_cards(df: pd.DataFrame) -> None:
    today_str = datetime.now().date().isoformat()
    total = len(df)
    today_new = int((df["scanned_at"].fillna("").str[:10] == today_str).sum())

    deadlines = df["deadline"].apply(parse_deadline)
    _now = datetime.now()
    soon = int(deadlines.apply(lambda d: d is not None and d >= _now).sum())
    applied = int((df["status"] == "applied").sum())
    channels = df["source_channel"].nunique() if "source_channel" in df.columns else 0
    grade_a = int((df.get("fit_grade", pd.Series(dtype=str)) == "A").sum())
    grade_b = int((df.get("fit_grade", pd.Series(dtype=str)) == "B").sum())
    eligible_cnt = int((df.get("eligible", pd.Series(dtype=str)) == "true").sum())

    st.html(
        _STAT_STYLE + f"""
        <div class="lk-stat-row">
          <div class="lk-stat-card">
            <div class="lk-stat-num">{total:,}</div>
            <div class="lk-stat-label">TOTAL JOBS</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num muted">{today_new:,}</div>
            <div class="lk-stat-label">TODAY NEW</div>
          </div>
          <div class="lk-stat-card amber">
            <div class="lk-stat-num amber">{soon:,}</div>
            <div class="lk-stat-label">DEADLINE AHEAD</div>
          </div>
          <div class="lk-stat-card green">
            <div class="lk-stat-num green">{grade_a:,}</div>
            <div class="lk-stat-label">GRADE A</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num">{grade_b:,}</div>
            <div class="lk-stat-label">GRADE B</div>
          </div>
          <div class="lk-stat-card green">
            <div class="lk-stat-num green">{eligible_cnt:,}</div>
            <div class="lk-stat-label">ELIGIBLE</div>
          </div>
          <div class="lk-stat-card purple">
            <div class="lk-stat-num purple">{applied:,}</div>
            <div class="lk-stat-label">APPLIED</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num muted">{channels:,}</div>
            <div class="lk-stat-label">CHANNELS</div>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# 탭 렌더러
# ---------------------------------------------------------------------------
def render_overview(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("아직 수집된 공고가 없습니다. '📡 스캔' 탭에서 수집을 시작하세요.")
        return

    render_stat_cards(df)

    # ── 추천 공고 (핵심 섹션) ──────────────────────────────────────────────────
    st.html(_SECTION_STYLE + '<div class="lk-section-title">⭐ 추천 공고 (자격충족 · 적합도순)</div>')
    _grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    rec_df = df[df["eligible"] == "true"].copy()
    rec_df["_grade_rank"] = rec_df["fit_grade"].map(_grade_order).fillna(9)
    rec_df = rec_df.sort_values(["_grade_rank", "fit_score"], ascending=[True, False])
    render_job_table(rec_df.head(20))

    # ── 마감 예정 공고 ──────────────────────────────────────────────────────────
    st.html(_SECTION_STYLE + '<div class="lk-section-title">⏰ 마감 예정 공고</div>')
    _now = datetime.now()

    def _is_future(d: Any) -> bool:
        dt = parse_deadline(d)
        return dt is not None and dt >= _now

    deadline_df = df[df["deadline"].apply(_is_future)].copy()
    deadline_df["_delta"] = deadline_df["deadline"].apply(dday_delta)
    deadline_df = deadline_df.sort_values("_delta", na_position="last")
    if deadline_df.empty:
        st.info("마감 예정 공고가 없습니다. (대부분 수시채용)")
    else:
        render_job_table(deadline_df.head(30))

    # ── 채널별 공고 수 (접힘) ────────────────────────────────────────────────────
    with st.expander("📊 채널별 공고 수"):
        ch = (
            df.groupby("source_channel")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
            .tail(30)
        )
        fig = px.bar(
            ch,
            x="count",
            y="source_channel",
            orientation="h",
            color="count",
            color_continuous_scale=["#1C2E47", "#0094FF"],
            template="plotly_dark",
            labels={"source_channel": "", "count": "공고 수"},
        )
        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
            paper_bgcolor="#0C1525",
            plot_bgcolor="#0C1525",
            font=dict(color="#8AABCC", size=12),
            xaxis=dict(gridcolor="#1C2E47", zerolinecolor="#1C2E47"),
            yaxis=dict(gridcolor="#1C2E47"),
        )
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)


def render_jobs(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("데이터가 없습니다.")
        return

    # 필터 바
    st.html(_SECTION_STYLE + '<div class="lk-section-title">공고 검색 · 필터</div>')
    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])

    keyword = col1.text_input("🔍 기업·공고명 검색", "", placeholder="예) 삼성, 인턴, 데이터")
    channels = sorted(df["source_channel"].dropna().unique().tolist())
    tiers = sorted(df["source_tier"].dropna().unique().tolist())
    archetypes = sorted(df["archetype"].dropna().unique().tolist()) if "archetype" in df.columns else []
    statuses = sorted(df["status"].dropna().unique().tolist())

    sel_channel = col2.multiselect("채널", channels, placeholder="전체")
    sel_tier = col3.multiselect("Tier", tiers, placeholder="전체")
    sel_grade = col4.multiselect("등급", ["A", "B", "C", "D", "F"], placeholder="전체")
    sel_archetype = col5.multiselect("유형", archetypes, placeholder="전체")

    col6, col7, col8 = st.columns([2, 3, 4])
    sel_status = col6.multiselect("상태", statuses, placeholder="전체")
    only_open = col7.checkbox("마감 임박만 (7일 내)", value=False)
    only_eligible = col8.checkbox("✅ 자격요건 충족만", value=True)

    sort_by = st.radio("정렬", ["적합도순", "마감순", "최신순"], horizontal=True)

    # 필터 적용
    filtered = df.copy()
    if sel_channel:
        filtered = filtered[filtered["source_channel"].isin(sel_channel)]
    if sel_tier:
        filtered = filtered[filtered["source_tier"].isin(sel_tier)]
    if sel_grade:
        filtered = filtered[filtered["fit_grade"].isin(sel_grade)]
    if sel_archetype:
        filtered = filtered[filtered["archetype"].isin(sel_archetype)]
    if sel_status:
        filtered = filtered[filtered["status"].isin(sel_status)]
    if only_eligible:
        filtered = filtered[filtered["eligible"] == "true"]
    if keyword:
        kw = keyword.lower()
        mask = (
            filtered["org"].fillna("").str.lower().str.contains(kw)
            | filtered["title"].fillna("").str.lower().str.contains(kw)
        )
        filtered = filtered[mask]
    if only_open:
        now, horizon = datetime.now(), datetime.now() + timedelta(days=7)
        filtered = filtered[
            filtered["deadline"].apply(
                lambda d: (dt := parse_deadline(d)) is not None and now <= dt <= horizon
            )
        ]

    # 정렬
    filtered = filtered.copy()
    filtered["_delta"] = filtered["deadline"].apply(dday_delta)
    if sort_by == "적합도순":
        _grade_order = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
        filtered["_grade_rank"] = filtered["fit_grade"].map(_grade_order).fillna(9)
        filtered = filtered.sort_values(
            ["_grade_rank", "fit_score"], ascending=[True, False], na_position="last"
        )
    elif sort_by == "마감순":
        filtered = filtered.sort_values("_delta", na_position="last")
    else:
        filtered = filtered.sort_values("scanned_at", ascending=False)

    # 현재 / 과거 공고 분리
    _now = datetime.now()

    def _is_expired(deadline: Any) -> bool:
        dt = parse_deadline(deadline)
        return dt is not None and dt < _now

    active = filtered[~filtered["deadline"].apply(_is_expired)].head(200)
    expired = filtered[filtered["deadline"].apply(_is_expired)].head(200)

    st.html(
        f'<p style="font-family:\'DM Sans\',sans-serif;font-size:13px;color:#8AABCC;margin:4px 0 8px;">'
        f'현재 <span style="color:#0094FF;font-weight:700;">{len(active):,}건</span>'
        f' · 마감 <span style="color:#4A6585;font-weight:700;">{len(expired):,}건</span>'
        f' / 전체 {len(df):,}건</p>'
    )

    # ── 현재 공고 ──────────────────────────────────────────────────────────────
    st.html(_SECTION_STYLE + '<div class="lk-section-title">📋 현재 공고</div>')
    render_job_table(active)

    # ── 과거 공고 (접힌 상태) ─────────────────────────────────────────────────
    if not expired.empty:
        with st.expander(f"🗂 마감된 공고 ({len(expired):,}건) — 클릭해서 펼치기", expanded=False):
            render_job_table(expired)

    # 상세보기
    if not filtered.empty:
        st.html(_SECTION_STYLE + '<div class="lk-section-title">공고 상세</div>')
        options = {
            f"[{r['source_channel']}] {r['org']} — {r['title'][:50]}": r["id"]
            for _, r in filtered.head(200).iterrows()
        }
        sel = st.selectbox("공고 선택", ["—"] + list(options.keys()), label_visibility="collapsed")
        if sel != "—":
            row = filtered[filtered["id"] == options[sel]].iloc[0]
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"### {row['title']}")
                    st.markdown(
                        f"**{row['org']}** · {row['source_channel']} · Tier {row['source_tier']}"
                    )
                    if row.get("source_url"):
                        st.markdown(f"[🔗 공고 바로가기]({row['source_url']})")
                with c2:
                    delta = dday_delta(row.get("deadline"))
                    st.markdown(f"**마감**: {row.get('deadline') or '—'}")
                    st.html(_TABLE_STYLE + dday_html(row.get("deadline")))
                    st.html(_TABLE_STYLE + f"<span style='font-size:13px;color:#8AABCC;'>유형: </span>{archetype_badge(row.get('archetype'))}")
                st.divider()
                st.markdown(row.get("description") or "_설명 없음_")


def render_scan(channels: list[str]) -> None:
    st.html(_SECTION_STYLE + '<div class="lk-section-title">스캔 실행</div>')

    col1, col2 = st.columns([2, 1])
    with col1:
        mode = st.radio("스캔 모드", ["전체 스캔", "채널 선택"], horizontal=True)
        selected_channel: str | None = None
        if mode == "채널 선택":
            selected_channel = st.selectbox("채널", channels) if channels else None
    with col2:
        concurrency = st.slider("동시 실행 수", 1, 8, 4)

    if st.button("🚀 스캔 시작", type="primary"):
        if mode == "전체 스캔":
            cmd = [
                sys.executable, "-m", "career_ops_kr.cli",
                "scan", "--all", "--concurrency", str(concurrency),
            ]
        else:
            if not selected_channel:
                st.error("채널을 선택하세요.")
                return
            cmd = [
                sys.executable, "-m", "career_ops_kr.cli",
                "scan", "--channel", selected_channel,
            ]

        st.code(" ".join(cmd), language="bash")
        log_area = st.empty()
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        logs: list[str] = []
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", env=env, bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                logs.append(line.rstrip())
                log_area.text_area("실시간 로그", "\n".join(logs[-300:]), height=360)
            proc.wait()
            if proc.returncode == 0:
                st.success(f"✅ 스캔 완료")
            else:
                st.error(f"❌ 스캔 실패 (exit {proc.returncode})")
        except Exception as exc:
            st.exception(exc)
        finally:
            st.cache_data.clear()

    st.html(_SECTION_STYLE + '<div class="lk-section-title">최근 스캔 로그</div>')
    log_df = load_scan_log()
    if log_df.empty:
        st.info("스캔 로그가 없습니다.")
    else:
        # 링커리어 스타일 로그 카드
        rows_html = ""
        for _, row in log_df.head(50).iterrows():
            err_html = f'<span class="log-error">⚠ {str(row.get("errors",""))[:60]}</span>' if row.get("errors") else ""
            rows_html += f"""
            <div class="lk-log-row">
              <span class="log-channel">{row.get("channel","—")}</span>
              <span class="log-count">+{int(row.get("count",0))}건</span>
              {err_html}
              <span class="log-time">{str(row.get("timestamp",""))[:16]}</span>
            </div>
            """
        st.html(_TABLE_STYLE + rows_html)


def render_channel_health(df: pd.DataFrame, log_df: pd.DataFrame) -> None:
    st.html(_SECTION_STYLE + '<div class="lk-section-title">채널 상태</div>')

    if df.empty and log_df.empty:
        st.info("데이터가 없습니다.")
        return

    channel_counts = (
        df.groupby("source_channel").size().reset_index(name="total_jobs")
        if not df.empty
        else pd.DataFrame(columns=["source_channel", "total_jobs"])
    )

    if not log_df.empty:
        last_scan = (
            log_df.sort_values("timestamp")
            .groupby("channel")
            .tail(1)[["channel", "timestamp", "count", "errors"]]
            .rename(columns={"channel": "source_channel"})
        )
    else:
        last_scan = pd.DataFrame(columns=["source_channel", "timestamp", "count", "errors"])

    merged = channel_counts.merge(last_scan, on="source_channel", how="outer").fillna(
        {"total_jobs": 0, "count": 0, "errors": "", "timestamp": "—"}
    )

    def _status(row: pd.Series) -> str:
        if row.get("errors"):
            return "🔴"
        if int(row.get("count", 0)) == 0:
            return "🟡"
        return "🟢"

    merged["상태"] = merged.apply(_status, axis=1)
    merged = merged.rename(
        columns={
            "source_channel": "채널",
            "total_jobs": "누적 공고",
            "timestamp": "마지막 스캔",
            "count": "최근 수집",
            "errors": "에러",
        }
    )

    # 링커리어 스타일 채널 테이블
    rows_html = ""
    for _, row in merged.iterrows():
        err_cell = f'<td class="log-error" style="font-size:11px;">{str(row["에러"])[:50]}</td>'
        rows_html += f"""
        <tr>
          <td><span style="font-weight:600;color:#DDE6F5;">{row["채널"]}</span></td>
          <td>{row["상태"]}</td>
          <td><span class="short-info">{str(row["마지막 스캔"])[:16]}</span></td>
          <td><span class="log-count">+{int(row["최근 수집"])}</span></td>
          <td><span style="font-weight:700;color:#0094FF;font-family:'JetBrains Mono',monospace;">{int(row["누적 공고"])}</span></td>
          {err_cell}
        </tr>
        """

    html = f"""
    <div class="lk-table-wrap">
      <table class="lk-table">
        <thead>
          <tr>
            <th>채널</th><th>상태</th><th>마지막 스캔</th>
            <th>최근 수집</th><th>누적 공고</th><th>에러</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """
    st.html(_TABLE_STYLE + html)

    broken = merged[merged["상태"] != "🟢"]
    if not broken.empty:
        st.warning(f"⚠️ 주의 채널: {len(broken)}개 (0건 or 에러)")


def render_tracker(df: pd.DataFrame) -> None:
    st.html(_SECTION_STYLE + '<div class="lk-section-title">지원 트래커</div>')

    if df.empty:
        st.info("데이터가 없습니다.")
        return

    show_all = st.checkbox("모든 상태 보기", value=False)
    target = df if show_all else df[df["status"] == "applied"]

    if target.empty:
        st.info("지원 중(applied) 공고가 없습니다.")
        return

    target = target.copy()
    target["_delta"] = target["deadline"].apply(dday_delta)
    target = target.sort_values("_delta", na_position="last")

    for _, row in target.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 2])
            with c1:
                st.html(
                    f"<span style='font-family:DM Sans,sans-serif;font-weight:700;font-size:15px;color:#DDE6F5;'>{row['org']}</span> "
                    f"<span style='font-family:DM Sans,sans-serif;color:#8AABCC;'>— {row['title'][:60]}</span>"
                )
                st.caption(
                    f"{row['source_channel']} · Tier {row['source_tier']} · "
                    f"{ARCHETYPE_LABELS.get(str(row.get('archetype','')), '—')}"
                )
                if row["source_url"]:
                    st.markdown(f"[🔗 공고 링크]({row['source_url']})")
            with c2:
                st.html(_TABLE_STYLE + dday_html(row.get("deadline")))
                st.caption(str(row.get("deadline") or "—"))
            with c3:
                current = str(row["status"])
                options = list(STATUS_LABELS.keys())
                idx = options.index(current) if current in options else 0
                new_status = st.selectbox(
                    "상태",
                    options,
                    index=idx,
                    format_func=lambda s: STATUS_LABELS.get(s, s),
                    key=f"status_{row['id']}",
                )
                if new_status != current:
                    if st.button("저장", key=f"save_{row['id']}"):
                        update_status(row["id"], new_status)
                        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="career-ops-kr",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    # 전역 CSS 주입 (<style> 태그만 → st.markdown 작동)
    st.markdown(LINKAREER_CSS, unsafe_allow_html=True)

    # 헤더 (iframe에 CSS embed)
    db_ok = DB_PATH.exists()
    dot_color = "#00C87A" if db_ok else "#F43F5E"
    db_label = "LIVE" if db_ok else "OFFLINE"
    _header_css = """
<link href="https://fonts.googleapis.com/css2?family=Oxanium:wght@700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070B14}
.lk-header{background:linear-gradient(120deg,#0C1525 60%,#111D30 100%);border:1px solid #1C2E47;border-top:2px solid #0094FF;padding:16px 28px;display:flex;align-items:center;gap:16px;border-radius:0 0 10px 10px;position:relative;overflow:hidden}
.lk-logo{font-family:'Oxanium',monospace;font-size:18px;font-weight:800;color:#0094FF;letter-spacing:2px;text-transform:uppercase}
.lk-sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:#4A6585}
.co-dot{width:7px;height:7px;border-radius:50%;animation:blink 2s ease infinite;display:inline-block}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
</style>
"""
    st.html(
        _header_css + f"""
        <div class="lk-header">
          <div class="lk-logo">CAREER-OPS-KR</div>
          <span class="lk-sub">한국 금융 · 블록체인 · 디지털 구직 파이프라인</span>
          <div style="margin-left:auto;display:flex;align-items:center;gap:10px;">
            <div class="co-dot" style="background:{dot_color};box-shadow:0 0 8px {dot_color};"></div>
            <span class="lk-sub">{db_label} · {DB_PATH.name}</span>
          </div>
        </div>
        """
    )

    if not DB_PATH.exists():
        st.error(
            f"DB 파일이 없습니다: `{DB_PATH}`\n\n"
            "`career-ops scan --all`로 최초 스캔을 실행하세요."
        )
        return

    df = load_jobs()
    log_df = load_scan_log()
    channels = sorted(df["source_channel"].dropna().unique().tolist()) if not df.empty else []

    tabs = st.tabs(["📊 대시보드", "🔍 공고 목록", "📡 스캔", "🏥 채널 상태", "📋 지원 트래커"])
    with tabs[0]:
        render_overview(df)
    with tabs[1]:
        render_jobs(df)
    with tabs[2]:
        render_scan(channels)
    with tabs[3]:
        render_channel_health(df, log_df)
    with tabs[4]:
        render_tracker(df)


if __name__ == "__main__":
    main()
