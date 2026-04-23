import matplotlib.pyplot as plt
import seaborn as sns
import folium


def plot_bar(df, x, y, title="", save_path=None):
    fig, ax = plt.subplots()
    sns.barplot(data=df, x=x, y=y, ax=ax)
    ax.set_title(title)
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def build_folium_map(gdf, column, legend_name="") -> folium.Map:
    m = folium.Map(location=[-9.19, -75.0152], zoom_start=5)
    folium.Choropleth(
        geo_data=gdf.to_json(),
        data=gdf,
        columns=["ubigeo", column],
        key_on="feature.properties.ubigeo",
        fill_color="YlOrRd",
        legend_name=legend_name,
    ).add_to(m)
    return m
