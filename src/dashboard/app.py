"""
Nodal · Urban Changemakers of Latin America — interactive directory.
Run: streamlit run src/dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.pipeline.ingest import load_csv, load_google_sheet, explode_multivalued
from src.pipeline.clean import clean
from src.pipeline import segment as seg
from src.analysis.insights import generate
from src.analysis.peers import peers_of
from src.dashboard.i18n import t

st.set_page_config(
    page_title="Nodal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette ──────────────────────────────────────────────────────────────────
INK         = "#111111"
MUTED       = "#6B6B6B"
SOFT        = "#EDEDED"
PAPER       = "#FAFAF7"
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

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Fraunces:wght@600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .block-container {{ padding-top: 3.5rem; padding-bottom: 5rem; max-width: 1200px; }}
    header[data-testid="stHeader"] {{ height: 0; background: transparent; }}

    h1 {{ font-family: 'Fraunces', Georgia, serif; font-size: 3.2rem; line-height: 1.02;
          letter-spacing: -0.02em; font-weight: 800; color: {INK};
          margin: 0.2rem 0 0.4rem 0; }}
    h2 {{ font-family: 'Inter'; font-size: 1.15rem; margin-top: 3rem; margin-bottom: 0.3rem;
          text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; color: {INK}; }}
    h3 {{ font-size: 0.82rem; margin: 0.5rem 0 0.5rem 0; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.1em; color: {MUTED}; }}

    .lede {{ color: {INK}; font-size: 1.2rem; line-height: 1.5;
             max-width: 680px; margin: 0.8rem 0 1.2rem 0; font-weight: 400; }}
    .eyebrow {{ color: {GREEN_DARK}; font-size: 0.78rem; text-transform: uppercase;
                letter-spacing: 0.2em; font-weight: 700; margin-bottom: 0.4rem; }}
    .note {{ color: {MUTED}; font-size: 0.82rem; font-style: italic; line-height: 1.5; }}
    .intro {{ color: {MUTED}; font-size: 0.95rem; margin: 0.2rem 0 1.2rem 0; max-width: 680px; }}
    hr.thick {{ border: none; border-top: 3px solid {INK}; margin: 1.6rem 0 2rem 0; }}

    .stat {{ padding: 1rem 0; border-top: 1px solid {SOFT}; }}
    .stat-label {{ color: {MUTED}; font-size: 0.72rem; text-transform: uppercase;
                   letter-spacing: 0.12em; margin-bottom: 0.35rem; font-weight: 600; }}
    .stat-value {{ color: {INK}; font-size: 2.2rem; font-weight: 700; line-height: 1;
                   font-variant-numeric: tabular-nums; font-family: 'Fraunces', Georgia, serif; }}
    .stat-unit {{ color: {MUTED}; font-size: 0.8rem; margin-top: 0.3rem; }}

    .insight {{ padding: 1.3rem 0; border-top: 1px solid {SOFT}; }}
    .insight-cat {{ color: {GREEN_DARK}; font-size: 0.7rem; text-transform: uppercase;
                    letter-spacing: 0.15em; font-weight: 700; margin-bottom: 0.5rem; }}
    .insight-find {{ color: {INK}; font-size: 1.15rem; font-weight: 600;
                     font-family: 'Fraunces', Georgia, serif;
                     line-height: 1.3; margin-bottom: 0.45rem; }}
    .insight-act {{ color: {MUTED}; font-size: 0.96rem; line-height: 1.6; max-width: 780px; }}

    /* Directory card — the whole row is a clickable button */
    .stButton > button[kind="tertiary"],
    div[data-testid="stButton"] button[kind="tertiary"] {{
        text-align: left !important;
        background: white !important;
        color: {INK} !important;
        border: none !important;
        border-top: 1px solid {SOFT} !important;
        border-radius: 0 !important;
        padding: 1.2rem 0.5rem 1.2rem 0 !important;
        width: 100% !important;
        font-family: 'Inter' !important;
        font-weight: 400 !important;
        white-space: normal !important;
        line-height: 1.5 !important;
        transition: background 0.12s ease !important;
    }}
    .stButton > button[kind="tertiary"]:hover {{
        background: {PAPER} !important;
        color: {INK} !important;
        cursor: pointer;
    }}

    /* Language & small pill buttons */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
        background: transparent !important;
        color: {MUTED} !important;
        border: 1px solid {SOFT} !important;
        border-radius: 999px !important;
        padding: 0.25rem 0.8rem !important;
        font-size: 0.82rem !important; min-height: 0 !important; height: auto !important;
    }}
    div[data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background: {INK} !important; color: white !important;
        border: 1px solid {INK} !important; border-radius: 999px !important;
        padding: 0.25rem 0.8rem !important;
        font-size: 0.82rem !important; min-height: 0 !important; height: auto !important;
    }}

    [data-testid="stSidebar"] {{ background: {PAPER}; border-right: 1px solid {SOFT}; }}

    .stPlotlyChart {{ border: none; }}

    /* Focus pill style */
    .pill {{ display:inline-block; background:{GREEN_SOFT}; color:{GREEN_DARK};
             padding:0.22rem 0.7rem; border-radius:999px; font-size:0.78rem;
             font-weight:600; letter-spacing:0.04em; margin:0.15rem 0.2rem 0.15rem 0; }}
    .pill-muted {{ display:inline-block; background:{SOFT}; color:{MUTED};
                   padding:0.22rem 0.7rem; border-radius:999px; font-size:0.78rem;
                   margin:0.15rem 0.2rem 0.15rem 0; }}

    /* Search input styling */
    div[data-testid="stTextInput"] input {{
        border: 1px solid {SOFT} !important;
        border-radius: 999px !important;
        padding: 0.6rem 1.1rem !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: {GREEN} !important;
        box-shadow: 0 0 0 3px {GREEN_SOFT} !important;
    }}

    /* Course card */
    .course-card {{
        background: white;
        border: 1px solid {SOFT};
        border-left: 4px solid {GREEN};
        border-radius: 10px;
        padding: 1.5rem 1.8rem;
        margin: 0.9rem 0;
    }}
    .course-title {{
        font-family: 'Fraunces', Georgia, serif;
        font-size: 1.85rem;
        font-weight: 700;
        color: {INK};
        line-height: 1.1;
        letter-spacing: -0.01em;
        margin: 0.25rem 0 0.55rem 0;
    }}
    .course-meta {{
        color: {MUTED};
        font-size: 0.9rem;
        margin: 0.25rem 0 0.6rem 0;
        font-variant-numeric: tabular-nums;
    }}
    .course-desc {{
        color: {INK};
        font-size: 1rem;
        line-height: 1.55;
        margin: 0.55rem 0 0.85rem 0;
        max-width: 760px;
    }}
    .course-kv {{
        color: {INK};
        font-size: 0.9rem;
        margin: 0.35rem 0;
    }}
    .course-kv .k {{
        color: {MUTED};
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.72rem;
        font-weight: 700;
        margin-right: 0.5rem;
    }}
    a.course-cta {{
        display: inline-block;
        background: {GREEN};
        color: white !important;
        padding: 0.6rem 1.3rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.92rem;
        text-decoration: none !important;
        margin-top: 0.8rem;
        transition: background 0.15s ease;
    }}
    a.course-cta:hover {{ background: {GREEN_DARK}; }}
</style>
""", unsafe_allow_html=True)

# ── Top bar ──────────────────────────────────────────────────────────────────
bar_l, _, bar_r1, bar_r2 = st.columns([6, 3.5, 0.8, 0.8])
with bar_l:
    st.markdown(
        f'<div style="font-weight:800; font-size:1.05rem; color:{INK}; padding-top:0.35rem;">'
        f'<span style="color:{GREEN_DARK};">●</span>&nbsp; NODAL'
        f'</div>',
        unsafe_allow_html=True,
    )
with bar_r1:
    if st.button("🇪🇸 ES",
                 type="primary" if st.session_state.lang == "es" else "secondary",
                 key="lang_es", use_container_width=True):
        st.session_state.lang = "es"; st.rerun()
with bar_r2:
    if st.button("🇬🇧 EN",
                 type="primary" if st.session_state.lang == "en" else "secondary",
                 key="lang_en", use_container_width=True):
        st.session_state.lang = "en"; st.rerun()

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

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div style="font-weight:800; font-size:1.3rem; color:{INK};">'
                f'<span style="color:{GREEN_DARK};">●</span>&nbsp; NODAL</div>',
                unsafe_allow_html=True)
    st.caption(t("sb_tag", lang))
    st.markdown("")

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

    st.markdown(f"### {t('sb_filters', lang)}")
    sel_types = st.multiselect(t("sb_type", lang),
                               sorted(df["type"].dropna().unique()),
                               default=sorted(df["type"].dropna().unique()))
    sel_countries = st.multiselect(t("sb_country", lang),
                                   sorted(df["country"].dropna().unique()),
                                   default=sorted(df["country"].dropna().unique()))
    all_focus = sorted({f for lst in df["focus_areas"] for f in lst})
    sel_focus = st.multiselect(t("sb_focus", lang), all_focus, default=all_focus)

    df_base = df[
        df["type"].isin(sel_types)
        & df["country"].isin(sel_countries)
        & df["focus_areas"].apply(lambda lst: any(f in sel_focus for f in lst) or not lst)
    ]

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

# ── Profile dialog ───────────────────────────────────────────────────────────
@st.dialog(" ", width="large")
def show_profile(name: str):
    row = df[df["name"] == name]
    if row.empty:
        st.write("—"); return
    row = row.iloc[0]

    st.markdown(f'<div class="eyebrow">{row["type"]} · {row["city"]}, {row["country"]}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<h1 style="font-size:2.3rem; margin:0.2rem 0 0.8rem 0;">{row["name"]}</h1>',
                unsafe_allow_html=True)

    pills = " ".join(f'<span class="pill">{f}</span>' for f in row["focus_areas"])
    st.markdown(f'<div style="margin-bottom:1.2rem;">{pills}</div>', unsafe_allow_html=True)

    st.markdown(f"### {t('p_about', lang)}")
    st.markdown(f'<div style="font-size:1rem; line-height:1.6; color:{INK};">'
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
                f'<div style="padding:0.45rem 0; border-top:1px solid {SOFT};">'
                f'<span style="color:{MUTED}; font-size:0.78rem; text-transform:uppercase; '
                f'letter-spacing:0.1em; font-weight:600;">{k}</span><br>'
                f'<span style="color:{INK}; font-size:0.98rem;">{v}</span></div>',
                unsafe_allow_html=True,
            )
        if pd.notna(row.get("website")) and row.get("website"):
            st.markdown(
                f'<div style="padding:0.6rem 0; border-top:1px solid {SOFT};">'
                f'<a href="{row["website"]}" target="_blank" style="color:{GREEN_DARK}; '
                f'font-weight:600; text-decoration:none; font-size:0.98rem;">'
                f'{t("p_visit", lang)}</a></div>',
                unsafe_allow_html=True,
            )

    with c2:
        st.markdown(f"### {t('p_peers', lang)}")
        peers = peers_of(df, row["name"], top_n=5)
        peers = peers[peers["score"] > 0]
        if peers.empty:
            st.markdown(f'<div class="note">{t("p_peers_none", lang)}</div>',
                        unsafe_allow_html=True)
        else:
            for _, p in peers.iterrows():
                shared = sorted(set(p["focus_areas"]) & set(row["focus_areas"]))
                shared_str = " · ".join(shared) if shared else p["type"]
                st.markdown(
                    f'<div style="padding:0.55rem 0; border-top:1px solid {SOFT};">'
                    f'<div style="font-weight:600; font-size:0.95rem; color:{INK};">{p["name"]}</div>'
                    f'<div style="color:{MUTED}; font-size:0.8rem;">'
                    f'{p["city"]}, {p["country"]} · {shared_str}</div></div>',
                    unsafe_allow_html=True,
                )

if st.session_state.selected_org:
    show_profile(st.session_state.selected_org)
    st.session_state.selected_org = None

# ── Hero ─────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="eyebrow">{t("hero_kicker", lang)}</div>', unsafe_allow_html=True)
st.markdown(f"# {t('title', lang)}")
st.markdown(f'<div class="lede">{t("hero_lede", lang)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="note">{t("note", lang)}</div>', unsafe_allow_html=True)

st.markdown('<hr class="thick">', unsafe_allow_html=True)

# Search bar
sc1, sc2 = st.columns([3, 1])
with sc1:
    st.session_state.search = st.text_input(
        t("search_label", lang),
        value=st.session_state.search,
        label_visibility="collapsed",
        placeholder="🔎  " + t("search_label", lang),
    )
with sc2:
    st.markdown(
        f'<div style="text-align:right; padding-top:0.55rem; color:{MUTED}; font-size:0.9rem;">'
        f'{t("search_result", lang, n=len(df_f))}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Stats ────────────────────────────────────────────────────────────────────
def stat(col, label, value, unit=""):
    col.markdown(
        f'<div class="stat">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'{("<div class=\"stat-unit\">" + unit + "</div>") if unit else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

c1, c2, c3, c4, c5 = st.columns(5)
stat(c1, t("stat_orgs", lang), len(df_f))
stat(c2, t("stat_country", lang), df_f["country"].nunique())
stat(c3, t("stat_cities", lang), df_f["city"].nunique())
stat(c4, t("stat_focus", lang), df_f["focus_areas"].explode().nunique())
median_age = int(df_f["age_years"].replace(0, pd.NA).median() or 0)
stat(c5, t("stat_age", lang), median_age, t("stat_yrs", lang))

# ── Map ──────────────────────────────────────────────────────────────────────
st.markdown(f"## {t('sec_where', lang)}")
st.markdown(f'<div class="intro">{t("sec_where_intro", lang)}</div>', unsafe_allow_html=True)

if len(df_f) == 0:
    st.info(t("search_empty", lang))
else:
    map_df = df_f.copy()
    map_df["primary_focus"] = map_df["focus_areas"].apply(lambda lst: lst[0] if lst else "Other")

    fig_map = px.scatter_map(
        map_df,
        lat="lat", lon="lon",
        hover_name="name",
        hover_data={"city": True, "country": True, "type": True,
                    "lat": False, "lon": False, "primary_focus": False},
        zoom=2.2, center={"lat": -12, "lon": -62},
        height=540,
        map_style="carto-positron",
    )
    fig_map.update_traces(marker=dict(size=13, color=GREEN, opacity=0.85))
    fig_map.update_layout(margin=dict(t=0, b=0, l=0, r=0),
                          paper_bgcolor="white", showlegend=False)

    # Enable point selection — clicking a dot opens the profile
    event = st.plotly_chart(fig_map, use_container_width=True,
                            on_select="rerun", selection_mode=["points"],
                            key="map_chart")
    if event and event.get("selection") and event["selection"].get("points"):
        pt = event["selection"]["points"][0]
        clicked_name = pt.get("hovertext") or pt.get("customdata", [None])[0]
        if clicked_name:
            st.session_state.selected_org = clicked_name
            st.rerun()

# ── Composition ──────────────────────────────────────────────────────────────
st.markdown(f"## {t('sec_who', lang)}")
st.markdown(f'<div class="intro">{t("sec_who_intro", lang)}</div>', unsafe_allow_html=True)

def clean_chart(fig, height=320):
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=5, b=5, l=0, r=10), height=height,
        font=dict(family="Inter", size=12, color=INK), showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=SOFT, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

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

# ── Topics ───────────────────────────────────────────────────────────────────
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

# ── Matrix ───────────────────────────────────────────────────────────────────
st.markdown(f"## {t('sec_matrix', lang)}")
if len(df_f) > 0:
    pivot = seg.cross_country_focus(df_f)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(pivot, aspect="auto",
                    color_continuous_scale=["white", GREEN_SOFT, GREEN, GREEN_DARK],
                    labels={"color": ""}, text_auto=True)
    fig.update_layout(paper_bgcolor="white", margin=dict(t=10, b=10, l=0, r=0),
                      height=380, font=dict(family="Inter", size=11, color=INK),
                      coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

# ── Insights ─────────────────────────────────────────────────────────────────
st.markdown(f"## {t('sec_insights', lang)}")
st.markdown(f'<div class="intro">{t("sec_insights_intro", lang)}</div>', unsafe_allow_html=True)

if len(df_f) > 0:
    for ins in generate(df_f, lang=lang):
        st.markdown(
            f'<div class="insight">'
            f'<div class="insight-cat">{ins["category"]}</div>'
            f'<div class="insight-find">{ins["finding"]}</div>'
            f'<div class="insight-act">{ins["implication"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Próximos cursos ──────────────────────────────────────────────────────────
COURSES_PATH = Path(__file__).parent.parent.parent / "data" / "courses_2026.csv"

@st.cache_data(show_spinner=False)
def load_courses(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    c = pd.read_csv(path)
    c["start_date"] = pd.to_datetime(c["start_date"], errors="coerce")
    c["end_date"]   = pd.to_datetime(c["end_date"],   errors="coerce")
    for col in ("instructors", "focus_areas", "includes"):
        c[col] = c[col].fillna("").apply(lambda s: [x.strip() for x in s.split(";") if x.strip()])
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

courses = load_courses(COURSES_PATH)
if not courses.empty:
    today = pd.Timestamp.today().normalize()
    upcoming = courses[courses["end_date"] >= today].sort_values("start_date")
    if len(upcoming) > 0:
        st.markdown(f"## {t('sec_courses', lang)}")
        st.markdown(f'<div class="intro">{t("sec_courses_intro", lang)}</div>',
                    unsafe_allow_html=True)

        for _, c in upcoming.iterrows():
            date_str = fmt_date_range(c["start_date"], c["end_date"], lang)
            sessions_str = t("c_sessions", lang,
                             n=int(c["sessions"]), h=int(c["hours_per_session"]))
            desc_col = f"description_{lang}"
            desc = c[desc_col] if desc_col in c and pd.notna(c.get(desc_col)) else \
                   (c.get("description_es") or "")
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

# ── Directory — clickable rows ───────────────────────────────────────────────
st.markdown(f"## {t('sec_dir', lang)}")
st.markdown(f'<div class="intro">{t("sec_dir_intro", lang)}</div>', unsafe_allow_html=True)

sort_options = [t("sort_name", lang), t("sort_new", lang),
                t("sort_old", lang), t("sort_country", lang)]
sort_by = st.selectbox(t("sort_label", lang), sort_options, label_visibility="collapsed")

if sort_by == t("sort_name", lang):
    table = df_f.sort_values("name")
elif sort_by == t("sort_new", lang):
    table = df_f.sort_values("founded_year", ascending=False, na_position="last")
elif sort_by == t("sort_old", lang):
    table = df_f.sort_values("founded_year", ascending=True, na_position="last")
else:
    table = df_f.sort_values(["country", "name"])

if len(table) == 0:
    st.markdown(f'<div class="note">{t("search_empty", lang)}</div>', unsafe_allow_html=True)

for _, row in table.iterrows():
    focus_str = " · ".join(row["focus_areas"])
    founded = f' · {int(row["founded_year"])}' if pd.notna(row["founded_year"]) else ""
    label = (
        f'{row["name"]}\n'
        f'{row["type"]} · {row["city"]}, {row["country"]}{founded}\n'
        f'{row["description"]}\n'
        f'{focus_str} ›'
    )
    if st.button(label, key=f"org_{row['name']}", type="tertiary", use_container_width=True):
        st.session_state.selected_org = row["name"]
        st.rerun()
