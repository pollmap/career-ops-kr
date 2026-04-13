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
# 섹터 분류 — 채널명 기반 (aggregator 공고는 org/title 키워드로 추론)
# ---------------------------------------------------------------------------
_FINANCE_CHANNELS: frozenset[str] = frozenset({
    # 은행
    "kb_bank", "shinhan_bank", "hana_bank", "woori_bank", "nh_bank",
    "busan_bank", "knb", "im_bank", "kwangju_bank", "jb_bank", "jeju_bank",
    "sh_bank", "kakao_bank", "toss_bank", "k_bank", "sc_bank", "citi_bank",
    "kdb_bank", "exim_bank", "ibk_bank",
    # 증권
    "shinhan_sec", "mirae_asset", "kb_sec", "hana_sec", "nh_sec",
    "samsung_sec", "korea_invest_sec", "ibk_sec", "daishin_sec",
    "kyobo_sec", "hanwha_sec", "yuanta_sec", "eugene_sec",
    "hyundai_car_sec", "hi_sec", "db_fi", "sk_sec", "im_sec",
    "cape_sec", "koreafoss_sec", "bookook_sec", "shinyoung_sec",
    "hanyang_sec", "yuhwa_sec", "bnk_sec", "heungkuk_sec", "daol_sec",
    "leading_sec", "korea_asset_sec", "meritz_sec", "miraeasset_sec",
    "kiwoom_kda", "kiwoomda",
    # 선물
    "samsung_futures", "nh_futures", "hana_futures", "kiwoom_futures",
    "shinhan_futures",
    # 생명보험
    "samsung_life", "hanwha_life", "kyobo_life", "shinhan_life",
    "nh_life", "hana_life", "kb_life", "dongyang_life", "miraeasset_life",
    "abl_life", "metlife", "aia_life", "chubb_life", "fubon_life", "kdb_life",
    # 손해보험
    "samsung_fire", "hyundai_marine", "db_ins", "kb_ins", "meritz_fire",
    "hanwha_ins", "lotte_ins", "heungkuk_fire", "mg_ins", "nh_fire",
    "thek_ins", "hana_ins", "carrot_ins", "korean_re",
    # 카드
    "shinhan_card", "samsung_card", "kb_card", "hyundai_card", "lotte_card",
    "woori_card", "bc_card", "hana_card",
    # 캐피탈
    "kb_capital", "hana_capital", "shinhan_capital", "woori_capital",
    "aju_capital", "lotte_capital", "bnk_capital", "jb_woori_capital",
    "nh_capital", "dgb_capital", "kdb_capital", "meritz_capital",
    "hyundai_capital",
    # 저축은행
    "sbi_savings", "ok_savings", "welcome_savings", "kiwoom_yes_savings",
    "pepper_savings", "aquon_savings", "kit_savings", "jt_savings",
    "osb_savings", "thek_savings",
    # 자산운용
    "miraeasset_am", "kit_am", "samsung_am", "kb_am", "shinhan_am",
    "hanwha_am", "nh_amundi_am", "kiwoom_am", "shinyoung_am",
    "kyobo_axa_am", "eastspring_am", "timefolio_am", "truston_am",
    "vi_am", "lazard_am", "ab_am",
    # 금융 인프라·협회·규제
    "kic", "kobc", "koscom", "smbs", "apfs",
    "kfb", "kofia", "knia", "klia", "crefia", "fsb", "cu_central",
    "kfcc", "krx", "ksfc", "ksd", "kftc", "fsec", "kcredit",
    "kfmb", "krca", "kodit", "kibo", "hf", "kamco", "kdic",
    "ksure", "hug", "sgi", "kinfa", "fsc", "fss",
})

_SECURITY_CHANNELS: frozenset[str] = frozenset({
    "nis", "mnd", "mofa", "police", "customs", "dapa", "kisa", "government",
})

_PUBLIC_CHANNELS: frozenset[str] = frozenset({
    "apply_bok", "jobalio", "gojobs", "yw_work24", "dataq",
    "mirae_naeil", "mjob", "ktcu", "mac", "poba", "loginet",
    "cgc", "special_cgc", "firefighter_fund", "sema", "sw_fund",
    "kofic_fund", "kvic", "kgf",
})

_FINTECH_CHANNELS: frozenset[str] = frozenset({
    "toss", "kakao_pay", "banksalad", "finda", "naver_pay",
    "eight_percent", "payco", "dunamu", "bithumb", "lambda256",
    "coinone", "kakao_inv", "lb_inv", "mbk", "hahn_co", "imm",
    "stic", "skylake", "daol_inv", "kit_partners",
})

# 키워드 기반 섹터 추론 (aggregator 채널용)
_FINANCE_KW: tuple[str, ...] = (
    "은행", "증권", "보험", "카드", "캐피탈", "저축", "자산운용", "투자",
    "금융", "선물", "파생", "운용사", "신탁", "펀드", "리츠", "금감원",
    "금융위", "예탁", "결제원", "거래소", "KRX", "KIC", "산업은행",
    "수출입은행", "기업은행", "신용보증", "주택금융", "예금보험",
)
_SECURITY_KW: tuple[str, ...] = (
    "국정원", "안보", "국방", "국가정보", "방위사업", "외교부", "경찰",
    "관세", "KISA", "정보보호", "사이버", "군", "보안",
)
_PUBLIC_KW: tuple[str, ...] = (
    "공사", "공단", "공기업", "공공기관", "청", "처", "원", "연구원",
    "한국은행", "한국거래소", "한국투자공사", "공제회", "중앙회",
)


def _infer_sector(channel: str, org: str, title: str) -> str:
    """채널명 → 섹터. aggregator는 org/title 키워드로 추론."""
    ch = str(channel).lower()
    if ch in _FINANCE_CHANNELS:
        return "금융"
    if ch in _SECURITY_CHANNELS:
        return "안보"
    if ch in _PUBLIC_CHANNELS:
        return "공공"
    if ch in _FINTECH_CHANNELS:
        return "핀테크"
    # aggregator fallback: keyword match
    combined = f"{org} {title}"
    if any(kw in combined for kw in _SECURITY_KW):
        return "안보"
    if any(kw in combined for kw in _FINANCE_KW):
        return "금융"
    if any(kw in combined for kw in _PUBLIC_KW):
        return "공공"
    return "기타"

# ---------------------------------------------------------------------------
# CSS — Linkareer 디자인 시스템
# ---------------------------------------------------------------------------
LINKAREER_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg-base:    #F5F7FA;
  --bg-surface: #FFFFFF;
  --bg-elev:    #EEF1F7;
  --border:     #DDE3ED;
  --border-hi:  #0066CC;
  --accent:     #0066CC;
  --accent-dim: rgba(0,102,204,0.08);
  --accent-glo: rgba(0,102,204,0.15);
  --green:      #1CA760;
  --green-dim:  rgba(28,167,96,0.10);
  --amber:      #D97706;
  --amber-dim:  rgba(217,119,6,0.10);
  --red:        #DC2626;
  --red-dim:    rgba(220,38,38,0.10);
  --purple:     #7C3AED;
  --purple-dim: rgba(124,58,237,0.10);
  --txt:        #1A2332;
  --txt-sec:    #4A5568;
  --txt-mute:   #8B9AB5;
  --ff-body:    'Noto Sans KR', 'Inter', -apple-system, sans-serif;
  --ff-num:     'Inter', -apple-system, sans-serif;
}

/* ── 전역 ── */
html, body, [class*="css"] {
  font-family: var(--ff-body) !important;
  background-color: var(--bg-base) !important;
  color: var(--txt) !important;
  font-size: 15px !important;
}
.stApp { background-color: var(--bg-base) !important; }
.stApp > header { background: var(--bg-surface) !important; border-bottom: 1px solid var(--border) !important; box-shadow: 0 1px 4px rgba(0,0,0,.06) !important; }
section[data-testid="stSidebar"] { background: var(--bg-surface) !important; border-right: 1px solid var(--border) !important; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
p, .stMarkdown p { color: var(--txt) !important; font-size: 15px !important; line-height: 1.6 !important; }
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
  font-size: 15px !important; font-weight: 600 !important;
  color: var(--txt-sec) !important;
  padding: 14px 24px !important;
  border-bottom: 2px solid transparent !important;
  background: transparent !important;
  margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  background: var(--accent-dim) !important;
}
.stTabs [data-baseweb="tab-panel"] { background: transparent !important; padding-top: 20px !important; }

/* ── Streamlit 위젯 ── */
.stTextInput input,
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div {
  background: var(--bg-surface) !important;
  color: var(--txt) !important;
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  font-size: 14px !important;
}
.stTextInput input::placeholder { color: var(--txt-mute) !important; }
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.stCheckbox label span, .stRadio label span, [data-testid="stWidgetLabel"] {
  color: var(--txt-sec) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}
[data-baseweb="menu"], [data-baseweb="popover"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,.08) !important;
}
[data-baseweb="option"] { color: var(--txt) !important; background: transparent !important; font-size: 14px !important; }
[data-baseweb="option"]:hover { background: var(--accent-dim) !important; }
[data-baseweb="tag"] { background: var(--accent-dim) !important; color: var(--accent) !important; }
.stButton button {
  background: var(--accent) !important; color: #fff !important;
  border: none !important; border-radius: 6px !important;
  font-weight: 600 !important; font-size: 15px !important;
  padding: 8px 20px !important;
  transition: background 0.15s, box-shadow 0.15s !important;
}
.stButton button:hover { background: #0055AA !important; box-shadow: 0 2px 10px var(--accent-glo) !important; }
[data-testid="stExpander"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  box-shadow: 0 1px 4px rgba(0,0,0,.04) !important;
}
[data-testid="stExpander"] summary { color: var(--txt-sec) !important; font-size: 14px !important; font-weight: 600 !important; }
[data-testid="stNotification"] { background: var(--bg-surface) !important; border: 1px solid var(--border) !important; }
div[data-testid="stMetricValue"] { color: var(--accent) !important; font-family: var(--ff-num) !important; font-weight: 700 !important; font-size: 28px !important; }
.stRadio div[role="radiogroup"] label span { color: var(--txt) !important; font-size: 14px !important; }
.stCheckbox label span { color: var(--txt) !important; font-size: 14px !important; }
</style>
"""

# ---------------------------------------------------------------------------
# 테이블 전용 CSS (st.html iframe embed — 화이트 테마)
# ---------------------------------------------------------------------------
_TABLE_STYLE = """
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR','Inter',-apple-system,sans-serif;font-size:14px;color:#1A2332;background:#F5F7FA}
.lk-table-wrap{background:#fff;border:1px solid #DDE3ED;border-radius:10px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.06)}
.lk-table{width:100%;border-collapse:collapse;font-size:14px}
.lk-table thead th{background:#F8FAFC;color:#8B9AB5;font-family:'Inter',-apple-system,sans-serif;font-weight:600;font-size:11px;padding:11px 14px;border-bottom:1px solid #DDE3ED;text-align:left;white-space:nowrap;text-transform:uppercase;letter-spacing:.7px}
.lk-table tbody tr{border-bottom:1px solid #EEF1F7;transition:background .1s}
.lk-table tbody tr:hover{background:#F0F6FF}
.lk-table tbody tr:last-child{border-bottom:none}
.lk-table td{padding:13px 14px;vertical-align:middle}
.td-company{min-width:110px}
.company-name{font-size:12px;color:#8B9AB5;display:block;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.td-title{min-width:200px;max-width:380px}
.recruit-name{font-size:14px;font-weight:600;color:#1A2332;display:block;line-height:1.45}
.recruit-name a{color:#1A2332!important;text-decoration:none}
.recruit-name a:hover{color:#0066CC!important}
.recruit-category{font-size:12px;color:#8B9AB5;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:340px;display:block}
.short-info{font-size:12px;color:#4A5568;white-space:nowrap;font-weight:500}
.badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.badge-intern{background:#EFF6FF;color:#1D6BBE}
.badge-entry{background:#F0FDF6;color:#15804D}
.badge-exp{background:#FFFBEB;color:#B45309}
.badge-it{background:#F5F3FF;color:#6D28D9}
.badge-default{background:#F1F5F9;color:#64748B}
.grade-badge{display:inline-block;padding:4px 11px;border-radius:20px;font-size:12px;min-width:36px;text-align:center;font-weight:700;letter-spacing:.3px}
.grade-A{background:#D1FAE5;color:#065F46}
.grade-B{background:#DBEAFE;color:#1E40AF}
.grade-C{background:#FEF3C7;color:#92400E}
.grade-D{background:#FEE2E2;color:#991B1B}
.grade-F{background:#F1F5F9;color:#64748B}
.dday-label{font-size:12px;font-weight:600;white-space:nowrap;font-family:'Inter',-apple-system,sans-serif}
.dday-urgent{color:#DC2626}
.dday-soon{color:#D97706}
.dday-ok{color:#0066CC}
.dday-closed{color:#8B9AB5}
.status-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.status-inbox{background:#F1F5F9;color:#64748B}
.status-applied{background:#EFF6FF;color:#1D6BBE}
.status-passed{background:#D1FAE5;color:#065F46}
.status-rejected{background:#FEE2E2;color:#991B1B}
.lk-log-row{background:#fff;border:1px solid #DDE3ED;border-radius:8px;padding:12px 16px;margin-bottom:6px;display:flex;align-items:center;gap:12px;font-size:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.log-channel{font-family:'Inter',-apple-system,sans-serif;font-weight:600;color:#1A2332;min-width:150px}
.log-count{color:#0066CC;font-weight:700;font-family:'Inter',-apple-system,sans-serif}
.log-time{color:#8B9AB5;margin-left:auto;font-size:12px}
.log-error{color:#DC2626}
</style>
"""

# ---------------------------------------------------------------------------
# 통계 카드 전용 CSS (st.html iframe embed — 화이트 테마)
# ---------------------------------------------------------------------------
_STAT_STYLE = """
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR','Inter',-apple-system,sans-serif;background:#F5F7FA;color:#1A2332}
.lk-stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;padding:4px 0 20px}
.lk-stat-card{background:#fff;border:1px solid #DDE3ED;border-top:3px solid #0066CC;border-radius:10px;padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.05);transition:box-shadow .15s}
.lk-stat-card:hover{box-shadow:0 4px 16px rgba(0,102,204,.12)}
.lk-stat-card.green{border-top-color:#1CA760}
.lk-stat-card.amber{border-top-color:#D97706}
.lk-stat-card.red{border-top-color:#DC2626}
.lk-stat-card.purple{border-top-color:#7C3AED}
.lk-stat-num{font-family:'Inter',-apple-system,sans-serif;font-size:30px;font-weight:700;color:#0066CC;line-height:1;margin-bottom:6px;font-variant-numeric:tabular-nums}
.lk-stat-num.green{color:#1CA760}
.lk-stat-num.amber{color:#D97706}
.lk-stat-num.red{color:#DC2626}
.lk-stat-num.purple{color:#7C3AED}
.lk-stat-num.muted{color:#4A5568}
.lk-stat-label{font-family:'Inter',-apple-system,sans-serif;font-size:11px;color:#8B9AB5;text-transform:uppercase;letter-spacing:.9px;font-weight:600}
@media(max-width:700px){.lk-stat-row{grid-template-columns:repeat(2,1fr)}}
</style>
"""

# ---------------------------------------------------------------------------
# 섹션 타이틀 전용 CSS (st.html iframe embed — 화이트 테마)
# ---------------------------------------------------------------------------
_SECTION_STYLE = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#F5F7FA;color:#1A2332;font-family:'Noto Sans KR','Inter',-apple-system,sans-serif}
.lk-section-title{font-size:13px;font-weight:700;color:#4A5568;text-transform:uppercase;letter-spacing:1.5px;padding:6px 0 10px;border-bottom:2px solid #DDE3ED;display:block;margin:0}
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

    _SECTOR_PILL = {
        "금융":  ("background:#EBF5FF;color:#1A56DB;border:1px solid #93C5FD;", "금융"),
        "공공":  ("background:#F0FDF4;color:#16A34A;border:1px solid #86EFAC;", "공공"),
        "안보":  ("background:#FFF7ED;color:#C2410C;border:1px solid #FDBA74;", "안보"),
        "핀테크": ("background:#FAF5FF;color:#7C3AED;border:1px solid #C4B5FD;", "핀테크"),
        "기타":  ("background:#F9FAFB;color:#6B7280;border:1px solid #D1D5DB;", "기타"),
    }

    rows_html = ""
    for _, row in filtered.iterrows():
        title = safe_str(row.get("title"), 70)
        org = safe_str(row.get("org"), 20)
        url = row.get("source_url", "#") or "#"
        channel = safe_str(row.get("source_channel"), 20)
        location = safe_str(row.get("location"), 12)
        if location == "—":
            location = "전국"
        fit_score = row.get("fit_score")
        score_html = (
            f'<span style="color:#0066CC;font-weight:700;font-family:Inter,sans-serif;">{int(fit_score)}</span>'
            if fit_score is not None and not pd.isna(fit_score)
            else "—"
        )
        sector = row.get("_sector", "기타")
        s_style, s_label = _SECTOR_PILL.get(sector, _SECTOR_PILL["기타"])
        sector_html = f'<span style="font-size:11px;padding:2px 7px;border-radius:9px;font-weight:600;white-space:nowrap;{s_style}">{s_label}</span>'

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
          </td>
          <td style="text-align:center;">{sector_html}</td>
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
            <th style="text-align:center;">섹터</th>
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

    # 섹터별 건수
    _sec = df.apply(
        lambda r: _infer_sector(
            r.get("source_channel", ""), r.get("org", "") or "", r.get("title", "") or ""
        ), axis=1
    )
    finance_cnt = int((_sec == "금융").sum())
    public_cnt  = int((_sec == "공공").sum())
    security_cnt = int((_sec == "안보").sum())

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
          <div class="lk-stat-card">
            <div class="lk-stat-num" style="color:#1A56DB;">{finance_cnt:,}</div>
            <div class="lk-stat-label">🏦 금융</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num green">{public_cnt:,}</div>
            <div class="lk-stat-label">🏛️ 공공</div>
          </div>
          <div class="lk-stat-card">
            <div class="lk-stat-num amber">{security_cnt:,}</div>
            <div class="lk-stat-label">🛡️ 안보</div>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# 탭 렌더러
# ---------------------------------------------------------------------------
def _add_sector_col(df: pd.DataFrame) -> pd.DataFrame:
    """df에 _sector 컬럼 추가 (없으면). render_overview/render_jobs 공용."""
    if "_sector" not in df.columns:
        df = df.copy()
        df["_sector"] = df.apply(
            lambda r: _infer_sector(
                r.get("source_channel", ""),
                r.get("org", "") or "",
                r.get("title", "") or "",
            ),
            axis=1,
        )
    return df


def render_overview(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("아직 수집된 공고가 없습니다. '📡 스캔' 탭에서 수집을 시작하세요.")
        return

    df = _add_sector_col(df)
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
            color_continuous_scale=["#BFDBFE", "#0066CC"],
            template="plotly_white",
            labels={"source_channel": "", "count": "공고 수"},
        )
        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FAFC",
            font=dict(color="#4A5568", size=13),
            xaxis=dict(gridcolor="#EEF1F7", zerolinecolor="#DDE3ED"),
            yaxis=dict(gridcolor="#EEF1F7"),
        )
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)


def render_jobs(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("데이터가 없습니다.")
        return

    # ── 섹터 컬럼 추가 ──────────────────────────────────────────────────────
    df = _add_sector_col(df)

    # ── 섹터 퀵필터 ─────────────────────────────────────────────────────────
    st.html(_SECTION_STYLE + '<div class="lk-section-title">섹터 · 공고 필터</div>')

    SECTOR_ICONS = {
        "전체": "🗂️",
        "금융": "🏦",
        "공공": "🏛️",
        "안보": "🛡️",
        "핀테크": "💳",
        "기타": "📌",
    }
    sector_counts: dict[str, int] = {"전체": len(df)}
    for s in ["금융", "공공", "안보", "핀테크", "기타"]:
        cnt = int((df["_sector"] == s).sum())
        if cnt:
            sector_counts[s] = cnt

    sector_labels = [
        f"{SECTOR_ICONS.get(s, '')} {s} ({c})"
        for s, c in sector_counts.items()
    ]
    sel_sector_label = st.radio(
        "섹터",
        sector_labels,
        horizontal=True,
        label_visibility="collapsed",
    )
    sel_sector = sel_sector_label.split()[1] if sel_sector_label else "전체"

    # ── 상세 필터 바 ─────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

    keyword = col1.text_input("🔍 기업·공고명 검색", "", placeholder="예) 삼성, 인턴, 블록체인")
    sel_grade = col2.multiselect("등급", ["A", "B", "C", "D", "F"], placeholder="전체")
    statuses = sorted(df["status"].dropna().unique().tolist())
    sel_status = col3.multiselect("상태", statuses, placeholder="전체")
    tiers = sorted(df["source_tier"].dropna().unique().tolist())
    sel_tier = col4.multiselect("Tier", tiers, placeholder="전체")

    col5, col6, col7 = st.columns([3, 3, 3])
    only_open = col5.checkbox("마감 임박만 (7일 내)", value=False)
    only_eligible = col6.checkbox("✅ 자격요건 충족만", value=True)
    sort_by = col7.radio("정렬", ["적합도순", "마감순", "최신순"], horizontal=True)

    # 필터 적용
    filtered = df.copy()
    if sel_sector != "전체":
        filtered = filtered[filtered["_sector"] == sel_sector]
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

    # 만료 공고 제외 — DB에는 남기고 대시보드엔 표시 안 함
    _now = datetime.now()

    def _is_expired(deadline: Any) -> bool:
        dt = parse_deadline(deadline)
        return dt is not None and dt < _now

    active = filtered[~filtered["deadline"].apply(_is_expired)].head(200)

    st.html(
        f'<p style="font-family:\'Noto Sans KR\',sans-serif;font-size:14px;color:#8B9AB5;margin:4px 0 8px;">'
        f'<span style="color:#0066CC;font-weight:700;">{len(active):,}건</span>'
        f' 표시 중 / 전체 {len(df):,}건</p>'
    )

    render_job_table(active)

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
          <td><span style="font-weight:700;color:#0066CC;font-family:Inter,sans-serif;">{int(row["누적 공고"])}</span></td>
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
                    f"<span style='font-family:Noto Sans KR,sans-serif;font-weight:700;font-size:15px;color:#1A2332;'>{row['org']}</span> "
                    f"<span style='font-family:Noto Sans KR,sans-serif;color:#4A5568;'>— {row['title'][:60]}</span>"
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@600;700&family=Inter:wght@500;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#F5F7FA}
.lk-header{background:#fff;border-bottom:2px solid #0066CC;padding:14px 28px;display:flex;align-items:center;gap:14px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.lk-logo{font-family:'Inter',-apple-system,sans-serif;font-size:17px;font-weight:700;color:#0066CC;letter-spacing:.5px}
.lk-sub{font-family:'Noto Sans KR',-apple-system,sans-serif;font-size:13px;color:#8B9AB5;font-weight:500}
.lk-dot{width:8px;height:8px;border-radius:50%;display:inline-block;animation:blink 2s ease infinite}
.lk-badge{font-family:'Inter',-apple-system,sans-serif;font-size:11px;font-weight:600;padding:2px 8px;border-radius:20px;background:#EFF6FF;color:#0066CC}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
</style>
"""
    st.html(
        _header_css + f"""
        <div class="lk-header">
          <div class="lk-logo">Career-Ops KR</div>
          <span class="lk-sub">한국 금융 · 블록체인 · 디지털 구직 파이프라인</span>
          <div style="margin-left:auto;display:flex;align-items:center;gap:10px;">
            <div class="lk-dot" style="background:{dot_color};"></div>
            <span class="lk-badge">{db_label}</span>
            <span style="font-family:Inter,sans-serif;font-size:12px;color:#8B9AB5;">{DB_PATH.name}</span>
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

    tabs = st.tabs(["📊 대시보드", "🔍 공고 목록", "🏥 채널 현황", "📋 지원 트래커"])
    with tabs[0]:
        render_overview(df)
    with tabs[1]:
        render_jobs(df)
    with tabs[2]:
        render_channel_health(df, log_df)
    with tabs[3]:
        render_tracker(df)


if __name__ == "__main__":
    main()
