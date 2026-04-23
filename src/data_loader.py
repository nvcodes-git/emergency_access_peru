import pandas as pd
import geopandas as gpd


def load_raw(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load_geodata(path: str) -> gpd.GeoDataFrame:
    return gpd.read_file(path)
