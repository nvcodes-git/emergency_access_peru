import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import geopandas as gpd
from pathlib import Path

FIGURES = Path("output/figures")
sns.set_theme(style="whitegrid", palette="muted")


def plot_top_bottom_districts(metrics: gpd.GeoDataFrame, n: int = 20) -> plt.Figure:
    """Horizontal bar chart of top-n and bottom-n districts by V1 access score.

    Chosen over a table because visual ranking is faster to interpret.
    Horizontal bars avoid overlapping long district names.
    """
    top = metrics.nlargest(n, "access_score_v1")[["distrito", "departamento", "access_score_v1"]].copy()
    bottom = metrics.nsmallest(n, "access_score_v1")[["distrito", "departamento", "access_score_v1"]].copy()
    top["label"] = top["distrito"] + " (" + top["departamento"] + ")"
    bottom["label"] = bottom["distrito"] + " (" + bottom["departamento"] + ")"

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    sns.barplot(data=top.sort_values("access_score_v1"), x="access_score_v1", y="label",
                color="#2ecc71", ax=ax1)
    ax1.set_title(f"Top {n} Districts — Best Access (V1)", fontweight="bold")
    ax1.set_xlabel("Access Score V1")
    ax1.set_ylabel("")
    ax1.set_xlim(0, 1)

    sns.barplot(data=bottom.sort_values("access_score_v1", ascending=False), x="access_score_v1",
                y="label", color="#e74c3c", ax=ax2)
    ax2.set_title(f"Bottom {n} Districts — Worst Access (V1)", fontweight="bold")
    ax2.set_xlabel("Access Score V1")
    ax2.set_ylabel("")
    ax2.set_xlim(0, 1)

    fig.suptitle("Emergency Healthcare Access Inequality — District Rankings", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIGURES / "district_rankings.png", dpi=150, bbox_inches="tight")
    print("  Saved district_rankings.png")
    return fig


def plot_department_boxplot(metrics: gpd.GeoDataFrame) -> plt.Figure:
    """Box plot of V1 access scores grouped by department.

    Chosen over a bar chart of means because it reveals within-department
    inequality — a department with a high mean but high variance is very
    different from one with a consistently moderate score.
    """
    dept_medians = (
        metrics.groupby("departamento")["access_score_v1"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )

    fig, ax = plt.subplots(figsize=(14, 9))
    sns.boxplot(data=metrics, x="access_score_v1", y="departamento",
                order=dept_medians, color="#3498db", width=0.6, ax=ax)
    ax.set_title("Access Score Distribution by Department (V1)\nSorted by median — box width shows inequality within department",
                 fontweight="bold")
    ax.set_xlabel("Access Score V1")
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(FIGURES / "department_boxplot.png", dpi=150, bbox_inches="tight")
    print("  Saved department_boxplot.png")
    return fig


def plot_facilities_vs_activity(metrics: gpd.GeoDataFrame) -> plt.Figure:
    """Scatter plot of facility count vs emergency attendees, colored by access score.

    Chosen to test whether infrastructure (facilities) correlates with actual
    emergency healthcare usage. A line chart would be wrong here since districts
    are independent observations, not a time series.
    """
    df = metrics[metrics["total_atendidos"] > 0].copy()

    fig, ax = plt.subplots(figsize=(10, 7))
    scatter = ax.scatter(
        df["n_ipress"],
        df["total_atendidos"],
        c=df["access_score_v1"],
        cmap="RdYlGn",
        alpha=0.7,
        edgecolors="white",
        linewidths=0.4,
        s=50,
    )
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Access Score V1")
    ax.set_xlabel("Number of IPRESS Facilities")
    ax.set_ylabel("Total Emergency Attendees (2025)")
    ax.set_title("Facilities vs Emergency Activity by District\nColored by Access Score V1",
                 fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIGURES / "facilities_vs_activity.png", dpi=150, bbox_inches="tight")
    print("  Saved facilities_vs_activity.png")
    return fig


def plot_score_comparison(metrics: gpd.GeoDataFrame) -> plt.Figure:
    """KDE overlay comparing V1 (linear) and V2 (log-normalized) score distributions.

    Shows how log normalization redistributes scores across districts.
    A table cannot communicate this shape difference — only a distribution
    plot reveals whether scores are clustered at the bottom or more spread out.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.kdeplot(metrics["access_score_v1"], ax=ax, fill=True, alpha=0.4,
                color="#e74c3c", label="V1 — Linear normalization")
    sns.kdeplot(metrics["access_score_v2"], ax=ax, fill=True, alpha=0.4,
                color="#3498db", label="V2 — Log normalization")
    ax.set_xlabel("Access Score")
    ax.set_ylabel("Density")
    ax.set_title("Access Score Distribution: V1 vs V2\nLog normalization (V2) spreads scores more evenly across districts",
                 fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIGURES / "score_comparison_v1_v2.png", dpi=150, bbox_inches="tight")
    print("  Saved score_comparison_v1_v2.png")
    return fig


def generate_all_figures(metrics: gpd.GeoDataFrame) -> dict:
    print("Generating static figures...")
    return {
        "rankings": plot_top_bottom_districts(metrics),
        "boxplot": plot_department_boxplot(metrics),
        "scatter": plot_facilities_vs_activity(metrics),
        "comparison": plot_score_comparison(metrics),
    }
