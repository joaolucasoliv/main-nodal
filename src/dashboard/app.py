"""
Nodal · Urban Changemakers of Latin America — interactive directory.
Run: streamlit run src/dashboard/app.py
"""
import csv
import re
import sys
import unicodedata
import base64
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px

from src.pipeline.ingest import load_csv, load_google_sheet, explode_multivalued
from src.pipeline.clean import clean
from src.pipeline import segment as seg
from src.analysis.insights import generate
from src.analysis.peers import peers_of
from src.dashboard.i18n import t
import sys, importlib
if "src.dashboard.i18n" in sys.modules:
    importlib.reload(sys.modules["src.dashboard.i18n"])

st.set_page_config(
    page_title="Nodal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette ──────────────────────────────────────────────────────────────────
INK         = "#111111"
MUTED       = "#6B6B6B"
SOFT        = "#EDEDED"
PAPER       = "#FFFFFF"
GREEN       = "#6FA83D"
GREEN_DARK  = "#4F7F28"
GREEN_SOFT  = "#E9F1DB"

# ── Session state ────────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "es"
if "selected_org" not in st.session_state:
    st.session_state.selected_org = None
if "search" not in st.session_state:
    st.session_state.search = ""
if "_route_applied" not in st.session_state:
    st.session_state._route_applied = None
if "_pending_scroll" not in st.session_state:
    st.session_state._pending_scroll = None
if "_directory_focus" not in st.session_state:
    st.session_state._directory_focus = None
if "route" not in st.session_state:
    st.session_state.route = "network"

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Fraunces:wght@600;700;800&display=swap');

    /* ── Theme tokens · light only ───────────────────────────────────────── */
    :root {{
        color-scheme: light only;
        --ink: #111111;
        --muted: #6B6B6B;
        --soft: #EDEDED;
        --paper: #FFFFFF;
        --green: #6FA83D;
        --green-dark: #4F7F28;
        --green-soft: #E9F1DB;
        --surface-warm: #FAF7F0;
        --surface-warm-soft: #F2ECE3;
        --surface-warm-edge: #ECE3D0;
        --hero-panel-from: #F6F2E8;
        --hero-panel-to: #FFFFFF;
        --hero-panel-edge: #E8E1D3;
        --card-from: #FFFFFF;
        --card-to: #F9F9F6;
        --tone-civic-from: #F3F8EC;
        --tone-civic-edge: #DAE7C8;
        --tone-public-from: #EEF3FB;
        --tone-public-edge: #DCE5F3;
        --tone-political-from: #F9EEF2;
        --tone-political-edge: #EBDCE1;
        --tone-business-from: #FFF5E3;
        --tone-business-edge: #F0E0BC;
        --tone-academia-from: #F1EEFB;
        --tone-academia-edge: #E1DAF3;
        --audience-inst-from: #14181F;
        --audience-inst-to: #1F252F;
        --audience-inst-text: #F5F1E6;
        --audience-inst-kicker: #C9D7B5;
        --gap-bg: #FFF7E5;
        --gap-edge: #F1E0B8;
        --gap-kicker: #7A541A;
        --traction-from: #FFFFFF;
        --traction-to: #F4F8EE;
        --traction-edge: #DAE7C8;
        --vision-from: #14181F;
        --vision-to: #1F252F;
        --vision-text: #F5F1E6;
        --vision-kicker: #C9D7B5;
        --pill-bg: var(--green-soft);
        --pill-text: var(--green-dark);
        --field-bg: rgba(255, 255, 255, 0.5);
        --field-border: rgba(0, 0, 0, 0.08);
        --shadow-card: 0 22px 50px -38px rgba(17, 17, 17, 0.4);
    }}

    /* CSS Magic Overlay for Clickable Cards */
    div[data-testid="stVerticalBlock"]:has(.magic-click) {{
        cursor: pointer !important;
    }}
    
    /* Make the .stButton totally invisible but functionally active in the DOM */
    div[data-testid="stVerticalBlock"]:has(.magic-click) > div.element-container .stButton button,
    div[data-testid="stVerticalBlock"]:has(.magic-click) > div[data-testid="stVerticalBlock"] > div.element-container .stButton button[kind="primary"] {{
        opacity: 0.01 !important;
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: -10 !important;
        overflow: hidden !important;
    }}

    /* Keep Visit Website button visually normal and clickable */
    div[data-testid="stVerticalBlock"]:has(.magic-click) div.visit-btn div[data-testid="stLinkButton"] {{
        position: relative !important;
        opacity: 1 !important;
        z-index: 20 !important;
    }}

    .stApp {{
        background-color: var(--paper);
    }}
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        background: #F1EFEC !important;
        border-right: 1px solid var(--surface-warm-edge);
    }}
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
        padding-top: 0.35rem;
    }}
    .sidebar-brand {{
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        padding: 0.15rem 0 0.5rem 0;
        margin-bottom: 0.45rem;
    }}
    .sidebar-brand img {{
        display: block;
        width: min(220px, 100%);
        height: auto;
        margin: 0 auto;
    }}
    
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: var(--field-bg) !important;
        border: 1px solid var(--field-border) !important;
        border-radius: 8px !important;
    }}

    [data-testid="stFileUploaderDropzone"] {{
        background-color: var(--field-bg) !important;
        border: 1.5px dashed var(--field-border) !important;
        border-radius: 8px !important;
    }}

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .block-container {{ padding-top: 3.5rem; padding-bottom: 5rem; max-width: 1200px; }}
    header[data-testid="stHeader"] {{ height: 0; background: transparent; }}

    h1 {{ font-family: 'Fraunces', Georgia, serif; font-size: 3.2rem; line-height: 1.02;
          letter-spacing: -0.02em; font-weight: 800; color: var(--ink);
          margin: 0.2rem 0 0.4rem 0; }}
    h2 {{ font-family: 'Inter'; font-size: 1.15rem; margin-top: 3rem; margin-bottom: 0.3rem;
          text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; color: var(--ink); }}
    h3 {{ font-size: 0.82rem; margin: 0.5rem 0 0.5rem 0; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }}

    .lede {{ color: var(--ink); font-size: 1.2rem; line-height: 1.5;
             max-width: 680px; margin: 0.8rem 0 1.2rem 0; font-weight: 400; }}
    .eyebrow {{ color: var(--green-dark); font-size: 0.78rem; text-transform: uppercase;
                letter-spacing: 0.2em; font-weight: 700; margin-bottom: 0.4rem; }}
    .note {{ color: var(--muted); font-size: 0.82rem; font-style: italic; line-height: 1.5; }}
    .intro {{ color: var(--muted); font-size: 0.95rem; margin: 0.2rem 0 1.2rem 0; max-width: 680px; }}
    hr.thick {{ border: none; border-top: 3px solid var(--ink); margin: 1.6rem 0 2rem 0; }}

    .stat {{ padding: 1rem 0; border-top: 1px solid var(--soft); }}
    .stat-label {{ color: var(--muted); font-size: 0.72rem; text-transform: uppercase;
                   letter-spacing: 0.12em; margin-bottom: 0.35rem; font-weight: 600; }}
    .stat-value {{ color: var(--ink); font-size: 2.2rem; font-weight: 700; line-height: 1;
                   font-variant-numeric: tabular-nums; font-family: 'Fraunces', Georgia, serif; }}
    .stat-unit {{ color: var(--muted); font-size: 0.8rem; margin-top: 0.3rem; }}

    .insight {{ padding: 1.3rem 0; border-top: 1px solid var(--soft); }}
    .insight-cat {{ color: var(--green-dark); font-size: 0.7rem; text-transform: uppercase;
                    letter-spacing: 0.15em; font-weight: 700; margin-bottom: 0.5rem; }}
    .insight-find {{ color: var(--ink); font-size: 1.15rem; font-weight: 600;
                     font-family: 'Fraunces', Georgia, serif;
                     line-height: 1.3; margin-bottom: 0.45rem; }}
    .insight-act {{ color: var(--muted); font-size: 0.96rem; line-height: 1.6; max-width: 780px; }}

    /* Directory card — the whole row is a clickable button */
    .stButton > button[kind="tertiary"],
    div[data-testid="stButton"] button[kind="tertiary"] {{
        text-align: left !important;
        background: white !important;
        color: var(--ink) !important;
        border: none !important;
        border-top: 1px solid var(--soft) !important;
        border-left: 3px solid transparent !important;
        border-radius: 0 !important;
        padding: 1.2rem 0.75rem 1.2rem 0.75rem !important;
        width: 100% !important;
        font-family: 'Inter' !important;
        font-weight: 400 !important;
        white-space: normal !important;
        line-height: 1.5 !important;
        transition: background 0.14s ease, border-left-color 0.14s ease !important;
    }}
    .stButton > button[kind="tertiary"]:hover {{
        background: var(--paper) !important;
        color: var(--ink) !important;
        border-left-color: var(--green) !important;
        cursor: pointer;
    }}

    /* Language & small pill buttons */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
        background: transparent !important;
        color: var(--muted) !important;
        border: 1px solid var(--soft) !important;
        border-radius: 999px !important;
        padding: 0.25rem 0.8rem !important;
        font-size: 0.82rem !important; min-height: 0 !important; height: auto !important;
    }}
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background: var(--ink) !important; color: white !important;
        border: 1px solid var(--ink) !important; border-radius: 999px !important;
        padding: 0.25rem 0.8rem !important;
        font-size: 0.82rem !important; min-height: 0 !important; height: auto !important;
    }}

    .stPlotlyChart {{ border: none; }}

    /* Focus pill style */
    .pill {{ display:inline-block; background:var(--green-soft); color:var(--green-dark);
             padding:0.22rem 0.7rem; border-radius:999px; font-size:0.78rem;
             font-weight:600; letter-spacing:0.04em; margin:0.15rem 0.2rem 0.15rem 0; }}
    .pill-muted {{ display:inline-block; background:var(--soft); color:var(--muted);
                   padding:0.22rem 0.7rem; border-radius:999px; font-size:0.78rem;
                   margin:0.15rem 0.2rem 0.15rem 0; }}

    /* Search input styling */
    div[data-testid="stTextInput"] input {{
        border: 1px solid var(--soft) !important;
        border-radius: 999px !important;
        padding: 0.6rem 1.1rem !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: var(--green) !important;
        box-shadow: 0 0 0 3px var(--green-soft) !important;
    }}

    /* Course card */
    .course-card {{
        background: white;
        border: 1px solid var(--soft);
        border-left: 4px solid var(--green);
        border-radius: 10px;
        padding: 1.5rem 1.8rem;
        margin: 0.9rem 0;
    }}
    .course-title {{
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: var(--ink);
        line-height: 1.1;
        letter-spacing: -0.01em;
        margin: 0.25rem 0 0.55rem 0;
    }}
    .course-meta {{
        color: var(--muted);
        font-size: 0.9rem;
        margin: 0.25rem 0 0.6rem 0;
        font-variant-numeric: tabular-nums;
    }}
    .course-desc {{
        color: var(--ink);
        font-size: 1rem;
        line-height: 1.55;
        margin: 0.55rem 0 0.85rem 0;
        max-width: 760px;
    }}
    .course-kv {{
        color: var(--ink);
        font-size: 0.9rem;
        margin: 0.35rem 0;
    }}
    .course-kv .k {{
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.72rem;
        font-weight: 700;
        margin-right: 0.5rem;
    }}
    a.course-cta {{
        display: inline-block;
        background: var(--green);
        color: white !important;
        padding: 0.6rem 1.3rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.92rem;
        text-decoration: none !important;
        margin-top: 0.8rem;
        transition: background 0.15s ease;
    }}
    a.course-cta:hover {{ background: var(--green-dark); transform: translateY(-1px); box-shadow: 0 6px 20px -8px rgba(111,168,61,0.55); }}

    /* ── Motion — subtle entrance for cards & stats ──────────────────────── */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .stat, .insight, .course-card, .peer-card, .contact-row {{
        animation: fadeInUp 0.42s ease both;
    }}

    /* Pill — small hover bloom */
    .pill, .pill-muted {{ transition: transform .15s ease, box-shadow .15s ease; }}
    .pill:hover {{ transform: translateY(-1px);
                   box-shadow: 0 4px 12px -6px rgba(111,168,61,0.45); }}

    /* Actor-class badge — small coloured chip */
    .class-badge {{
        display: inline-block;
        padding: 0.22rem 0.7rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-left: 0.55rem;
        vertical-align: 0.08em;
    }}
    .cb-institution   {{ background: #E7EEF8; color: #2F4A7A; }}
    .cb-civil_society {{ background: var(--green-soft); color: var(--green-dark); }}
    .cb-politician    {{ background: #F6E8EE; color: #8A2B50; }}
    .cb-entrepreneur  {{ background: #FFF2D6; color: #7A541A; }}
    .cb-company       {{ background: #ECECEC; color: #2E2E2E; }}
    .cb-professor     {{ background: #EAE6F8; color: #4F388B; }}
    .cb-researcher    {{ background: #E6F5F3; color: #1F6B63; }}

    /* Contact block inside profile */
    .contact-row {{
        display: flex; flex-wrap: wrap; gap: 0.55rem;
        margin: 0.6rem 0 1rem 0;
    }}
    .contact-chip {{
        display: inline-flex; align-items: center; gap: 0.45rem;
        padding: 0.55rem 1rem;
        border-radius: 999px;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none !important;
        transition: all .16s ease;
        border: 1px solid var(--soft);
    }}
    .chip-primary {{ background: var(--green); color: white !important; border-color: var(--green); }}
    .chip-primary:hover {{ background: var(--green-dark); border-color: var(--green-dark);
                           transform: translateY(-1px);
                           box-shadow: 0 8px 22px -8px rgba(111,168,61,0.6); }}
    .chip-ghost {{ background: white; color: var(--ink) !important; }}
    .chip-ghost:hover {{ border-color: var(--ink); transform: translateY(-1px); }}
    .chip-mute {{ background: var(--soft); color: var(--muted) !important; cursor: default; }}

    /* Peer card with why-matched pills */
    .peer-card {{
        padding: 0.85rem 0;
        border-top: 1px solid var(--soft);
        transition: background .15s ease, padding-left .15s ease;
    }}
    .peer-card:hover {{ background: var(--paper); padding-left: 0.4rem; }}
    .why-pill {{
        display: inline-block;
        background: white;
        border: 1px solid var(--soft);
        padding: 0.18rem 0.6rem 0.18rem 0.55rem;
        border-radius: 999px;
        font-size: 0.72rem;
        color: var(--ink);
        margin: 0.25rem 0.25rem 0 0;
    }}
    .why-pill .why-k {{
        color: var(--muted);
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-size: 0.62rem;
        margin-right: 0.4rem;
    }}

    /* Segmented control — larger, pill-y */
    div[data-testid="stSegmentedControl"] button {{
        border-radius: 999px !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        transition: all .16s ease !important;
    }}
    div[data-testid="stSegmentedControl"] button:hover {{
        border-color: var(--green) !important;
        color: var(--green-dark) !important;
    }}

    /* Refined hero */
    .lede {{ letter-spacing: -0.005em; }}
    h1 {{ background: linear-gradient(180deg, var(--ink) 0%, #3A3A3A 100%);
          -webkit-background-clip: text; background-clip: text;
          -webkit-text-fill-color: transparent; }}

    /* Hide the auto-rendered dialog title — the body has its own h1 */
    div[role="dialog"] h2 {{ display: none; }}

    /* Subtle green underline accent under top bar */
    .accent-line {{
        height: 2px; width: 100%;
        background: linear-gradient(90deg, transparent 0%, var(--green) 20%, var(--green-dark) 50%, var(--green) 80%, transparent 100%);
        opacity: 0.55;
        margin-top: 0.7rem;
    }}

    .hero-panel {{
        background: linear-gradient(180deg, var(--hero-panel-from) 0%, var(--hero-panel-to) 100%);
        border: 1px solid var(--hero-panel-edge);
        border-radius: 24px;
        padding: 1.3rem 1.35rem;
        box-shadow: 0 18px 45px -34px rgba(17, 17, 17, 0.45);
    }}
    .hero-panel-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}
    .hero-panel-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.15;
        margin-bottom: 0.9rem;
    }}
    .hero-points {{
        display: grid;
        gap: 0.75rem;
    }}
    .hero-point {{
        display: flex;
        gap: 0.7rem;
        align-items: flex-start;
        color: var(--ink);
        font-size: 0.95rem;
        line-height: 1.5;
    }}
    .hero-point-dot {{
        width: 0.65rem;
        height: 0.65rem;
        border-radius: 999px;
        background: linear-gradient(180deg, var(--green) 0%, var(--green-dark) 100%);
        flex: 0 0 0.65rem;
        margin-top: 0.32rem;
        box-shadow: 0 0 0 4px rgba(111, 168, 61, 0.12);
    }}
    .hero-metrics {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin-top: 1rem;
    }}
    .hero-metric {{
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid var(--soft);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
    }}
    .hero-metric-value {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 0.3rem;
    }}
    .hero-metric-label {{
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.35;
    }}
    .platform-grid {{
        display: grid;
        grid-template-columns: repeat(12, minmax(0, 1fr));
        gap: 1rem;
        margin: 1rem 0 0.5rem 0;
    }}
    .platform-card {{
        grid-column: span 4;
        border-radius: 22px;
        border: 1px solid var(--soft);
        padding: 1.2rem 1.2rem 1.15rem 1.2rem;
        min-height: 220px;
        background: linear-gradient(180deg, var(--card-from) 0%, var(--card-to) 100%);
        box-shadow: 0 20px 45px -38px rgba(17, 17, 17, 0.38);
    }}
    .platform-card.tone-civic {{
        background: linear-gradient(180deg, var(--tone-civic-from) 0%, var(--card-to) 100%);
        border-color: var(--tone-civic-edge);
    }}
    .platform-card.tone-public {{
        background: linear-gradient(180deg, var(--tone-public-from) 0%, var(--card-to) 100%);
        border-color: var(--tone-public-edge);
    }}
    .platform-card.tone-political {{
        background: linear-gradient(180deg, var(--tone-political-from) 0%, var(--card-to) 100%);
        border-color: var(--tone-political-edge);
    }}
    .platform-card.tone-business {{
        background: linear-gradient(180deg, var(--tone-business-from) 0%, var(--card-to) 100%);
        border-color: var(--tone-business-edge);
    }}
    .platform-card.tone-academia {{
        background: linear-gradient(180deg, var(--tone-academia-from) 0%, var(--card-to) 100%);
        border-color: var(--tone-academia-edge);
    }}
    .platform-card.tone-beta {{
        background: linear-gradient(180deg, #1A1A1A 0%, #2C2C2C 100%);
        border-color: #2A2A2A;
    }}
    .platform-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 700;
        margin-bottom: 0.55rem;
    }}
    .platform-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.12;
        margin-bottom: 0.65rem;
    }}
    .platform-desc {{
        color: var(--ink);
        font-size: 0.96rem;
        line-height: 1.55;
        margin-bottom: 1.05rem;
    }}
    .platform-meta {{
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.45;
    }}
    .platform-meta strong {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.2rem;
        font-weight: 700;
        margin-right: 0.15rem;
    }}
    .platform-card.tone-beta .platform-kicker,
    .platform-card.tone-beta .platform-title,
    .platform-card.tone-beta .platform-desc,
    .platform-card.tone-beta .platform-meta,
    .platform-card.tone-beta .platform-meta strong,
    .platform-card.tone-beta .platform-footer {{
        color: #FFFFFF;
    }}
    .platform-card.tone-beta .platform-meta,
    .platform-card.tone-beta .platform-footer {{
        color: rgba(255, 255, 255, 0.78);
    }}
    /* Breathing room between every platform card and the CTA button below it */
    .platform-card {{
        margin-bottom: 0.75rem;
    }}
    /* Vertical gap between consecutive leader cards in the directory grid */
    .leader-card-spacer {{
        height: 1.9rem;
    }}
    .platform-footer {{
        margin-top: 0.7rem;
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.45;
    }}

    /* ── Dual-audience entry strip ───────────────────────────────────────── */
    .audience-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.1rem;
        margin: 1.4rem 0 0.4rem 0;
    }}
    .audience-card {{
        position: relative;
        border-radius: 22px;
        padding: 1.4rem 1.5rem 1.55rem 1.5rem;
        border: 1px solid var(--soft);
        background: linear-gradient(180deg, var(--card-from) 0%, var(--surface-warm) 100%);
        box-shadow: var(--shadow-card);
        transition: transform .18s ease, box-shadow .18s ease;
    }}
    .audience-card.audience-inst {{
        background: linear-gradient(180deg, var(--audience-inst-from) 0%, var(--audience-inst-to) 100%);
        border-color: var(--audience-inst-from);
    }}
    .audience-card.audience-inst .audience-kicker,
    .audience-card.audience-inst .audience-title,
    .audience-card.audience-inst .audience-copy {{ color: var(--audience-inst-text); }}
    .audience-card.audience-inst .audience-kicker {{ color: var(--audience-inst-kicker); }}
    .audience-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 26px 60px -36px rgba(17,17,17,0.45);
    }}
    .audience-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }}
    .audience-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.4rem;
        font-weight: 700;
        line-height: 1.18;
        margin-bottom: 0.6rem;
    }}
    .audience-copy {{
        color: var(--ink);
        font-size: 0.96rem;
        line-height: 1.55;
        margin-bottom: 0.75rem;
    }}

    /* ── Partners strip ──────────────────────────────────────────────────── */
    .partners-block {{
        background: var(--surface-warm);
        border: 1px solid var(--surface-warm-edge);
        border-radius: 22px;
        padding: 1.6rem 1.7rem 1.55rem 1.7rem;
        margin: 1.6rem 0 0.6rem 0;
    }}
    .partners-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .partners-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.18;
        margin-bottom: 0.5rem;
    }}
    .partners-copy {{
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.55;
        max-width: 760px;
        margin-bottom: 1.1rem;
    }}
    .partners-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.9rem;
    }}
    .partners-segment {{
        background: white;
        border: 1px solid var(--soft);
        border-radius: 16px;
        padding: 0.85rem 1rem 0.95rem 1rem;
    }}
    .partners-segment-label {{
        color: var(--muted);
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .partners-segment-list {{
        color: var(--ink);
        font-size: 0.96rem;
        line-height: 1.45;
        font-weight: 600;
    }}

    /* ── Traction metrics block ─────────────────────────────────────────── */
    .traction-block {{
        background: linear-gradient(180deg, var(--traction-from) 0%, var(--traction-to) 100%);
        border: 1px solid var(--traction-edge);
        border-radius: 24px;
        padding: 1.8rem 1.9rem 1.7rem 1.9rem;
        margin: 1.8rem 0 0.6rem 0;
    }}
    .traction-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .traction-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.7rem;
        font-weight: 700;
        line-height: 1.15;
        margin-bottom: 0.55rem;
    }}
    .traction-copy {{
        color: var(--muted);
        font-size: 0.97rem;
        line-height: 1.55;
        max-width: 760px;
        margin-bottom: 1.4rem;
    }}
    .traction-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 1rem;
    }}
    .traction-cell {{
        background: white;
        border: 1px solid var(--soft);
        border-radius: 18px;
        padding: 1rem 1.1rem 1.05rem 1.1rem;
    }}
    .traction-value {{
        color: var(--green-dark);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 0.45rem;
    }}
    .traction-label {{
        color: var(--ink);
        font-size: 0.9rem;
        line-height: 1.45;
    }}

    /* ── Products grid (PDF §6 — what NODAL delivers) ───────────────────── */
    .products-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1.1rem;
        margin: 1.1rem 0 0.5rem 0;
    }}
    .product-card {{
        background: white;
        border: 1px solid var(--soft);
        border-left: 4px solid var(--green);
        border-radius: 18px;
        padding: 1.2rem 1.3rem 1.25rem 1.3rem;
        transition: transform .18s ease, box-shadow .18s ease;
    }}
    .product-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 26px 50px -36px rgba(17,17,17,0.32);
    }}
    .product-kicker {{
        color: var(--green-dark);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .product-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.25rem;
        font-weight: 700;
        line-height: 1.18;
        margin-bottom: 0.55rem;
    }}
    .product-desc {{
        color: var(--ink);
        font-size: 0.95rem;
        line-height: 1.55;
        margin-bottom: 0.7rem;
    }}
    .product-meta {{
        color: var(--muted);
        font-size: 0.85rem;
    }}

    /* ── Propose section (helpers used in the join-network area) ─────────── */
    .propose-hero {{
        background: linear-gradient(180deg, var(--surface-warm) 0%, var(--paper) 100%);
        border: 1px solid var(--surface-warm-edge);
        border-radius: 22px;
        padding: 1.6rem 1.7rem 1.5rem 1.7rem;
        margin-bottom: 1rem;
    }}
    .propose-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .propose-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.5rem;
        font-weight: 700;
        line-height: 1.18;
        margin-bottom: 0.55rem;
    }}
    .propose-copy {{
        color: var(--ink);
        font-size: 0.96rem;
        line-height: 1.55;
        margin-bottom: 1rem;
    }}
    .propose-list {{
        display: grid;
        gap: 0.5rem;
        margin-bottom: 0.9rem;
    }}
    .propose-item {{
        display: flex;
        gap: 0.6rem;
        align-items: flex-start;
        color: var(--ink);
        font-size: 0.92rem;
        line-height: 1.5;
    }}
    .propose-item-dot {{
        width: 0.55rem; height: 0.55rem;
        border-radius: 999px;
        background: var(--green);
        flex: 0 0 0.55rem;
        margin-top: 0.42rem;
        box-shadow: 0 0 0 4px rgba(111,168,61,0.15);
    }}
    .propose-trust {{
        color: var(--muted);
        font-size: 0.82rem;
        font-style: italic;
    }}
    .propose-forms-kicker {{
        color: var(--green-dark);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 700;
        margin: 0.6rem 0 0.3rem 0;
    }}
    .propose-forms-note {{
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }}
    .propose-route-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.85rem;
        margin-bottom: 0.6rem;
    }}
    .propose-route-card {{
        background: white;
        border: 1px solid var(--soft);
        border-left: 4px solid var(--green);
        border-radius: 14px;
        padding: 0.95rem 1.1rem;
    }}
    .propose-route-kicker {{
        color: var(--green-dark);
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }}
    .propose-route-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }}
    .propose-route-copy {{
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.45;
    }}

    /* ── App-shell sidebar nav ──────────────────────────────────────────── */
    .sidebar-section-label {{
        color: var(--muted);
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin: 0.4rem 0 0.55rem 0;
    }}
    .sidebar-nav-sub {{
        color: var(--muted);
        font-size: 0.78rem;
        line-height: 1.35;
        margin: -0.15rem 0 0.55rem 0.15rem;
        padding-left: 0.05rem;
    }}
    .sidebar-divider {{
        border: none;
        border-top: 1px solid var(--surface-warm-edge);
        margin: 0.85rem 0 0.95rem 0;
    }}
    /* Sidebar nav buttons — flat, left-aligned, distinct active state */
    [data-testid="stSidebar"] div[data-testid="stButton"] button {{
        text-align: left !important;
        justify-content: flex-start !important;
        font-weight: 600 !important;
        letter-spacing: 0 !important;
        border-radius: 12px !important;
        border: 1px solid transparent !important;
        padding: 0.5rem 0.85rem !important;
        font-size: 0.95rem !important;
        background: transparent !important;
        color: var(--ink) !important;
        text-transform: none !important;
        transition: background .15s ease, border-color .15s ease, color .15s ease !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stButton"] button:hover {{
        background: rgba(255, 255, 255, 0.6) !important;
        border-color: var(--surface-warm-edge) !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {{
        background: var(--ink) !important;
        color: var(--paper) !important;
        border-color: var(--ink) !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]:hover {{
        background: var(--ink) !important;
    }}

    /* Page header used at the top of each route */
    .page-header {{
        margin: 0.4rem 0 1.6rem 0;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--soft);
    }}
    .page-header-eyebrow {{
        color: var(--green-dark);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .page-header-title {{
        font-family: 'Fraunces', Georgia, serif;
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -0.01em;
        color: var(--ink);
        margin-bottom: 0.4rem;
    }}
    .page-header-subtitle {{
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
        max-width: 720px;
    }}

    /* Sticky search/toolbar inside the Network route */
    .network-toolbar {{
        position: sticky;
        top: 0;
        z-index: 5;
        background: var(--paper);
        padding: 0.6rem 0 0.55rem 0;
        margin: 0 0 0.9rem 0;
        border-bottom: 1px solid var(--soft);
    }}
    /* Map column on Network route — keep the LEFT column sticky to top while the
       RIGHT column scrolls. Targeting the column itself (not just the inner div)
       avoids the "hole" of empty whitespace under the map. */
    [data-testid="stHorizontalBlock"]:has(.network-map-sticky) > [data-testid="stColumn"]:first-child {{
        position: sticky;
        top: 4.5rem;
        align-self: flex-start;
        height: fit-content;
        z-index: 2;
    }}
    .network-map-sticky {{
        /* class is just a marker for the :has() selector above */
    }}

    /* ── Vision close (PDF §9) ──────────────────────────────────────────── */
    .vision-block {{
        background: linear-gradient(135deg, var(--vision-from) 0%, var(--vision-to) 100%);
        border-radius: 28px;
        padding: 2.6rem 2.2rem 2.6rem 2.2rem;
        margin: 2.4rem 0 1rem 0;
        text-align: center;
        color: var(--vision-text);
        box-shadow: 0 30px 70px -40px rgba(0,0,0,0.55);
    }}
    .vision-kicker {{
        color: var(--vision-kicker);
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.22em;
        font-weight: 700;
        margin-bottom: 0.85rem;
    }}
    .vision-quote {{
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.3;
        letter-spacing: -0.005em;
        max-width: 820px;
        margin: 0 auto;
    }}

    /* ── Talent gap insight (PDF §4) ─────────────────────────────────────── */
    .gap-block {{
        background: var(--gap-bg);
        border: 1px solid var(--gap-edge);
        border-radius: 22px;
        padding: 1.5rem 1.7rem 1.55rem 1.7rem;
        margin: 1.6rem 0 0.6rem 0;
    }}
    .gap-kicker {{
        color: var(--gap-kicker);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }}
    .gap-title {{
        color: var(--ink);
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.18;
        margin-bottom: 0.5rem;
    }}
    .gap-copy {{
        color: var(--ink);
        font-size: 0.97rem;
        line-height: 1.55;
        max-width: 780px;
    }}

    @media (max-width: 980px) {{
        .hero-metrics {{
            grid-template-columns: 1fr;
        }}
        .platform-card {{
            grid-column: 1 / -1;
            min-height: 0;
        }}
        .sidebar-metrics {{
            grid-template-columns: 1fr;
        }}
        .propose-route-grid {{
            grid-template-columns: 1fr;
        }}
        .audience-grid,
        .partners-grid,
        .traction-grid,
        .products-grid {{
            grid-template-columns: 1fr;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# ── Top bar ──────────────────────────────────────────────────────────────────
bar_l, _, bar_r1, bar_r2 = st.columns([6, 3.5, 0.8, 0.8])
with bar_l:
    st.markdown(
        f'<div style="font-weight:800; font-size:1.05rem; color:var(--ink); padding-top:0.35rem;">'
        f'<span style="color:var(--green-dark);">●</span>&nbsp; Sistema Urbano | Nodal &nbsp;<span style="color:var(--green-dark);">●</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with bar_r1:
    if st.button("ES",
                 type="primary" if st.session_state.lang == "es" else "secondary",
                 key="lang_es", use_container_width=True):
        st.session_state.lang = "es"; st.rerun()
with bar_r2:
    if st.button("EN",
                 type="primary" if st.session_state.lang == "en" else "secondary",
                 key="lang_en", use_container_width=True):
        st.session_state.lang = "en"; st.rerun()

st.markdown('<div class="accent-line"></div>', unsafe_allow_html=True)

lang = st.session_state.lang

# ── Data ─────────────────────────────────────────────────────────────────────
SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "urban_changemakers_latam.csv"

@st.cache_data(show_spinner=False)
def get_data(source: str, sheet_id: str = "", uploaded=None) -> pd.DataFrame:
    if source == "Google Sheet" and sheet_id:
        raw = load_google_sheet(sheet_id)
    elif source == "Upload CSV" and uploaded is not None:
        raw = pd.read_csv(uploaded)
    else:
        raw = load_csv(SAMPLE_PATH)
    return explode_multivalued(clean(raw))

PAPERS_PATH = Path(__file__).parent.parent.parent / "data" / "papers_database.csv"
COURSES_PATH = Path(__file__).parent.parent.parent / "data" / "courses_2026.csv"
COURSE_HUB_URL = "https://sistemaurbano.org/nodal"

@st.cache_data(show_spinner=False)
def load_papers(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    p = pd.read_csv(path)
    if "focus_areas" in p.columns:
        p["focus_areas"] = p["focus_areas"].fillna("").apply(
            lambda s: [x.strip() for x in str(s).split(";") if x.strip()]
        )
    return p

@st.cache_data(show_spinner=False)
def load_courses(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    c = pd.read_csv(path)
    for date_col in ("start_date", "end_date"):
        if date_col in c.columns:
            c[date_col] = pd.to_datetime(c[date_col], errors="coerce")
    for col in ("instructors", "focus_areas", "includes"):
        if col in c.columns:
            c[col] = c[col].fillna("").apply(
                lambda s: [x.strip() for x in str(s).split(";") if x.strip()]
            )
        else:
            c[col] = [[] for _ in range(len(c))]
    return c

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def fmt_date_range(start, end, lang: str) -> str:
    if pd.isna(start) or pd.isna(end):
        return ""
    if lang == "es":
        if start.month == end.month and start.year == end.year:
            return f"{start.day}–{end.day} de {MONTHS_ES[start.month-1]} {start.year}"
        return (f"{start.day} {MONTHS_ES[start.month-1]} – "
                f"{end.day} {MONTHS_ES[end.month-1]} {start.year}")
    if start.month == end.month and start.year == end.year:
        return f"{start.strftime('%b')} {start.day}–{end.day}, {start.year}"
    return f"{start.strftime('%b')} {start.day} – {end.strftime('%b')} {end.day}, {start.year}"

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_courses = load_courses(COURSES_PATH)
    sidebar_today = pd.Timestamp.today().normalize()
    sidebar_upcoming = (
        sidebar_courses[sidebar_courses["end_date"] >= sidebar_today].sort_values("start_date")
        if not sidebar_courses.empty else pd.DataFrame()
    )
    sidebar_course_url = (
        str(sidebar_upcoming.iloc[0].get("register_url")).strip()
        if not sidebar_upcoming.empty and pd.notna(sidebar_upcoming.iloc[0].get("register_url"))
        else COURSE_HUB_URL
    )
    LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo.png"
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div class="sidebar-brand"><img src="data:image/png;base64,{b64}" alt="NODAL"></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div style="font-weight:800; font-size:1.3rem; color:var(--ink);">'
                    f'<span style="color:var(--green-dark);">●</span>&nbsp; NODAL</div>',
                    unsafe_allow_html=True)
    st.caption(t("sb_tag", lang))

    # ── Route navigation ────────────────────────────────────────────────────
    ROUTES = [
        ("network",      "route_network",      "route_network_sub"),
        ("research",     "route_research",     "route_research_sub"),
        ("courses",      "route_courses",      "route_courses_sub"),
        ("intelligence", "route_intel",        "route_intel_sub"),
        ("about",        "route_about",        "route_about_sub"),
    ]
    st.markdown(f'<div class="sidebar-section-label">{t("nav_section", lang)}</div>',
                unsafe_allow_html=True)
    for route_key, label_key, sub_key in ROUTES:
        is_active = st.session_state.route == route_key
        cls = "sidebar-nav-item" + (" sidebar-nav-active" if is_active else "")
        if st.button(t(label_key, lang),
                     key=f"nav_{route_key}",
                     use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.route = route_key
            st.rerun()
        st.markdown(
            f'<div class="sidebar-nav-sub">{t(sub_key, lang)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # ── Data source (always available) ──────────────────────────────────────
    st.markdown(f"### {t('sb_source', lang)}")
    source_label_map = {
        t("sb_curated", lang): "curated",
        t("sb_sheet", lang):   "sheet",
        t("sb_upload", lang):  "upload",
    }
    source_choice = st.radio("Source", list(source_label_map.keys()),
                             label_visibility="collapsed")
    source_key = source_label_map[source_choice]

    if source_key == "sheet":
        sheet_id = st.text_input(t("sb_sheet_id", lang))
        df = get_data("Google Sheet", sheet_id=sheet_id)
    elif source_key == "upload":
        uploaded_file = st.file_uploader(t("sb_csv", lang), type="csv")
        df = get_data("Upload CSV", uploaded=uploaded_file)
    else:
        df = get_data("Curated")

    # ── Filters: only relevant on Network and Intelligence routes ───────────
    if st.session_state.route in ("network", "intelligence"):
        st.markdown(f"### {t('sb_filters', lang)}")
        sel_types = st.multiselect(t("sb_type", lang),
                                   sorted(df["type"].dropna().unique()),
                                   default=sorted(df["type"].dropna().unique()))
        sel_countries = st.multiselect(t("sb_country", lang),
                                       sorted(df["country"].dropna().unique()),
                                       default=sorted(df["country"].dropna().unique()))
        all_focus = sorted({f for lst in df["focus_areas"] for f in lst})
        sel_focus = st.multiselect(t("sb_focus", lang), all_focus, default=all_focus)
    else:
        sel_types = sorted(df["type"].dropna().unique())
        sel_countries = sorted(df["country"].dropna().unique())
        sel_focus = sorted({f for lst in df["focus_areas"] for f in lst})

    # An empty multiselect means "no filter" rather than "match nothing" —
    # otherwise clearing a chip wipes the whole dashboard.
    type_ok    = df["type"].isin(sel_types)         if sel_types     else True
    country_ok = df["country"].isin(sel_countries)  if sel_countries else True
    if sel_focus:
        focus_ok = df["focus_areas"].apply(
            lambda lst: any(f in sel_focus for f in lst) or not lst
        )
    else:
        focus_ok = True
    df_base = df[type_ok & country_ok & focus_ok]

    st.markdown(
        f'<div class="sidebar-panel">'
        f'<div class="sidebar-panel-kicker">{t("sb_panel_kicker", lang)}</div>'
        f'<div class="sidebar-panel-title">{t("sb_panel_title", lang)}</div>'
        f'<div class="sidebar-metrics">'
        f'<div class="sidebar-metric"><div class="sidebar-metric-value">{len(df_base)}</div><div class="sidebar-metric-label">{t("sb_metric_profiles", lang)}</div></div>'
        f'<div class="sidebar-metric"><div class="sidebar-metric-value">{df_base["country"].nunique()}</div><div class="sidebar-metric-label">{t("sb_metric_countries", lang)}</div></div>'
        f'<div class="sidebar-metric"><div class="sidebar-metric-value">{len(sidebar_upcoming)}</div><div class="sidebar-metric-label">{t("sb_metric_courses", lang)}</div></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# Apply search on top of filters
search_term = st.session_state.search.strip().lower()
if search_term:
    mask = (
        df_base["name"].str.lower().str.contains(search_term, na=False)
        | df_base["city"].str.lower().str.contains(search_term, na=False)
        | df_base["country"].str.lower().str.contains(search_term, na=False)
    )
    df_f = df_base[mask]
else:
    df_f = df_base

def slugify(s: str) -> str:
    """Turn 'Cali Cómo Vamos' into 'cali-como-vamos' — clean URLs, stable across langs."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s).strip().lower()
    return re.sub(r"[\s_-]+", "-", s) or "x"

name_by_slug = {slugify(n): n for n in df["name"]}

# Deep-link: ?org=slug-or-name opens the profile once per session.
# (Without the guard, closing the dialog would trigger an infinite re-open loop.)
_qp_raw = st.query_params.get("org")
_qp_org = _qp_raw[0] if isinstance(_qp_raw, list) else _qp_raw
if (
    _qp_org
    and st.session_state.selected_org is None
    and not st.session_state.get("_deep_linked")
):
    target = name_by_slug.get(_qp_org) or (_qp_org if _qp_org in set(df["name"]) else None)
    if target:
        st.session_state.selected_org = target
        st.session_state._deep_linked = True

_qp_route_raw = st.query_params.get("route")
_qp_route = _qp_route_raw[0] if isinstance(_qp_route_raw, list) else _qp_route_raw
if _qp_route in {"all", "institution", "civil_society", "politician", "entrepreneur", "company", "professor", "researcher"}:
    if st.session_state._route_applied != _qp_route:
        st.session_state.directory_tab = _qp_route
        st.session_state.search = ""
        st.session_state._route_applied = _qp_route
        st.session_state._pending_scroll = "connect-hub"
else:
    st.session_state._route_applied = None

# Class-badge helper
CLASS_KEYS = ["institution", "civil_society", "politician", "entrepreneur", "company", "professor", "researcher"]

def class_badge_html(actor_class: str, lang: str) -> str:
    label = t(f"cls_{actor_class}", lang) if actor_class in CLASS_KEYS else actor_class
    return f'<span class="class-badge cb-{actor_class}">{label}</span>'

CLASS_TONES = {
    "institution": "#2F4A7A",
    "civil_society": GREEN_DARK,
    "politician": "#8A2B50",
    "entrepreneur": "#7A541A",
    "company": "#2E2E2E",
    "professor": "#4F388B",
    "researcher": "#1F6B63",
}

def class_tone(actor_class: str) -> str:
    return CLASS_TONES.get(actor_class, MUTED)

def truncate_text(text: str, max_chars: int = 200) -> str:
    s = str(text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"

def propose_item_html(text: str) -> str:
    return (
        '<div class="propose-item">'
        '<span class="propose-item-dot"></span>'
        f'<span>{text}</span>'
        '</div>'
    )

def propose_route_card_html(kicker: str, title: str, copy: str) -> str:
    return (
        '<div class="propose-route-card">'
        f'<div class="propose-route-kicker">{kicker}</div>'
        f'<div class="propose-route-title">{title}</div>'
        f'<div class="propose-route-copy">{copy}</div>'
        '</div>'
    )

papers = load_papers(PAPERS_PATH)
courses = load_courses(COURSES_PATH)
today = pd.Timestamp.today().normalize()
upcoming = (
    courses[courses["end_date"] >= today].sort_values("start_date")
    if not courses.empty else pd.DataFrame()
)

def preferred_tab(*classes: str) -> str:
    """Pick the actor_class with the most entries among the candidates; first one wins ties."""
    counts = {c: actor_count(df_f, c) for c in classes}
    return max(counts, key=lambda c: (counts[c], -classes.index(c)))

def actor_count(frame: pd.DataFrame, *classes: str) -> int:
    if frame.empty or "actor_class" not in frame.columns:
        return 0
    return int(frame["actor_class"].isin(classes).sum())

def hero_point_html(text: str) -> str:
    return (
        '<div class="hero-point">'
        '<span class="hero-point-dot"></span>'
        f"<span>{text}</span>"
        "</div>"
    )

def platform_card_html(kicker: str, title: str, desc: str, meta: str, tone: str, footer: str = "") -> str:
    footer_html = f'<div class="platform-footer">{footer}</div>' if footer else ""
    return (
        f'<div class="platform-card tone-{tone}">'
        f'<div class="platform-kicker">{kicker}</div>'
        f'<div class="platform-title">{title}</div>'
        f'<div class="platform-desc">{desc}</div>'
        f'<div class="platform-meta">{meta}</div>'
        f'{footer_html}'
        "</div>"
    )

PARTNER_SEGMENTS = [
    ("partners_segment_global", "ARUP · Vinci"),
    ("partners_segment_mobility", "Uber · Yango"),
    ("partners_segment_industry", "UNACEM"),
    ("partners_segment_dev", "UNNA · Sistema Urbano"),
]

def render_audience_strip() -> None:
    inst_html = (
        f'<div class="audience-card audience-inst">'
        f'<div class="audience-kicker">{t("audience_inst_kicker", lang)}</div>'
        f'<div class="audience-title">{t("audience_inst_title", lang)}</div>'
        f'<div class="audience-copy">{t("audience_inst_copy", lang)}</div>'
        f'</div>'
    )
    pract_html = (
        f'<div class="audience-card">'
        f'<div class="audience-kicker">{t("audience_pract_kicker", lang)}</div>'
        f'<div class="audience-title">{t("audience_pract_title", lang)}</div>'
        f'<div class="audience-copy">{t("audience_pract_copy", lang)}</div>'
        f'</div>'
    )
    st.markdown(
        f'<div class="audience-grid">{inst_html}{pract_html}</div>',
        unsafe_allow_html=True,
    )
    cta_l, cta_r = st.columns(2, gap="large")
    with cta_l:
        st.link_button(
            t("audience_inst_cta", lang),
            "mailto:nodal@sistemaurbano.org?subject=NODAL%20institutional%20inquiry",
            use_container_width=True,
        )
    with cta_r:
        if st.button(t("audience_pract_cta", lang),
                     key="audience_pract_btn",
                     type="primary",
                     use_container_width=True):
            st.session_state._pending_scroll = "join-network"
            st.rerun()

def render_partners_strip() -> None:
    segments_html = "".join(
        f'<div class="partners-segment">'
        f'<div class="partners-segment-label">{t(label_key, lang)}</div>'
        f'<div class="partners-segment-list">{names}</div>'
        f'</div>'
        for label_key, names in PARTNER_SEGMENTS
    )
    st.markdown(
        f'<div class="partners-block">'
        f'<div class="partners-kicker">{t("partners_kicker", lang)}</div>'
        f'<div class="partners-title">{t("partners_title", lang)}</div>'
        f'<div class="partners-copy">{t("partners_copy", lang)}</div>'
        f'<div class="partners-grid">{segments_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_products() -> None:
    st.markdown(f'<div class="eyebrow">{t("products_kicker", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f"## {t('products_title', lang)}")
    st.markdown(f'<div class="intro">{t("products_intro", lang)}</div>', unsafe_allow_html=True)

    cards = [
        {
            "kicker": t("product_intel_kicker", lang),
            "title":  t("product_intel_title", lang),
            "desc":   t("product_intel_desc", lang),
            "meta":   t("product_meta_actors", lang, n=len(df_f)),
        },
        {
            "kicker": t("product_activation_kicker", lang),
            "title":  t("product_activation_title", lang),
            "desc":   t("product_activation_desc", lang),
            "meta":   t("product_meta_courses", lang, n=len(upcoming)),
        },
        {
            "kicker": t("product_marketplace_kicker", lang),
            "title":  t("product_marketplace_title", lang),
            "desc":   t("product_marketplace_desc", lang),
            "meta":   t("product_meta_actors", lang, n=len(df_f)),
        },
        {
            "kicker": t("product_data_kicker", lang),
            "title":  t("product_data_title", lang),
            "desc":   t("product_data_desc", lang),
            "meta":   t("product_meta_research", lang, n=len(papers)),
        },
    ]
    cards_html = "".join(
        f'<div class="product-card">'
        f'<div class="product-kicker">{c["kicker"]}</div>'
        f'<div class="product-title">{c["title"]}</div>'
        f'<div class="product-desc">{c["desc"]}</div>'
        f'<div class="product-meta">{c["meta"]}</div>'
        f'</div>'
        for c in cards
    )
    st.markdown(f'<div class="products-grid">{cards_html}</div>', unsafe_allow_html=True)

def render_traction_block() -> None:
    metrics = [
        ("traction_metric_social_value",     "traction_metric_social_label"),
        ("traction_metric_advisory_value",   "traction_metric_advisory_label"),
        ("traction_metric_membership_value", "traction_metric_membership_label"),
        ("traction_metric_waitlist_value",   "traction_metric_waitlist_label"),
        ("traction_metric_revenue_value",    "traction_metric_revenue_label"),
        ("traction_metric_clients_value",    "traction_metric_clients_label"),
    ]
    cells_html = "".join(
        f'<div class="traction-cell">'
        f'<div class="traction-value">{t(v, lang)}</div>'
        f'<div class="traction-label">{t(l, lang)}</div>'
        f'</div>'
        for v, l in metrics
    )
    st.markdown(
        f'<div class="traction-block">'
        f'<div class="traction-kicker">{t("traction_kicker", lang)}</div>'
        f'<div class="traction-title">{t("traction_title", lang)}</div>'
        f'<div class="traction-copy">{t("traction_copy", lang)}</div>'
        f'<div class="traction-grid">{cells_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_gap_insight() -> None:
    st.markdown(
        f'<div class="gap-block">'
        f'<div class="gap-kicker">{t("gap_kicker", lang)}</div>'
        f'<div class="gap-title">{t("gap_title", lang)}</div>'
        f'<div class="gap-copy">{t("gap_copy", lang)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_vision_close() -> None:
    st.markdown(
        f'<div class="vision-block">'
        f'<div class="vision-kicker">{t("vision_kicker", lang)}</div>'
        f'<div class="vision-quote">{t("vision_quote", lang)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_beta_banner() -> None:
    st.markdown('<div id="beta-banner"></div>', unsafe_allow_html=True)
    banner_l, banner_r = st.columns([1.35, 0.9], gap="large")
    with banner_l:
        st.markdown(
            f'<div class="beta-banner">'
            f'<div class="beta-banner-kicker">{t("beta_banner_kicker", lang)}</div>'
            f'<div class="beta-banner-title">{t("beta_banner_title", lang)}</div>'
            f'<div class="beta-banner-copy">{t("beta_banner_copy", lang)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with banner_r:
        join_link = f'<a class="inline-anchor anchor-dark" href="#join-network" target="_self">{t("beta_banner_join", lang)}</a>'
        courses_link = f'<a class="inline-anchor anchor-light" href="{COURSE_HUB_URL}" target="_blank" rel="noopener">{t("beta_banner_courses", lang)}</a>'
        st.markdown(
            f'<div style="padding-top:1.25rem; display:grid; gap:0.75rem;">{join_link}{courses_link}</div>',
            unsafe_allow_html=True,
        )

def render_platform_overview() -> None:
    st.markdown(f"## {t('sec_platform', lang)}")
    st.markdown(f'<div class="intro">{t("sec_platform_intro", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="directory-head-note">{t("platform_actions_hint", lang)}</div>', unsafe_allow_html=True)

    cards = [
        {
            "key": "civic",
            "tone": "civic",
            "kicker": t("platform_civic_kicker", lang),
            "title": t("platform_civic_title", lang),
            "desc": t("platform_civic_desc", lang),
            "meta": t("platform_meta_profiles", lang, n=actor_count(df_f, "civil_society")),
            "footer": t("platform_footer_civic", lang),
            "cta": t("platform_cta_civic", lang),
            "tab": "civil_society",
        },
        {
            "key": "public",
            "tone": "public",
            "kicker": t("platform_public_kicker", lang),
            "title": t("platform_public_title", lang),
            "desc": t("platform_public_desc", lang),
            "meta": t("platform_meta_profiles", lang, n=actor_count(df_f, "institution")),
            "footer": t("platform_footer_public", lang),
            "cta": t("platform_cta_public", lang),
            "tab": "institution",
        },
        {
            "key": "political",
            "tone": "political",
            "kicker": t("platform_political_kicker", lang),
            "title": t("platform_political_title", lang),
            "desc": t("platform_political_desc", lang),
            "meta": t("platform_meta_profiles", lang, n=actor_count(df_f, "politician")),
            "footer": t("platform_footer_political", lang),
            "cta": t("platform_cta_political", lang),
            "tab": "politician",
        },
        {
            "key": "business",
            "tone": "business",
            "kicker": t("platform_business_kicker", lang),
            "title": t("platform_business_title", lang),
            "desc": t("platform_business_desc", lang),
            "meta": t("platform_meta_profiles", lang, n=actor_count(df_f, "company", "entrepreneur")),
            "footer": t("platform_footer_business", lang),
            "cta": t("platform_cta_business", lang),
            "tab": preferred_tab("company", "entrepreneur"),
        },
        {
            "key": "academia",
            "tone": "academia",
            "kicker": t("platform_academia_kicker", lang),
            "title": t("platform_academia_title", lang),
            "desc": t("platform_academia_desc", lang),
            "meta": t("platform_meta_academia", lang, n=actor_count(df_f, "professor", "researcher"), m=len(papers)),
            "footer": t("platform_footer_academia", lang),
            "cta": t("platform_cta_academia", lang),
            "tab": preferred_tab("researcher", "professor"),
        },
        {
            "key": "beta",
            "tone": "beta",
            "kicker": t("platform_beta_kicker", lang),
            "title": t("platform_beta_title", lang),
            "desc": t("platform_beta_desc", lang),
            "meta": t("platform_meta_beta", lang, n=len(upcoming)),
            "footer": t("platform_footer_beta", lang),
            "cta": t("platform_cta_beta", lang),
            "url": (
                str(upcoming.iloc[0].get("register_url")).strip()
                if not upcoming.empty and pd.notna(upcoming.iloc[0].get("register_url"))
                else "https://sistemaurbano.org/nodal"
            ),
        },
    ]

    for start in range(0, len(cards), 3):
        row = cards[start:start + 3]
        cols = st.columns(3, gap="large")
        for col, card in zip(cols, row):
            with col:
                st.markdown(
                    platform_card_html(
                        card["kicker"],
                        card["title"],
                        card["desc"],
                        card["meta"],
                        card["tone"],
                        card["footer"],
                    ),
                    unsafe_allow_html=True,
                )
                if card.get("url"):
                    st.link_button(card["cta"], card["url"], use_container_width=True)
                else:
                    if st.button(card["cta"], key=f"route_{card['key']}", use_container_width=True):
                        st.session_state.directory_tab = card["tab"]
                        st.session_state.search = ""
                        st.rerun()

def launchpad_html(next_course) -> str:
    if next_course is None:
        course_html = (
            f'<div class="launchpad-course">'
            f'<div class="launchpad-course-kicker">{t("connect_launch_course", lang)}</div>'
            f'<div class="launchpad-course-meta">{t("connect_launch_empty", lang)}</div>'
            f'</div>'
        )
    else:
        course_html = (
            f'<div class="launchpad-course">'
            f'<div class="launchpad-course-kicker">{t("connect_launch_course", lang)}</div>'
            f'<div class="launchpad-course-title">{next_course["name"]}</div>'
            f'<div class="launchpad-course-meta">'
            f'{fmt_date_range(next_course["start_date"], next_course["end_date"], lang)} · {next_course["modality"]}<br>'
            f'{t("connect_launch_course_site", lang)}: sistemaurbano.org/nodal'
            f'</div>'
            f'</div>'
        )
    return (
        f'<div class="launchpad-card">'
        f'<div class="launchpad-kicker">{t("connect_launch_kicker", lang)}</div>'
        f'<div class="launchpad-title">{t("connect_launch_title", lang)}</div>'
        f'<div class="launchpad-copy">{t("connect_launch_copy", lang)}</div>'
        f'{course_html}'
        f'</div>'
    )

def render_leader_card(row: pd.Series, active: str) -> None:
    actor_class = row.get("actor_class", "institution")
    tone = class_tone(actor_class)
    focus_items = row.get("focus_areas") or []
    focus_html = "".join(f'<span class="pill">{f}</span>' for f in focus_items[:3])
    founded = f' · {int(row["founded_year"])}' if pd.notna(row.get("founded_year")) else ""
    kicker = f'{row["type"]} · {row["city"]}, {row["country"]}{founded}'
    desc = truncate_text(row.get("description", ""), max_chars=190)
    website = str(row.get("website")).strip() if pd.notna(row.get("website")) else ""

    st.markdown(
        f'<div class="leader-card" style="border-top: 4px solid {tone};">'
        f'<div class="leader-card-top">'
        f'<div class="leader-card-kicker">{kicker}</div>'
        f'{class_badge_html(actor_class, lang)}'
        f'</div>'
        f'<div class="leader-card-name">{row["name"]}</div>'
        f'<div class="leader-card-meta">{row["city"]}, {row["country"]}</div>'
        f'<div class="leader-card-desc">{desc}</div>'
        f'<div class="leader-focus-row">{focus_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    btn_cols = st.columns(2 if website else 1, gap="small")
    with btn_cols[0]:
        if st.button(t("dir_open_profile", lang), key=f"org_{active}_{row['name']}", type="primary", use_container_width=True):
            st.session_state.selected_org = row["name"]
            st.rerun()
    if website:
        with btn_cols[1]:
            st.link_button(t("p_visit", lang), website, use_container_width=True)
    st.markdown('<div class="leader-card-spacer"></div>', unsafe_allow_html=True)

def render_connect_directory() -> None:
    next_course = upcoming.iloc[0] if not upcoming.empty else None
    course_url = (
        str(next_course.get("register_url")).strip()
        if next_course is not None and pd.notna(next_course.get("register_url"))
        else "https://sistemaurbano.org/nodal"
    )

    head_l, head_r = st.columns([1.35, 0.95], gap="large")
    with head_l:
        st.markdown(f"## {t('sec_connect', lang)}")
        st.markdown(f'<div class="intro">{t("sec_connect_intro", lang)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="directory-head-note">{t("sec_connect_hint", lang)}</div>', unsafe_allow_html=True)
    with head_r:
        st.markdown(launchpad_html(next_course), unsafe_allow_html=True)
        st.link_button(t("connect_launch_site_cta", lang), course_url, use_container_width=True)

    sort_options = [t("sort_name", lang), t("sort_new", lang),
                    t("sort_old", lang), t("sort_country", lang)]

    sc_sort, sc_count = st.columns([1, 1.3])
    with sc_sort:
        sort_by = st.selectbox(t("sort_label", lang), sort_options, label_visibility="collapsed")

    if sort_by == t("sort_name", lang):
        table = df_f.sort_values("name")
    elif sort_by == t("sort_new", lang):
        table = df_f.sort_values("founded_year", ascending=False, na_position="last")
    elif sort_by == t("sort_old", lang):
        table = df_f.sort_values("founded_year", ascending=True, na_position="last")
    else:
        table = df_f.sort_values(["country", "name"])

    tab_defs = [
        ("all",            t("tab_all",          lang), None),
        ("institution",    t("tab_institution",  lang), "institution"),
        ("civil_society",  t("tab_civil",        lang), "civil_society"),
        ("politician",     t("tab_politician",   lang), "politician"),
        ("entrepreneur",   t("tab_entrepreneur", lang), "entrepreneur"),
        ("company",        t("tab_company",      lang), "company"),
        ("professor",      t("tab_professor",    lang), "professor"),
        ("researcher",     t("tab_researcher",   lang), "researcher"),
    ]
    tab_keys = [k for k, _, _ in tab_defs]
    tab_labels = {k: lbl for k, lbl, _ in tab_defs}
    tab_filter = {k: cls for k, _, cls in tab_defs}

    active = st.segmented_control(
        " ",
        options=tab_keys,
        format_func=lambda k: tab_labels[k],
        default="all",
        key="directory_tab",
        label_visibility="collapsed",
    ) or "all"

    focus_tab = st.session_state.get("_directory_focus")
    if focus_tab and focus_tab in tab_labels and active == focus_tab:
        st.markdown(
            f'<div class="directory-head-note">{t("connect_route_active", lang)}: {tab_labels[focus_tab]} · {t("connect_route_hint", lang)}</div>',
            unsafe_allow_html=True,
        )

    active_cls = tab_filter[active]
    subset = table if active_cls is None else table[table["actor_class"] == active_cls]

    with sc_count:
        st.markdown(
            f'<div class="toolbar-count">{t("connect_visible", lang, n=len(subset))}</div>',
            unsafe_allow_html=True,
        )

    if len(table) == 0:
        st.markdown(f'<div class="note">{t("search_empty", lang)}</div>', unsafe_allow_html=True)
        return
    if len(subset) == 0:
        st.markdown(f'<div class="note">{t("tab_empty", lang)}</div>', unsafe_allow_html=True)
        return

    grid_cols = st.columns(2, gap="large")
    for idx, (_, row) in enumerate(subset.iterrows()):
        with grid_cols[idx % 2]:
            render_leader_card(row, active)

def render_research_hub() -> None:
    st.markdown(f"## {t('sec_research', lang)}")
    st.markdown(f'<div class="intro">{t("sec_research_intro", lang)}</div>', unsafe_allow_html=True)

    st.markdown(f"### {t('sub_research_topics', lang)}")
    focus_labels = sorted({f for lst in df["focus_areas"] for f in lst})
    topics_html = " ".join(
        f'<span class="pill" style="font-size: 0.85rem; padding: 0.4rem 1rem; margin: 0 0.5rem 0.6rem 0;">{f}</span>'
        for f in focus_labels
    )
    st.markdown(f'<div style="margin-bottom: 2rem;">{topics_html}</div>', unsafe_allow_html=True)

    st.markdown(f"### {t('sub_research_database', lang)}")
    if papers.empty:
        st.info("No research papers in database.")
        return

    cols = st.columns(2)
    for i, (_, p) in enumerate(papers.iterrows()):
        col = cols[i % 2]
        pills = " ".join(f'<span class="pill-muted">{f}</span>' for f in p.get("focus_areas", []))
        col.markdown(
            f'<div class="course-card" style="border-left: 4px solid var(--muted); padding: 1.2rem; margin-bottom: 0.8rem; height: 95%; display: flex; flex-direction: column;">'
            f'<div class="course-title" style="font-size: 1.25rem; line-height: 1.25; margin-bottom: 0.4rem;">{p["title"]}</div>'
            f'<div class="course-meta">{t("paper_authors", lang)}: {p["authors"]} &nbsp;·&nbsp; {p["year"]}</div>'
            f'<div style="margin:0.25rem 0 0.5rem 0;">{pills}</div>'
            f'<div class="course-desc" style="font-size: 0.9rem; max-width: 100%; flex-grow: 1;">{p["abstract"]}</div>'
            f'<div style="margin-top:auto;">'
            f'<a class="course-cta" style="background: var(--ink); padding: 0.4rem 1rem; align-self: flex-start; margin-top: 0.8rem;" href="{p["link"]}" target="_blank" rel="noopener">'
            f'{t("paper_read", lang)}</a></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

def render_courses_section() -> None:
    if upcoming.empty:
        return

    st.markdown(f"## {t('sec_courses', lang)}")
    st.markdown(f'<div class="intro">{t("sec_courses_intro", lang)}</div>',
                unsafe_allow_html=True)

    for _, c in upcoming.iterrows():
        date_str = fmt_date_range(c["start_date"], c["end_date"], lang)
        n_sessions = int(c["sessions"]) if pd.notna(c.get("sessions")) else 0
        n_hours = int(c["hours_per_session"]) if pd.notna(c.get("hours_per_session")) else 0
        sessions_str = t("c_sessions", lang, n=n_sessions, h=n_hours)
        desc_col = f"description_{lang}"
        desc = (c.get(desc_col) if pd.notna(c.get(desc_col)) else None) \
               or c.get("description_es") or ""
        pills = " ".join(f'<span class="pill">{f}</span>' for f in c["focus_areas"])
        instructors_str = " · ".join(c["instructors"])
        includes_str = " · ".join(c["includes"])
        register_url = c["register_url"] if pd.notna(c.get("register_url")) else "#"

        st.markdown(
            f'<div class="course-card">'
            f'<div class="eyebrow">{c["program"]} · {c["level"]} · {c["modality"]}</div>'
            f'<div class="course-title">{c["name"]}</div>'
            f'<div class="course-meta">{date_str} · {sessions_str} · {c["timezone"]}</div>'
            f'<div style="margin:0.35rem 0 0.2rem 0;">{pills}</div>'
            f'<div class="course-desc">{desc}</div>'
            f'<div class="course-kv"><span class="k">{t("c_instructors", lang)}</span>'
            f'{instructors_str}</div>'
            f'<div class="course-kv"><span class="k">{t("c_includes", lang)}</span>'
            f'{includes_str}</div>'
            f'<a class="course-cta" href="{register_url}" target="_blank" rel="noopener">'
            f'{t("c_register", lang)} →</a>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Route renderers (app shell) ──────────────────────────────────────────────
def page_header(eyebrow_key: str, title_key: str, subtitle_key: str, **kwargs) -> None:
    st.markdown(
        f'<div class="page-header">'
        f'<div class="page-header-eyebrow">{t(eyebrow_key, lang)}</div>'
        f'<div class="page-header-title">{t(title_key, lang)}</div>'
        f'<div class="page-header-subtitle">{t(subtitle_key, lang, **kwargs)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def render_directory_grid_single() -> None:
    """Sortable, tabbed leader cards rendered as a single column (used inside Network split view)."""
    sort_options = [t("sort_name", lang), t("sort_new", lang),
                    t("sort_old", lang), t("sort_country", lang)]
    sort_by = st.selectbox(t("sort_label", lang), sort_options, label_visibility="collapsed",
                           key="network_sort")

    if sort_by == t("sort_name", lang):
        table = df_f.sort_values("name")
    elif sort_by == t("sort_new", lang):
        table = df_f.sort_values("founded_year", ascending=False, na_position="last")
    elif sort_by == t("sort_old", lang):
        table = df_f.sort_values("founded_year", ascending=True, na_position="last")
    else:
        table = df_f.sort_values(["country", "name"])

    tab_defs = [
        ("all",            t("tab_all",          lang), None),
        ("institution",    t("tab_institution",  lang), "institution"),
        ("civil_society",  t("tab_civil",        lang), "civil_society"),
        ("politician",     t("tab_politician",   lang), "politician"),
        ("entrepreneur",   t("tab_entrepreneur", lang), "entrepreneur"),
        ("company",        t("tab_company",      lang), "company"),
        ("professor",      t("tab_professor",    lang), "professor"),
        ("researcher",     t("tab_researcher",   lang), "researcher"),
    ]
    tab_keys = [k for k, _, _ in tab_defs]
    tab_labels = {k: lbl for k, lbl, _ in tab_defs}
    tab_filter = {k: cls for k, _, cls in tab_defs}

    active = st.segmented_control(
        " ", options=tab_keys,
        format_func=lambda k: tab_labels[k],
        default="all", key="directory_tab",
        label_visibility="collapsed",
    ) or "all"

    active_cls = tab_filter[active]
    subset = table if active_cls is None else table[table["actor_class"] == active_cls]

    st.markdown(
        f'<div class="toolbar-count">{t("connect_visible", lang, n=len(subset))}</div>',
        unsafe_allow_html=True,
    )

    if len(table) == 0:
        st.markdown(f'<div class="note">{t("search_empty", lang)}</div>', unsafe_allow_html=True)
        return
    if len(subset) == 0:
        st.markdown(f'<div class="note">{t("tab_empty", lang)}</div>', unsafe_allow_html=True)
        return

    for _, row in subset.iterrows():
        render_leader_card(row, active)

def render_route_network() -> None:
    page_header("route_network", "network_header", "network_subtitle",
                n=len(df_f), c=df_f["country"].nunique())

    # Sticky toolbar with search
    st.markdown('<div class="network-toolbar">', unsafe_allow_html=True)
    sc1, sc2 = st.columns([3, 1])
    with sc1:
        st.session_state.search = st.text_input(
            t("search_label", lang),
            value=st.session_state.search,
            label_visibility="collapsed",
            placeholder=t("search_label", lang),
            key="network_search",
        )
    with sc2:
        st.markdown(
            f'<div style="text-align:right; padding-top:0.55rem; color:var(--muted); font-size:0.9rem;">'
            f'{t("search_result", lang, n=len(df_f))}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    map_col, list_col = st.columns([5, 7], gap="medium")
    with map_col:
        st.markdown('<div class="network-map-sticky">', unsafe_allow_html=True)
        if len(df_f) == 0:
            st.info(t("search_empty", lang))
        else:
            map_df = df_f.copy()
            map_df["primary_focus"] = map_df["focus_areas"].apply(
                lambda lst: lst[0] if lst else "Other"
            )
            fig_map = px.scatter_map(
                map_df, lat="lat", lon="lon",
                hover_name="name",
                hover_data={"city": True, "country": True, "type": True,
                            "lat": False, "lon": False, "primary_focus": False},
                zoom=2.2, center={"lat": -12, "lon": -62},
                height=620, map_style="carto-positron",
            )
            fig_map.update_traces(marker=dict(size=13, color=GREEN, opacity=0.85))
            fig_map.update_layout(margin=dict(t=0, b=0, l=0, r=0),
                                  paper_bgcolor=PAPER, showlegend=False)
            event = st.plotly_chart(fig_map, use_container_width=True,
                                    on_select="rerun", selection_mode=["points"],
                                    key="map_chart_network")
            if event and event.get("selection") and event["selection"].get("points"):
                pt = event["selection"]["points"][0]
                cd = pt.get("customdata") or [None]
                clicked_name = pt.get("hovertext") or (cd[0] if cd else None)
                if clicked_name:
                    st.session_state.selected_org = clicked_name
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with list_col:
        render_directory_grid_single()

def render_route_research() -> None:
    page_header("route_research", "sec_research", "route_research_sub")
    if papers.empty:
        st.info(t("no_research_yet", lang))
        return
    render_research_hub()

def render_route_courses() -> None:
    page_header("route_courses", "sec_courses", "route_courses_sub")
    if upcoming.empty:
        st.info(t("connect_launch_empty", lang))
        return
    render_courses_section()

def render_route_intelligence() -> None:
    page_header("route_intel", "intel_header", "intel_subtitle")

    if len(df_f) == 0:
        st.info(t("search_empty", lang))
        return

    # Stats strip
    c1, c2, c3, c4, c5 = st.columns(5)
    def _stat(col, label, value, unit=""):
        unit_html = f'<div class="stat-unit">{unit}</div>' if unit else ""
        col.markdown(
            f'<div class="stat">'
            f'<div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div>'
            f'{unit_html}</div>',
            unsafe_allow_html=True,
        )
    _stat(c1, t("stat_orgs", lang),    len(df_f))
    _stat(c2, t("stat_country", lang), df_f["country"].nunique())
    _stat(c3, t("stat_cities", lang),  df_f["city"].nunique())
    _stat(c4, t("stat_focus", lang),   df_f["focus_areas"].explode().nunique())
    _median = df_f["age_years"].replace(0, pd.NA).median()
    _stat(c5, t("stat_age", lang),
          int(_median) if pd.notna(_median) else 0,
          t("stat_yrs", lang))

    st.markdown('<hr class="thick">', unsafe_allow_html=True)

    # Composition · Topics · Matrix · Insights — reuse the existing inline blocks
    # via a callable helper (defined below at module level)
    render_intelligence_charts()

def render_route_about() -> None:
    page_header("route_about", "about_header", "about_subtitle")

    # Hero block (slimmed — no metric card on the right; just the lede)
    st.markdown(f'<div class="eyebrow">{t("hero_kicker", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f"# {t('title', lang)}")
    st.markdown(f'<div class="lede">{t("hero_lede", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="intro">{t("hero_mission", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="intro">{t("hero_beta", lang)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="note">{t("hero_transparency", lang)}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="thick">', unsafe_allow_html=True)
    render_audience_strip()
    render_partners_strip()
    st.markdown('<hr class="thick">', unsafe_allow_html=True)
    render_products()
    render_gap_insight()
    render_traction_block()
    st.markdown('<hr class="thick">', unsafe_allow_html=True)
    render_propose_section()
    render_vision_close()


# ── Profile dialog ───────────────────────────────────────────────────────────
@st.dialog("·", width="large")
def show_profile(name: str):
    import urllib.parse
    row = df[df["name"] == name]
    if row.empty:
        st.write("—"); return
    row = row.iloc[0]

    actor_class = row.get("actor_class", "institution")
    st.markdown(
        f'<div class="eyebrow">{row["type"]} · {row["city"]}, {row["country"]}'
        f'{class_badge_html(actor_class, lang)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<h1 style="font-size:2.3rem; margin:0.2rem 0 0.8rem 0;">{row["name"]}</h1>',
                unsafe_allow_html=True)

    pills = " ".join(f'<span class="pill">{f}</span>' for f in row["focus_areas"])
    st.markdown(f'<div style="margin-bottom:0.7rem;">{pills}</div>', unsafe_allow_html=True)

    # ── Contact block (fast path to reach out) ──────────────────────────────
    raw_email = row.get("email")
    email = str(raw_email).strip() if pd.notna(raw_email) else ""
    raw_site = row.get("website")
    website = str(raw_site).strip() if pd.notna(raw_site) else ""
    chips = []
    if email:
        subject = urllib.parse.quote(f"Nodal · {row['name']}")
        chips.append(
            f'<a class="contact-chip chip-primary" '
            f'href="mailto:{email}?subject={subject}">{t("p_write", lang)} →</a>'
        )
    else:
        chips.append(
            f'<span class="contact-chip chip-mute">{t("p_no_email", lang)}</span>'
        )
    if website:
        chips.append(
            f'<a class="contact-chip chip-ghost" href="{website}" target="_blank" rel="noopener">'
            f'{t("p_visit", lang)}</a>'
        )
    if not email and not website:
        nodal_subject = urllib.parse.quote(f"Nodal · {row['name']}")
        chips.append(
            f'<a class="contact-chip chip-ghost" '
            f'href="mailto:nodal@sistemaurbano.org?subject={nodal_subject}">'
            f'{t("p_via_nodal", lang)} →</a>'
        )
    st.markdown(
        f'<div class="contact-row">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )

    # ── About ───────────────────────────────────────────────────────────────
    st.markdown(f"### {t('p_about', lang)}")
    st.markdown(f'<div style="font-size:1rem; line-height:1.6; color:var(--ink);">'
                f'{row["description"]}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### {t('p_details', lang)}")
        detail_rows = [
            (t("p_type", lang),     row["type"]),
            (t("p_location", lang), f'{row["city"]}, {row["country"]}'),
        ]
        if pd.notna(row.get("founded_year")):
            detail_rows.append((t("p_founded", lang), int(row["founded_year"])))
        for k, v in detail_rows:
            st.markdown(
                f'<div style="padding:0.45rem 0; border-top:1px solid var(--soft);">'
                f'<span style="color:var(--muted); font-size:0.78rem; text-transform:uppercase; '
                f'letter-spacing:0.1em; font-weight:600;">{k}</span><br>'
                f'<span style="color:var(--ink); font-size:0.98rem;">{v}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"### {t('p_share', lang)}")
        st.caption(t("p_share_hint", lang))
        copy_label = t("p_copy", lang)
        copied_label = t("p_copied", lang)
        components.html(
            f"""
            <div style="display:flex; gap:0.5rem; align-items:stretch;
                        font-family:Inter,system-ui,sans-serif;">
              <input id="share-url" readonly
                     style="flex:1; min-width:0; padding:0.55rem 0.7rem;
                            border:1px solid #EDEDED; border-radius:10px;
                            background:#FAFAF7; color:#111; font-size:0.9rem;
                            font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"/>
              <button id="share-copy"
                      style="padding:0.55rem 0.95rem; border:1px solid #6FA83D;
                             background:#6FA83D; color:white; border-radius:10px;
                             font-weight:600; font-size:0.85rem; cursor:pointer;
                             transition:background .15s ease;">{copy_label}</button>
            </div>
            <script>
              (function() {{
                const slug = {slugify(row['name'])!r};
                const loc = window.parent.location;
                const base = loc.origin + loc.pathname;
                const url = base + "?org=" + slug;
                const input = document.getElementById("share-url");
                const btn = document.getElementById("share-copy");
                input.value = url;
                btn.addEventListener("click", async () => {{
                  try {{
                    await navigator.clipboard.writeText(url);
                  }} catch (e) {{
                    input.select(); document.execCommand("copy");
                  }}
                  const prev = btn.textContent;
                  btn.textContent = {copied_label!r};
                  btn.style.background = "#4F7F28";
                  setTimeout(() => {{
                    btn.textContent = prev;
                    btn.style.background = "#6FA83D";
                  }}, 1400);
                }});
              }})();
            </script>
            """,
            height=60,
        )

    with c2:
        st.markdown(f"### {t('p_peers', lang)}")
        peers = peers_of(df, row["name"], top_n=5)
        peers = peers[peers["score"] > 0]
        if peers.empty:
            st.markdown(f'<div class="note">{t("p_peers_none", lang)}</div>',
                        unsafe_allow_html=True)
        else:
            why_labels = {
                "focus":   t("p_why_focus",   lang),
                "city":    t("p_why_city",    lang),
                "country": t("p_why_country", lang),
                "class":   t("p_why_class",   lang),
            }
            for _, p in peers.iterrows():
                p_class = p.get("actor_class", "institution")
                why_html = ""
                for reason in (p.get("why") or []):
                    kind, _, val = reason.partition(":")
                    label = why_labels.get(kind, kind)
                    display_val = t(f"cls_{val}", lang) if kind == "class" and val in CLASS_KEYS else val
                    why_html += (f'<span class="why-pill">'
                                 f'<span class="why-k">{label}</span>{display_val}</span>')
                st.markdown(
                    f'<div class="peer-card">'
                    f'<div style="font-weight:600; font-size:0.97rem; color:var(--ink);">'
                    f'{p["name"]}{class_badge_html(p_class, lang)}</div>'
                    f'<div style="color:var(--muted); font-size:0.82rem; margin-top:0.15rem;">'
                    f'{p["city"]}, {p["country"]} · {p["type"]}</div>'
                    f'<div style="margin-top:0.35rem;">{why_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

if st.session_state.selected_org:
    # Keep the URL in sync with what's actually open, so copying the browser
    # URL always shares the right profile (not a stale slug from earlier).
    st.query_params["org"] = slugify(st.session_state.selected_org)
    show_profile(st.session_state.selected_org)
    st.session_state.selected_org = None

# ── Module-level helpers (used inside multiple route renderers) ──────────────
def clean_chart(fig, height=320):
    fig.update_layout(
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        margin=dict(t=5, b=5, l=0, r=10), height=height,
        font=dict(family="Inter", size=12, color=INK), showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=SOFT, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

# ── Submission persistence (curator-gated; pending entries land in CSVs) ─────
SUBMISSIONS_PATH = Path(__file__).parent.parent.parent / "data" / "submissions.csv"
SUBMISSION_FIELDS = [
    "submitted_at", "submitter_name", "submitter_email",
    "name", "actor_class", "type", "city", "country",
    "focus_areas", "founded_year", "description",
    "website", "email", "source", "status",
]

def append_submission(entry: dict) -> None:
    SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not SUBMISSIONS_PATH.exists()
    with SUBMISSIONS_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SUBMISSION_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow({k: entry.get(k, "") for k in SUBMISSION_FIELDS})

def append_research(entry: dict) -> None:
    p = Path(__file__).parent.parent.parent / "data" / "research_submissions.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    new_file = not p.exists()
    fields = ["submitted_at", "title", "authors", "year", "focus_areas", "link", "abstract"]
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            w.writeheader()
        w.writerow({k: entry.get(k, "") for k in fields})

CLASS_OPTIONS = [
    ("institution",    t("cls_institution",   lang)),
    ("civil_society",  t("cls_civil_society", lang)),
    ("politician",     t("cls_politician",    lang)),
    ("entrepreneur",   t("cls_entrepreneur",  lang)),
    ("company",        t("cls_company",       lang)),
    ("professor",      t("cls_professor",     lang)),
    ("researcher",     t("cls_researcher",    lang)),
]
_class_label_to_key = {lbl: key for key, lbl in CLASS_OPTIONS}
_known_focus = sorted({f for lst in df["focus_areas"] for f in lst})


# ── Intelligence dashboards ──────────────────────────────────────────────────
def render_intelligence_charts() -> None:
    # Composition
    st.markdown(f"## {t('sec_who', lang)}")
    st.markdown(f'<div class="intro">{t("sec_who_intro", lang)}</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"### {t('sub_type', lang)}")
        d = seg.by_type(df_f)
        fig = px.bar(d, x="count", y="type", orientation="h",
                     color_discrete_sequence=[GREEN], labels={"count": "", "type": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(clean_chart(fig), use_container_width=True)
    with col_b:
        st.markdown(f"### {t('sub_country', lang)}")
        d = seg.by_country(df_f).head(10)
        fig = px.bar(d, x="count", y="country", orientation="h",
                     color_discrete_sequence=[GREEN], labels={"count": "", "country": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(clean_chart(fig), use_container_width=True)

    # Topics
    st.markdown(f"## {t('sec_topics', lang)}")
    st.markdown(f'<div class="intro">{t("sec_topics_intro", lang)}</div>', unsafe_allow_html=True)
    col_c, col_d = st.columns([1.3, 1])
    with col_c:
        st.markdown(f"### {t('sub_focus', lang)}")
        focus_s = seg.by_focus(df_f).reset_index()
        focus_s.columns = ["area", "count"]
        fig = px.bar(focus_s, x="count", y="area", orientation="h",
                     color_discrete_sequence=[GREEN], labels={"count": "", "area": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(clean_chart(fig), use_container_width=True)
    with col_d:
        st.markdown(f"### {t('sub_gen', lang)}")
        if "generation" in df_f.columns:
            gen_df = df_f["generation"].value_counts().reset_index()
            gen_df.columns = ["generation", "count"]
            gen_label_map = {
                "Pre-2000 (foundational)":   t("gen_pre2000", lang),
                "2000s (institutional)":     t("gen_2000s", lang),
                "2010s (civic tech wave)":   t("gen_2010s", lang),
                "2020s (new generation)":    t("gen_2020s", lang),
            }
            gen_df["generation"] = gen_df["generation"].astype(str).map(gen_label_map).fillna(gen_df["generation"])
            fig = px.bar(gen_df, x="count", y="generation", orientation="h",
                         color_discrete_sequence=[GREEN], labels={"count": "", "generation": ""})
            st.plotly_chart(clean_chart(fig), use_container_width=True)

    # Matrix
    st.markdown(f"## {t('sec_matrix', lang)}")
    st.markdown(f'<div class="intro">{t("sec_matrix_intro", lang)}</div>', unsafe_allow_html=True)
    pivot = seg.cross_country_focus(df_f)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(pivot, aspect="auto",
                    color_continuous_scale=["white", GREEN_SOFT, GREEN, GREEN_DARK],
                    labels={"color": ""}, text_auto=True)
    fig.update_layout(paper_bgcolor="white", margin=dict(t=10, b=10, l=0, r=0),
                      height=380, font=dict(family="Inter", size=11, color=INK),
                      coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    st.markdown(f"## {t('sec_insights', lang)}")
    st.markdown(f'<div class="intro">{t("sec_insights_intro", lang)}</div>', unsafe_allow_html=True)
    for ins in generate(df_f, lang=lang):
        st.markdown(
            f'<div class="insight">'
            f'<div class="insight-cat">{ins["category"]}</div>'
            f'<div class="insight-find">{ins["finding"]}</div>'
            f'<div class="insight-act">{ins["implication"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Propose section (organisation + research forms) ──────────────────────────
def render_propose_section() -> None:
    st.markdown('<div id="join-network"></div>', unsafe_allow_html=True)
    prop_l, prop_r = st.columns([0.95, 1.2], gap="large")
    with prop_l:
        propose_points = "".join([
            propose_item_html(t("prop_panel_point_1", lang)),
            propose_item_html(t("prop_panel_point_2", lang)),
            propose_item_html(t("prop_panel_point_3", lang)),
        ])
        st.markdown(
            f'<div class="propose-hero">'
            f'<div class="propose-kicker">{t("prop_panel_kicker", lang)}</div>'
            f'<div class="propose-title">{t("prop_panel_title", lang)}</div>'
            f'<div class="propose-copy">{t("prop_panel_copy", lang)}</div>'
            f'<div class="propose-list">{propose_points}</div>'
            f'<div class="propose-trust">{t("prop_panel_trust", lang)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.link_button(t("beta_banner_courses", lang), COURSE_HUB_URL, use_container_width=True)
    with prop_r:
        st.markdown(f"## {t('sec_propose', lang)}")
        st.markdown(f'<div class="intro">{t("sec_propose_intro", lang)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="propose-forms-kicker">{t("prop_forms_kicker", lang)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="propose-forms-note">{t("prop_forms_note", lang)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="propose-route-grid">'
            f'{propose_route_card_html(t("prop_route_people_kicker", lang), t("prop_expand", lang), t("prop_route_people_copy", lang))}'
            f'{propose_route_card_html(t("prop_route_research_kicker", lang), t("prop_res_expand", lang), t("prop_route_research_copy", lang))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with st.expander(t("prop_expand", lang), expanded=True):
        with st.form("propose_member", clear_on_submit=True):
            pc1, pc2 = st.columns(2)
            with pc1:
                f_name     = st.text_input(t("prop_name", lang))
                f_class_lbl= st.selectbox(t("prop_class", lang),
                                          [lbl for _, lbl in CLASS_OPTIONS])
                f_type     = st.text_input(t("prop_type", lang),
                                           help=t("prop_type_help", lang))
                f_city     = st.text_input(t("prop_city", lang))
                f_country  = st.text_input(t("prop_country", lang))
                f_founded  = st.number_input(t("prop_founded", lang),
                                             min_value=1800, max_value=2100,
                                             value=2020, step=1)
            with pc2:
                f_focus    = st.multiselect(t("prop_focus", lang), _known_focus)
                f_focus_other = st.text_input(t("prop_focus_other", lang),
                                              help=t("prop_focus_other_help", lang))
                f_website  = st.text_input(t("prop_website", lang))
                f_email    = st.text_input(t("prop_email", lang))
                f_desc     = st.text_area(t("prop_desc", lang), height=120)
            st.markdown(f'<div class="note" style="margin-top:0.6rem;">{t("prop_who", lang)}</div>',
                        unsafe_allow_html=True)
            wc1, wc2 = st.columns(2)
            with wc1:
                f_sub_name = st.text_input(t("prop_your_name", lang))
            with wc2:
                f_sub_email= st.text_input(t("prop_your_email", lang))
            submitted = st.form_submit_button(t("prop_submit", lang), type="primary")
        if submitted:
            missing = [k for k, v in {
                "name": f_name, "city": f_city, "country": f_country,
                "description": f_desc, "submitter_email": f_sub_email,
            }.items() if not str(v).strip()]
            if missing:
                st.error(t("prop_missing", lang))
            elif f_name.strip() in set(df["name"]):
                st.warning(t("prop_duplicate", lang, name=f_name.strip()))
            else:
                focus_list = list(f_focus)
                if f_focus_other.strip():
                    focus_list += [x.strip() for x in f_focus_other.split(",") if x.strip()]
                entry = {
                    "submitted_at":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "submitter_name":  f_sub_name.strip(),
                    "submitter_email": f_sub_email.strip(),
                    "name":            f_name.strip(),
                    "actor_class":     _class_label_to_key.get(f_class_lbl, "institution"),
                    "type":            f_type.strip() or "Organization",
                    "city":            f_city.strip(),
                    "country":         f_country.strip(),
                    "focus_areas":     ";".join(focus_list),
                    "founded_year":    int(f_founded),
                    "description":     f_desc.strip(),
                    "website":         f_website.strip(),
                    "email":           f_email.strip(),
                    "source":          "community-submission",
                    "status":          "pending",
                }
                try:
                    append_submission(entry)
                    st.success(t("prop_success", lang, name=entry["name"]))
                except Exception as e:
                    st.error(t("prop_error", lang, err=str(e)))

    with st.expander(t("prop_res_expand", lang), expanded=False):
        with st.form("propose_research", clear_on_submit=True):
            r_c1, r_c2 = st.columns(2)
            with r_c1:
                r_title = st.text_input(t("prop_res_title", lang))
                r_authors = st.text_input(t("prop_res_authors", lang))
                r_year = st.number_input(t("prop_res_year", lang),
                                         min_value=1900, max_value=2100, value=2024, step=1)
                r_link = st.text_input(t("prop_res_link", lang))
            with r_c2:
                r_focus = st.multiselect(t("prop_focus", lang), _known_focus)
                r_abstract = st.text_area(t("prop_res_abstract", lang), height=180)
            r_submitted = st.form_submit_button(t("prop_submit", lang), type="primary")
        if r_submitted:
            missing = [k for k, v in {"title": r_title, "authors": r_authors, "link": r_link}.items()
                       if not str(v).strip()]
            if missing:
                st.error(t("prop_missing", lang))
            else:
                entry = {
                    "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "title": r_title.strip(),
                    "authors": r_authors.strip(),
                    "year": int(r_year),
                    "focus_areas": ";".join(r_focus),
                    "link": r_link.strip(),
                    "abstract": r_abstract.strip(),
                }
                try:
                    append_research(entry)
                    st.success(t("prop_res_success", lang, name=r_title.strip()))
                except Exception as e:
                    st.error(t("prop_error", lang, err=str(e)))


# ── Route dispatch ───────────────────────────────────────────────────────────
_route = st.session_state.route
if _route == "network":
    render_route_network()
elif _route == "research":
    render_route_research()
elif _route == "courses":
    render_route_courses()
elif _route == "intelligence":
    render_route_intelligence()
elif _route == "about":
    render_route_about()
else:
    st.session_state.route = "network"
    st.rerun()
