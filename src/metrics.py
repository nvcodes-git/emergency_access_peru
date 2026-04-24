import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

PROCESSED = Path("data/processed")


def _minmax(s: pd.Series) -> pd.Series:
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(0.0, index=s.index)
    return (s - mn) / (mx - mn)


def _log_minmax(s: pd.Series) -> pd.Series:
    return _minmax(np.log1p(s))


def aggregate_emergency_activity(emerg_path=PROCESSED / "emergencias.csv") -> pd.DataFrame:
    df = pd.read_csv(emerg_path, dtype={"ubigeo": str})
    agg = (
        df.groupby("ubigeo")[["nro_total_atenciones", "nro_total_atendidos"]]
        .sum()
        .reset_index()
        .rename(columns={
            "nro_total_atenciones": "total_atenciones",
            "nro_total_atendidos": "total_atendidos",
        })
    )
    return agg


def compute_access_index(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Baseline access index (v1): min-max normalization, equal weights.

    Components:
      - facilities_norm   : n_ipress normalized (higher = better)
      - emergency_norm    : total emergency attendees normalized (higher = better)
      - coverage_norm     : 1 / (1 + centros_per_facility) normalized (higher = better)

    Final score is the mean of the three components (0 = worst, 1 = best access).
    """
    emerg = aggregate_emergency_activity()
    df = layer.merge(emerg, on="ubigeo", how="left")
    df["total_atendidos"] = df["total_atendidos"].fillna(0)

    df["centros_per_facility"] = df["n_centros"] / (df["n_ipress"] + 1)
    df["coverage_raw"] = 1 / (1 + df["centros_per_facility"])

    df["facilities_norm"] = _minmax(df["n_ipress"].astype(float))
    df["emergency_norm"] = _minmax(df["total_atendidos"])
    df["coverage_norm"] = _minmax(df["coverage_raw"])

    df["access_score_v1"] = df[["facilities_norm", "emergency_norm", "coverage_norm"]].mean(axis=1)
    return df


def compute_access_index_log(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Alternative access index (v2): log-normalized, equal weights.

    Same components as v1 but log-transformed before normalization.
    This reduces the dominance of large urban districts (e.g. Lima) and makes
    relative differences between smaller districts more visible.

    V1 answers: which districts have the most resources in absolute terms?
    V2 answers: how does access look when we reduce urban dominance?
    """
    emerg = aggregate_emergency_activity()
    df = layer.merge(emerg, on="ubigeo", how="left")
    df["total_atendidos"] = df["total_atendidos"].fillna(0)

    df["centros_per_facility"] = df["n_centros"] / (df["n_ipress"] + 1)
    df["coverage_raw"] = 1 / (1 + df["centros_per_facility"])

    df["facilities_norm_log"] = _log_minmax(df["n_ipress"].astype(float))
    df["emergency_norm_log"] = _log_minmax(df["total_atendidos"])
    df["coverage_norm_log"] = _minmax(df["coverage_raw"])

    df["access_score_v2"] = df[["facilities_norm_log", "emergency_norm_log", "coverage_norm_log"]].mean(axis=1)
    return df


def build_full_metrics(layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Compute both index versions and merge into a single GeoDataFrame."""
    v1 = compute_access_index(layer)
    v2 = compute_access_index_log(layer)

    result = v1.copy()
    result["access_score_v2"] = v2["access_score_v2"]
    result["score_diff"] = result["access_score_v2"] - result["access_score_v1"]

    result.to_file(PROCESSED / "district_metrics.gpkg", driver="GPKG")
    print(f"  Metrics computed for {len(result)} districts")
    print(f"  V1 score range: {result['access_score_v1'].min():.3f} – {result['access_score_v1'].max():.3f}")
    print(f"  V2 score range: {result['access_score_v2'].min():.3f} – {result['access_score_v2'].max():.3f}")
    return result
