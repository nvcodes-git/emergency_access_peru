# Emergency Healthcare Access in Peru

A geospatial analytics pipeline to study emergency healthcare access inequality across Peru's 1,873 districts, using public datasets on health facilities, emergency care activity, populated centers, and district boundaries.

---

## Project Structure

```
emergency_access_peru/
├── app.py                  # Streamlit application (4 tabs)
├── requirements.txt
├── src/
│   ├── data_loader.py      # Raw file loading functions
│   ├── cleaning.py         # Cleaning pipelines per dataset
│   ├── geospatial.py       # Spatial joins, map outputs
│   ├── metrics.py          # Access index computation (V1 & V2)
│   ├── visualization.py    # Static chart generation
│   └── utils.py
├── data/
│   ├── raw/                # Original downloaded files (not pushed)
│   └── processed/          # Cleaned outputs (not pushed)
├── output/
│   ├── figures/            # Saved charts and static maps
│   └── tables/             # Final district-level tables (CSV)
└── video/
    └── link.txt
```

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Before running the app for the first time, generate the processed data and figures by running this in a Python shell from the project root:

```python
from src.data_loader import load_centros_poblados, load_distritos, load_emergencias, load_ipress
from src.cleaning import clean_centros_poblados, clean_distritos, clean_emergencias, clean_ipress
from src.geospatial import load_ipress_gdf, load_centros_gdf, load_distritos_gdf, build_district_layer, generate_all_maps
from src.metrics import build_full_metrics
from src.visualization import generate_all_figures

# Step 1: Clean raw data → saves to data/processed/
clean_centros_poblados(load_centros_poblados())
clean_distritos(load_distritos())
clean_emergencias(load_emergencias())
clean_ipress(load_ipress())

# Step 2: Spatial joins + metrics
layer = build_district_layer(load_ipress_gdf(), load_centros_gdf(), load_distritos_gdf())
metrics = build_full_metrics(layer)

# Step 3: Figures, tables, and maps
generate_all_figures(metrics)
generate_all_maps(metrics)
```

---

## Data Sources

| Dataset | Source | Format |
|---|---|---|
| Centros Poblados (CCPP) | IGN / datosabiertos.gob.pe | Shapefile |
| District Boundaries | Course repository | Shapefile |
| Emergency Production 2025 | SUSALUD | CSV (semicolon-separated) |
| IPRESS Health Facilities | MINSA / datosabiertos.gob.pe | CSV |

---

## Data Cleaning Decisions

- **Centros Poblados**: removed rows with null geometry; standardized column names; reprojected to EPSG:4326. Column `CAT_POBLAD` renamed to `tipo` (not `categoria`) to avoid conflict with the existing `CATEGORIA` column.
- **Distritos**: removed rows with null geometry; `IDDIST` used as the UBIGEO join key since it already carries the 6-digit district code.
- **Emergencias**: removed 19,458 duplicate rows; file uses latin-1 encoding (not UTF-8); UBIGEO zero-padded to 6 digits to ensure consistent joins.
- **IPRESS**: removed 14 duplicates; filtered to `ACTIVADO` (active) facilities only; removed 12,853 rows with missing or out-of-bounds coordinates. Important: the `norte` and `este` columns are **swapped** in the source data — `norte` holds longitude and `este` holds latitude.

All cleaned outputs are saved to `data/processed/`. Shapefiles are stored as GeoPackage (`.gpkg`).

---

## CRS Handling

All geospatial layers are projected to **EPSG:4326 (WGS84)** — the standard geographic coordinate system using decimal degrees. This was chosen because:
- The IPRESS coordinates are already in decimal degrees
- Folium and most web mapping tools expect WGS84
- It allows consistent spatial joins across all datasets without reprojection errors

---

## Methodology — Emergency Access Index

Both index versions use **three components**, each normalized to 0–1 and averaged with equal weights. A higher score means better emergency healthcare access.

| Component | Formula | What it captures |
|---|---|---|
| Facility component | `n_ipress` (normalized) | Raw infrastructure availability |
| Emergency activity | `total_atendidos` (normalized) | Actual healthcare usage in 2025 |
| Coverage ratio | `1 / (1 + n_centros / (n_ipress + 1))` | Populated centers served per facility |

### V1 — Baseline (Linear normalization)
Standard min-max scaling applied to each component. Answers: *which districts have the most resources in absolute terms?*

**Limitation:** Lima district has 44 facilities — far more than any other — which dominates the linear scale and compresses all other districts toward 0, making differences between smaller districts nearly invisible.

### V2 — Alternative (Log normalization)
Each component is log-transformed (`log1p`) before min-max normalization. Answers: *how does access look when we reduce urban dominance?*

The key insight: going from 0 → 1 facility is a much larger relative improvement than going from 43 → 44. Log scaling captures this. The result is a more spread-out distribution that makes inequality between non-urban districts more visible and comparable.

### Comparison
The score distribution chart (Tab 2) shows the effect directly: V1 produces a sharp spike near 0 (most districts compressed at the bottom), while V2 produces a flatter, wider distribution where differences between districts are more distinguishable.

---

## Visualizations

### District Rankings (horizontal bar chart)
**Answers:** Which specific districts have the best and worst emergency access?
**Why chosen:** Horizontal bars keep long district names readable. Splitting into top/bottom side by side makes the inequality immediately visible.
**Why not a table:** A visual ranking communicates magnitude instantly — you can see how large the gap is between first and last, which a sorted table does not convey as effectively.

### Department Box Plot
**Answers:** Which departments have the most internal inequality between their districts?
**Why chosen:** A box plot shows both the median access level and the spread within each department simultaneously.
**Why not a bar chart of means:** A bar chart of means would hide within-department inequality entirely. Lima, for example, has a moderate mean but extreme outliers in both directions — some world-class urban districts and some rural districts with near-zero access. Only the box plot reveals this.

### Facilities vs Emergency Activity (scatter plot)
**Answers:** Are existing facilities actually being used? Are any being overwhelmed?
**Why chosen:** A scatter plot reveals the relationship between infrastructure (input) and usage (output) for each district independently.
**Why not a line chart:** Districts are independent observations, not a time series. A line chart would imply a sequence or trend that doesn't exist here. The scatter plot correctly treats each district as a point in a two-dimensional space.

**Key finding:** The top-left cluster (few facilities, very high attendees) identifies overstretched districts — places where the problem is not just absence of facilities but severe overload of the ones that exist.

### Score Distribution KDE (V1 vs V2)
**Answers:** How does our methodological choice between linear and log normalization change the overall picture?
**Why chosen:** A KDE (density) plot shows the full shape of the distribution — where scores are concentrated and how spread out they are.
**Why not a table of summary statistics:** Mean and standard deviation alone cannot reveal whether scores are clustered, bimodal, or skewed. Only the distribution shape communicates the full story of how normalization affects the results.

---

## Limitations

- **No true population data**: populated centers are used as a proxy for population, but do not capture actual population size. Lima district has 1 populated center but millions of residents, while a rural district may have 50 centers each with a few hundred people.
- **2025 data is partial**: the emergency production dataset covers only January–March 2025. Full-year figures would change the emergency activity component, particularly for seasonal health events.
- **Coordinate gaps in IPRESS**: 12,853 facilities (62% of raw records) had missing or invalid coordinates and were excluded from geospatial analysis. They are still counted in the facility component via the UBIGEO join, but cannot be placed on a map.
- **Equal weighting**: all three index components are weighted equally. A policy-driven weighting (e.g. prioritizing emergency activity over facility count) could produce meaningfully different district rankings.
- **District-level aggregation**: aggregating to districts masks within-district inequality. A district with one facility in its capital and many remote populated centers may score the same as one where the facility is centrally accessible.
