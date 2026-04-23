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
