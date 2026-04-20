"""
Nodal · Latin American Urban Changemakers
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

st.set_page_config(
    page_title="Nodal",
    layout="wide",
    initial_sidebar_state="expanded",
)

INK = "#111111"
MUTED = "#6B6B6B"
RULE = "#111111"
SOFT = "#EDEDED"
ACCENT = "#111111"

MONO_SEQUENCE = ["#111111", "#3E3E3E", "#6B6B6B", "#9A9A9A", "#BEBEBE", "#D8D8D8"]

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"]  {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    .block-container {{ padding-top: 2.5rem; padding-bottom: 5rem; max-width: 1180px; }}
    h1, h2, h3, h4 {{ color: {INK}; font-weight: 700; letter-spacing: -0.015em; }}
    h1 {{ font-size: 2.6rem; line-height: 1.1; margin-bottom: 0.2rem; font-weight: 800; }}
    h2 {{ font-size: 1.3rem; margin-top: 2.5rem; margin-bottom: 1rem;
          text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
    h3 {{ font-size: 1rem; margin-bottom: 0.8rem; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.08em; color: {INK}; }}
    .lede {{ color: {MUTED}; font-size: 1.1rem; line-height: 1.5;
             max-width: 720px; margin-bottom: 0.5rem; }}
    .eyebrow {{ color: {MUTED}; font-size: 0.78rem; text-transform: uppercase;
                letter-spacing: 0.18em; font-weight: 600; margin-bottom: 1rem; }}
    hr.thick {{ border: none; border-top: 2px solid {INK}; margin: 1.5rem 0 2rem 0; }}
    hr.thin  {{ border: none; border-top: 1px solid {SOFT}; margin: 2rem 0; }}
    .stat {{ padding: 0.8rem 0; border-top: 1px solid {SOFT}; }}
    .stat-label {{ color: {MUTED}; font-size: 0.78rem; text-transform: uppercase;
                   letter-spacing: 0.1em; margin-bottom: 0.3rem; }}
    .stat-value {{ color: {INK}; font-size: 2.2rem; font-weight: 700;
                   line-height: 1; font-variant-numeric: tabular-nums; }}
    .insight {{ padding: 1.2rem 0; border-top: 1px solid {SOFT}; }}
    .insight-cat {{ color: {MUTED}; font-size: 0.72rem; text-transform: uppercase;
                    letter-spacing: 0.15em; font-weight: 600; margin-bottom: 0.5rem; }}
    .insight-find {{ color: {INK}; font-size: 1.1rem; font-weight: 600;
                     line-height: 1.35; margin-bottom: 0.5rem; }}
    .insight-act {{ color: {MUTED}; font-size: 0.95rem; line-height: 1.55; }}
    .org-row {{ padding: 1rem 0; border-top: 1px solid {SOFT}; }}
    .org-name {{ font-size: 1.05rem; font-weight: 600; color: {INK}; }}
    .org-meta {{ color: {MUTED}; font-size: 0.82rem; margin-top: 0.15rem; }}
    .org-desc {{ color: {INK}; font-size: 0.95rem; line-height: 1.55;
                 margin-top: 0.5rem; max-width: 780px; }}
    .org-focus {{ color: {MUTED}; font-size: 0.82rem; margin-top: 0.4rem;
                  text-transform: uppercase; letter-spacing: 0.08em; }}
    .note {{ color: {MUTED}; font-size: 0.85rem; font-style: italic;
             max-width: 780px; line-height: 1.5; margin-top: 0.3rem; }}

    [data-testid="stSidebar"] {{ background: #FAFAFA; border-right: 1px solid {SOFT}; }}
    [data-testid="stSidebar"] h2 {{ font-size: 0.9rem; letter-spacing: 0.15em; }}

    .stPlotlyChart, [data-testid="stDataFrame"] {{ border: none; }}
</style>
""", unsafe_allow_html=True)

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
    st.markdown("## NODAL")
    st.markdown('<div style="color:#6B6B6B; font-size:0.82rem; margin-bottom:1.5rem;">'
                'Urban Changemakers · Latin America</div>',
                unsafe_allow_html=True)

    st.markdown("### Source")
    source = st.radio("Source", ["Curated dataset", "Google Sheet", "Upload CSV"],
                      label_visibility="collapsed")

    if source == "Google Sheet":
        sheet_id = st.text_input("Sheet ID")
        df = get_data(source, sheet_id=sheet_id)
    elif source == "Upload CSV":
        uploaded_file = st.file_uploader("CSV file", type="csv")
        df = get_data(source, uploaded=uploaded_file)
    else:
        df = get_data(source)

    st.markdown("### Filters")
    sel_types = st.multiselect("Type", sorted(df["type"].dropna().unique()),
                               default=sorted(df["type"].dropna().unique()))
    sel_countries = st.multiselect("Country", sorted(df["country"].dropna().unique()),
                                   default=sorted(df["country"].dropna().unique()))
    all_focus = sorted({f for lst in df["focus_areas"] for f in lst})
    sel_focus = st.multiselect("Focus", all_focus, default=all_focus)

    df_f = df[
        df["type"].isin(sel_types)
        & df["country"].isin(sel_countries)
        & df["focus_areas"].apply(lambda lst: any(f in sel_focus for f in lst) or not lst)
    ]

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="eyebrow">Nodal · Member Intelligence</div>', unsafe_allow_html=True)
st.markdown("# Nodos urbanos de América Latina")
st.markdown(
    '<div class="lede">A working directory of the civic-urbanism ecosystem across the region. '
    f'{len(df_f)} entries drawn from public sources, intended as a seed for Nodal\'s own '
    'member base as intake scales.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="note">Sources: Americas Quarterly · IDB · PlacemakingX · '
    'Red Cómo Vamos · Sistema Urbano · UN-Habitat. Last compiled April 2026.</div>',
    unsafe_allow_html=True,
)
st.markdown('<hr class="thick">', unsafe_allow_html=True)

# ── Overview stats ───────────────────────────────────────────────────────────
def stat(col, label, value):
    col.markdown(
        f'<div class="stat">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

c1, c2, c3, c4, c5 = st.columns(5)
stat(c1, "Organisations", len(df_f))
stat(c2, "Countries", df_f["country"].nunique())
stat(c3, "Cities", df_f["city"].nunique())
stat(c4, "Focus areas", df_f["focus_areas"].explode().nunique())
median_age = int(df_f["age_years"].replace(0, pd.NA).median() or 0)
stat(c5, "Median age", f"{median_age} yrs")

# ── Map ──────────────────────────────────────────────────────────────────────
st.markdown("## Dónde están")

map_df = df_f.copy()
map_df["primary_focus"] = map_df["focus_areas"].apply(lambda lst: lst[0] if lst else "Other")

fig_map = px.scatter_map(
    map_df,
    lat="lat", lon="lon",
    hover_name="name",
    hover_data={"city": True, "country": True, "type": True,
                "lat": False, "lon": False, "primary_focus": False},
    color_discrete_sequence=[INK],
    zoom=2.2,
    center={"lat": -12, "lon": -62},
    height=520,
    map_style="carto-positron",
)
fig_map.update_traces(marker=dict(size=11, color=INK, opacity=0.85))
fig_map.update_layout(
    margin=dict(t=0, b=0, l=0, r=0),
    paper_bgcolor="white",
    showlegend=False,
)
st.plotly_chart(fig_map, use_container_width=True)

# ── Composition ──────────────────────────────────────────────────────────────
st.markdown("## Quiénes son")

col_a, col_b = st.columns(2)

def clean_chart(fig, height=340):
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=10, b=10, l=0, r=10),
        height=height,
        font=dict(family="Inter", size=12, color=INK),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=SOFT, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

with col_a:
    st.markdown("### Por tipo de actor")
    d = seg.by_type(df_f)
    fig = px.bar(d, x="count", y="type", orientation="h",
                 color_discrete_sequence=[INK],
                 labels={"count": "", "type": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(clean_chart(fig), use_container_width=True)

with col_b:
    st.markdown("### Por país")
    d = seg.by_country(df_f).head(10)
    fig = px.bar(d, x="count", y="country", orientation="h",
                 color_discrete_sequence=[INK],
                 labels={"count": "", "country": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(clean_chart(fig), use_container_width=True)

# ── Focus areas ──────────────────────────────────────────────────────────────
st.markdown("## Qué temas trabajan")

col_c, col_d = st.columns([1.3, 1])

with col_c:
    st.markdown("### Áreas de enfoque")
    focus_s = seg.by_focus(df_f).reset_index()
    focus_s.columns = ["area", "count"]
    fig = px.bar(focus_s, x="count", y="area", orientation="h",
                 color_discrete_sequence=[INK],
                 labels={"count": "", "area": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(clean_chart(fig), use_container_width=True)

with col_d:
    st.markdown("### Por generación")
    if "generation" in df_f.columns:
        gen_df = df_f["generation"].value_counts().reset_index()
        gen_df.columns = ["generation", "count"]
        fig = px.bar(gen_df.sort_values("generation"),
                     x="count", y="generation", orientation="h",
                     color_discrete_sequence=[INK],
                     labels={"count": "", "generation": ""})
        st.plotly_chart(clean_chart(fig), use_container_width=True)

# ── Country × focus matrix ───────────────────────────────────────────────────
st.markdown("## Matriz país × tema")
pivot = seg.cross_country_focus(df_f)
pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
fig = px.imshow(pivot, aspect="auto",
                color_continuous_scale=["white", INK],
                labels={"color": ""}, text_auto=True)
fig.update_layout(
    paper_bgcolor="white",
    margin=dict(t=10, b=10, l=0, r=0),
    height=380,
    font=dict(family="Inter", size=11, color=INK),
    coloraxis_showscale=False,
)
st.plotly_chart(fig, use_container_width=True)

# ── Insights ─────────────────────────────────────────────────────────────────
st.markdown("## Lecturas para Nodal")

insights = generate(df_f)
for ins in insights:
    st.markdown(
        f'<div class="insight">'
        f'<div class="insight-cat">{ins["category"]}</div>'
        f'<div class="insight-find">{ins["finding"]}</div>'
        f'<div class="insight-act">{ins["implication"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Directory ────────────────────────────────────────────────────────────────
st.markdown("## Directorio")

sort_by = st.selectbox("Ordenar por", ["Nombre", "Más recientes", "Más antiguas", "País"],
                       label_visibility="collapsed")
if sort_by == "Nombre":
    table = df_f.sort_values("name")
elif sort_by == "Más recientes":
    table = df_f.sort_values("founded_year", ascending=False, na_position="last")
elif sort_by == "Más antiguas":
    table = df_f.sort_values("founded_year", ascending=True, na_position="last")
else:
    table = df_f.sort_values(["country", "name"])

for _, row in table.iterrows():
    focus_str = " · ".join(row["focus_areas"])
    founded = f"· fundada en {int(row['founded_year'])}" if pd.notna(row['founded_year']) else ""
    st.markdown(
        f'<div class="org-row">'
        f'<div class="org-name">{row["name"]}</div>'
        f'<div class="org-meta">{row["type"]} · {row["city"]}, {row["country"]} {founded}</div>'
        f'<div class="org-desc">{row["description"]}</div>'
        f'<div class="org-focus">{focus_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
