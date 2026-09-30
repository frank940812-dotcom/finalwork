import os
import html
import datetime
import time
from contextlib import contextmanager

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


# =========================================================
# 1. 基本設定
# =========================================================
st.set_page_config(
    page_title="Social Insight｜社群輿情決策中心",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE_URL = "http://127.0.0.1:8000"


# =========================================================
# 2. 色彩設定
# =========================================================
COLOR_MAP = {
    "正面": "#4ECAC2",
    "中立": "#A9BCC6",
    "負面": "#FF8B88",
    "提問": "#73CBE8"
}

TOPIC_BAR_COLORS = [
    "#4ECAC2",
    "#7FD9D2",
    "#9EE6E0",
    "#73CBE8",
    "#A9DDF2",
    "#A7EAE4",
    "#7BC8D8",
    "#B6F1EC",
    "#90D9E8",
    "#D5F7F4"
]


# =========================================================
# 3. 全站樣式（淺 Tiffany 藍）
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --bg-main: #F3FCFB;
        --bg-soft: #E7F9F7;
        --bg-card: #FFFFFF;
        --bg-card-2: #F8FEFD;
        --line: #BFEAE6;
        --line-soft: #DDF4F2;
        --text: #163B47;
        --muted: #557381;
        --primary: #4ECAC2;
        --primary-dark: #1E8D89;
        --primary-soft: #DDF8F5;
        --blue-soft: #DDF3FB;
        --danger: #FF8B88;
        --warning: #F5C56B;
        --shadow: 0 14px 36px rgba(48, 96, 112, .10);
    }

    .stApp {
        background:
            radial-gradient(circle at 0% 0%, rgba(78,202,194,.14), transparent 24%),
            radial-gradient(circle at 100% 0%, rgba(115,203,232,.16), transparent 28%),
            linear-gradient(180deg, #F4FCFB 0%, #EDF9F8 44%, #F7FDFC 100%);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(243,252,251,.82);
        backdrop-filter: blur(14px);
        border-bottom: 1px solid rgba(191,234,230,.70);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #E5FAF7 0%, #DDF7F4 45%, #EEFDFC 100%);
        border-right: 1px solid rgba(191,234,230,.85);
    }

    [data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: var(--text);
    }

    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .st-emotion-cache-16txtl3 {
        color: var(--text) !important;
    }

    .block-container {
        max-width: 1560px;
        padding-top: 1.25rem;
        padding-bottom: 2.6rem;
    }

    .sidebar-brand {
        padding: .45rem .15rem 1rem;
    }

    .sidebar-brand-title {
        color: #12505F !important;
        font-size: 1.12rem;
        font-weight: 900;
        letter-spacing: .05em;
    }

    .sidebar-brand-sub {
        color: #4C6F7C !important;
        font-size: .75rem;
        margin-top: .15rem;
    }

    .mini-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .8rem;
        padding: .62rem .78rem;
        border-radius: 12px;
        background: rgba(255,255,255,.70);
        border: 1px solid rgba(191,234,230,.9);
        margin-bottom: .5rem;
        font-size: .79rem;
        color: #234754;
    }

    .dot-ok {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #2CB7AE;
        box-shadow: 0 0 10px rgba(44,183,174,.45);
        display: inline-block;
        margin-right: .45rem;
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 2rem 2.15rem;
        margin-bottom: 1.2rem;
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(255,255,255,.96), rgba(235,251,248,.98));
        box-shadow: var(--shadow);
    }

    .hero::after {
        content: "";
        position: absolute;
        right: -45px;
        top: -65px;
        width: 230px;
        height: 230px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(78,202,194,.18), transparent 68%);
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        color: #279F9B;
        font-size: .8rem;
        font-weight: 800;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: .68rem;
    }

    .hero-title {
        margin: 0;
        color: #163B47;
        font-size: clamp(2rem, 4vw, 3.2rem);
        font-weight: 900;
        line-height: 1.08;
    }

    .hero-subtitle {
        max-width: 860px;
        color: #4F6E7B;
        font-size: 1rem;
        line-height: 1.8;
        margin-top: .9rem;
        margin-bottom: 0;
    }

    .hero-badges {
        display: flex;
        flex-wrap: wrap;
        gap: .58rem;
        margin-top: 1.2rem;
    }

    .badge {
        border: 1px solid rgba(78,202,194,.38);
        background: rgba(78,202,194,.12);
        color: #1D615E;
        border-radius: 999px;
        padding: .42rem .72rem;
        font-size: .79rem;
        font-weight: 700;
    }

    .section-head {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        margin: 1.8rem 0 .95rem;
    }

    .section-kicker {
        color: #219F9A;
        font-size: .76rem;
        font-weight: 900;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: .24rem;
    }

    .section-title {
        color: #173A46;
        font-size: 1.42rem;
        font-weight: 900;
        margin: 0;
    }

    .section-note {
        color: #63818F;
        font-size: .83rem;
        text-align: right;
    }

    .kpi-card {
        min-height: 142px;
        padding: 1.1rem 1.18rem;
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(246,254,253,.98));
        box-shadow: 0 10px 28px rgba(52, 102, 113, .08);
    }

    .kpi-label {
        color: #4E6A78;
        font-size: .79rem;
        font-weight: 700;
        letter-spacing: .03em;
    }

    .kpi-value {
        color: #173A46;
        font-size: 2rem;
        font-weight: 900;
        margin-top: .42rem;
        line-height: 1.08;
    }

    .kpi-foot {
        color: #6D8792;
        font-size: .76rem;
        margin-top: .62rem;
        line-height: 1.5;
    }

    .kpi-accent-primary { border-top: 4px solid #4ECAC2; }
    .kpi-accent-sky { border-top: 4px solid #73CBE8; }
    .kpi-accent-coral { border-top: 4px solid #FF8B88; }
    .kpi-accent-mint { border-top: 4px solid #6ED9D2; }

    .status-panel {
        min-height: 142px;
        padding: 1.12rem 1.2rem;
        border-radius: 18px;
        border: 1px solid rgba(191,234,230,.95);
        background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(245,253,252,.98));
        box-shadow: 0 10px 28px rgba(52, 102, 113, .08);
    }

    .status-normal { border-left: 5px solid #4ECAC2; }
    .status-warning { border-left: 5px solid #F3BE5A; }
    .status-danger { border-left: 5px solid #FF8B88; }

    .status-title {
        color: #173A46;
        font-weight: 900;
        font-size: 1rem;
    }

    .status-body {
        color: #587583;
        font-size: .82rem;
        line-height: 1.7;
        margin-top: .45rem;
    }

    .glass-card {
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 18px;
        background: rgba(255,255,255,.94);
        padding: 1.15rem;
        box-shadow: 0 10px 28px rgba(52, 102, 113, .08);
    }

    .topic-card {
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 15px;
        background: rgba(252,255,255,.95);
        padding: 1rem 1.05rem;
        margin-bottom: .72rem;
    }

    .topic-name {
        color: #183B46;
        font-weight: 800;
        font-size: .98rem;
    }

    .topic-count {
        color: #259D99;
        font-size: .78rem;
        font-weight: 800;
        margin-top: .12rem;
    }

    .comment-line {
        color: #496674;
        font-size: .84rem;
        line-height: 1.65;
        border-left: 3px solid rgba(78,202,194,.42);
        padding-left: .72rem;
        margin-top: .55rem;
    }

    .empty-state {
        border: 1px dashed rgba(191,234,230,1);
        border-radius: 18px;
        text-align: center;
        padding: 2.5rem 1.2rem;
        color: #5A7784;
        background: rgba(255,255,255,.75);
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 2.85rem;
        border-radius: 12px;
        font-weight: 800;
        border: 1px solid rgba(78,202,194,.38);
        background: #7FE3DD;
        color: #173A46;
        box-shadow: 0 8px 18px rgba(78,202,194,.18);
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: #6AD8D1;
        color: #163B47;
        border: 1px solid rgba(78,202,194,.58);
    }

    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        background: linear-gradient(90deg, #45C7BF, #72D6EB);
        color: #143742;
        border: none;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled {
        background: #DFF4F2 !important;
        color: #7C969F !important;
        border: 1px solid #CDEBE7 !important;
    }

    .stTextInput input,
    .stDateInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: rgba(255,255,255,.92) !important;
        color: #173A46 !important;
        border: 1px solid rgba(191,234,230,.95) !important;
        border-radius: 12px !important;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #7D98A1 !important;
    }

    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        background: rgba(255,255,255,.94) !important;
        color: #173A46 !important;
        border: 1px solid rgba(191,234,230,.95) !important;
        border-radius: 12px !important;
        min-height: 46px;
    }

    .stMultiSelect span[data-baseweb="tag"] {
        background: #DDF8F5 !important;
        border: 1px solid #BDEBE6 !important;
        color: #17414D !important;
    }

    .stSelectbox label,
    .stMultiSelect label,
    .stTextInput label,
    .stDateInput label,
    .stRadio label,
    .stMarkdown,
    label, p, h1, h2, h3, h4, h5, h6 {
        color: #173A46 !important;
    }

    .stRadio [role="radiogroup"] label {
        background: rgba(255,255,255,.74);
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 12px;
        padding: .55rem .75rem;
        margin-bottom: .45rem;
    }

    div[data-testid="stPlotlyChart"] {
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 18px;
        overflow: hidden;
        background: rgba(255,255,255,.82);
        padding: .5rem;
        box-shadow: 0 10px 28px rgba(52, 102, 113, .08);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 16px;
        overflow: hidden;
        background: rgba(255,255,255,.92);
    }

    .stTabs [data-baseweb="tab-list"] {
        position: sticky;
        top: 4.15rem;
        z-index: 900;
        gap: .45rem;
        background: rgba(255,255,255,.92);
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 14px;
        padding: .35rem;
        box-shadow: 0 10px 24px rgba(40, 70, 80, .10);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }

    .stTabs [data-baseweb="tab"] {
        color: #55727F !important;
        border-radius: 10px;
        padding: .58rem 1rem;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background: #DDF8F5 !important;
        color: #173A46 !important;
    }

    [data-testid="stExpander"] {
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 14px;
        background: rgba(255,255,255,.88);
    }

    [data-testid="stAlert"] {
        border-radius: 14px;
    }

    hr {
        border-color: rgba(191,234,230,.75);
    }

    .welcome-panel {
        margin-top: 1.35rem;
        padding: 2rem 2.1rem;
        border: 1px solid var(--line);
        border-radius: 22px;
        background: rgba(255,255,255,.72);
        box-shadow: 0 12px 32px rgba(40,70,80,.06);
    }

    .welcome-kicker { color: var(--primary-dark); font-size: .76rem; font-weight: 900; letter-spacing: .16em; }
    .welcome-title { color: var(--text); font-size: 1.5rem; font-weight: 900; margin-top: .35rem; }
    .welcome-description { color: var(--muted); max-width: 860px; line-height: 1.8; margin-top: .65rem; font-size: .92rem; }
    .welcome-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .9rem; margin-top: 1.4rem; }
    .welcome-item { padding: 1rem 1.05rem; border: 1px solid var(--line); border-radius: 16px; background: rgba(255,255,255,.72); }
    .welcome-number { color: var(--primary-dark); font-size: .72rem; font-weight: 900; letter-spacing: .12em; }
    .welcome-item-title { color: var(--text); font-weight: 900; margin-top: .35rem; }
    .welcome-item-text { color: var(--muted); font-size: .8rem; margin-top: .25rem; }
    .initial-footer { color: var(--muted); text-align: center; font-size: .75rem; padding: 1.6rem 0 .4rem; opacity: .8; }


    /* 執行分析時的置中翻頁動畫 */
    div[data-testid="stSpinner"] {
        position: fixed !important;
        inset: 0 !important;
        z-index: 99999 !important;
        width: 100vw !important;
        height: 100vh !important;
        padding: 0 !important;
        margin: 0 !important;
        background: rgba(24, 30, 34, .22) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stSpinner"] > div {
        position: relative !important;
        width: min(640px, calc(100vw - 40px)) !important;
        min-height: 250px !important;
        padding: 2rem 2.2rem 1.8rem !important;
        margin: 0 !important;
        border: 1px solid var(--line) !important;
        border-radius: 24px !important;
        background: rgba(255,255,255,.97) !important;
        box-shadow: 0 28px 80px rgba(30,50,60,.24) !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
        text-align: center !important;
    }

    div[data-testid="stSpinner"] > div::before {
        content: "AI ANALYSIS IN PROGRESS";
        color: var(--primary-dark);
        font-size: .72rem;
        font-weight: 900;
        letter-spacing: .16em;
        margin-bottom: 1rem;
    }

    div[data-testid="stSpinner"] > div::after {
        content: "";
        width: 76%;
        height: 5px;
        margin-top: 1.3rem;
        border-radius: 999px;
        background:
            linear-gradient(
                90deg,
                var(--primary) 0 28%,
                var(--primary-soft) 28% 100%
            );
        background-size: 260% 100%;
        animation: insight-progress 3.6s ease-in-out infinite;
        box-shadow: 0 5px 16px rgba(30,50,60,.08);
    }

    div[data-testid="stSpinner"] p {
        position: relative !important;
        width: 100% !important;
        min-height: 72px !important;
        margin: 0 !important;
        color: transparent !important;
        font-size: 0 !important;
        line-height: 1.7 !important;
        overflow: hidden !important;
    }

    div[data-testid="stSpinner"] p::before,
    div[data-testid="stSpinner"] p::after {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        color: var(--text);
        font-size: 1.18rem;
        font-weight: 900;
        line-height: 1.55;
        text-align: center;
        backface-visibility: hidden;
        transform-origin: center bottom;
    }

    div[data-testid="stSpinner"] p::before {
        content: "正在抓取留言與整理原始資料";
        animation: insight-flip-a 9s infinite;
    }

    div[data-testid="stSpinner"] p::after {
        content: "正在執行情緒辨識與主題分析";
        animation: insight-flip-b 9s infinite;
    }

    div[data-testid="stSpinner"] svg {
        width: 46px !important;
        height: 46px !important;
        color: var(--primary) !important;
        margin-bottom: 1rem !important;
        animation: insight-pulse 1.2s ease-in-out infinite !important;
    }

    @keyframes insight-flip-a {
        0%, 28% {
            opacity: 1;
            transform: perspective(500px) rotateX(0deg) translateY(0);
        }
        34%, 61% {
            opacity: 0;
            transform: perspective(500px) rotateX(-92deg) translateY(-10px);
        }
        67%, 94% {
            opacity: 1;
            content: "正在建立圖表與產生分析報告";
            transform: perspective(500px) rotateX(0deg) translateY(0);
        }
        100% {
            opacity: 0;
            transform: perspective(500px) rotateX(92deg) translateY(10px);
        }
    }

    @keyframes insight-flip-b {
        0%, 28% {
            opacity: 0;
            transform: perspective(500px) rotateX(92deg) translateY(10px);
        }
        34%, 61% {
            opacity: 1;
            transform: perspective(500px) rotateX(0deg) translateY(0);
        }
        67%, 100% {
            opacity: 0;
            transform: perspective(500px) rotateX(-92deg) translateY(-10px);
        }
    }

    @keyframes insight-progress {
        0%   { background-position: 100% 0; }
        50%  { background-position: 15% 0; }
        100% { background-position: -80% 0; }
    }

    @keyframes insight-pulse {
        0%, 100% { transform: scale(.92); opacity: .65; }
        50%      { transform: scale(1.08); opacity: 1; }
    }


    /* 真正可播放的分析動畫遮罩 */
    .analysis-overlay {
        position: fixed;
        inset: 0;
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(24, 30, 34, .22);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }

    .analysis-card {
        width: min(640px, calc(100vw - 40px));
        min-height: 260px;
        padding: 2rem 2.2rem 1.8rem;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: rgba(255,255,255,.98);
        box-shadow: 0 28px 80px rgba(30,50,60,.24);
        text-align: center;
        overflow: hidden;
    }

    .analysis-kicker {
        color: var(--primary-dark);
        font-size: .72rem;
        font-weight: 900;
        letter-spacing: .16em;
        margin-bottom: 1.15rem;
    }

    .analysis-icon {
        width: 58px;
        height: 58px;
        margin: 0 auto 1.1rem;
        border-radius: 50%;
        border: 6px solid var(--primary-soft);
        border-top-color: var(--primary);
        animation: analysis-spin 1s linear infinite;
    }

    .analysis-stage {
        position: relative;
        min-height: 84px;
        perspective: 700px;
    }

    .analysis-stage-item {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text);
        font-size: 1.18rem;
        font-weight: 900;
        line-height: 1.55;
        opacity: 0;
        backface-visibility: hidden;
        transform-origin: center bottom;
    }

    .analysis-stage-item:nth-child(1) { animation: analysis-page-one 9s infinite; }
    .analysis-stage-item:nth-child(2) { animation: analysis-page-two 9s infinite; }
    .analysis-stage-item:nth-child(3) { animation: analysis-page-three 9s infinite; }

    .analysis-progress {
        width: 78%;
        height: 6px;
        margin: 1.25rem auto 0;
        border-radius: 999px;
        background: var(--primary-soft);
        overflow: hidden;
    }

    .analysis-progress::after {
        content: "";
        display: block;
        width: 42%;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--primary), var(--primary-dark));
        animation: analysis-progress-move 1.8s ease-in-out infinite;
    }

    .analysis-hint {
        color: var(--muted);
        font-size: .82rem;
        margin-top: .9rem;
    }

    @keyframes analysis-spin {
        to { transform: rotate(360deg); }
    }

    @keyframes analysis-page-one {
        0%, 26% { opacity: 1; transform: rotateX(0deg) translateY(0); }
        31%, 100% { opacity: 0; transform: rotateX(-90deg) translateY(-12px); }
    }

    @keyframes analysis-page-two {
        0%, 28% { opacity: 0; transform: rotateX(90deg) translateY(12px); }
        34%, 59% { opacity: 1; transform: rotateX(0deg) translateY(0); }
        64%, 100% { opacity: 0; transform: rotateX(-90deg) translateY(-12px); }
    }

    @keyframes analysis-page-three {
        0%, 61% { opacity: 0; transform: rotateX(90deg) translateY(12px); }
        67%, 93% { opacity: 1; transform: rotateX(0deg) translateY(0); }
        100% { opacity: 0; transform: rotateX(-90deg) translateY(-12px); }
    }

    @keyframes analysis-progress-move {
        0% { transform: translateX(-115%); }
        50% { transform: translateX(85%); }
        100% { transform: translateX(235%); }
    }

    .task-panel {
        margin: 1.15rem auto 1.4rem;
        padding: 1.3rem 1.4rem .55rem;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: rgba(255,255,255,.86);
        box-shadow: 0 12px 30px rgba(40,70,80,.07);
    }

    .task-panel-kicker {
        color: var(--primary-dark);
        font-size: .73rem;
        font-weight: 900;
        letter-spacing: .15em;
        text-transform: uppercase;
        margin-bottom: .2rem;
    }

    .task-panel-title {
        color: var(--text);
        font-size: 1.28rem;
        font-weight: 900;
        margin-bottom: .75rem;
    }


    .history-hero {
        padding: 1.9rem 2rem;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: rgba(255,255,255,.94);
        box-shadow: var(--shadow);
        margin-bottom: 1.25rem;
    }

    .history-card {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255,255,255,.94);
        padding: 1.1rem 1.2rem;
        margin-bottom: .8rem;
        box-shadow: 0 10px 26px rgba(40,70,80,.07);
    }

    .history-meta {
        color: var(--muted);
        font-size: .8rem;
        line-height: 1.7;
        margin-top: .4rem;
    }

    .history-title {
        color: var(--text);
        font-size: 1rem;
        font-weight: 900;
        word-break: break-word;
    }

    .history-platform-pill {
        display: inline-block;
        padding: .28rem .58rem;
        border-radius: 999px;
        background: #F0F0F0;
        color: #222222;
        font-size: .72rem;
        font-weight: 900;
        margin-bottom: .55rem;
    }

    .history-neutral .stApp {
        background: linear-gradient(180deg, #FFFFFF 0%, #F6F6F6 100%) !important;
        color: #111111 !important;
    }

    .history-neutral [data-testid="stHeader"] {
        background: rgba(255,255,255,.92) !important;
        border-bottom: 1px solid #DDDDDD !important;
    }

    .history-neutral [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F2F2F2 100%) !important;
        border-right: 1px solid #DDDDDD !important;
    }

    .history-neutral [data-testid="stSidebar"] * {
        color: #111111 !important;
    }

    .history-neutral .history-hero,
    .history-neutral .history-card,
    .history-neutral .glass-card,
    .history-neutral .kpi-card,
    .history-neutral div[data-testid="stDataFrame"] {
        border-color: #D8D8D8 !important;
        background: #FFFFFF !important;
        box-shadow: 0 10px 26px rgba(0,0,0,.05) !important;
    }

    .history-neutral .hero-title,
    .history-neutral .hero-subtitle,
    .history-neutral .section-title,
    .history-neutral .section-note,
    .history-neutral .history-title,
    .history-neutral .history-meta,
    .history-neutral .kpi-label,
    .history-neutral .kpi-value,
    .history-neutral .kpi-foot {
        color: #111111 !important;
    }


    .auth-card {
        padding: 1rem 1rem .95rem;
        border: 1px solid rgba(191,234,230,.95);
        border-radius: 16px;
        background: rgba(255,255,255,.78);
        margin-bottom: .9rem;
    }

    .auth-user {
        font-weight: 900;
        font-size: .92rem;
        margin-bottom: .2rem;
    }

    .auth-note {
        font-size: .75rem;
        color: var(--muted);
        line-height: 1.55;
    }


    /* 專業主題洞察模組 */
    .topic-summary-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .8rem;
        margin: .35rem 0 1.15rem;
    }

    .topic-summary-card {
        padding: 1rem 1.05rem;
        border: 1px solid var(--line);
        border-radius: 16px;
        background: rgba(255,255,255,.94);
        box-shadow: 0 9px 24px rgba(40,70,80,.07);
    }

    .topic-summary-label {
        color: var(--muted);
        font-size: .75rem;
        font-weight: 800;
    }

    .topic-summary-value {
        color: var(--text);
        font-size: 1.28rem;
        font-weight: 900;
        margin-top: .28rem;
        line-height: 1.35;
    }

    .topic-summary-foot {
        color: var(--muted);
        font-size: .72rem;
        margin-top: .32rem;
        line-height: 1.45;
    }

    .topic-insight-box {
        padding: 1.05rem 1.15rem;
        margin: .5rem 0 1rem;
        border-left: 5px solid var(--primary);
        border-radius: 14px;
        background: var(--primary-soft);
        color: var(--text);
        line-height: 1.75;
        font-size: .88rem;
    }

    @media (max-width: 900px) {
        .hero {
            padding: 1.45rem 1.2rem;
        }

        .section-note {
            display: none;
        }

        .welcome-grid {
            grid-template-columns: 1fr;
        }

        .stTabs [data-baseweb="tab-list"] {
            top: 3.65rem;
            overflow-x: auto;
            flex-wrap: nowrap;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 4. Session State
# =========================================================
DEFAULT_STATES = {
    "searched_videos": None,
    "dcard_articles": None,
    "dcard_search_message": None,
    "selected_dcard_article": None,
    "crawled_data": None,
    "topic_chart_html": None,
    "active_video_id": None,
    "active_target_label": None,
    "word_report_path": None,
    "last_analysis_time": None,
    "current_view": "analysis",
    "history_platform": "YouTube",
    "history_selected_id": None,
    "auth_token": None,
    "current_user": None,
    "auth_mode": "登入",
    "verification_sent_email": None,
    "platform_results": {
        "YouTube": None,
        "Dcard": None,
        "Instagram": None
    }
}

for key, value in DEFAULT_STATES.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 5. 共用函式
# =========================================================
def resolve_output_path(file_path):
    if not file_path:
        return None

    file_path = str(file_path)
    possible_paths = [
        file_path,
        os.path.join(CURRENT_DIR, file_path),
        os.path.join(CURRENT_DIR, "outputs", file_path),
        os.path.join(CURRENT_DIR, "outputs", os.path.basename(file_path))
    ]

    for path in possible_paths:
        absolute_path = os.path.abspath(path)
        if os.path.exists(absolute_path):
            return absolute_path

    return os.path.abspath(
        os.path.join(CURRENT_DIR, "outputs", os.path.basename(file_path))
    )


def restore_platform_result(selected_platform):
    result = st.session_state.platform_results.get(
        selected_platform
    )

    if result:
        st.session_state.crawled_data = result.get("crawled_data")
        st.session_state.topic_chart_html = result.get("topic_chart_html")
        st.session_state.active_video_id = result.get("active_video_id")
        st.session_state.active_target_label = result.get("active_target_label")
        st.session_state.word_report_path = result.get("word_report_path")
        st.session_state.last_analysis_time = result.get("last_analysis_time")
    else:
        st.session_state.crawled_data = None
        st.session_state.topic_chart_html = None
        st.session_state.active_video_id = None
        st.session_state.active_target_label = None
        st.session_state.word_report_path = None
        st.session_state.last_analysis_time = None


def save_pipeline_result(
    result_data,
    active_video,
    target_label=None,
    platform_name=None
):
    final_csv_path = resolve_output_path(
        result_data.get("final_csv")
    )

    if not final_csv_path or not os.path.exists(
        final_csv_path
    ):
        raise FileNotFoundError(
            f"找不到後端產生的 CSV：{final_csv_path}"
        )

    loaded_dataframe = pd.read_csv(
        final_csv_path,
        encoding="utf-8-sig"
    )

    completed_time = datetime.datetime.now()
    resolved_platform = (
        platform_name
        or result_data.get("platform")
        or platform
    )

    platform_result = {
        "crawled_data": loaded_dataframe,
        "topic_chart_html": result_data.get("topic_chart"),
        "active_video_id": active_video,
        "active_target_label": target_label or active_video,
        "word_report_path": result_data.get("word_report"),
        "last_analysis_time": completed_time
    }

    st.session_state.platform_results[
        resolved_platform
    ] = platform_result

    st.session_state.crawled_data = loaded_dataframe
    st.session_state.topic_chart_html = platform_result[
        "topic_chart_html"
    ]
    st.session_state.word_report_path = platform_result[
        "word_report_path"
    ]
    st.session_state.active_video_id = platform_result[
        "active_video_id"
    ]
    st.session_state.active_target_label = platform_result[
        "active_target_label"
    ]
    st.session_state.last_analysis_time = completed_time


def get_auth_headers():
    token = st.session_state.get(
        "auth_token"
    )

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }


def call_send_verification(username):
    response = requests.post(
        f"{API_BASE_URL}/api/auth/send-verification",
        json={
            "username": username
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.json().get(
                "detail",
                response.text
            )
        )

    return response.json()


def call_register(
    username,
    password,
    verification_code
):
    response = requests.post(
        f"{API_BASE_URL}/api/auth/register",
        json={
            "username": username,
            "password": password,
            "verification_code": verification_code
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.json().get(
                "detail",
                response.text
            )
        )

    return response.json()


def call_login(username, password):
    response = requests.post(
        f"{API_BASE_URL}/api/auth/login",
        json={
            "username": username,
            "password": password
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.json().get(
                "detail",
                response.text
            )
        )

    return response.json()


def call_logout():
    response = requests.post(
        f"{API_BASE_URL}/api/auth/logout",
        headers=get_auth_headers(),
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.json().get(
                "detail",
                response.text
            )
        )

    return response.json()


def call_me():
    response = requests.get(
        f"{API_BASE_URL}/api/auth/me",
        headers=get_auth_headers(),
        timeout=30
    )

    if response.status_code != 200:
        return None

    return response.json().get(
        "user"
    )


def call_pipeline(video_url):
    response = requests.post(
        f"{API_BASE_URL}/api/run_pipeline",
        json={"url": video_url},
        headers=get_auth_headers(),
        timeout=600
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    return response.json()


def call_dcard_pipeline(article):
    response = requests.post(
        f"{API_BASE_URL}/api/dcard/analyze_article",
        json={
            "article_id": str(article.get("id", "")),
            "title": str(article.get("title", "")),
            "url": str(article.get("url", ""))
        },
        headers=get_auth_headers(),
        timeout=600
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    return response.json()



def call_instagram_url_pipeline(reel_url):
    response = requests.post(
        f"{API_BASE_URL}/api/instagram/analyze_reel",
        json={
            "reel_id": "",
            "url": reel_url,
            "caption": ""
        },
        headers=get_auth_headers(),
        timeout=600
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.text
        )

    return response.json()


def fetch_history(platform_name):
    response = requests.get(
        f"{API_BASE_URL}/api/history",
        params={
            "platform": platform_name,
            "limit": 100
        },
        headers=get_auth_headers(),
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.text
        )

    return response.json().get(
        "history",
        []
    )


def fetch_history_detail(analysis_id):
    response = requests.get(
        f"{API_BASE_URL}/api/history/{analysis_id}",
        headers=get_auth_headers(),
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            response.text
        )

    return response.json().get(
        "history"
    )


@contextmanager
def analysis_progress(platform_name):
    placeholder = st.empty()
    platform_label = html.escape(str(platform_name))
    placeholder.markdown(
        f"""
        <div class="analysis-overlay">
            <div class="analysis-card">
                <div class="analysis-kicker">{platform_label.upper()} · AI ANALYSIS</div>
                <div class="analysis-icon"></div>
                <div class="analysis-stage">
                    <div class="analysis-stage-item">正在抓取留言與整理原始資料</div>
                    <div class="analysis-stage-item">正在執行情緒辨識與主題分析</div>
                    <div class="analysis-stage-item">正在建立圖表與產生分析報告</div>
                </div>
                <div class="analysis-progress"></div>
                <div class="analysis-hint">請稍候，系統正在處理完整分析流程</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    try:
        yield
    finally:
        placeholder.empty()


def show_analysis_complete(message="分析完成，正在載入結果"):
    complete_box = st.empty()
    complete_box.markdown(
        f"""
        <div style="
            position:fixed;
            inset:0;
            z-index:99999;
            background:rgba(24,30,34,.18);
            backdrop-filter:blur(7px);
            display:flex;
            align-items:center;
            justify-content:center;
        ">
            <div style="
                width:min(560px,calc(100vw - 40px));
                padding:2rem;
                border:1px solid var(--line);
                border-radius:24px;
                background:rgba(255,255,255,.98);
                box-shadow:0 28px 80px rgba(30,50,60,.22);
                text-align:center;
            ">
                <div style="
                    width:64px;
                    height:64px;
                    margin:0 auto 1rem;
                    border-radius:50%;
                    background:var(--primary-soft);
                    color:var(--primary-dark);
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:2rem;
                    font-weight:900;
                ">✓</div>
                <div style="
                    color:var(--text);
                    font-size:1.25rem;
                    font-weight:900;
                ">{html.escape(str(message))}</div>
                <div style="
                    color:var(--muted);
                    margin-top:.5rem;
                    font-size:.88rem;
                ">分析結果已準備完成</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    time.sleep(0.9)
    complete_box.empty()


def get_risk_info(negative_rate):
    if negative_rate > 30:
        return {
            "label": "危機型預警",
            "class": "status-danger",
            "color": "#FF8B88",
            "description": (
                "負面聲量已超過 30%，建議立即檢視高互動負評、主要負面主題，並啟動回應流程。"
            )
        }

    if negative_rate > 15:
        return {
            "label": "輕度風險",
            "class": "status-warning",
            "color": "#F3BE5A",
            "description": (
                "負面聲量已進入觀察區間，建議持續追蹤主要議題變化，並準備常見問題回覆方向。"
            )
        }

    return {
        "label": "輿情正常",
        "class": "status-normal",
        "color": "#4ECAC2",
        "description": (
            "目前未偵測到明顯危機訊號，整體情緒結構穩定，可持續觀察新出現的議題。"
        )
    }


def render_kpi_card(label, value, foot, accent_class):
    st.markdown(
        f"""
        <div class="kpi-card kpi-accent-{accent_class}">
            <div class="kpi-label">{html.escape(str(label))}</div>
            <div class="kpi-value">{html.escape(str(value))}</div>
            <div class="kpi-foot">{html.escape(str(foot))}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(kicker, title, note=""):
    st.markdown(
        f"""
        <div class="section-head">
            <div>
                <div class="section-kicker">{html.escape(kicker)}</div>
                <div class="section-title">{html.escape(title)}</div>
            </div>
            <div class="section-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )



@st.dialog("Dcard 搜尋提示")
def show_dcard_search_dialog(
    title,
    message,
    keyword="",
    is_error=False
):
    icon = "⚠️" if is_error else "🔎"

    dialog_html = f"""<div style="text-align:center;padding:.5rem .25rem .15rem;">
<div style="font-size:3.3rem;line-height:1;margin-bottom:.9rem;">{icon}</div>
<div style="font-size:1.5rem;font-weight:900;color:var(--text);margin-bottom:.65rem;">{html.escape(str(title))}</div>
<div style="color:var(--muted);font-size:.96rem;line-height:1.85;max-width:470px;margin:0 auto;">{html.escape(str(message))}</div>
</div>"""

    st.markdown(
        dialog_html,
        unsafe_allow_html=True
    )

    if keyword:
        keyword_html = f"""<div style="margin:1.05rem auto .35rem;max-width:430px;padding:.78rem .95rem;border-radius:13px;background:var(--primary-soft);border:1px solid var(--line);text-align:center;color:var(--text);font-size:.86rem;">
本次搜尋關鍵字：<b>{html.escape(str(keyword))}</b>
</div>"""

        st.markdown(
            keyword_html,
            unsafe_allow_html=True
        )

    st.markdown(
        "<div style='height:.3rem'></div>",
        unsafe_allow_html=True
    )

    if st.button(
        "知道了，重新搜尋",
        type="primary",
        use_container_width=True,
        key="close_dcard_search_dialog"
    ):
        st.rerun()



def chart_layout(title=None, height=420, showlegend=True):
    return dict(
        title=dict(text=title, font=dict(size=21, color="#173A46")) if title else None,
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F7FCFB",
        font=dict(family="Microsoft JhengHei, Arial", color="#173A46", size=14),
        margin=dict(l=40, r=30, t=70, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#DDF1EF",
            zeroline=False,
            linecolor="#D0ECE9"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#DDF1EF",
            zeroline=False,
            linecolor="#D0ECE9"
        ),
        showlegend=showlegend
    )


def get_topic_and_comment_columns(dataframe):
    topic_column = "topic_name" if "topic_name" in dataframe.columns else ("topic" if "topic" in dataframe.columns else None)
    comment_column = "comment" if "comment" in dataframe.columns else ("jieba_cut" if "jieba_cut" in dataframe.columns else None)
    return topic_column, comment_column


def make_styled_table(dataframe):
    if dataframe.empty:
        return dataframe

    styled = (
        dataframe.style
        .set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("background-color", "#DDF8F5"),
                    ("color", "#173A46"),
                    ("font-weight", "700"),
                    ("border", "1px solid #C9EEEA")
                ]
            },
            {
                "selector": "td",
                "props": [
                    ("background-color", "#FBFEFE"),
                    ("color", "#173A46"),
                    ("border", "1px solid #E5F5F3")
                ]
            }
        ])
        .set_properties(**{
            "font-size": "14px",
            "padding": "8px",
            "text-align": "left"
        })
    )
    return styled



# =========================================================
# 5-1. 平台動態主題
# =========================================================
PLATFORM_THEMES = {
    "Dcard": {
        "theme_name": "Tiffany Blue",
        "bg_start": "#F4FCFB",
        "bg_mid": "#EDF9F8",
        "bg_end": "#F7FDFC",
        "sidebar_start": "#E5FAF7",
        "sidebar_mid": "#DDF7F4",
        "sidebar_end": "#EEFDFC",
        "header": "rgba(243,252,251,.84)",
        "primary": "#4ECAC2",
        "primary_dark": "#1E8D89",
        "primary_soft": "#DDF8F5",
        "secondary": "#73CBE8",
        "line": "#BFEAE6",
        "hero_tint": "#EBFBF8",
        "button_start": "#45C7BF",
        "button_end": "#72D6EB",
        "button_normal": "#7FE3DD",
        "button_hover": "#6AD8D1",
        "accent_rgb": "78,202,194",
        "secondary_rgb": "115,203,232",
        "text": "#163B47",
        "muted": "#557381",
        "kicker": "#219F9A",
        "badge_text": "#1D615E",
        "card_tint": "#F6FEFD"
    },
    "YouTube": {
        "theme_name": "Soft Red",
        "bg_start": "#FFF9F9",
        "bg_mid": "#FFF2F2",
        "bg_end": "#FFFBFB",
        "sidebar_start": "#FFF0F0",
        "sidebar_mid": "#FFE7E7",
        "sidebar_end": "#FFF7F7",
        "header": "rgba(255,249,249,.86)",
        "primary": "#F06F75",
        "primary_dark": "#C94B52",
        "primary_soft": "#FFE5E7",
        "secondary": "#F6A3A8",
        "line": "#F3C7CA",
        "hero_tint": "#FFF1F2",
        "button_start": "#ED6C73",
        "button_end": "#F49AA0",
        "button_normal": "#F7A7AC",
        "button_hover": "#F18D94",
        "accent_rgb": "240,111,117",
        "secondary_rgb": "246,163,168",
        "text": "#4A2528",
        "muted": "#7C565A",
        "kicker": "#D85D64",
        "badge_text": "#8E3D43",
        "card_tint": "#FFF8F8"
    },
    "Instagram": {
        "theme_name": "Soft Yellow",
        "bg_start": "#FFFDF6",
        "bg_mid": "#FFF8E6",
        "bg_end": "#FFFCF4",
        "sidebar_start": "#FFF8DF",
        "sidebar_mid": "#FFF1C7",
        "sidebar_end": "#FFFBEC",
        "header": "rgba(255,253,246,.86)",
        "primary": "#E6B94F",
        "primary_dark": "#B9851D",
        "primary_soft": "#FFF1C6",
        "secondary": "#F3D47A",
        "line": "#EFDDAA",
        "hero_tint": "#FFF8E2",
        "button_start": "#E6B94F",
        "button_end": "#F3D47A",
        "button_normal": "#F2CF76",
        "button_hover": "#E9BF55",
        "accent_rgb": "230,185,79",
        "secondary_rgb": "243,212,122",
        "text": "#4A3A1D",
        "muted": "#796947",
        "kicker": "#C5962C",
        "badge_text": "#7A5A14",
        "card_tint": "#FFFDF7"
    }
}


def apply_platform_theme(selected_platform):
    theme = PLATFORM_THEMES[selected_platform]

    st.markdown(
        f"""
        <style>
        :root {{
            --bg-main: {theme["bg_start"]};
            --bg-soft: {theme["primary_soft"]};
            --bg-card: #FFFFFF;
            --bg-card-2: {theme["card_tint"]};
            --line: {theme["line"]};
            --line-soft: {theme["line"]};
            --text: {theme["text"]};
            --muted: {theme["muted"]};
            --primary: {theme["primary"]};
            --primary-dark: {theme["primary_dark"]};
            --primary-soft: {theme["primary_soft"]};
        }}

        .stApp {{
            background:
                radial-gradient(circle at 0% 0%, rgba({theme["accent_rgb"]},.14), transparent 24%),
                radial-gradient(circle at 100% 0%, rgba({theme["secondary_rgb"]},.16), transparent 28%),
                linear-gradient(180deg, {theme["bg_start"]} 0%, {theme["bg_mid"]} 44%, {theme["bg_end"]} 100%) !important;
            color: {theme["text"]} !important;
        }}

        [data-testid="stHeader"] {{
            background: {theme["header"]} !important;
            border-bottom: 1px solid {theme["line"]} !important;
        }}

        [data-testid="stSidebar"] {{
            background:
                linear-gradient(180deg, {theme["sidebar_start"]} 0%, {theme["sidebar_mid"]} 45%, {theme["sidebar_end"]} 100%) !important;
            border-right: 1px solid {theme["line"]} !important;
        }}

        [data-testid="stSidebar"] * {{
            color: {theme["text"]} !important;
        }}

        .sidebar-brand-title,
        .hero-title,
        .section-title,
        .kpi-value,
        .status-title,
        .topic-name {{
            color: {theme["text"]} !important;
        }}

        .sidebar-brand-sub,
        .hero-subtitle,
        .section-note,
        .kpi-label,
        .kpi-foot,
        .status-body,
        .comment-line {{
            color: {theme["muted"]} !important;
        }}

        .hero {{
            border-color: {theme["line"]} !important;
            background:
                linear-gradient(135deg, rgba(255,255,255,.97), {theme["hero_tint"]}) !important;
            box-shadow: 0 14px 36px rgba({theme["accent_rgb"]},.12) !important;
        }}

        .hero::after {{
            background:
                radial-gradient(circle, rgba({theme["accent_rgb"]},.19), transparent 68%) !important;
        }}

        .eyebrow,
        .section-kicker,
        .topic-count {{
            color: {theme["kicker"]} !important;
        }}

        .badge {{
            border-color: rgba({theme["accent_rgb"]},.38) !important;
            background: rgba({theme["accent_rgb"]},.12) !important;
            color: {theme["badge_text"]} !important;
        }}

        .mini-status,
        .glass-card,
        .topic-card,
        .kpi-card,
        .status-panel,
        .empty-state,
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"],
        .stTabs [data-baseweb="tab-list"],
        [data-testid="stExpander"] {{
            border-color: {theme["line"]} !important;
        }}

        .kpi-card,
        .status-panel {{
            background:
                linear-gradient(180deg, rgba(255,255,255,.98), {theme["card_tint"]}) !important;
        }}

        .dot-ok {{
            background: {theme["primary"]} !important;
            box-shadow: 0 0 10px rgba({theme["accent_rgb"]},.45) !important;
        }}

        .stButton > button,
        .stDownloadButton > button {{
            background: {theme["button_normal"]} !important;
            border-color: rgba({theme["accent_rgb"]},.42) !important;
            color: {theme["text"]} !important;
            box-shadow: 0 8px 18px rgba({theme["accent_rgb"]},.18) !important;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            background: {theme["button_hover"]} !important;
            border-color: rgba({theme["accent_rgb"]},.62) !important;
            color: {theme["text"]} !important;
        }}

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {{
            background:
                linear-gradient(90deg, {theme["button_start"]}, {theme["button_end"]}) !important;
            color: {theme["text"]} !important;
            border: none !important;
        }}

        .stTextInput input,
        .stDateInput input,
        .stNumberInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {{
            border-color: {theme["line"]} !important;
            color: {theme["text"]} !important;
        }}

        .stMultiSelect span[data-baseweb="tag"],
        .stTabs [aria-selected="true"] {{
            background: {theme["primary_soft"]} !important;
            border-color: {theme["line"]} !important;
            color: {theme["text"]} !important;
        }}

        .stRadio [role="radiogroup"] label {{
            border-color: {theme["line"]} !important;
        }}

        hr {{
            border-color: {theme["line"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    return theme


# =========================================================
# 6. 側邊欄
# =========================================================
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">◈ SOCIAL INSIGHT</div>
        <div class="sidebar-brand-sub">
            AI-powered public opinion intelligence
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 帳號登入 / 註冊 / 登出
# =========================================================
if st.session_state.auth_token and not st.session_state.current_user:
    try:
        st.session_state.current_user = call_me()

        if st.session_state.current_user is None:
            st.session_state.auth_token = None

    except Exception:
        st.session_state.auth_token = None
        st.session_state.current_user = None


if st.session_state.current_user:
    username = st.session_state.current_user.get(
        "username",
        "使用者"
    )

    st.sidebar.markdown(
        f"""
        <div class="auth-card">
            <div class="auth-user">已登入：{html.escape(str(username))}</div>
            <div class="auth-note">
                你的分析會自動保存到個人歷史紀錄。
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.sidebar.button(
        "登出",
        use_container_width=True,
        key="logout_button"
    ):
        try:
            call_logout()
        except Exception:
            pass

        st.session_state.auth_token = None
        st.session_state.current_user = None
        st.session_state.current_view = "analysis"
        st.session_state.history_selected_id = None
        st.rerun()

else:
    with st.sidebar.expander(
        "登入 / 註冊",
        expanded=False
    ):
        auth_mode = st.radio(
            "帳號功能",
            ["登入", "註冊"],
            horizontal=True,
            key="auth_mode_selector"
        )

        auth_username = st.text_input(
            "Gmail 帳號",
            placeholder="example@gmail.com",
            key="auth_username"
        )

        auth_password = st.text_input(
            "密碼",
            type="password",
            placeholder="至少 6 位字元",
            key="auth_password"
        )

        gmail_value = auth_username.strip().lower()

        if auth_mode == "登入":
            if st.button(
                "登入",
                type="primary",
                use_container_width=True,
                key="auth_login_submit"
            ):
                try:
                    if not gmail_value.endswith(
                        "@gmail.com"
                    ):
                        raise ValueError(
                            "請使用 Gmail 信箱，例如：example@gmail.com"
                        )

                    if len(auth_password) < 6:
                        raise ValueError(
                            "密碼至少需要 6 位字元。"
                        )

                    auth_result = call_login(
                        gmail_value,
                        auth_password
                    )

                    st.session_state.auth_token = (
                        auth_result.get("token")
                    )

                    st.session_state.current_user = (
                        auth_result.get("user")
                    )

                    st.success("登入成功。")
                    st.rerun()

                except Exception as error:
                    st.error(str(error))

        else:
            st.caption(
                "註冊需要先取得寄到 Gmail 的 6 位數驗證碼。"
            )

            if st.button(
                "取得 6 位數驗證碼",
                use_container_width=True,
                key="send_verification_code"
            ):
                try:
                    if not gmail_value.endswith(
                        "@gmail.com"
                    ):
                        raise ValueError(
                            "請先輸入有效的 Gmail。"
                        )

                    if len(auth_password) < 6:
                        raise ValueError(
                            "密碼至少需要 6 位字元。"
                        )

                    result = call_send_verification(
                        gmail_value
                    )

                    st.session_state.verification_sent_email = (
                        gmail_value
                    )

                    st.success(
                        result.get(
                            "message",
                            "驗證碼已寄出。"
                        )
                    )

                except Exception as error:
                    st.error(str(error))

            verification_code = st.text_input(
                "6 位數驗證碼",
                max_chars=6,
                placeholder="例如：384271",
                key="verification_code"
            )

            if (
                st.session_state.verification_sent_email
                == gmail_value
            ):
                st.caption(
                    "驗證碼已寄送；10 分鐘內有效。"
                )

            if st.button(
                "驗證並建立帳號",
                type="primary",
                use_container_width=True,
                key="auth_register_submit"
            ):
                try:
                    if not gmail_value.endswith(
                        "@gmail.com"
                    ):
                        raise ValueError(
                            "請使用 Gmail 信箱，例如：example@gmail.com"
                        )

                    if len(auth_password) < 6:
                        raise ValueError(
                            "密碼至少需要 6 位字元。"
                        )

                    if (
                        len(verification_code) != 6
                        or not verification_code.isdigit()
                    ):
                        raise ValueError(
                            "請輸入寄到 Gmail 的 6 位數驗證碼。"
                        )

                    auth_result = call_register(
                        gmail_value,
                        auth_password,
                        verification_code
                    )

                    st.session_state.auth_token = (
                        auth_result.get("token")
                    )

                    st.session_state.current_user = (
                        auth_result.get("user")
                    )

                    st.session_state.verification_sent_email = None

                    st.success(
                        "驗證成功，帳號已建立並自動登入。"
                    )

                    st.rerun()

                except Exception as error:
                    st.error(str(error))

    st.sidebar.caption(
        "未登入也可以分析，但不會保存歷史紀錄。"
    )

# =========================================================
# 6-0. 主介面 / 歷史紀錄中心切換
# =========================================================
if st.session_state.current_view == "analysis":
    history_button_disabled = (
        st.session_state.current_user is None
    )

    if st.sidebar.button(
        "查看歷史紀錄",
        use_container_width=True,
        key="open_history_center",
        disabled=history_button_disabled
    ):
        st.session_state.current_view = "history"
        st.session_state.history_selected_id = None
        st.rerun()

    if history_button_disabled:
        st.sidebar.caption(
            "登入後即可查看個人歷史紀錄。"
        )

else:
    if st.sidebar.button(
        "← 回到分析中心",
        use_container_width=True,
        key="back_to_analysis_center"
    ):
        st.session_state.current_view = "analysis"
        st.session_state.history_selected_id = None
        st.rerun()


if st.session_state.current_view == "history":
    if st.session_state.current_user is None:
        st.warning(
            "請先登入後再查看歷史紀錄。"
        )

        if st.button(
            "回到分析中心",
            use_container_width=True
        ):
            st.session_state.current_view = "analysis"
            st.rerun()

        st.stop()

    history_platform_colors = {
        "YouTube": {
            "primary": "#E53935",
            "soft": "#FDECEC",
            "dark": "#B71C1C",
            "line": "#F0B7B5",
            "gradient": "linear-gradient(135deg, #FF8A80 0%, #FF6B6B 35%, #E53935 100%)",
            "text": "#FFFFFF"
        },
        "Dcard": {
            "primary": "#3397CF",
            "soft": "#E9F6FC",
            "dark": "#1675A8",
            "line": "#B9DDF0",
            "gradient": "linear-gradient(135deg, #8EE3FF 0%, #5CC4F5 38%, #3397CF 100%)",
            "text": "#FFFFFF"
        },
        "Instagram": {
            "primary": "#E7B83B",
            "soft": "#FFF6D8",
            "dark": "#A97600",
            "line": "#EBD58B",
            "gradient": "linear-gradient(135deg, #FFF1A8 0%, #F4D46A 40%, #E7B83B 100%)",
            "text": "#3D2A00"
        }
    }

    history_theme = history_platform_colors[
        st.session_state.history_platform
    ]

    st.markdown(
        f"""
        <style>
        .history-neutral {{
            --history-primary: {history_theme["primary"]};
            --history-soft: {history_theme["soft"]};
            --history-dark: {history_theme["dark"]};
            --history-line: {history_theme["line"]};
        }}

        /* 歷史紀錄頁：強制整個頁面改成灰白漸層 */
        html,
        body,
        #root,
        .stApp,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .main,
        section.main {{
            background:
                radial-gradient(circle at 12% 8%, rgba(255,255,255,.98), transparent 24%),
                radial-gradient(circle at 88% 12%, rgba(220,220,220,.45), transparent 30%),
                linear-gradient(135deg, #FFFFFF 0%, #F1F1F1 52%, #E4E4E4 100%) !important;
            color: #1F1F1F !important;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            background: transparent !important;
        }}

        [data-testid="stHeader"] {{
            background: rgba(248,248,248,.94) !important;
            border-bottom: 1px solid #D7D7D7 !important;
            backdrop-filter: blur(14px) !important;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #FAFAFA 0%, #ECECEC 100%) !important;
            border-right: 1px solid #D6D6D6 !important;
        }}

        [data-testid="stSidebar"] > div {{
            background: transparent !important;
        }}

        [data-testid="stSidebar"] * {{
            color: #202020 !important;
        }}

        /* 把原本平台主題留下的卡片色也洗成灰白 */
        .history-hero,
        .history-card,
        .glass-card,
        .kpi-card,
        .status-panel,
        .empty-state,
        .task-panel,
        div[data-testid="stDataFrame"],
        div[data-testid="stPlotlyChart"],
        [data-testid="stExpander"] {{
            background: linear-gradient(
                180deg,
                rgba(255,255,255,.98) 0%,
                rgba(245,245,245,.98) 100%
            ) !important;
            border-color: #D9D9D9 !important;
            box-shadow: 0 12px 30px rgba(0,0,0,.06) !important;
        }}

        .history-hero::after,
        .hero::after {{
            background: radial-gradient(
                circle,
                rgba(120,120,120,.10),
                transparent 68%
            ) !important;
        }}

        .history-neutral .hero-title,
        .history-neutral .hero-subtitle,
        .history-neutral .section-title,
        .history-neutral .section-note,
        .history-neutral .history-title,
        .history-neutral .history-meta,
        .history-neutral .kpi-label,
        .history-neutral .kpi-value,
        .history-neutral .kpi-foot {{
            color: #1F1F1F !important;
        }}

        .history-neutral .section-kicker,
        .history-neutral .eyebrow {{
            color: #626262 !important;
        }}

        /* 三個平台按鈕預設：灰白漸層 */
        .st-key-history_platform_selector button {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F1F1F1 100%) !important;
            color: #1A1A1A !important;
            border: 1px solid #D5D5D5 !important;
            box-shadow: 0 8px 18px rgba(0,0,0,0.05) !important;
            font-weight: 900 !important;
            border-radius: 16px !important;
            transition: all .22s ease !important;
        }}

        .st-key-history_platform_selector button:hover {{
            background: linear-gradient(180deg, #FFFFFF 0%, #EBEBEB 100%) !important;
            color: #111111 !important;
            border-color: #BDBDBD !important;
            transform: translateY(-1px) !important;
        }}

        /* 依目前選中的平台套用漸層品牌色 */
        {
            ".st-key-history_youtube button { background:linear-gradient(135deg, #FF8A80 0%, #FF6B6B 35%, #E53935 100%) !important; color:#FFFFFF !important; border-color:#F36C67 !important; box-shadow:0 10px 24px rgba(229,57,53,.25) !important; }"
            if st.session_state.history_platform == "YouTube"
            else
            ".st-key-history_dcard button { background:linear-gradient(135deg, #8EE3FF 0%, #5CC4F5 38%, #3397CF 100%) !important; color:#FFFFFF !important; border-color:#52B9EC !important; box-shadow:0 10px 24px rgba(51,151,207,.24) !important; }"
            if st.session_state.history_platform == "Dcard"
            else
            ".st-key-history_instagram button { background:linear-gradient(135deg, #FFF1A8 0%, #F4D46A 40%, #E7B83B 100%) !important; color:#3D2A00 !important; border-color:#E5C55C !important; box-shadow:0 10px 24px rgba(231,184,59,.24) !important; }"
        }

        .history-neutral .history-platform-pill {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F4F4F4 100%) !important;
            color: #3A3A3A !important;
            border: 1px solid #DADADA !important;
        }}

        .history-neutral .section-kicker,
        .history-neutral .eyebrow {{
            color: #5B5B5B !important;
        }}

        /* HISTORY CENTER 標籤改成銀灰色 */
        .history-hero .eyebrow {{
            color: #666666 !important;
            letter-spacing: .18em !important;
        }}

       /* 歷史頁左側：登出按鈕 → 深灰黑漸層 */

        .st-key-logout_button button {{
        background: linear-gradient(
            135deg,
            #666666 0%,
            #474747 45%,
            #242424 100%
                ) !important;

            color: #FFFFFF !important;

            border: 1px solid #4A4A4A !important;

            box-shadow:
             0 10px 22px rgba(0,0,0,.16) !important;

            font-weight: 800 !important;
        }}

            /* 強制「登出」文字變白 */
                .st-key-logout_button button p,
                .st-key-logout_button button span,
                .st-key-logout_button button div {{
                color: #FFFFFF !important;
                }}

            /* 滑鼠移上去 */
            .st-key-logout_button button:hover {{
             background: linear-gradient(
                 135deg,
                 #5A5A5A 0%,
                 #383838 48%,
                 #171717 100%
                    ) !important;

                    color: #FFFFFF !important;

                    border-color: #333333 !important;

                    transform: translateY(-1px);

                box-shadow:
                 0 12px 26px rgba(0,0,0,.20) !important;
                            }}

                /* hover 時文字一樣保持白色 */
                .st-key-logout_button button:hover p,
                        .st-key-logout_button button:hover span,
                    .st-key-logout_button button:hover div {{
                            color: #FFFFFF !important;
                    }}

        .st-key-logout_button button:hover {{
            background: linear-gradient(135deg, #5A5A5A 0%, #383838 48%, #171717 100%) !important;
            color: #FFFFFF !important;
            border-color: #333333 !important;
        }}

        /* 回分析中心 → 白灰漸層 */
        .st-key-back_to_analysis_center button {{
            background: linear-gradient(180deg, #FFFFFF 0%, #EAEAEA 100%) !important;
            color: #292929 !important;
            border: 1px solid #D1D1D1 !important;
            box-shadow: 0 8px 18px rgba(0,0,0,.07) !important;
        }}

        .st-key-back_to_analysis_center button:hover {{
            background: linear-gradient(180deg, #F8F8F8 0%, #DCDCDC 100%) !important;
            color: #111111 !important;
            border-color: #BFBFBF !important;
        }}

        /* 歷史卡片的「查看詳細」 → 炭黑漸層 */
        [class*="st-key-history_detail_"] button {{
            background: linear-gradient(
                135deg,
                #575757 0%,
                #3A3A3A 48%,
                #1F1F1F 100%
            ) !important;
            color: #FFFFFF !important;
            border: 1px solid #444444 !important;
            box-shadow: 0 9px 20px rgba(0,0,0,.14) !important;
            font-weight: 800 !important;
        }}

        /* 強制「查看詳細」文字變白 */
        [class*="st-key-history_detail_"] button p,
        [class*="st-key-history_detail_"] button span,
        [class*="st-key-history_detail_"] button div {{
            color: #FFFFFF !important;
        }}

        [class*="st-key-history_detail_"] button:hover {{
            background: linear-gradient(
                135deg,
                #494949 0%,
                #2D2D2D 48%,
                #111111 100%
            ) !important;
            color: #FFFFFF !important;
            border-color: #2D2D2D !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 11px 24px rgba(0,0,0,.18) !important;
        }}

        /* hover 時「查看詳細」文字保持白色 */
        [class*="st-key-history_detail_"] button:hover p,
        [class*="st-key-history_detail_"] button:hover span,
        [class*="st-key-history_detail_"] button:hover div {{
            color: #FFFFFF !important;
        }}

        /* 詳細頁返回列表按鈕 → 淺灰 */
        .st-key-back_to_history_list button {{
            background: linear-gradient(180deg, #FFFFFF 0%, #E8E8E8 100%) !important;
            color: #2D2D2D !important;
            border: 1px solid #D0D0D0 !important;
            box-shadow: 0 8px 18px rgba(0,0,0,.06) !important;
        }}

        .st-key-back_to_history_list button:hover {{
            background: linear-gradient(180deg, #F7F7F7 0%, #DADADA 100%) !important;
            color: #111111 !important;
        }}
        </style>
        <div class="history-neutral">
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <section class="history-hero">
            <div class="eyebrow">◈ HISTORY CENTER</div>
            <h1 class="hero-title">歷史分析紀錄中心</h1>
            <p class="hero-subtitle">
                選擇平台後即可查看過去完成的分析紀錄。
                目前先顯示系統中的歷史資料；下一階段加入登入後，
                會改成只顯示目前登入帳號自己的歷史紀錄。
            </p>
        </section>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 選擇歷史紀錄平台")

    with st.container(key="history_platform_selector"):
        history_col1, history_col2, history_col3 = st.columns(3)

        with history_col1:
            if st.button(
                "YouTube",
                use_container_width=True,
                key="history_youtube"
            ):
                st.session_state.history_platform = "YouTube"
                st.session_state.history_selected_id = None
                st.rerun()

        with history_col2:
            if st.button(
                "Dcard",
                use_container_width=True,
                key="history_dcard"
            ):
                st.session_state.history_platform = "Dcard"
                st.session_state.history_selected_id = None
                st.rerun()

        with history_col3:
            if st.button(
                "Instagram",
                use_container_width=True,
                key="history_instagram"
            ):
                st.session_state.history_platform = "Instagram"
                st.session_state.history_selected_id = None
                st.rerun()

    selected_history_platform = (
        st.session_state.history_platform
    )

    render_section_header(
        "HISTORY RECORDS",
        f"{selected_history_platform} 歷史分析",
        "依分析時間由新到舊排列"
    )

    try:
        # -------------------------------------------------
        # 如果已選擇某筆歷史紀錄，就直接切換到「詳細頁」
        # 避免詳細內容出現在整個列表最下面，看起來像按鈕沒反應
        # -------------------------------------------------
        if st.session_state.history_selected_id:
            detail = fetch_history_detail(
                st.session_state.history_selected_id
            )

            if st.button(
                "← 回到歷史紀錄列表",
                use_container_width=False,
                key="back_to_history_list"
            ):
                st.session_state.history_selected_id = None
                st.rerun()

            if detail:
                detail_title = (
                    detail.get("target_title")
                    or detail.get("target_id")
                    or "歷史分析"
                )

                render_section_header(
                    "HISTORY DETAIL",
                    detail_title,
                    f"Analysis ID：{detail.get('analysis_id')}"
                )

                k1, k2, k3, k4 = st.columns(4)

                with k1:
                    render_kpi_card(
                        "有效留言",
                        f"{int(detail.get('total_comments', 0)):,}",
                        "該次分析留言數",
                        "primary"
                    )

                with k2:
                    render_kpi_card(
                        "正面比例",
                        f"{float(detail.get('positive_rate', 0) or 0):.1f}%",
                        f"{int(detail.get('positive_count', 0)):,} 則",
                        "mint"
                    )

                with k3:
                    render_kpi_card(
                        "負面比例",
                        f"{float(detail.get('negative_rate', 0) or 0):.1f}%",
                        f"{int(detail.get('negative_count', 0)):,} 則",
                        "coral"
                    )

                with k4:
                    render_kpi_card(
                        "主要主題",
                        detail.get("top_topic") or "-",
                        detail.get("analyzed_at") or "",
                        "sky"
                    )

                comments = detail.get(
                    "comments",
                    []
                )

                if comments:
                    history_comments_df = pd.DataFrame(
                        comments
                    )

                    history_comments_df = (
                        history_comments_df.rename(
                            columns={
                                "author": "帳號",
                                "comment_text": "留言內容",
                                "sentiment_label": "情緒",
                                "confidence_score": "信心度",
                                "topic_id": "Topic ID",
                                "topic_name": "AI主題名稱",
                                "topic_keywords": "BERTopic關鍵字",
                                "comment_time": "留言時間"
                            }
                        )
                    )

                    display_history_columns = [
                        column
                        for column in [
                            "帳號",
                            "留言內容",
                            "情緒",
                            "信心度",
                            "AI主題名稱",
                            "BERTopic關鍵字",
                            "留言時間",
                            "Topic ID"
                        ]
                        if column in history_comments_df.columns
                    ]

                    st.dataframe(
                        make_styled_table(
                            history_comments_df[
                                display_history_columns
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                        height=520
                    )
                else:
                    st.info(
                        "這筆歷史分析沒有可顯示的留言資料。"
                    )

            else:
                st.warning(
                    "找不到這筆歷史分析，可能已被刪除。"
                )

        # -------------------------------------------------
        # 尚未選擇紀錄：顯示歷史列表
        # -------------------------------------------------
        else:
            history_rows = fetch_history(
                selected_history_platform
            )

            if not history_rows:
                st.markdown(
                    """
                    <div class="empty-state">
                        目前這個平台還沒有歷史分析紀錄。
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:
                for history_row in history_rows:
                    analysis_id = history_row.get(
                        "analysis_id"
                    )
                    title = (
                        history_row.get("target_title")
                        or history_row.get("target_id")
                        or "未命名分析"
                    )
                    analyzed_at = history_row.get(
                        "analyzed_at",
                        "-"
                    )
                    total_comments = history_row.get(
                        "total_comments",
                        0
                    )
                    positive_rate = float(
                        history_row.get(
                            "positive_rate",
                            0
                        ) or 0
                    )
                    negative_rate = float(
                        history_row.get(
                            "negative_rate",
                            0
                        ) or 0
                    )
                    top_topic = (
                        history_row.get("top_topic")
                        or "尚無主要主題"
                    )

                    card_col, action_col = st.columns(
                        [5.2, 1.15]
                    )

                    with card_col:
                        st.markdown(
                            f"""
                            <div class="history-card">
                                <div class="history-platform-pill">
                                    {html.escape(str(selected_history_platform))}
                                </div>
                                <div class="history-title">
                                    {html.escape(str(title))}
                                </div>
                                <div class="history-meta">
                                    分析時間：{html.escape(str(analyzed_at))}<br>
                                    有效留言：{int(total_comments):,} 則　
                                    正面：{positive_rate:.1f}%　
                                    負面：{negative_rate:.1f}%<br>
                                    主要主題：{html.escape(str(top_topic))}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with action_col:
                        st.markdown(
                            "<div style='height:1.45rem'></div>",
                            unsafe_allow_html=True
                        )

                        if st.button(
                            "查看詳細",
                            key=f"history_detail_{analysis_id}",
                            use_container_width=True
                        ):
                            st.session_state.history_selected_id = (
                                analysis_id
                            )
                            st.rerun()

    except requests.exceptions.ConnectionError:
        st.error(
            "無法連線到 FastAPI。請先啟動 "
            "uvicorn main_api:app --reload"
        )

    except Exception as error:
        st.error(
            f"歷史紀錄讀取失敗：{error}"
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )

    st.stop()


st.sidebar.markdown("### 監測平台")

platform = st.sidebar.selectbox(
    "資料來源",
    ["YouTube", "Dcard", "Instagram"],
    help="請選擇要分析的社群平台。"
)

current_theme = apply_platform_theme(platform)

restore_platform_result(platform)

platform_chart_palette = {
    "YouTube": [
        "#F06F75", "#F58D93", "#F7A7AC", "#F9BEC2", "#FAD2D5",
        "#E95D65", "#D94C54", "#F6B0B5", "#FCDDE0", "#C94B52"
    ],
    "Dcard": [
        "#4ECAC2", "#6FD6CF", "#8FE1DB", "#AEEBE6", "#C9F3EF",
        "#3AB7B0", "#2AA39E", "#79DCEB", "#A9E9F4", "#1E8D89"
    ],
    "Instagram": [
        "#E6B94F", "#EDC765", "#F3D47A", "#F6DE96", "#FAE9B6",
        "#DDAA35", "#C99524", "#F1CC64", "#F8E3A1", "#B9851D"
    ]
}[platform]

platform_heat_scale = {
    "YouTube": [
        [0.0, "#FFF8F8"],
        [0.25, "#FDE1E3"],
        [0.5, "#F8B8BC"],
        [0.75, "#F28B91"],
        [1.0, "#D94C54"]
    ],
    "Dcard": [
        [0.0, "#F5FFFE"],
        [0.25, "#D8F6F3"],
        [0.5, "#AEEBE6"],
        [0.75, "#79D7D1"],
        [1.0, "#2AA39E"]
    ],
    "Instagram": [
        [0.0, "#FFFDF6"],
        [0.25, "#FFF1C6"],
        [0.5, "#F8E3A1"],
        [0.75, "#F0CD68"],
        [1.0, "#C99524"]
    ]
}[platform]

# 預設值
monitor_mode = None
search_target = ""
start_monitoring = False
dcard_forum = None
dcard_forum_alias = None
dcard_keyword = ""
dcard_search_button = False
instagram_mode = None
instagram_target = ""
instagram_action_button = False


# =========================================================
# 6-1. Hero
# =========================================================
active_target = st.session_state.active_target_label or "尚未選定分析目標"

st.markdown(
    f"""
    <section class="hero">
        <div class="eyebrow">◈ AI PUBLIC OPINION COMMAND CENTER</div>
        <h1 class="hero-title">社群輿情監測與決策支援中心</h1>
        <p class="hero-subtitle">
            以淺色、清晰、專業化的介面呈現 YouTube、Dcard 與 Instagram 留言情緒分析、主題建模、風險預警與報告導出，
            幫助你更快速掌握社群討論重點與行動方向。
        </p>
        <div class="hero-badges">
            <span class="badge">目前目標：{html.escape(str(active_target))}</span>
            <span class="badge">資料來源：{html.escape(str(platform))}</span>
            <span class="badge">主色系：{html.escape(str(current_theme["theme_name"]))}</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 6-2. 中央任務設定區
# =========================================================
st.markdown(
    """
    <div class="task-panel">
        <div class="task-panel-kicker">MONITORING SETUP</div>
        <div class="task-panel-title">建立分析任務</div>
    </div>
    """,
    unsafe_allow_html=True
)

if platform == "YouTube":
    monitor_mode = st.radio(
        "分析模式",
        ["單一影片分析", "主題關鍵字追蹤"],
        captions=[
            "直接分析指定影片的留言",
            "先搜尋熱門影片，再選擇分析目標"
        ],
        horizontal=True
    )

    youtube_input_col, youtube_button_col = st.columns([4.6, 1.25])

    with youtube_input_col:
        if monitor_mode == "單一影片分析":
            search_target = st.text_input(
                "YouTube 影片連結",
                placeholder="https://youtu.be/...",
                help="支援完整網址或影片 ID。"
            )
        else:
            search_target = st.text_input(
                "追蹤關鍵字",
                placeholder="例如：iPhone 17、AI 教育",
                help="系統會先搜尋最具討論度的相關影片。"
            )

    with youtube_button_col:
        st.markdown("<div style='height:1.77rem'></div>", unsafe_allow_html=True)
        start_monitoring = st.button(
            "啟動完整分析" if monitor_mode == "單一影片分析" else "搜尋熱門影片",
            type="primary",
            use_container_width=True,
            key="youtube_main_action"
        )

elif platform == "Dcard":
    dcard_forum_options = {
        "感情": "relationship",
        "心情": "mood",
        "工作": "job",
        "理財": "money",
        "3C": "3c",
        "美食": "food",
        "穿搭": "dressup",
        "有趣": "funny"
    }

    dcard_forum_col, dcard_keyword_col, dcard_button_col = st.columns([1.25, 3.2, 1.25])

    with dcard_forum_col:
        dcard_forum = st.selectbox(
            "Dcard 看板",
            list(dcard_forum_options.keys()),
            help="選擇要搜尋文章的 Dcard 看板。"
        )
        dcard_forum_alias = dcard_forum_options[dcard_forum]

    with dcard_keyword_col:
        dcard_keyword = st.text_input(
            "搜尋關鍵字",
            placeholder="例如：出軌、遠距離戀愛、台積電",
            help="系統將在所選看板中搜尋相關文章。"
        )

    with dcard_button_col:
        st.markdown("<div style='height:1.77rem'></div>", unsafe_allow_html=True)
        dcard_search_button = st.button(
            "搜尋 Dcard 文章",
            type="primary",
            use_container_width=True,
            key="dcard_search_button"
        )

else:
    instagram_mode = "單一貼文分析"
    instagram_input_col, instagram_button_col = st.columns([4.6, 1.25])

    with instagram_input_col:
        instagram_target = st.text_input(
            "Instagram 貼文或 Reels 連結",
            placeholder="https://www.instagram.com/p/... 或 /reel/...",
            help="貼上公開貼文或 Reels 網址，系統會嘗試抓取可取得的真實留言。"
        )

    with instagram_button_col:
        st.markdown("<div style='height:1.77rem'></div>", unsafe_allow_html=True)
        instagram_action_button = st.button(
            "啟動完整分析",
            type="primary",
            use_container_width=True,
            key="instagram_direct_analyze"
        )

st.sidebar.markdown("---")
st.sidebar.markdown("### 系統模組")

module_names = [
    "AI 情緒辨識",
    "BERTopic 主題建模",
    "MySQL 分析資料庫",
    "Word 報告引擎"
]

if platform == "YouTube":
    module_names.insert(0, "YouTube Data API")
elif platform == "Dcard":
    module_names.insert(0, "Dcard 文章搜尋")
else:
    module_names.insert(0, "Instagram 貼文分析")

for module_name in module_names:
    st.sidebar.markdown(
        f"""
        <div class="mini-status">
            <span><span class="dot-ok"></span>{module_name}</span>
            <span>READY</span>
        </div>
        """,
        unsafe_allow_html=True
    )

if st.session_state.last_analysis_time:
    st.sidebar.caption(
        "最近完成時間："
        + st.session_state.last_analysis_time.strftime("%Y-%m-%d %H:%M:%S")
    )


# =========================================================
# 7. 任務執行
# =========================================================

# =========================================================
# YouTube 任務
# =========================================================
if platform == "YouTube" and start_monitoring:

    if not search_target.strip():
        st.sidebar.warning(
            "請先輸入影片連結或搜尋關鍵字。"
        )

    # -----------------------------------------------------
    # YouTube：分析單一影片
    # -----------------------------------------------------
    elif monitor_mode == "單一影片分析":

        with analysis_progress("YouTube"):
            try:
                result_data = call_pipeline(
                    search_target
                )

                save_pipeline_result(
                    result_data=result_data,
                    active_video=search_target,
                    target_label=search_target,
                    platform_name="YouTube"
                )
                show_analysis_complete("YouTube 影片分析完成")

                st.sidebar.success(
                    "影片分析已完成。"
                )

            except requests.exceptions.ConnectionError:
                st.sidebar.error(
                    "無法連線到 FastAPI。"
                    "請先啟動 main_api.py。"
                )

            except requests.exceptions.Timeout:
                st.sidebar.error(
                    "分析超過 600 秒，"
                    "請查看後端終端機狀態。"
                )

            except Exception as error:
                st.sidebar.error(
                    f"分析失敗：{error}"
                )

    # -----------------------------------------------------
    # YouTube：關鍵字搜尋影片
    # -----------------------------------------------------
    elif monitor_mode == "主題關鍵字追蹤":

        with analysis_progress("YouTube"):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/search_videos",
                    json={
                        "keyword": search_target
                    },
                    timeout=180
                )

                if response.status_code != 200:
                    raise RuntimeError(
                        response.text
                    )

                response_data = response.json()

                st.session_state.searched_videos = (
                    response_data.get(
                        "videos",
                        []
                    )
                )

                st.session_state.platform_results["YouTube"] = None
                restore_platform_result("YouTube")

                st.sidebar.success(
                    "已找到 "
                    f"{len(st.session_state.searched_videos)} "
                    "支影片。"
                )

            except requests.exceptions.ConnectionError:
                st.sidebar.error(
                    "無法連線到 FastAPI。"
                )

            except Exception as error:
                st.sidebar.error(
                    f"搜尋失敗：{error}"
                )


# =========================================================
# Dcard 任務
# =========================================================
if platform == "Dcard" and dcard_search_button:

    if not dcard_keyword.strip():
        show_dcard_search_dialog(
            title="還沒有輸入搜尋關鍵字",
            message=(
                "請先輸入想搜尋的主題，例如：儲蓄、ETF、遠距離戀愛，"
                "再重新搜尋一次。"
            ),
            keyword="",
            is_error=False
        )

    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/dcard/search_articles",
                json={
                    "forum": dcard_forum_alias,
                    "keyword": dcard_keyword.strip()
                },
                timeout=30
            )

            if response.status_code != 200:
                error_detail = ""

                try:
                    error_detail = response.json().get(
                        "detail",
                        ""
                    )
                except Exception:
                    error_detail = response.text

                # 資料檔缺失：顯示友善提示，不把 Windows 路徑丟給使用者
                if (
                    "找不到以下 Dcard 本機資料檔" in error_detail
                    or "dcard_articles.csv" in error_detail
                    or "dcard_comments.csv" in error_detail
                ):
                    friendly_message = (
                        "Dcard 資料目前無法讀取。"
                        "請確認 dcard_data 資料夾內已有文章與留言資料檔，"
                        "再重新搜尋。"
                    )

                else:
                    friendly_message = (
                        "Dcard 搜尋服務暫時無法完成這次請求。"
                        "請稍後再試，或更換看板與關鍵字重新搜尋。"
                    )

                show_dcard_search_dialog(
                    title="唉呀，這次搜尋沒有成功",
                    message=friendly_message,
                    keyword=dcard_keyword.strip(),
                    is_error=True
                )

            else:
                response_data = response.json()

                st.session_state.dcard_articles = response_data.get(
                    "articles",
                    []
                )

                st.session_state.dcard_search_message = response_data.get(
                    "message",
                    ""
                )

                st.session_state.selected_dcard_article = None

                # 真正沒有搜尋結果
                if not st.session_state.dcard_articles:
                    show_dcard_search_dialog(
                        title="唉呀，找不到相關文章",
                        message=(
                            "目前沒有找到符合這個關鍵字的 Dcard 文章。"
                            "可以試著換成比較簡短、常見或範圍更大的關鍵字再搜尋一次。"
                        ),
                        keyword=dcard_keyword.strip(),
                        is_error=False
                    )

                else:
                    st.toast(
                        f"找到 {len(st.session_state.dcard_articles)} 篇相關文章",
                        icon="✅"
                    )

        except requests.exceptions.ConnectionError:
            show_dcard_search_dialog(
                title="目前連不到分析伺服器",
                message=(
                    "請確認 FastAPI 已經啟動。"
                    "在另一個 PowerShell 執行 "
                    "uvicorn main_api:app --reload 後再試一次。"
                ),
                keyword=dcard_keyword.strip(),
                is_error=True
            )

        except requests.exceptions.Timeout:
            show_dcard_search_dialog(
                title="搜尋時間有點久",
                message=(
                    "Dcard 搜尋逾時了。請稍後再試一次，"
                    "或先改用更精簡的關鍵字。"
                ),
                keyword=dcard_keyword.strip(),
                is_error=True
            )

        except Exception:
            show_dcard_search_dialog(
                title="唉呀，搜尋時發生問題",
                message=(
                    "這次搜尋沒有順利完成。"
                    "請稍後再試一次；如果持續發生，再檢查後端執行狀態。"
                ),
                keyword=dcard_keyword.strip(),
                is_error=True
            )


# =========================================================
# Instagram 任務：真實貼文或 Reels 分析
# =========================================================
if platform == "Instagram" and instagram_action_button:

    if not instagram_target.strip():
        st.sidebar.warning(
            "請先輸入 Instagram 貼文或 Reels 網址。"
        )

    else:
        with analysis_progress("Instagram"):
            try:
                result_data = call_instagram_url_pipeline(
                    instagram_target.strip()
                )

                save_pipeline_result(
                    result_data=result_data,
                    active_video=result_data.get(
                        "reel_id",
                        instagram_target.strip()
                    ),
                    target_label=result_data.get(
                        "caption",
                        instagram_target.strip()
                    ),
                    platform_name="Instagram"
                )
                show_analysis_complete("Instagram 貼文分析完成")

                st.sidebar.success(
                    result_data.get(
                        "message",
                        "Instagram 貼文分析已完成。"
                    )
                )

            except requests.exceptions.ConnectionError:
                st.sidebar.error(
                    "無法連線到 FastAPI。"
                    "請先啟動 main_api.py。"
                )

            except requests.exceptions.Timeout:
                st.sidebar.error(
                    "Instagram 分析超過 600 秒，"
                    "請查看後端終端機狀態。"
                )

            except Exception as error:
                st.sidebar.error(
                    f"Instagram 分析失敗：{error}"
                )

# =========================================================
# 8-1. Dcard 搜尋結果
# =========================================================
# 只有搜尋到文章時才顯示文章選擇區；
# 沒有結果時改由中央 Dialog 顯示友善提示。
if (
    platform == "Dcard"
    and st.session_state.dcard_articles
):
    dcard_articles = st.session_state.dcard_articles or []

    if dcard_articles:
        render_section_header(
            "DCARD DISCOVERY",
            "Dcard 文章搜尋結果",
            "選擇一篇文章，下一步再分析該文章留言"
        )

        article_labels = []

        for article in dcard_articles:
            title = article.get("title", "未命名文章")
            created_at = article.get("created_at", "")
            like_count = article.get("like_count", 0)
            comment_count = article.get("comment_count", 0)

            article_labels.append(
                f"{title}｜{created_at}｜愛心 {like_count}｜留言 {comment_count}"
            )

        selected_label = st.selectbox(
            "選擇要分析的 Dcard 文章",
            options=article_labels,
            key="dcard_article_selector"
        )

        selected_index = article_labels.index(selected_label)
        selected_article = dcard_articles[selected_index]

        st.session_state.selected_dcard_article = selected_article

        selected_title = selected_article.get("title", "未命名文章")
        selected_id = selected_article.get("id", "")
        selected_forum_name = selected_article.get("forum_name", "")
        selected_date = selected_article.get("created_at", "")
        selected_like_count = selected_article.get("like_count", 0)
        selected_comment_count = selected_article.get("comment_count", 0)
        selected_url = selected_article.get("url", "")

        st.markdown(
            f"""
            <div class="glass-card">
                <div class="section-kicker">SELECTED DCARD ARTICLE</div>
                <div style="font-size:1.12rem;font-weight:900;color:#173A46;">
                    {html.escape(str(selected_title))}
                </div>
                <div style="color:#5E7B88;font-size:.84rem;line-height:1.8;margin-top:.55rem;">
                    文章 ID：{html.escape(str(selected_id))}<br>
                    看板：{html.escape(str(selected_forum_name))}<br>
                    日期：{html.escape(str(selected_date))}<br>
                    愛心數：{html.escape(str(selected_like_count))}<br>
                    留言數：{html.escape(str(selected_comment_count))}
                </div>
                <div style="color:#7A939D;font-size:.76rem;margin-top:.55rem;word-break:break-all;">
                    {html.escape(str(selected_url))}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.success(
            f"目前已選擇：{selected_title}"
        )

        analyze_dcard_article = st.button(
            "分析此文章留言",
            type="primary",
            use_container_width=True,
            key=f"analyze_dcard_{selected_id}"
        )

        if analyze_dcard_article:
            with analysis_progress("Dcard"):
                try:
                    result_data = call_dcard_pipeline(
                        selected_article
                    )

                    save_pipeline_result(
                        result_data=result_data,
                        active_video=f"dcard:{selected_id}",
                        target_label=selected_title,
                        platform_name="Dcard"
                    )
                    show_analysis_complete("Dcard 文章分析完成")

                    st.success(
                        result_data.get(
                            "message",
                            f"「{selected_title}」留言分析完成。"
                        )
                    )

                except requests.exceptions.ConnectionError:
                    st.error(
                        "無法連線到 FastAPI。"
                        "請確認 uvicorn main_api:app --reload 正在執行。"
                    )

                except requests.exceptions.Timeout:
                    st.error(
                        "Dcard 留言分析超過 600 秒，"
                        "請查看 FastAPI 終端機狀態。"
                    )

                except Exception as error:
                    st.error(
                        f"Dcard 留言分析失敗：{error}"
                    )



# =========================================================
# 9. 關鍵字搜尋結果
# =========================================================
if monitor_mode == "主題關鍵字追蹤" and st.session_state.searched_videos:
    render_section_header("DISCOVERY", "熱門影片探索", "選擇最值得深入分析的影片來源")

    video_options = []
    for video in st.session_state.searched_videos:
        title = video.get("title", "未命名影片")
        video_id = video.get("video_id", "")
        video_options.append(f"{title}｜ID：{video_id}")

    selected_option = st.selectbox(
        "分析目標",
        options=video_options,
        label_visibility="collapsed"
    )

    selected_index = video_options.index(selected_option)
    selected_video = st.session_state.searched_videos[selected_index]
    chosen_video_id = selected_video.get("video_id")
    chosen_video_title = selected_video.get("title", "未命名影片")

    preview_col1, preview_col2 = st.columns([4.4, 1.2])
    with preview_col1:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="section-kicker">SELECTED SOURCE</div>
                <div style="color:#173A46;font-size:1.08rem;font-weight:800;">
                    {html.escape(chosen_video_title)}
                </div>
                <div style="color:#62808E;font-size:.82rem;margin-top:.4rem;">
                    Video ID：{html.escape(str(chosen_video_id))}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with preview_col2:
        analyze_selected = st.button(
            "分析此影片",
            type="primary",
            use_container_width=True
        )

    if analyze_selected:
        with analysis_progress("YouTube"):
            try:
                result_data = call_pipeline(chosen_video_id)
                save_pipeline_result(
                    result_data=result_data,
                    active_video=chosen_video_id,
                    target_label=chosen_video_title,
                    platform_name="YouTube"
                )
                show_analysis_complete("YouTube 影片深度分析完成")
                st.success("影片深度分析完成。")
            except requests.exceptions.ConnectionError:
                st.error("無法連線到 FastAPI。")
            except requests.exceptions.Timeout:
                st.error("分析逾時。")
            except Exception as error:
                st.error(f"分析失敗：{error}")


# =========================================================
# 9-1. 尚未完成分析時的專業起始畫面
# =========================================================
if st.session_state.crawled_data is None:
    st.markdown(
        """
        <div class="welcome-panel">
            <div class="welcome-kicker">GET STARTED</div>
            <div class="welcome-title">從左側建立第一個監測任務</div>
            <div class="welcome-description">
                選擇資料來源並輸入分析目標。完成抓取後，系統才會顯示情緒指標、
                主題洞察、風險判定與報告下載，避免在尚無資料時出現空白圖表與無效數值。
            </div>
            <div class="welcome-grid">
                <div class="welcome-item">
                    <div class="welcome-number">01</div>
                    <div class="welcome-item-title">選擇平台</div>
                    <div class="welcome-item-text">YouTube、Dcard 或 Instagram</div>
                </div>
                <div class="welcome-item">
                    <div class="welcome-number">02</div>
                    <div class="welcome-item-title">指定目標</div>
                    <div class="welcome-item-text">貼上連結或輸入搜尋條件</div>
                </div>
                <div class="welcome-item">
                    <div class="welcome-number">03</div>
                    <div class="welcome-item-title">啟動分析</div>
                    <div class="welcome-item-text">取得真實留言與決策報告</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="initial-footer">
            Social Insight Intelligence Platform · Ready for analysis
        </div>
        """,
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# 10. 分析設定
# =========================================================
render_section_header(
    "CONTROL PANEL",
    "分析設定",
    "目前顯示全部留言資料"
)

filter_card = st.container(border=True)

with filter_card:
    filter_col1, filter_col2 = st.columns(
        [1.4, 1]
    )

    with filter_col1:
        video_type = st.selectbox(
            "內容情境",
            [
                "科技專業評論 (Deep Review)",
                "新品開箱測試 (Unboxing)",
                "重大公關／爭議事件 (Crisis)"
            ]
        )

    with filter_col2:
        st.text_input(
            "分析版本",
            value="Hybrid AI v2.0",
            disabled=True
        )


# =========================================================
# 11. 數據整理
# =========================================================
if st.session_state.crawled_data is not None:
    df_raw = (
        st.session_state.crawled_data
        .copy()
    )

    # 不再進行日期篩選，直接顯示全部留言
    df = df_raw.reset_index(
        drop=True
    )

    total_comments_count = len(df)

    if "sentiment" in df.columns:
        sentiment_counts = (
            df["sentiment"]
            .value_counts()
        )
    else:
        sentiment_counts = pd.Series(
            dtype="int64"
        )

    pos_count = int(
        sentiment_counts.get(
            "正面",
            0
        )
    )

    neu_count = int(
        sentiment_counts.get(
            "中立",
            0
        )
    )

    neg_count = int(
        sentiment_counts.get(
            "負面",
            0
        )
    )

    question_count = int(
        sentiment_counts.get(
            "提問",
            0
        )
    )

    if total_comments_count > 0:
        current_pos_rate = round(
            pos_count
            / total_comments_count
            * 100,
            1
        )

        current_neg_rate = round(
            neg_count
            / total_comments_count
            * 100,
            1
        )

        current_question_rate = round(
            question_count
            / total_comments_count
            * 100,
            1
        )

        current_neu_rate = round(
            neu_count
            / total_comments_count
            * 100,
            1
        )

    else:
        current_pos_rate = 0
        current_neg_rate = 0
        current_question_rate = 0
        current_neu_rate = 0

else:
    df = pd.DataFrame()

    total_comments_count = 0
    pos_count = 0
    neu_count = 0
    neg_count = 0
    question_count = 0

    current_pos_rate = 0
    current_neg_rate = 0
    current_question_rate = 0
    current_neu_rate = 0


risk_info = get_risk_info(current_neg_rate)

# 自動辨識主題與留言欄位，避免 topic_column / comment_column 未定義
topic_column, comment_column = get_topic_and_comment_columns(df)

# =========================================================
# 12. KPI 摘要
# =========================================================
render_section_header("EXECUTIVE SNAPSHOT", "核心輿情指標", "快速掌握聲量、情緒與風險")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns([1, 1, 1, 1, 1.15])

with kpi1:
    render_kpi_card("有效留言聲量", f"{total_comments_count:,}", "目前篩選條件內的留言數", "primary")
with kpi2:
    render_kpi_card("正面情緒", f"{current_pos_rate:.1f}%", f"{pos_count:,} 則正面留言", "mint")
with kpi3:
    render_kpi_card("負面情緒", f"{current_neg_rate:.1f}%", f"{neg_count:,} 則負面留言", "coral")
with kpi4:
    render_kpi_card("提問比例", f"{current_question_rate:.1f}%", f"{question_count:,} 則提問留言", "sky")
with kpi5:
    st.markdown(
        f"""
        <div class="status-panel {risk_info['class']}">
            <div class="kpi-label">系統風險判定</div>
            <div class="status-title">{risk_info['label']}</div>
            <div class="status-body">{risk_info['description']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 13. 分頁
# =========================================================
overview_tab, topic_tab, comments_tab, report_tab = st.tabs([
    "總覽分析",
    "主題洞察",
    "留言明細",
    "報告中心"
])


# =========================================================
# 13-1 總覽分析
# =========================================================
with overview_tab:
    if st.session_state.crawled_data is None:
        st.markdown(
            """
            <div class="empty-state">
                <div style="font-size:2.2rem;margin-bottom:.6rem;">◌</div>
                尚未載入分析資料。請從左側選擇 YouTube、Dcard 或 Instagram 的分析目標。
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        chart_col1, chart_col2 = st.columns([1.02, 1])

        with chart_col1:
            sentiment_df = pd.DataFrame({
                "情緒": ["正面", "中立", "負面", "提問"],
                "留言數": [pos_count, neu_count, neg_count, question_count]
            })
            sentiment_df = sentiment_df[sentiment_df["留言數"] > 0]

            fig_donut = go.Figure(
                data=[
                    go.Pie(
                        labels=sentiment_df["情緒"],
                        values=sentiment_df["留言數"],
                        hole=.65,
                        textinfo="label+percent",
                        textfont=dict(color="#173A46", size=14),
                        marker=dict(
                            colors=[COLOR_MAP.get(x, "#4ECAC2") for x in sentiment_df["情緒"]],
                            line=dict(color="#FFFFFF", width=2)
                        ),
                        hovertemplate="%{label}<br>留言數：%{value}<br>占比：%{percent}<extra></extra>"
                    )
                ]
            )
            fig_donut.update_layout(
                **chart_layout("情緒結構分布", height=450),
                annotations=[
                    dict(
                        text=f"<b>{total_comments_count:,}</b><br><span style='font-size:12px'>留言總數</span>",
                        x=.5,
                        y=.5,
                        font=dict(size=26, color="#173A46"),
                        showarrow=False
                    )
                ]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with chart_col2:
            sentiment_bar = pd.DataFrame({
                "情緒": ["正面", "中立", "負面", "提問"],
                "留言數": [pos_count, neu_count, neg_count, question_count]
            })
            fig_bar = px.bar(
                sentiment_bar,
                x="留言數",
                y="情緒",
                orientation="h",
                text="留言數",
                color="情緒",
                color_discrete_map=COLOR_MAP
            )
            fig_bar.update_layout(
                **chart_layout("各情緒留言量比較", height=450, showlegend=False),
                xaxis_title="留言數",
                yaxis_title=""
            )
            fig_bar.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        # 取代原本的時間趨勢圖：改成更有意義的主題情緒分布
        if topic_column and "sentiment" in df.columns:
            topic_focus = (
                df.groupby([topic_column, "sentiment"])
                .size()
                .reset_index(name="留言數")
            )

            top_topics = (
                df[topic_column]
                .value_counts()
                .head(6)
                .index.tolist()
            )

            topic_focus = topic_focus[topic_focus[topic_column].isin(top_topics)]

            if not topic_focus.empty:
                fig_topic_stack = px.bar(
                    topic_focus,
                    x=topic_column,
                    y="留言數",
                    color="sentiment",
                    barmode="stack",
                    color_discrete_map=COLOR_MAP,
                    category_orders={topic_column: top_topics}
                )
                fig_topic_stack.update_layout(
                    **chart_layout("高聲量主題的情緒分布", height=440),
                    xaxis_title="主題",
                    yaxis_title="留言數"
                )
                fig_topic_stack.update_xaxes(tickangle=-18)
                st.plotly_chart(fig_topic_stack, use_container_width=True)


# =========================================================
# 13-2 主題洞察
# =========================================================
with topic_tab:
    render_section_header(
        "TOPIC INTELLIGENCE",
        "AI 主題洞察中心",
        "主題規模、分類、情緒風險與代表留言一次看懂"
    )

    if (
        st.session_state.crawled_data is None
        or df.empty
        or not topic_column
    ):
        st.markdown(
            """
            <div class="empty-state">
                尚未產生主題資料。
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        # -------------------------------------------------
        # 建立主題層級總表
        # -------------------------------------------------
        group_columns = [
            topic_column
        ]

        for optional_column in [
            "topic_category",
            "topic_summary",
            "topic_keywords"
        ]:
            if optional_column in df.columns:
                group_columns.append(
                    optional_column
                )

        topic_summary_df = (
            df.groupby(
                group_columns,
                dropna=False
            )
            .size()
            .reset_index(
                name="留言數"
            )
        )

        topic_summary_df[
            "聲量占比"
        ] = (
            topic_summary_df["留言數"]
            / max(len(df), 1)
            * 100
        ).round(1)

        if "sentiment" in df.columns:
            sentiment_topic_df = (
                df.groupby(
                    [
                        topic_column,
                        "sentiment"
                    ]
                )
                .size()
                .unstack(
                    fill_value=0
                )
            )

            for sentiment_name in [
                "正面",
                "中立",
                "負面",
                "提問"
            ]:
                if sentiment_name not in sentiment_topic_df.columns:
                    sentiment_topic_df[
                        sentiment_name
                    ] = 0

            selected_sentiment_cols = [
                "正面",
                "中立",
                "負面",
                "提問"
            ]

            sentiment_pct = (
                sentiment_topic_df[
                    selected_sentiment_cols
                ]
                .div(
                    sentiment_topic_df[
                        selected_sentiment_cols
                    ]
                    .sum(axis=1)
                    .replace(0, 1),
                    axis=0
                )
                * 100
            ).round(1)

            sentiment_pct = (
                sentiment_pct
                .reset_index()
                .rename(
                    columns={
                        "正面": "正面率",
                        "中立": "中立率",
                        "負面": "負面率",
                        "提問": "提問率"
                    }
                )
            )

            topic_summary_df = (
                topic_summary_df
                .merge(
                    sentiment_pct,
                    on=topic_column,
                    how="left"
                )
            )

        else:
            for rate_column in [
                "正面率",
                "中立率",
                "負面率",
                "提問率"
            ]:
                topic_summary_df[
                    rate_column
                ] = 0.0

        topic_summary_df[
            "風險等級"
        ] = (
            topic_summary_df[
                "負面率"
            ]
            .apply(
                lambda value: (
                    "高風險"
                    if value >= 30
                    else "需關注"
                    if value >= 15
                    else "穩定"
                )
            )
        )

        topic_summary_df = (
            topic_summary_df
            .sort_values(
                "留言數",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

        topic_summary_df.insert(
            0,
            "排名",
            range(
                1,
                len(topic_summary_df) + 1
            )
        )

        # -------------------------------------------------
        # 1. 主題 KPI
        # -------------------------------------------------
        topic_count_total = len(
            topic_summary_df
        )

        if topic_count_total:
            largest_topic = (
                topic_summary_df.iloc[0]
            )

            riskiest_topic = (
                topic_summary_df
                .sort_values(
                    [
                        "負面率",
                        "留言數"
                    ],
                    ascending=[
                        False,
                        False
                    ]
                )
                .iloc[0]
            )

            question_topic = (
                topic_summary_df
                .sort_values(
                    [
                        "提問率",
                        "留言數"
                    ],
                    ascending=[
                        False,
                        False
                    ]
                )
                .iloc[0]
            )
        else:
            largest_topic = None
            riskiest_topic = None
            question_topic = None

        topic_summary_html = f"""
<div class="topic-summary-grid">
    <div class="topic-summary-card">
        <div class="topic-summary-label">辨識主題數</div>
        <div class="topic-summary-value">{topic_count_total}</div>
        <div class="topic-summary-foot">本次留言被分成的主要討論群組</div>
    </div>
    <div class="topic-summary-card">
        <div class="topic-summary-label">最大主題</div>
        <div class="topic-summary-value">{html.escape(str(largest_topic[topic_column]) if largest_topic is not None else "-")}</div>
        <div class="topic-summary-foot">占全部留言 {float(largest_topic["聲量占比"]) if largest_topic is not None else 0:.1f}%</div>
    </div>
    <div class="topic-summary-card">
        <div class="topic-summary-label">最高負面主題</div>
        <div class="topic-summary-value">{html.escape(str(riskiest_topic[topic_column]) if riskiest_topic is not None else "-")}</div>
        <div class="topic-summary-foot">負面比例 {float(riskiest_topic["負面率"]) if riskiest_topic is not None else 0:.1f}%</div>
    </div>
    <div class="topic-summary-card">
        <div class="topic-summary-label">最多提問主題</div>
        <div class="topic-summary-value">{html.escape(str(question_topic[topic_column]) if question_topic is not None else "-")}</div>
        <div class="topic-summary-foot">提問比例 {float(question_topic["提問率"]) if question_topic is not None else 0:.1f}%</div>
    </div>
</div>
"""
        st.markdown(
            topic_summary_html,
            unsafe_allow_html=True
        )

        # -------------------------------------------------
        # 2. 聲量排行 + 情緒結構
        # -------------------------------------------------
        chart_left, chart_right = (
            st.columns(
                [
                    1,
                    1.08
                ]
            )
        )

        with chart_left:
            rank_df = (
                topic_summary_df
                .head(10)
                .sort_values(
                    "留言數",
                    ascending=True
                )
            )

            rank_title = (
                "前十大主題聲量"
                if len(rank_df) >= 10
                else f"主題聲量排行（共 {len(rank_df)} 類）"
            )

            fig_topic_rank = px.bar(
                rank_df,
                x="留言數",
                y=topic_column,
                orientation="h",
                text="留言數",
                custom_data=[
                    "聲量占比",
                    "風險等級"
                ]
            )

            fig_topic_rank.update_traces(
                marker_color=(
                    platform_chart_palette[
                        :len(rank_df)
                    ]
                ),
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "主題：%{y}<br>"
                    "留言數：%{x}<br>"
                    "聲量占比：%{customdata[0]:.1f}%<br>"
                    "風險：%{customdata[1]}"
                    "<extra></extra>"
                )
            )

            topic_rank_layout = chart_layout(
                rank_title,
                height=max(
                    500,
                    len(rank_df) * 48
                ),
                showlegend=False
            )

            topic_rank_layout[
                "margin"
            ] = dict(
                l=190,
                r=70,
                t=70,
                b=45
            )

            fig_topic_rank.update_layout(
                **topic_rank_layout,
                xaxis_title="留言數",
                yaxis_title=""
            )

            st.plotly_chart(
                fig_topic_rank,
                use_container_width=True
            )

        with chart_right:
            top_topic_names = (
                topic_summary_df
                .head(10)[
                    topic_column
                ]
                .astype(str)
                .tolist()
            )

            if "sentiment" in df.columns:
                stack_source = df[
                    df[
                        topic_column
                    ]
                    .astype(str)
                    .isin(
                        top_topic_names
                    )
                ]

                stack_df = (
                    stack_source
                    .groupby(
                        [
                            topic_column,
                            "sentiment"
                        ]
                    )
                    .size()
                    .reset_index(
                        name="留言數"
                    )
                )

                stack_df[
                    "主題總數"
                ] = (
                    stack_df
                    .groupby(
                        topic_column
                    )[
                        "留言數"
                    ]
                    .transform(
                        "sum"
                    )
                    .replace(
                        0,
                        1
                    )
                )

                stack_df[
                    "占比"
                ] = (
                    stack_df[
                        "留言數"
                    ]
                    / stack_df[
                        "主題總數"
                    ]
                    * 100
                )

                fig_topic_pct = px.bar(
                    stack_df,
                    x="占比",
                    y=topic_column,
                    color="sentiment",
                    orientation="h",
                    barmode="stack",
                    color_discrete_map=COLOR_MAP,
                    category_orders={
                        topic_column: list(
                            reversed(
                                top_topic_names
                            )
                        ),
                        "sentiment": [
                            "正面",
                            "中立",
                            "負面",
                            "提問"
                        ]
                    },
                    custom_data=[
                        "留言數"
                    ]
                )

                fig_topic_pct.update_traces(
                    hovertemplate=(
                        "主題：%{y}<br>"
                        "比例：%{x:.1f}%<br>"
                        "留言數：%{customdata[0]}"
                        "<extra></extra>"
                    )
                )

                fig_topic_pct.update_layout(
                    **chart_layout(
                        "各主題情緒結構（100%）",
                        height=max(
                            500,
                            len(
                                top_topic_names
                            ) * 48
                        )
                    ),
                    xaxis_title="情緒占比 (%)",
                    yaxis_title=""
                )

                fig_topic_pct.update_xaxes(
                    range=[
                        0,
                        100
                    ]
                )

                st.plotly_chart(
                    fig_topic_pct,
                    use_container_width=True
                )

        # -------------------------------------------------
        # 3. 聲量 × 負面率優先矩陣
        # -------------------------------------------------
        render_section_header(
            "PRIORITY MATRIX",
            "主題優先處理矩陣",
            "越靠右代表聲量越高；越往上代表負面比例越高"
        )

        priority_df = (
            topic_summary_df
            .head(15)
            .copy()
        )

        fig_priority = px.scatter(
            priority_df,
            x="留言數",
            y="負面率",
            size="留言數",
            color="風險等級",
            text=topic_column,
            hover_name=topic_column,
            hover_data={
                "留言數": True,
                "聲量占比": ":.1f",
                "正面率": ":.1f",
                "負面率": ":.1f",
                "提問率": ":.1f",
                "風險等級": True
            },
            color_discrete_map={
                "高風險": "#FF8B88",
                "需關注": "#F5C56B",
                "穩定": "#4ECAC2"
            },
            size_max=48
        )

        fig_priority.update_traces(
            textposition="top center"
        )

        fig_priority.update_layout(
            **chart_layout(
                "聲量 × 負面率：議題優先順序",
                height=520
            ),
            xaxis_title="留言聲量",
            yaxis_title="負面比例 (%)"
        )

        fig_priority.add_hline(
            y=30,
            line_dash="dash",
            line_color="#FF8B88",
            annotation_text="高風險 30%"
        )

        fig_priority.add_hline(
            y=15,
            line_dash="dot",
            line_color="#F5C56B",
            annotation_text="關注線 15%"
        )

        st.plotly_chart(
            fig_priority,
            use_container_width=True
        )

        # -------------------------------------------------
        # 4. 主題分類總表
        # -------------------------------------------------
        render_section_header(
            "TOPIC CLASSIFICATION",
            "主題分類與數據總表",
            "比較每個主題的分類、聲量、情緒結構與風險"
        )

        table_columns = [
            "排名",
            topic_column
        ]

        if "topic_category" in topic_summary_df.columns:
            table_columns.append(
                "topic_category"
            )

        table_columns += [
            "留言數",
            "聲量占比",
            "正面率",
            "中立率",
            "負面率",
            "提問率",
            "風險等級"
        ]

        if "topic_keywords" in topic_summary_df.columns:
            table_columns.append(
                "topic_keywords"
            )

        topic_table = (
            topic_summary_df[
                table_columns
            ]
            .copy()
        )

        topic_table = (
            topic_table
            .rename(
                columns={
                    topic_column: "主題名稱",
                    "topic_category": "上層分類",
                    "topic_keywords": "核心關鍵字",
                    "聲量占比": "聲量占比(%)",
                    "正面率": "正面(%)",
                    "中立率": "中立(%)",
                    "負面率": "負面(%)",
                    "提問率": "提問(%)"
                }
            )
        )

        st.dataframe(
            topic_table,
            use_container_width=True,
            hide_index=True,
            height=min(
                560,
                48
                + len(
                    topic_table
                ) * 38
            )
        )

        # -------------------------------------------------
        # 5. 單一主題詳細解讀
        # -------------------------------------------------
        render_section_header(
            "TOPIC DETAIL",
            "單一主題深度解讀",
            "選一個主題，看摘要、核心詞、情緒與代表留言"
        )

        selected_topic_name = (
            st.selectbox(
                "選擇要查看的主題",
                options=(
                    topic_summary_df[
                        topic_column
                    ]
                    .astype(str)
                    .tolist()
                ),
                key="topic_detail_selector"
            )
        )

        selected_topic_row = (
            topic_summary_df[
                topic_summary_df[
                    topic_column
                ]
                .astype(str)
                == str(
                    selected_topic_name
                )
            ]
            .iloc[0]
        )

        selected_topic_df = df[
            df[
                topic_column
            ]
            .astype(str)
            == str(
                selected_topic_name
            )
        ]

        category_text = str(
            selected_topic_row.get(
                "topic_category",
                "其他"
            )
        )

        summary_text = str(
            selected_topic_row.get(
                "topic_summary",
                ""
            )
        )

        keywords_text = str(
            selected_topic_row.get(
                "topic_keywords",
                ""
            )
        )

        st.markdown(
            f"""
            <div class="topic-insight-box">
                <b>{html.escape(str(selected_topic_name))}</b>
                ｜分類：{html.escape(category_text)}
                ｜聲量：{int(selected_topic_row["留言數"]):,} 則
                （{float(selected_topic_row["聲量占比"]):.1f}%）
                <br>
                {html.escape(summary_text) if summary_text and summary_text != "nan" else "此主題聚合語意相近的留言，可搭配下方代表留言進一步理解。"}
                <br>
                <b>核心關鍵字：</b>
                {html.escape(keywords_text) if keywords_text and keywords_text != "nan" else "尚無關鍵字資料"}
            </div>
            """,
            unsafe_allow_html=True
        )

        detail_k1, detail_k2, detail_k3, detail_k4 = (
            st.columns(4)
        )

        with detail_k1:
            render_kpi_card(
                "正面",
                f"{float(selected_topic_row['正面率']):.1f}%",
                "此主題正面留言比例",
                "mint"
            )

        with detail_k2:
            render_kpi_card(
                "中立",
                f"{float(selected_topic_row['中立率']):.1f}%",
                "此主題中立留言比例",
                "primary"
            )

        with detail_k3:
            render_kpi_card(
                "負面",
                f"{float(selected_topic_row['負面率']):.1f}%",
                f"風險：{selected_topic_row['風險等級']}",
                "coral"
            )

        with detail_k4:
            render_kpi_card(
                "提問",
                f"{float(selected_topic_row['提問率']):.1f}%",
                "此主題詢問／求助比例",
                "sky"
            )

        sample_comments = []

        if (
            comment_column
            and comment_column
            in selected_topic_df.columns
        ):
            if "sentiment" in selected_topic_df.columns:
                for sentiment_name in [
                    "負面",
                    "提問",
                    "正面",
                    "中立"
                ]:
                    sentiment_samples = (
                        selected_topic_df[
                            selected_topic_df[
                                "sentiment"
                            ]
                            == sentiment_name
                        ][
                            comment_column
                        ]
                        .dropna()
                        .astype(str)
                        .head(2)
                        .tolist()
                    )

                    for sample in sentiment_samples:
                        if sample not in sample_comments:
                            sample_comments.append(
                                sample
                            )

            if not sample_comments:
                sample_comments = (
                    selected_topic_df[
                        comment_column
                    ]
                    .dropna()
                    .astype(str)
                    .head(6)
                    .tolist()
                )

        with st.expander(
            "查看代表留言",
            expanded=True
        ):
            if sample_comments:
                for index, comment in enumerate(
                    sample_comments[:6],
                    start=1
                ):
                    st.markdown(
                        f"""
                        <div class="comment-line">
                            {index}. {html.escape(comment)}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info(
                    "目前沒有可顯示的代表留言。"
                )


# =========================================================
# 13-3 留言明細
# =========================================================
with comments_tab:
    render_section_header("DATA EXPLORER", "留言資料探索器", "篩選、排序並檢視原始留言與分析標籤")

    if st.session_state.crawled_data is not None and not df.empty:
        control1, control2, control3 = st.columns([1.1, 1.1, 2])

        sentiment_options = sorted(df["sentiment"].dropna().astype(str).unique().tolist()) if "sentiment" in df.columns else []
        with control1:
            selected_sentiments = st.multiselect(
                "情緒篩選",
                options=sentiment_options,
                default=sentiment_options
            )

        topic_column_name = topic_column
        topic_options = sorted(df[topic_column_name].dropna().astype(str).unique().tolist()) if topic_column_name else []
        with control2:
            selected_topics = st.multiselect(
                "主題篩選",
                options=topic_options,
                default=[]
            )

        with control3:
            keyword_filter = st.text_input("留言關鍵字搜尋", placeholder="輸入文字即可篩選留言內容")

        display_df = df.copy()
        if selected_sentiments and "sentiment" in display_df.columns:
            display_df = display_df[display_df["sentiment"].astype(str).isin(selected_sentiments)]
        if selected_topics and topic_column_name:
            display_df = display_df[display_df[topic_column_name].astype(str).isin(selected_topics)]

        comment_column_name = "comment" if "comment" in display_df.columns else ("jieba_cut" if "jieba_cut" in display_df.columns else None)
        if keyword_filter and comment_column_name:
            display_df = display_df[
                display_df[comment_column_name].astype(str).str.contains(keyword_filter, case=False, na=False)
            ]

        display_columns = [
            column for column in [
                "author",
                comment_column_name,
                "sentiment",
                "sentiment_score",
                topic_column_name,
                "time"
            ] if column and column in display_df.columns
        ]

        ui_df = display_df[display_columns].copy()
        rename_mapping = {
            "author": "帳號",
            "comment": "留言內容",
            "jieba_cut": "留言內容",
            "sentiment": "情緒極性",
            "sentiment_score": "情緒信心度",
            "time": "留言時間"
        }
        if topic_column_name:
            rename_mapping[topic_column_name] = "歸屬主題"
        ui_df = ui_df.rename(columns=rename_mapping)

        st.caption(f"目前顯示 {len(ui_df):,} 筆資料")
        st.dataframe(
            make_styled_table(ui_df),
            height=590,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.markdown(
            """
            <div class="empty-state">尚無留言資料可供檢視。</div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# 13-4 報告中心
# =========================================================
with report_tab:
    render_section_header("REPORTING CENTER", "決策報告與資料導出", "下載摘要資料與完整 Word 分析報告")

    if current_neg_rate > 30:
        risk_status = "危機型預警"
    elif current_neg_rate > 15:
        risk_status = "輕度風險"
    else:
        risk_status = "正常"

    current_target = (
        st.session_state.active_target_label
        or search_target
        or instagram_target
        or "尚未設定"
    )

    summary_report = pd.DataFrame({
        "監測指標": [
            "監測平台",
            "監測目標",
            "總留言聲量",
            "正面情緒比例",
            "中立比例",
            "負面情緒比例",
            "提問比例",
            "系統預警狀態",
            "內容情境",
            "報告產出日期"
        ],
        "數據結果": [
            platform,
            current_target,
            f"{total_comments_count} 則",
            f"{current_pos_rate:.1f}%",
            f"{current_neu_rate:.1f}%",
            f"{current_neg_rate:.1f}%",
            f"{current_question_rate:.1f}%",
            risk_status,
            video_type,
            str(datetime.date.today())
        ]
    })

    csv_data = summary_report.to_csv(index=False).encode("utf-8-sig")

    # =====================================================
    # 建立「完整留言分析 CSV」
    # =====================================================
    full_export_df = df.copy()

    export_column_candidates = [
        ("platform", "平台"),
        ("author", "帳號"),
        ("username", "帳號"),
        ("user", "帳號"),
        ("comment", "留言內容"),
        ("text", "留言內容"),
        ("content", "留言內容"),
        ("sentiment", "情緒"),
        ("sentiment_score", "情緒信心度"),
        ("confidence", "情緒信心度"),
        ("topic_name", "AI主題名稱"),
        ("topic_keywords", "BERTopic關鍵字"),
        ("time", "留言時間"),
        ("created_at", "留言時間"),
        ("published_at", "留言時間"),
        ("topic", "Topic ID"),
    ]

    selected_export_columns = []
    export_rename_mapping = {}
    used_display_names = set()

    for source_column, display_name in export_column_candidates:
        if (
            source_column in full_export_df.columns
            and display_name not in used_display_names
        ):
            selected_export_columns.append(source_column)
            export_rename_mapping[source_column] = display_name
            used_display_names.add(display_name)

    full_export_df = full_export_df[
        selected_export_columns
    ].copy()

    full_export_df = full_export_df.rename(
        columns=export_rename_mapping
    )

    # 如果原始資料沒有平台欄，直接補上目前平台
    if "平台" not in full_export_df.columns:
        full_export_df.insert(
            0,
            "平台",
            platform
        )

    # 清理文字欄位的空白與 NaN 顯示
    text_columns = [
        "平台",
        "帳號",
        "留言內容",
        "情緒",
        "AI主題名稱",
        "BERTopic關鍵字",
        "留言時間"
    ]

    for column_name in text_columns:
        if column_name in full_export_df.columns:
            full_export_df[column_name] = (
                full_export_df[column_name]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    # 信心度統一保留 3 位小數
    if "情緒信心度" in full_export_df.columns:
        full_export_df["情緒信心度"] = (
            pd.to_numeric(
                full_export_df["情緒信心度"],
                errors="coerce"
            )
            .round(3)
        )

    # Topic ID 統一轉成可讀整數
    if "Topic ID" in full_export_df.columns:
        full_export_df["Topic ID"] = (
            pd.to_numeric(
                full_export_df["Topic ID"],
                errors="coerce"
            )
            .astype("Int64")
        )

    # 去除完全重複列
    full_export_df = (
        full_export_df
        .drop_duplicates()
        .reset_index(drop=True)
    )

    full_csv_data = (
        full_export_df
        .to_csv(
            index=False
        )
        .encode("utf-8-sig")
    )

    report_info_col, report_action_col = st.columns([1.45, 1])

    with report_info_col:
        st.markdown(
            f"""
            <div class="glass-card">
                <div class="section-kicker">CURRENT REPORT</div>
                <div style="font-size:1.12rem;font-weight:800;color:#173A46;word-break:break-word;">
                    {html.escape(str(current_target))}
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem;margin-top:1rem;">
                    <div>
                        <div class="kpi-label">有效留言</div>
                        <div style="font-size:1.35rem;font-weight:900;color:#173A46;">{total_comments_count:,}</div>
                    </div>
                    <div>
                        <div class="kpi-label">負面比例</div>
                        <div style="font-size:1.35rem;font-weight:900;color:#FF8B88;">{current_neg_rate:.1f}%</div>
                    </div>
                    <div>
                        <div class="kpi-label">風險狀態</div>
                        <div style="font-size:1.02rem;font-weight:900;color:#1E8D89;">{html.escape(risk_status)}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with report_action_col:
        st.download_button(
            label="下載 CSV 摘要報告",
            data=csv_data,
            file_name=f"輿情監測摘要_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.download_button(
            label="下載完整留言分析 CSV",
            data=full_csv_data,
            file_name=(
                f"{platform}_完整留言分析_"
                f"{datetime.date.today()}.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

        word_report_path = resolve_output_path(st.session_state.word_report_path)
        if word_report_path and os.path.exists(word_report_path):
            try:
                with open(word_report_path, "rb") as word_file:
                    word_data = word_file.read()
                st.download_button(
                    label="下載完整 Word 決策報告",
                    data=word_data,
                    file_name=f"社群輿情決策報告_{datetime.date.today()}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as error:
                st.error(f"Word 檔案讀取失敗：{error}")
        elif st.session_state.crawled_data is not None:
            st.warning("分析已完成，但後端尚未回傳 Word 報告路徑。")
        else:
            st.button("尚未產生 Word 報告", disabled=True, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(
        make_styled_table(summary_report),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# 14. 頁尾
# =========================================================
st.markdown(
    """
    <div style="
        margin-top:2.3rem;
        padding-top:1rem;
        border-top:1px solid rgba(191,234,230,.85);
        color:#668390;
        font-size:.76rem;
        display:flex;
        justify-content:space-between;
        gap:1rem;
    ">
        <span>Social Insight Intelligence Platform</span>
        <span>YouTube · Dcard · Instagram · Hybrid Sentiment AI · BERTopic · MySQL · Word Report</span>
    </div>
    """,
    unsafe_allow_html=True
)