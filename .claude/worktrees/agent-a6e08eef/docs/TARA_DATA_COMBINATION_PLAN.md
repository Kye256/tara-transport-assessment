# TARA Data Combination Plan
## Kontur Population + HeiGIT Road Surface + Edinburgh Travel Time Roads
**Date:** Thursday, February 12, 2026

---

## The Three Datasets at a Glance

### 1. Kontur Population — Uganda (400m H3 Hexagons)
- **Source:** HDX — `https://data.humdata.org/dataset/kontur-population-uganda`
- **Format:** GeoPackage (`.gpkg`) — vector H3 hexagons
- **Resolution:** 400m (H3 resolution 8)
- **What's in it:** Each hexagon has a `population` count
- **Built from:** Fusion of GHSL, Facebook HRSL, Microsoft Buildings, Copernicus Land Cover, and OSM
- **Temporal:** 2023
- **Why it's better than WorldPop for TARA:** Vector hexagons are trivially easy to spatial-join with road buffers. No raster extraction needed. No API calls. Just `geopandas.sjoin()`.
- **Size:** Manageable for Uganda country subset (not the 6.6 GB global file)

### 2. HeiGIT/Mapillary Road Surface Prediction — Uganda
- **Source:** HDX — `https://data.humdata.org/dataset/uganda-road-surface-data`
- **Format:** GeoJSON + GeoPackage available
- **What's in it:** Every OSM road segment enriched with:
  - `surface` (original OSM tag, often missing)
  - `pred_label` — AI prediction: 0 = paved, 1 = unpaved
  - `combined_surface_osm_priority` — uses OSM tag when available, falls back to AI prediction
  - `combined_surface_DL_priority` — prioritizes AI prediction over OSM tag
  - `predicted_length` — length in meters
  - `osm_id`, `osm_type` — links back to OSM
  - `highway` — OSM road classification (trunk, primary, secondary, etc.)
  - `urban` — binary urban/rural flag (from GHSU 2019)
  - `n_of_predictions_used` — confidence proxy
- **Coverage:** ~416,600 km of roads, with surface predictions for ~140,700 km (rest still missing)
- **Key stat:** 66% of Uganda's OSM roads have no surface tag. This dataset fills that gap for roads where Mapillary imagery exists.

### 3. Edinburgh/UNICEF Travel Time Roads — Uganda
- **Source:** Edinburgh DataShare — `https://datashare.ed.ac.uk/handle/10283/3946`
- **Format:** Shapefile (`.shp`) — polyline
- **What's in it:** Road network merged from OSM + MapWithAI project roads
  - More complete rural coverage than OSM alone (MapWithAI detects roads from satellite imagery that aren't yet in OSM)
  - Used to create 20m resolution friction/cost surfaces for walking travel time
  - Road types with associated travel speeds
- **Temporal:** 2016-2020
- **Bonus outputs from the same project:**
  - **Travel time to Level III health facilities** (20m GeoTIFF, ~5.8 GB)
  - **Travel time to Level IV health facilities** (20m GeoTIFF)
  - **Travel time to any health facility** (20m GeoTIFF)
  - These are pre-computed walking travel times (reduced by 22% for children's walking speed)
- **Key value:** The travel time GeoTIFFs are directly usable for TARA's equity/accessibility scoring without computing your own routing

---

## How They Combine for TARA

### The Core Idea: "Smart Road Segments"

For each road that TARA appraises, we build a **rich profile** by spatially joining these datasets:

```
Road selected by user (from HOT OSM / UNRA)
    │
    ├── Buffer road geometry (5km corridor)
    │   └── Spatial join with Kontur hexagons → Population served
    │
    ├── Match road segments by osm_id
    │   └── Join with HeiGIT → Surface type (paved/unpaved) + urban/rural
    │
    └── Sample travel time raster along corridor
        └── Edinburgh GeoTIFFs → Before/after accessibility scores
```

### Step-by-Step Data Pipeline

#### Step 1: Road Selection (Your existing HOT OSM GeoJSON)
User picks a road from dropdown → you have the road's LineString geometry and OSM attributes.

#### Step 2: Population Along Corridor (Kontur)
```python
import geopandas as gpd
from shapely.ops import unary_union

# Load once at app startup (or pre-process to smaller file)
kontur = gpd.read_file("data/kontur_uganda_population.gpkg")

# Buffer the road (5km each side)
road_buffer = road_geometry.buffer(0.045)  # ~5km in degrees at Uganda's latitude

# Spatial join
corridor_pop = gpd.sjoin(kontur, gpd.GeoDataFrame(geometry=[road_buffer], crs="EPSG:4326"))
total_population = corridor_pop['population'].sum()
```

**Why this is better than WorldPop API:**
- No API calls, no timeouts, no truncation issues
- H3 hexagons give clean boundaries (no partial-pixel problems)
- Pre-computed fusion of multiple sources = more accurate than any single source
- Fast: spatial join on vectors is much faster than raster extraction

#### Step 3: Surface Type (HeiGIT)
```python
# Load the HeiGIT data (filter to main roads to keep manageable)
heigit = gpd.read_file("data/heigit_uganda_road_surface.gpkg")

# Match by osm_id to get surface prediction for selected road segments
road_osm_ids = selected_road['osm_id'].tolist()
road_surface = heigit[heigit['osm_id'].isin(road_osm_ids)]

# Get surface classification
surface_type = road_surface['combined_surface_osm_priority'].mode()[0]  # most common
pct_paved = (road_surface['pred_label'] == 0).mean() * 100
is_urban = road_surface['urban'].mode()[0]
```

**What this gives TARA:**
- Pre-fills Step 2 (Condition) with actual surface type instead of asking the user
- `urban` flag helps calibrate traffic estimates and VOC rates
- `n_of_predictions_used` indicates confidence — TARA can say "Surface type: Unpaved (high confidence, based on 12 Mapillary images)" vs "Unpaved (estimated, limited imagery)"

#### Step 4: Accessibility/Equity Scoring (Edinburgh Travel Time)
Two approaches, depending on file size tolerance:

**Option A: Use the pre-computed travel time GeoTIFFs (best but large)**
```python
import rasterio
from rasterstats import zonal_stats

# Sample travel time along the road corridor
with rasterio.open("data/uganda_travel_time_health_III.tif") as src:
    stats = zonal_stats(road_buffer, src.read(1), affine=src.transform,
                        stats=['mean', 'max', 'min'], nodata=src.nodata)
    
avg_travel_time_health = stats[0]['mean']  # minutes walking to Level III facility
```
- **Problem:** These GeoTIFFs are ~5.8 GB each. Too large for hackathon deployment.
- **Solution:** Pre-process: clip to main road corridors only and save as smaller files.

**Option B: Use the Edinburgh road shapefile for better routing (lighter)**
```python
# The Edinburgh roads have MapWithAI roads that OSM misses
edinburgh_roads = gpd.read_file("data/uganda_roads_edinburgh.shp")

# Clip to corridor
corridor_roads = gpd.clip(edinburgh_roads, road_buffer)

# Compare road density (proxy for accessibility)
road_density_km = corridor_roads.geometry.length.sum() * 111  # rough km conversion
```
- Use road density within corridor as an accessibility proxy
- MapWithAI roads show feeder/rural roads that connect communities to the main road

**Option C (Recommended for hackathon): Pre-compute corridor statistics**
- At data prep time, for each main road in your GeoJSON, pre-compute:
  - Population within 5km (Kontur)
  - Surface type (HeiGIT)
  - Average health facility travel time (Edinburgh, if you clip the raster)
- Store these as attributes directly in `uganda_main_roads.geojson`
- At runtime: zero computation, instant display

---

## Pre-Processing Script Outline

```python
"""
TARA Data Enrichment Pipeline
Run once to create enriched uganda_main_roads.geojson
"""

import geopandas as gpd
import pandas as pd

# 1. Load base road network (your existing filtered HOT OSM)
roads = gpd.read_file("data/uganda_main_roads.geojson")

# 2. Load Kontur population
kontur = gpd.read_file("data/kontur_uganda_population.gpkg")

# 3. Load HeiGIT surface data (filter to main road types)
heigit = gpd.read_file("data/heigit_uganda_road_surface.gpkg",
                         where="highway IN ('trunk','primary','secondary','tertiary')")

# 4. For each road, compute corridor stats
enriched = []
for idx, road in roads.iterrows():
    # Buffer 5km
    buffer = road.geometry.buffer(0.045)
    
    # Population
    pop_hex = gpd.sjoin(kontur, gpd.GeoDataFrame(geometry=[buffer], crs="EPSG:4326"))
    pop_5km = int(pop_hex['population'].sum())
    
    # Surface from HeiGIT (match by spatial intersection if osm_id unavailable)
    surface_segs = gpd.sjoin(heigit, gpd.GeoDataFrame(geometry=[buffer], crs="EPSG:4326"))
    if len(surface_segs) > 0:
        pct_paved = round((surface_segs['pred_label'] == 0).mean() * 100, 1)
        surface = surface_segs['combined_surface_osm_priority'].mode().iloc[0] \
                  if len(surface_segs['combined_surface_osm_priority'].mode()) > 0 else 'unknown'
        urban_pct = round(surface_segs['urban'].mean() * 100, 1)
    else:
        pct_paved = None
        surface = 'unknown'
        urban_pct = None
    
    enriched.append({
        'pop_5km': pop_5km,
        'surface_predicted': surface,
        'pct_paved': pct_paved,
        'urban_pct': urban_pct,
    })

# 5. Merge back
roads_enriched = pd.concat([roads, pd.DataFrame(enriched)], axis=1)
roads_enriched.to_file("data/uganda_main_roads_enriched.geojson", driver="GeoJSON")
```

---

## What This Gives TARA at Runtime

When a user selects "Gulu-Atiak Road" from the dropdown, TARA instantly knows:

| Attribute | Source | Value (example) |
|-----------|--------|-----------------|
| Length | HOT OSM | 47.3 km |
| Surface type | HeiGIT prediction | Unpaved (78% unpaved segments) |
| Width | HOT OSM | 6m |
| Urban/Rural | HeiGIT | 92% rural |
| Population within 5km | Kontur H3 | 118,400 people |
| Avg travel time to health III | Edinburgh (if pre-computed) | 2.8 hours walking |

**Zero API calls. Zero latency. All pre-computed.**

The agent then says:
> "I've found the Gulu-Atiak road. It's a 47km unpaved road serving approximately 118,000 people. 92% of the corridor is rural. Communities along this road currently walk an average of 2.8 hours to reach a Level III health centre. I need you to confirm: traffic count, construction cost per km, and current condition (IRI)."

That's the "wow" moment. The agent already knows more about the road than most junior engineers would assemble in a week.

---

## Practical Considerations for the Hackathon

### File Sizes
| Dataset | Raw Size | After filtering to main roads |
|---------|----------|-------------------------------|
| Kontur Uganda | ~50-100 MB (gpkg) | Keep full (needed for buffer queries) |
| HeiGIT Uganda | ~200-400 MB (GeoJSON) | ~20-40 MB (trunk/primary/secondary/tertiary only) |
| Edinburgh Roads | ~100-200 MB (shp) | Use only if needed for rural road density |
| Edinburgh Travel Time | ~5.8 GB per facility level | NOT feasible raw — pre-clip or skip |
| **Final enriched GeoJSON** | — | **~5-10 MB** (your main roads with pre-computed attributes) |

### Recommendation: What to Actually Download

1. **MUST:** Kontur Uganda population (gpkg from HDX)
2. **MUST:** HeiGIT Uganda road surface (gpkg from HDX — smaller than GeoJSON)
3. **NICE TO HAVE:** Edinburgh roads shapefile (for richer rural road coverage)
4. **SKIP for now:** Edinburgh travel time GeoTIFFs (too large, compute accessibility from OSM facilities + Kontur population instead)

### The Enriched GeoJSON Is Your Deliverable
Pre-process once → commit `data/uganda_main_roads_enriched.geojson` → app reads it at startup → instant rich road profiles with zero runtime dependencies.

---

## Data Attribution (for your README / report)

```
Population data: Kontur Population Dataset (2023), built from GHSL, Facebook HRSL, 
  Microsoft Buildings, Copernicus Land Cover. CC BY 4.0.
  https://data.humdata.org/dataset/kontur-population-uganda

Road surface predictions: HeiGIT/Heidelberg University (2024), AI-predicted road 
  surface types from Mapillary street-view imagery, matched to OSM geometries.
  https://data.humdata.org/dataset/uganda-road-surface-data
  Paper: Randhawa et al. (2025), ISPRS J. Photogrammetry & Remote Sensing.

Road geometry: Humanitarian OpenStreetMap Team (HOT) Uganda Roads Export.
  https://data.humdata.org/dataset/hotosm_uga_roads

Travel time data: Watmough et al. (2021), University of Edinburgh / 
  Data for Children Collaborative with UNICEF.
  https://doi.org/10.7488/ds/3074
```
