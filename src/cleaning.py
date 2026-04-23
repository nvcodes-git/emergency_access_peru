import re
import pandas as pd
import geopandas as gpd
from pathlib import Path

PROCESSED = Path("data/processed")


# --- General helpers ---

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9]+", "_", col.strip().lower()).strip("_")
        for col in df.columns
    ]
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    if dropped:
        print(f"  Removed {dropped} duplicate rows")
    return df


def remove_invalid_coords(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    before = len(df)
    df = df.copy()
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    # Peru bounding box: lat -18.4 to -0.03, lon -81.4 to -68.7
    mask = (
        df[lat_col].notna() & df[lon_col].notna() &
        df[lat_col].between(-18.4, -0.03) &
        df[lon_col].between(-81.4, -68.7)
    )
    df = df[mask]
    print(f"  Removed {before - len(df)} rows with invalid coordinates")
    return df


# --- Dataset-specific pipelines ---

def clean_centros_poblados(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = standardize_columns(gdf)
    gdf = remove_duplicates(gdf)
    gdf = gdf.dropna(subset=["geometry"])
    gdf = gdf.rename(columns={"c_d_int": "ubigeo_ref", "nom_poblad": "nombre", "cat_poblad": "tipo"})
    gdf = gdf.to_crs(epsg=4326)
    gdf.to_file(PROCESSED / "centros_poblados.gpkg", driver="GPKG")
    print(f"  Saved centros_poblados.gpkg - {len(gdf)} rows")
    return gdf


def clean_distritos(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = standardize_columns(gdf)
    gdf = remove_duplicates(gdf)
    gdf = gdf.dropna(subset=["geometry"])
    gdf = gdf.rename(columns={"iddist": "ubigeo", "departamen": "departamento"})
    gdf["ubigeo"] = gdf["ubigeo"].astype(str).str.zfill(6)
    gdf = gdf.to_crs(epsg=4326)
    gdf.to_file(PROCESSED / "distritos.gpkg", driver="GPKG")
    print(f"  Saved distritos.gpkg - {len(gdf)} rows")
    return gdf


def clean_emergencias(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_columns(df)
    df = remove_duplicates(df)
    df = df.dropna(subset=["ubigeo"])
    df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)
    df["anho"] = df["anho"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["nro_total_atenciones"] = pd.to_numeric(df["nro_total_atenciones"], errors="coerce")
    df["nro_total_atendidos"] = pd.to_numeric(df["nro_total_atendidos"], errors="coerce")
    df.to_csv(PROCESSED / "emergencias.csv", index=False)
    print(f"  Saved emergencias.csv - {len(df)} rows")
    return df


def clean_ipress(df: pd.DataFrame) -> pd.DataFrame:
    df = standardize_columns(df)
    df = remove_duplicates(df)
    df = df.dropna(subset=["ubigeo"])
    df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)
    df = df[df["estado"].str.upper() == "ACTIVADO"]
    # in this dataset norte holds longitude and este holds latitude
    df = remove_invalid_coords(df, lat_col="este", lon_col="norte")
    df.to_csv(PROCESSED / "ipress.csv", index=False)
    print(f"  Saved ipress.csv - {len(df)} rows")
    return df
