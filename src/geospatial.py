import geopandas as gpd


def spatial_join(gdf_left: gpd.GeoDataFrame, gdf_right: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.sjoin(gdf_left, gdf_right, how="left", predicate="within")
