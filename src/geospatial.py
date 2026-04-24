import pandas as pd
import geopandas as gpd
from pathlib import Path

PROCESSED = Path("data/processed")


def load_ipress_gdf() -> gpd.GeoDataFrame:
    # norte = longitude, este = latitude (columns are swapped in source data)
    df = pd.read_csv(PROCESSED / "ipress.csv", dtype={"ubigeo": str})
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["norte"], df["este"]),
        crs="EPSG:4326",
    )
    return gdf


def load_centros_gdf() -> gpd.GeoDataFrame:
    return gpd.read_file(PROCESSED / "centros_poblados.gpkg")


def load_distritos_gdf() -> gpd.GeoDataFrame:
    return gpd.read_file(PROCESSED / "distritos.gpkg")


def assign_facilities_to_districts(
    ipress: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    ipress = ipress.to_crs(distritos.crs)
    joined = gpd.sjoin(ipress, distritos[["ubigeo", "distrito", "departamento", "geometry"]],
                       how="left", predicate="within")
    joined = joined.drop(columns=["index_right"], errors="ignore")
    joined = joined.rename(columns={"ubigeo_left": "ubigeo_ipress", "ubigeo_right": "ubigeo_distrito"})
    joined.to_file(PROCESSED / "ipress_con_distrito.gpkg", driver="GPKG")
    print(f"  Facilities assigned: {joined['ubigeo_distrito'].notna().sum()} / {len(joined)}")
    return joined


def assign_centros_to_districts(
    centros: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    centros = centros.to_crs(distritos.crs)
    joined = gpd.sjoin(centros, distritos[["ubigeo", "distrito", "departamento", "geometry"]],
                       how="left", predicate="within")
    joined = joined.drop(columns=["index_right"], errors="ignore")
    joined.to_file(PROCESSED / "centros_con_distrito.gpkg", driver="GPKG")
    print(f"  Centros assigned: {joined['ubigeo'].notna().sum()} / {len(joined)}")
    return joined


def build_district_layer(
    ipress: gpd.GeoDataFrame, centros: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    ipress_joined = assign_facilities_to_districts(ipress, distritos)
    centros_joined = assign_centros_to_districts(centros, distritos)

    facilities_per_district = (
        ipress_joined.groupby("ubigeo_distrito")
        .size()
        .reset_index(name="n_ipress")
        .rename(columns={"ubigeo_distrito": "ubigeo"})
    )

    centros_per_district = (
        centros_joined.groupby("ubigeo")
        .size()
        .reset_index(name="n_centros")
    )

    layer = distritos.merge(facilities_per_district, on="ubigeo", how="left")
    layer = layer.merge(centros_per_district, on="ubigeo", how="left")
    layer["n_ipress"] = layer["n_ipress"].fillna(0).astype(int)
    layer["n_centros"] = layer["n_centros"].fillna(0).astype(int)

    layer.to_file(PROCESSED / "district_layer.gpkg", driver="GPKG")
    print(f"  District layer built: {len(layer)} districts")
    print(f"  Districts with 0 facilities: {(layer['n_ipress'] == 0).sum()}")
    return layer


# --- Map outputs (Task 5) ---

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium
from pathlib import Path

FIGURES = Path("output/figures")


def plot_static_choropleth(metrics: gpd.GeoDataFrame) -> plt.Figure:
    """Side-by-side static choropleth: V1 (linear) vs V2 (log-normalized).

    Lets the viewer compare how normalization choice changes the geographic
    picture of inequality — not just a score table but a spatial story.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10))

    metrics.plot(column="access_score_v1", cmap="RdYlGn", legend=True,
                 legend_kwds={"label": "Access Score V1", "shrink": 0.6},
                 missing_kwds={"color": "lightgrey"}, ax=ax1, linewidth=0.1, edgecolor="white")
    ax1.set_title("V1 — Linear Normalization\n(Large urban districts dominate)", fontweight="bold")
    ax1.axis("off")

    metrics.plot(column="access_score_v2", cmap="RdYlGn", legend=True,
                 legend_kwds={"label": "Access Score V2", "shrink": 0.6},
                 missing_kwds={"color": "lightgrey"}, ax=ax2, linewidth=0.1, edgecolor="white")
    ax2.set_title("V2 — Log Normalization\n(Relative differences more visible)", fontweight="bold")
    ax2.axis("off")

    fig.suptitle("Emergency Healthcare Access by District — Peru 2025",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIGURES / "choropleth_v1_vs_v2.png", dpi=150, bbox_inches="tight")
    print("  Saved choropleth_v1_vs_v2.png")
    return fig


def plot_zero_facilities_map(metrics: gpd.GeoDataFrame) -> plt.Figure:
    """Static map highlighting districts with zero health facilities.

    A binary map is more impactful than a choropleth here — the absence
    of any facility is a categorical problem, not a gradual one.
    """
    metrics = metrics.copy()
    metrics["has_facility"] = metrics["n_ipress"] > 0

    fig, ax = plt.subplots(figsize=(10, 12))
    metrics[metrics["has_facility"]].plot(color="#2ecc71", ax=ax, linewidth=0.1,
                                          edgecolor="white", label="Has facilities")
    metrics[~metrics["has_facility"]].plot(color="#e74c3c", ax=ax, linewidth=0.1,
                                           edgecolor="white", label="No facilities")

    green = mpatches.Patch(color="#2ecc71", label=f"Has facilities ({metrics['has_facility'].sum()})")
    red = mpatches.Patch(color="#e74c3c", label=f"No facilities ({(~metrics['has_facility']).sum()})")
    ax.legend(handles=[green, red], loc="lower left", fontsize=11)
    ax.set_title("Districts with No Emergency Health Facilities — Peru 2025",
                 fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    fig.savefig(FIGURES / "zero_facilities_map.png", dpi=150, bbox_inches="tight")
    print("  Saved zero_facilities_map.png")
    return fig


def build_folium_choropleth(metrics: gpd.GeoDataFrame, column: str = "access_score_v1") -> folium.Map:
    """Interactive Folium choropleth with per-district tooltips.

    Uses GeoJsonTooltip (single layer) instead of per-row GeoJson objects
    for performance with 1873 districts.
    """
    m = folium.Map(location=[-9.19, -75.0], zoom_start=5, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=metrics[["ubigeo", "geometry"]].to_json(),
        data=metrics[["ubigeo", column]],
        columns=["ubigeo", column],
        key_on="feature.properties.ubigeo",
        fill_color="RdYlGn",
        fill_opacity=0.75,
        line_opacity=0.2,
        legend_name=f"Access Score ({column})",
    ).add_to(m)

    tooltip_gdf = metrics[["ubigeo", "distrito", "departamento", "n_ipress",
                            "n_centros", "access_score_v1", "access_score_v2", "geometry"]].copy()
    tooltip_gdf["access_score_v1"] = tooltip_gdf["access_score_v1"].round(3)
    tooltip_gdf["access_score_v2"] = tooltip_gdf["access_score_v2"].round(3)

    folium.GeoJson(
        tooltip_gdf.to_json(),
        style_function=lambda x: {"fillOpacity": 0, "weight": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["distrito", "departamento", "n_ipress", "n_centros",
                    "access_score_v1", "access_score_v2"],
            aliases=["District", "Department", "Facilities", "Populated Centers",
                     "Score V1", "Score V2"],
        ),
    ).add_to(m)

    m.save(str(FIGURES / f"map_{column}.html"))
    print(f"  Saved map_{column}.html")
    return m


def generate_all_maps(metrics: gpd.GeoDataFrame) -> dict:
    print("Generating geospatial outputs...")
    return {
        "choropleth": plot_static_choropleth(metrics),
        "zero_facilities": plot_zero_facilities_map(metrics),
        "folium_v1": build_folium_choropleth(metrics, "access_score_v1"),
        "folium_v2": build_folium_choropleth(metrics, "access_score_v2"),
    }
