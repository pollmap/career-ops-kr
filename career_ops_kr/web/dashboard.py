"""career-ops-kr Streamlit 웹 대시보드.

실행:
    python -m streamlit run career_ops_kr/web/dashboard.py --server.port 8501

탭 구성:
    📊 대시보드 / 🔍 공고 목록 / 📡 스캔 / 🏥 채널 상태 / 📋 지원 트래커
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
    "inbox": "📥 Inbox",
    "applied": "📤 지원함",
    "passed": "✅ 합격",
    "rejected": "❌ 탈락",
}

GRADE_COLORS = {
    "A": "#22c55e",
    "B": "#3b82f6",
    "C": "#eab308",
    "D": "#f97316",
    "F": "#ef4444",
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    """읽기 전용 연결 반환 (UTF-8)."""
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
            "SELECT * FROM scan_log ORDER BY timestamp DESC LIMIT 200", conn
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


def dday_label(deadline: Any) -> str:
    dt = parse_deadline(deadline)
    if dt is None:
        return "—"
    delta = (dt.date() - datetime.now().date()).days
    if delta < 0:
        return f"마감 (D+{-delta})"
    if delta == 0:
        return "D-DAY"
    return f"D-{delta}"


def apply_dark_theme() -> None:
    st.markdown(
        """
        <style>
            .stApp { background-color: #0e1117; color: #e4e7eb; }
            .metric-card {
                background: #1c2028; border-radius: 10px;
                padding: 14px 18px; border: 1px solid #2a2f3a;
            }
            h1, h2, h3 { color: #f3f4f6 !important; }
            .dday-urgent { color:#ef4444; font-weight:700; }
            .dday-soon { color:#f97316; font-weight:600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
def render_overview(df: pd.DataFrame) -> None:
    st.subheader("📊 대시보드")
    if df.empty:
        st.info("아직 수집된 공고가 없습니다. '📡 스캔' 탭에서 수집을 시작하세요.")
        return

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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 공고", f"{total:,}")
    c2.metric("오늘 신규", f"{today_new:,}")
    c3.metric("마감임박 (7일)", f"{soon:,}")
    c4.metric("지원함", f"{applied:,}")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.markdown("#### 채널별 공고 수")
        ch = (
            df.groupby("source_channel")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=True)
        )
        fig = px.bar(
            ch,
            x="count",
            y="source_channel",
            orientation="h",
            color="count",
            color_continuous_scale="Viridis",
            template="plotly_dark",
        )
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Fit Grade 분포")
        if "fit_grade" in df.columns and df["fit_grade"].notna().any():
            g = (
                df["fit_grade"]
                .fillna("미평가")
                .value_counts()
                .reset_index()
            )
            g.columns = ["grade", "count"]
            fig = px.pie(
                g,
                names="grade",
                values="count",
                hole=0.45,
                color="grade",
                color_discrete_map={**GRADE_COLORS, "미평가": "#6b7280"},
                template="plotly_dark",
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("아직 fit_grade가 평가된 공고가 없습니다.")

    st.markdown("#### 상태 분포")
    s = df["status"].value_counts().reset_index()
    s.columns = ["status", "count"]
    s["label"] = s["status"].map(STATUS_LABELS).fillna(s["status"])
    fig = px.bar(
        s,
        x="label",
        y="count",
        color="status",
        template="plotly_dark",
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)


def render_jobs(df: pd.DataFrame) -> None:
    st.subheader("🔍 공고 목록")
    if df.empty:
        st.info("데이터가 없습니다.")
        return

    with st.expander("🔧 필터", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        channels = sorted(df["source_channel"].dropna().unique().tolist())
        tiers = sorted(df["source_tier"].dropna().unique().tolist())
        grades = sorted(df["fit_grade"].dropna().unique().tolist())
        statuses = sorted(df["status"].dropna().unique().tolist())

        sel_channel = c1.multiselect("채널", channels)
        sel_tier = c2.multiselect("Tier", tiers)
        sel_grade = c3.multiselect("Fit Grade", grades)
        sel_status = c4.multiselect("Status", statuses)
        keyword = st.text_input("키워드 검색 (org/title/description)", "")

    filtered = df.copy()
    if sel_channel:
        filtered = filtered[filtered["source_channel"].isin(sel_channel)]
    if sel_tier:
        filtered = filtered[filtered["source_tier"].isin(sel_tier)]
    if sel_grade:
        filtered = filtered[filtered["fit_grade"].isin(sel_grade)]
    if sel_status:
        filtered = filtered[filtered["status"].isin(sel_status)]
    if keyword:
        kw = keyword.lower()
        mask = (
            filtered["org"].fillna("").str.lower().str.contains(kw)
            | filtered["title"].fillna("").str.lower().str.contains(kw)
            | filtered["description"].fillna("").str.lower().str.contains(kw)
        )
        filtered = filtered[mask]

    st.caption(f"총 {len(filtered):,}건 / 전체 {len(df):,}건")

    cols = [
        "org",
        "title",
        "source_channel",
        "source_tier",
        "fit_grade",
        "deadline",
        "status",
        "source_url",
    ]
    view = filtered[cols].copy()
    view["deadline"] = view["deadline"].apply(lambda d: f"{d} ({dday_label(d)})" if d else "—")

    st.dataframe(
        view,
        use_container_width=True,
        height=500,
        column_config={
            "source_url": st.column_config.LinkColumn("URL", width="small"),
        },
        hide_index=True,
    )

    st.markdown("#### 📄 상세보기")
    if not filtered.empty:
        options = {
            f"[{r['source_channel']}] {r['org']} — {r['title']}": r["id"]
            for _, r in filtered.iterrows()
        }
        sel = st.selectbox("공고 선택", ["—"] + list(options.keys()))
        if sel != "—":
            row = filtered[filtered["id"] == options[sel]].iloc[0]
            st.markdown(f"**기관**: {row['org']}")
            st.markdown(f"**직무**: {row['title']}")
            st.markdown(f"**채널**: {row['source_channel']} (Tier {row['source_tier']})")
            st.markdown(f"**Archetype**: {row.get('archetype') or '—'}")
            st.markdown(f"**마감**: {row.get('deadline') or '—'} ({dday_label(row.get('deadline'))})")
            st.markdown(f"**URL**: {row['source_url']}")
            st.markdown("---")
            st.markdown(row.get("description") or "_설명 없음_")


def render_scan(channels: list[str]) -> None:
    st.subheader("📡 스캔 실행")

    mode = st.radio("스캔 모드", ["전체 스캔", "채널 선택"], horizontal=True)
    selected_channel: str | None = None
    if mode == "채널 선택":
        selected_channel = st.selectbox("채널 선택", channels) if channels else None

    concurrency = st.slider("동시 실행 수", 1, 8, 4)

    if st.button("🚀 스캔 시작", type="primary"):
        if mode == "전체 스캔":
            cmd = [
                sys.executable,
                "-m",
                "career_ops_kr.cli",
                "scan",
                "--all",
                "--concurrency",
                str(concurrency),
            ]
        else:
            if not selected_channel:
                st.error("채널을 선택하세요.")
                return
            cmd = [
                sys.executable,
                "-m",
                "career_ops_kr.cli",
                "scan",
                "--channel",
                selected_channel,
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
                text=True,
                encoding="utf-8",
                env=env,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                logs.append(line.rstrip())
                log_area.text_area("실시간 로그", "\n".join(logs[-300:]), height=360)
            proc.wait()
            if proc.returncode == 0:
                st.success(f"✅ 스캔 완료 (exit {proc.returncode})")
            else:
                st.error(f"❌ 스캔 실패 (exit {proc.returncode})")
        except Exception as exc:  # noqa: BLE001
            st.exception(exc)
        finally:
            st.cache_data.clear()

    st.divider()
    st.markdown("#### 🕑 최근 스캔 로그")
    log_df = load_scan_log()
    if log_df.empty:
        st.info("스캔 로그가 없습니다.")
    else:
        st.dataframe(log_df, use_container_width=True, height=360, hide_index=True)


def render_channel_health(df: pd.DataFrame, log_df: pd.DataFrame) -> None:
    st.subheader("🏥 채널 상태")
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
            return "🔴 실패"
        if int(row.get("count", 0)) == 0:
            return "🟡 0건"
        return "🟢 정상"

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

    st.dataframe(
        merged[["채널", "상태", "마지막 스캔", "최근 수집", "누적 공고", "에러"]],
        use_container_width=True,
        height=520,
        hide_index=True,
    )

    broken = merged[merged["상태"] != "🟢 정상"]
    if not broken.empty:
        st.warning(f"⚠️ 수리 필요 채널: {len(broken)}개")
        st.dataframe(broken[["채널", "상태", "에러"]], use_container_width=True, hide_index=True)


def render_tracker(df: pd.DataFrame) -> None:
    st.subheader("📋 지원 트래커")
    if df.empty:
        st.info("데이터가 없습니다.")
        return

    show_all = st.checkbox("모든 상태 보기 (기본: applied만)", value=False)
    target = df if show_all else df[df["status"] == "applied"]

    if target.empty:
        st.info("지원 중(applied) 공고가 없습니다.")
        return

    target = target.copy()
    target["D-day"] = target["deadline"].apply(dday_label)
    target = target.sort_values("deadline", na_position="last")

    for _, row in target.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 2])
            with c1:
                st.markdown(f"**{row['org']}** — {row['title']}")
                st.caption(
                    f"{row['source_channel']} · Tier {row['source_tier']} · "
                    f"Grade {row.get('fit_grade') or '—'}"
                )
                if row["source_url"]:
                    st.markdown(f"[🔗 공고 링크]({row['source_url']})")
            with c2:
                st.metric("마감", row["D-day"], row.get("deadline") or "—")
            with c3:
                current = row["status"]
                options = list(STATUS_LABELS.keys())
                idx = options.index(current) if current in options else 0
                new_status = st.selectbox(
                    "상태 변경",
                    options,
                    index=idx,
                    format_func=lambda s: STATUS_LABELS.get(s, s),
                    key=f"status_{row['id']}",
                )
                if new_status != current:
                    if st.button("저장", key=f"save_{row['id']}"):
                        update_status(row["id"], new_status)
                        st.success("업데이트 완료")
                        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="career-ops-kr 대시보드",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_dark_theme()

    st.title("🎯 career-ops-kr")
    st.caption(
        "한국형 AI 구직 자동화 에이전트 — Luxon AI · "
        f"DB: `{DB_PATH}` · {'✅ 연결' if DB_PATH.exists() else '❌ DB 없음'}"
    )

    if not DB_PATH.exists():
        st.error(
            f"DB 파일이 없습니다: `{DB_PATH}`\n\n"
            "`career-ops scan --all`로 최초 스캔을 실행하거나 DB를 초기화하세요."
        )
        return

    df = load_jobs()
    log_df = load_scan_log()
    channels = sorted(df["source_channel"].dropna().unique().tolist()) if not df.empty else []

    tabs = st.tabs(
        ["📊 대시보드", "🔍 공고 목록", "📡 스캔", "🏥 채널 상태", "📋 지원 트래커"]
    )
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
