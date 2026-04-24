import matplotlib
matplotlib.use("Agg")

import streamlit as st
import geopandas as gpd
import pandas as pd
from pathlib import Path
from streamlit_folium import st_folium

from src.visualization import (
    plot_top_bottom_districts, plot_department_boxplot,
    plot_facilities_vs_activity, plot_score_comparison,
)
from src.geospatial import build_folium_choropleth

PROCESSED = Path("data/processed")
FIGURES = Path("output/figures")

st.set_page_config(page_title="Emergency Access Peru", layout="wide")
st.title("Emergency Healthcare Access Inequality in Peru")
st.caption("District-level geospatial analysis — 2025 data")


@st.cache_data
def load_metrics():
    return gpd.read_file(PROCESSED / "district_metrics.gpkg")


metrics = load_metrics()

tab1, tab2, tab3, tab4 = st.tabs([
    "Data & Methodology",
    "Static Analysis",
    "GeoSpatial Results",
    "Interactive Exploration",
])


# ── Tab 1: Data & Methodology ─────────────────────────────────────────────────
with tab1:
    st.header("Problem Statement")
    st.markdown("""
    Emergency healthcare access in Peru is highly unequal across its 1,873 districts.
    This project builds a geospatial analytics pipeline to measure and visualize that
    inequality using public datasets on health facilities, emergency care activity,
    populated centers, and district boundaries.

    **Central question:** Which districts have the best and worst emergency healthcare
    access, and what geographic patterns does this inequality follow?
    """)

    st.header("Data Sources")
    st.dataframe(pd.DataFrame({
        "Dataset": ["Centros Poblados (CCPP)", "District Boundaries", "Emergency Production 2025", "IPRESS Health Facilities"],
        "Source": ["IGN / datosabiertos.gob.pe", "Course repository", "SUSALUD", "MINSA / datosabiertos.gob.pe"],
        "Format": ["Shapefile", "Shapefile", "CSV (semicolon)", "CSV"],
        "Records (raw)": ["136,587", "1,873", "342,753", "20,785"],
        "Records (cleaned)": ["136,587", "1,873", "323,295", "7,952"],
    }), use_container_width=True)

    st.header("Cleaning Decisions")
    with st.expander("See cleaning summary"):
        st.markdown("""
        - **Centros Poblados**: removed rows with null geometry; standardized column names; reprojected to EPSG:4326
        - **Distritos**: removed rows with null geometry; `IDDIST` used as UBIGEO key (already 6-digit code)
        - **Emergencias**: removed 19,458 duplicate rows; latin-1 encoding (not UTF-8); UBIGEO zero-padded to 6 digits
        - **IPRESS**: removed 14 duplicates; filtered to `ACTIVADO` facilities only; removed 12,853 rows with missing or
          out-of-bounds coordinates. Note: `norte`/`este` columns are swapped in the source data — `norte` holds longitude
          and `este` holds latitude.
        """)

    st.header("Methodology")
    with st.expander("Access Index — V1 vs V2"):
        st.markdown("""
        Both versions use **three components**, each normalized to 0–1 and averaged with equal weights:

        | Component | What it measures |
        |---|---|
        | Facility component | Number of IPRESS facilities in the district |
        | Emergency activity | Total emergency patients attended in 2025 |
        | Coverage ratio | `1 / (1 + populated_centers_per_facility)` — fewer centers per facility = better |

        **V1 — Linear normalization (baseline):** Standard min-max scaling. Answers: *which districts have the most
        resources in absolute terms?* Limitation: Lima's 44 facilities dominate the scale, compressing all other
        districts toward 0.

        **V2 — Log normalization (alternative):** Log-transforms each component before normalizing. Answers: *how does
        access look when we reduce urban dominance?* A district going from 0 → 1 facility is treated as a bigger
        relative gain than going from 43 → 44.
        """)

    st.header("Limitations")
    with st.expander("Known limitations"):
        st.markdown("""
        - **No true population data**: populated centers are used as a population proxy, but do not capture actual
          population size. Lima district has 1 populated center but millions of residents.
        - **2025 data is partial**: the emergency production dataset covers only Jan–Mar 2025. Full-year figures
          would change the emergency activity component.
        - **Coordinate gaps in IPRESS**: 12,853 facilities (62%) had missing or invalid coordinates and were excluded
          from the geospatial analysis, though they are still counted in the facility component via the UBIGEO join.
        - **Equal weighting**: all three components are weighted equally. A policy-driven weighting (e.g. giving more
          weight to emergency activity) could produce different rankings.
        """)


# ── Tab 2: Static Analysis ────────────────────────────────────────────────────
with tab2:
    st.header("Static Analysis")

    st.subheader("District Rankings — Top & Bottom 20")
    st.markdown("""
    **What it answers:** Which specific districts have the best and worst emergency access?
    **Why this chart:** Horizontal bars let long district names stay readable. Splitting into
    top/bottom makes the inequality immediately visible side by side.
    """)
    fig_rank = plot_top_bottom_districts(metrics)
    st.pyplot(fig_rank)
    st.markdown("""
    *Lima and Callao districts dominate the top. The bottom 20 are almost entirely from Puno
    and Huánuco — all with zero facilities.*
    """)

    st.divider()

    st.subheader("Access Score Distribution by Department")
    st.markdown("""
    **What it answers:** Which departments have the most internal inequality?
    **Why this chart:** A box plot shows both the median and the spread. A bar chart of means
    would hide the fact that Lima has extreme outliers while most departments are uniformly poor.
    """)
    fig_box = plot_department_boxplot(metrics)
    st.pyplot(fig_box)
    st.markdown("""
    *Lima shows the widest spread — some districts are excellent, others are terrible.
    Most departments cluster near 0, showing how concentrated access is in the capital.*
    """)

    st.divider()

    st.subheader("Facilities vs Emergency Activity")
    st.markdown("""
    **What it answers:** Are existing facilities actually being used — and are any being overwhelmed?
    **Why this chart:** A scatter plot reveals the relationship between infrastructure and usage.
    The top-left cluster (few facilities, high attendees) identifies overstretched facilities.
    """)
    fig_scat = plot_facilities_vs_activity(metrics)
    st.pyplot(fig_scat)
    st.markdown("""
    *Districts in the top-left have 1–5 facilities handling over 200,000 emergency patients — 
    a sign of severe overcrowding. The problem is not just absence of facilities but also overload.*
    """)

    st.divider()

    st.subheader("Score Distribution: V1 vs V2")
    st.markdown("""
    **What it answers:** How does our methodological choice change the picture?
    **Why this chart:** Only a distribution plot reveals whether scores are clustered or spread.
    A table of numbers cannot communicate this shape difference.
    """)
    fig_cmp = plot_score_comparison(metrics)
    st.pyplot(fig_cmp)
    st.markdown("""
    *V1 has a sharp spike near 0 — most districts are compressed at the bottom.
    V2's flatter, wider curve means differences between districts are more distinguishable.*
    """)


# ── Tab 3: GeoSpatial Results ─────────────────────────────────────────────────
with tab3:
    st.header("GeoSpatial Results")

    st.subheader("Access Score by District — V1 vs V2")
    st.image(str(FIGURES / "choropleth_v1_vs_v2.png"), use_container_width=True)
    st.markdown("""
    V1 is almost entirely red — urban dominance compresses the national picture.
    V2 reveals geographic patterns: the coast is generally better served than the highlands and jungle.
    """)

    st.divider()

    st.subheader("Districts with No Emergency Health Facilities")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(str(FIGURES / "zero_facilities_map.png"), use_container_width=True)
    with col2:
        st.markdown("""
        **55 districts (2.9%) have zero IPRESS health facilities.**

        These districts are not randomly distributed — they cluster in:
        - **Puno** (southern highlands)
        - **Huánuco** (central highlands)
        - Scattered border districts in Arequipa

        This is a categorical problem: no score, no access.
        """)
        zero = metrics[metrics["n_ipress"] == 0][["distrito", "departamento", "n_centros"]].copy()
        zero.columns = ["District", "Department", "Populated Centers"]
        st.dataframe(zero.reset_index(drop=True), use_container_width=True)

    st.divider()

    st.subheader("District-level Data Table")
    display_cols = ["distrito", "departamento", "n_ipress", "n_centros",
                    "access_score_v1", "access_score_v2", "score_diff"]
    df_display = metrics[display_cols].copy()
    df_display.columns = ["District", "Department", "Facilities", "Populated Centers",
                           "Score V1", "Score V2", "V2 - V1"]
    df_display = df_display.round(3).sort_values("Score V1", ascending=False).reset_index(drop=True)
    st.dataframe(df_display, use_container_width=True)


# ── Tab 4: Interactive Exploration ────────────────────────────────────────────
with tab4:
    st.header("Interactive Exploration")

    st.subheader("Choropleth Map")
    score_col = st.radio(
        "Score version:",
        ["access_score_v1", "access_score_v2"],
        format_func=lambda x: "V1 — Linear normalization" if x == "access_score_v1" else "V2 — Log normalization",
        horizontal=True,
    )
    with st.spinner("Building map..."):
        folium_map = build_folium_choropleth(metrics, score_col)
    st_folium(folium_map, use_container_width=True, height=550)

    st.divider()

    st.subheader("District Comparison")
    st.markdown("Select districts to compare their access scores and components side by side.")

    dept_options = sorted(metrics["departamento"].unique())
    selected_dept = st.selectbox("Filter by department:", ["All"] + dept_options)

    if selected_dept == "All":
        dist_options = sorted(metrics["distrito"].unique())
    else:
        dist_options = sorted(metrics[metrics["departamento"] == selected_dept]["distrito"].unique())

    selected_dists = st.multiselect("Select districts:", dist_options, max_selections=6)

    if selected_dists:
        comp_cols = ["distrito", "departamento", "n_ipress", "n_centros",
                     "total_atendidos", "access_score_v1", "access_score_v2"]
        comp = metrics[metrics["distrito"].isin(selected_dists)][comp_cols].copy()
        comp.columns = ["District", "Department", "Facilities", "Populated Centers",
                        "Emergency Attendees", "Score V1", "Score V2"]
        comp = comp.round(3).reset_index(drop=True)
        st.dataframe(comp, use_container_width=True)

    st.divider()

    st.subheader("Baseline vs Alternative — Score Shift")
    st.markdown("""
    Districts where V2 score is much **higher** than V1 are places where log normalization
    reveals relatively better access than raw counts suggest.
    Districts where V2 is **lower** than V1 are places that look better in absolute terms
    but perform poorly relative to their size.
    """)
    n_show = st.slider("Number of districts to show:", 10, 50, 20)
    shift = metrics[["distrito", "departamento", "access_score_v1", "access_score_v2", "score_diff"]].copy()
    shift = shift.reindex(shift["score_diff"].abs().nlargest(n_show).index)
    shift = shift.sort_values("score_diff", ascending=False).round(3).reset_index(drop=True)
    shift.columns = ["District", "Department", "Score V1", "Score V2", "Shift (V2-V1)"]
    st.dataframe(shift, use_container_width=True)
