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
/* ── 전역 ── */
html, body, [class*="css"] {
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', -apple-system, sans-serif !important;
    background-color: #F8F8FA !important;
    color: #333333 !important;
}
.stApp { background-color: #F8F8FA !important; }
section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #EEEEEE; }

/* ── 헤더 바 ── */
.lk-header {
    background: #FFFFFF;
    border-bottom: 2px solid #01A0FF;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
}
.lk-logo {
    font-size: 22px;
    font-weight: 800;
    color: #01A0FF;
    letter-spacing: -0.5px;
}
.lk-subtitle {
    font-size: 13px;
    color: #999999;
    margin-left: auto;
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    background: #FFFFFF;
    border-bottom: 2px solid #EEEEEE;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 600;
    color: #666666;
    padding: 12px 20px;
    border-bottom: 2px solid transparent;
}
.stTabs [aria-selected="true"] {
    color: #01A0FF !important;
    border-bottom: 2px solid #01A0FF !important;
}

/* ── 통계 카드 ── */
.lk-stat-row {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.lk-stat-card {
    flex: 1;
    min-width: 140px;
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 8px;
    padding: 18px 20px;
    text-align: center;
}
.lk-stat-num {
    font-size: 28px;
    font-weight: 800;
    color: #01A0FF;
    line-height: 1.1;
}
.lk-stat-label {
    font-size: 12px;
    color: #999999;
    margin-top: 4px;
}

/* ── 필터 바 ── */
.lk-filter-bar {
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 16px;
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
}

/* ── 공고 테이블 ── */
.lk-table-wrap {
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 8px;
    overflow: hidden;
}
.lk-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.lk-table thead th {
    background: #F8F8FA;
    color: #999999;
    font-weight: 600;
    font-size: 12px;
    padding: 10px 14px;
    border-bottom: 1px solid #EEEEEE;
    text-align: left;
    white-space: nowrap;
}
.lk-table tbody tr {
    border-bottom: 1px solid #F0F0F0;
    transition: background 0.12s;
}
.lk-table tbody tr:hover { background: #F2FAFF; }
.lk-table tbody tr:last-child { border-bottom: none; }
.lk-table td { padding: 14px; vertical-align: middle; }

/* 기업명 셀 */
.td-company { min-width: 120px; }
.company-name {
    font-size: 12px;
    color: #666666;
    display: block;
    max-width: 110px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* 공고명 셀 */
.td-title { min-width: 200px; max-width: 340px; }
.recruit-name {
    font-size: 14px;
    font-weight: 600;
    color: #333333;
    display: block;
    line-height: 1.4;
}
.recruit-name a {
    color: #333333 !important;
    text-decoration: none;
}
.recruit-name a:hover { color: #01A0FF !important; }
.recruit-category {
    font-size: 11px;
    color: #999999;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 300px;
    display: block;
}

/* 타입 뱃지 */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}
.badge-intern  { background: #E8F4FF; color: #01A0FF; }
.badge-entry   { background: #E8FFE8; color: #16a34a; }
.badge-exp     { background: #FFF3E0; color: #EA8C00; }
.badge-it      { background: #F3E8FF; color: #9333ea; }
.badge-default { background: #F0F0F0; color: #666666; }

/* 지역 / 유형 */
.short-info {
    font-size: 12px;
    color: #666666;
    white-space: nowrap;
}

/* 마감 */
.dday-label {
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
}
.dday-urgent { color: #EF2929; }
.dday-soon   { color: #EA8C00; }
.dday-ok     { color: #01A0FF; }
.dday-closed { color: #CCCCCC; }

/* 상태 뱃지 */
.status-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
}
.status-inbox    { background: #F0F0F0; color: #666666; }
.status-applied  { background: #E8F4FF; color: #01A0FF; }
.status-passed   { background: #E8FFE8; color: #16a34a; }
.status-rejected { background: #FFE8E8; color: #EF2929; }

/* ── 섹션 헤더 ── */
.lk-section-title {
    font-size: 16px;
    font-weight: 700;
    color: #333333;
    margin: 20px 0 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.lk-section-title::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 16px;
    background: #01A0FF;
    border-radius: 2px;
}

/* ── 스캔 로그 ── */
.lk-log-row {
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
}
.log-channel { font-weight: 700; color: #333333; min-width: 140px; }
.log-count   { color: #01A0FF; font-weight: 700; }
.log-time    { color: #999999; margin-left: auto; }
.log-error   { color: #EF2929; }

/* Streamlit 기본 UI 정리 */
.stButton button {
    background: #01A0FF !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
.stButton button:hover { background: #0090EE !important; }
div[data-testid="stMetricValue"] { color: #01A0FF !important; font-weight: 800 !important; }
.stSelectbox label, .stMultiSelect label, .stTextInput label { color: #666666 !important; font-size: 12px !important; }
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
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(value)[: len(fmt)], fmt)
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
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 통계 카드
# ---------------------------------------------------------------------------
def render_stat_cards(df: pd.DataFrame) -> None:
    today_str = datetime.now().date().isoformat()
    total = len(df)
    today_new = int((df["scanned_at"].fillna("").str[:10] == today_str).sum())

    deadlines = df["deadline"].apply(parse_deadline)
    horizon = datetime.now() + timedelta(days=7)
    soon = int(
        deadlines.apply(
            lambda d: d is not None and datetime.now() <= d <= horizon
        ).sum()
    )
    applied = int((df["status"] == "applied").sum())
    channels = df["source_channel"].nunique() if "source_channel" in df.columns else 0

    st.markdown(
        f"""
        <div class="lk-stat-row">
          <div class="lk-stat-card">
            <div class="lk-stat-num">{total:,}</div>
            <div class="lk-stat-label">총 공고</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num">{today_new:,}</div>
            <div class="lk-stat-label">오늘 신규</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num">{soon:,}</div>
            <div class="lk-stat-label">마감임박 7일</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num">{applied:,}</div>
            <div class="lk-stat-label">지원 중</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num">{channels:,}</div>
            <div class="lk-stat-label">활성 채널</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 탭 렌더러
# ---------------------------------------------------------------------------
def render_overview(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("아직 수집된 공고가 없습니다. '📡 스캔' 탭에서 수집을 시작하세요.")
        return

    render_stat_cards(df)

    st.markdown('<div class="lk-section-title">채널별 공고 수</div>', unsafe_allow_html=True)
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
        color_continuous_scale=["#E8F4FF", "#01A0FF"],
        template="plotly_white",
        labels={"source_channel": "", "count": "공고 수"},
    )
    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#333333", size=12),
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="lk-section-title">마감임박 공고 (7일 내)</div>', unsafe_allow_html=True)
    now = datetime.now()
    horizon = now + timedelta(days=7)

    def _is_soon(d: Any) -> bool:
        dt = parse_deadline(d)
        return dt is not None and now <= dt <= horizon

    soon_df = df[df["deadline"].apply(_is_soon)].copy()
    soon_df["delta"] = soon_df["deadline"].apply(dday_delta)
    soon_df = soon_df.sort_values("delta", na_position="last")
    render_job_table(soon_df.head(20))


def render_jobs(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("데이터가 없습니다.")
        return

    # 필터 바
    st.markdown('<div class="lk-section-title">공고 검색 · 필터</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

    keyword = col1.text_input("🔍 기업·공고명 검색", "", placeholder="예) 삼성, 인턴, 데이터")
    channels = sorted(df["source_channel"].dropna().unique().tolist())
    tiers = sorted(df["source_tier"].dropna().unique().tolist())
    archetypes = sorted(df["archetype"].dropna().unique().tolist()) if "archetype" in df.columns else []
    statuses = sorted(df["status"].dropna().unique().tolist())

    sel_channel = col2.multiselect("채널", channels, placeholder="전체")
    sel_tier = col3.multiselect("Tier", tiers, placeholder="전체")
    sel_archetype = col4.multiselect("유형", archetypes, placeholder="전체")

    col5, col6, _ = st.columns([2, 6, 1])
    sel_status = col5.multiselect("상태", statuses, placeholder="전체")
    only_open = col6.checkbox("마감 임박만 (7일 내)", value=False)

    # 필터 적용
    filtered = df.copy()
    if sel_channel:
        filtered = filtered[filtered["source_channel"].isin(sel_channel)]
    if sel_tier:
        filtered = filtered[filtered["source_tier"].isin(sel_tier)]
    if sel_archetype:
        filtered = filtered[filtered["archetype"].isin(sel_archetype)]
    if sel_status:
        filtered = filtered[filtered["status"].isin(sel_status)]
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

    # 정렬: 마감 가까운 순
    filtered = filtered.copy()
    filtered["_delta"] = filtered["deadline"].apply(dday_delta)
    filtered = filtered.sort_values("_delta", na_position="last")

    st.markdown(
        f'<p style="font-size:13px;color:#999;margin-bottom:8px;">'
        f'<span style="color:#01A0FF;font-weight:700;">{len(filtered):,}건</span>'
        f' / 전체 {len(df):,}건</p>',
        unsafe_allow_html=True,
    )

    render_job_table(filtered.head(200))

    # 상세보기
    if not filtered.empty:
        st.markdown('<div class="lk-section-title">공고 상세</div>', unsafe_allow_html=True)
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
                    st.markdown(
                        f"**마감**: {row.get('deadline') or '—'}  \n"
                        f"{dday_html(row.get('deadline'))}",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**유형**: {archetype_badge(row.get('archetype'))}", unsafe_allow_html=True)
                st.divider()
                st.markdown(row.get("description") or "_설명 없음_")


def render_scan(channels: list[str]) -> None:
    st.markdown('<div class="lk-section-title">스캔 실행</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="lk-section-title">최근 스캔 로그</div>', unsafe_allow_html=True)
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
        st.markdown(rows_html, unsafe_allow_html=True)


def render_channel_health(df: pd.DataFrame, log_df: pd.DataFrame) -> None:
    st.markdown('<div class="lk-section-title">채널 상태</div>', unsafe_allow_html=True)

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
          <td><span style="font-weight:600;color:#333;">{row["채널"]}</span></td>
          <td>{row["상태"]}</td>
          <td><span class="short-info">{str(row["마지막 스캔"])[:16]}</span></td>
          <td><span class="log-count">+{int(row["최근 수집"])}</span></td>
          <td><span style="font-weight:700;color:#01A0FF;">{int(row["누적 공고"])}</span></td>
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
    st.markdown(html, unsafe_allow_html=True)

    broken = merged[merged["상태"] != "🟢"]
    if not broken.empty:
        st.warning(f"⚠️ 주의 채널: {len(broken)}개 (0건 or 에러)")


def render_tracker(df: pd.DataFrame) -> None:
    st.markdown('<div class="lk-section-title">지원 트래커</div>', unsafe_allow_html=True)

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
                st.markdown(
                    f"<span style='font-weight:700;font-size:15px;'>{row['org']}</span> "
                    f"— {row['title'][:60]}",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{row['source_channel']} · Tier {row['source_tier']} · "
                    f"{ARCHETYPE_LABELS.get(str(row.get('archetype','')), '—')}"
                )
                if row["source_url"]:
                    st.markdown(f"[🔗 공고 링크]({row['source_url']})")
            with c2:
                st.markdown(dday_html(row.get("deadline")), unsafe_allow_html=True)
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
    st.markdown(LINKAREER_CSS, unsafe_allow_html=True)

    # 헤더
    db_status = "✅ DB 연결" if DB_PATH.exists() else "❌ DB 없음"
    st.markdown(
        f"""
        <div class="lk-header">
          <div class="lk-logo">🎯 career-ops-kr</div>
          <span style="color:#CCCCCC;">|</span>
          <span style="font-size:13px;color:#666;">한국 금융·IT 구직 자동화</span>
          <div class="lk-subtitle">{db_status} · {DB_PATH.name}</div>
        </div>
        """,
        unsafe_allow_html=True,
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
