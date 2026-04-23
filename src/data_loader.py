import pandas as pd
import geopandas as gpd
from pathlib import Path

RAW = Path("data/raw")


def load_centros_poblados() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / "CCPP_IGN100K.shp")


def load_distritos() -> gpd.GeoDataFrame:
    return gpd.read_file(RAW / "DISTRITOS.shp")


def load_emergencias() -> pd.DataFrame:
    return pd.read_csv(RAW / "ConsultaC1_2025_v20.csv", sep=";", encoding="latin-1", dtype={"UBIGEO": str})


def load_ipress() -> pd.DataFrame:
    return pd.read_csv(RAW / "IPRESS.csv", encoding="latin-1", dtype={"UBIGEO": str})
