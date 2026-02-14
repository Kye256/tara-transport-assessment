# TARA: Add UBOS Subcounty Population Layer
## Claude Code Build Prompt

---

## Context

We have a 30MB GeoJSON file at `data/ubos/subcounty_boundaries.geojson` containing 1,382 Uganda subcounty polygons with these properties:
- `SNAME2014` — subcounty name (ALL CAPS, e.g. "KASANGATI TOWN COUNCIL")
- `DNAME2014` — district name (e.g. "WAKISO")
- `POP2014` — population (integer)
- `HH2014` — households (integer)
- `HHSIZE2014` — average household size (float)
- `MALES2014` / `FEMALE2014` — gender split

Our demo roads are in Wakiso District (~23 subcounties in this file).

The app is a Dash application with dash-leaflet maps. There are two existing equity systems that we are NOT modifying:
- `engine/equity.py` — quantitative scoring using WorldPop population data
- `video/equity.py` — qualitative narrative from dashcam camera observations

We are ADDING a third layer: UBOS subcounty population context. This enriches both existing systems without replacing them.

---

## Task: 3 deliverables

### Deliverable 1: Data module — `modules/ubos_population.py`

Create a new module that:

1. **On import / first call**, loads the GeoJSON and filters to ONLY features where `DNAME2014` contains "WAKISO". Cache the result in a module-level variable so the 30MB file is only read once.

2. **`get_corridor_subcounties(road_geojson)`** function:
   - Takes the road GeoJSON (from `road-data-store`, which has a `geometry` with coordinates)
   - Creates a 2km buffer around the road linestring using shapely
   - Returns all Wakiso subcounties whose polygons intersect this buffer
   - Output: list of dicts, each with:
     ```python
     {
         "name": "Kasangati Town Council",  # title-cased from SNAME2014
         "population": 120000,               # POP2014
         "households": 25000,                # HH2014
         "avg_household_size": 4.8,          # HHSIZE2014
         "area_km2": 12.5,                   # computed from polygon
         "density_per_km2": 9600,            # population / area
         "geometry": {...}                    # GeoJSON geometry for map rendering
     }
     ```
   - Sort by population descending

3. **`get_subcounty_geojson(corridor_subcounties)`** function:
   - Takes the list from above
   - Returns a GeoJSON FeatureCollection suitable for dl.GeoJSON
   - Each feature's properties include: name, population, density_per_km2, density_category
   - `density_category`: "very_high" (>5000/km²), "high" (2000-5000), "moderate" (500-2000), "low" (<500)

4. **`get_population_summary(corridor_subcounties)`** function:
   - Returns a summary dict:
     ```python
     {
         "total_population": 340000,
         "total_households": 72000,
         "num_subcounties": 5,
         "highest_density": {"name": "Kasangati TC", "density": 9600},
         "lowest_density": {"name": "Namayumba", "density": 800},
         "subcounties": [...]  # the full list
     }
     ```

Dependencies: shapely, json. Use `shape()` from `shapely.geometry` to convert GeoJSON geometries. Handle any malformed geometries with try/except (skip them, don't crash).

---

### Deliverable 2: Map overlay in app.py

Add a subcounty polygon layer to the dash-leaflet map:

1. **New store**: `subcounty-population-store` (dcc.Store, storage_type='memory')

2. **Populate the store**: In the callback that runs after road selection (wherever road-data-store is written), also call `get_corridor_subcounties()` and write the result to `subcounty-population-store`. If it fails for any reason, store an empty dict — never crash.

3. **Map layer**: Add a `dl.GeoJSON` component to the map that renders subcounty polygons:
   - **Style**: Semi-transparent fill, color-coded by population density:
     - very_high: `#2d5f4a` (primary green) at 0.35 opacity
     - high: `#4a8c6f` at 0.30 opacity
     - moderate: `#8ab5a0` at 0.25 opacity
     - low: `#c8ddd1` at 0.20 opacity
   - **Border**: 1px `#2d5f4a` at 0.5 opacity
   - **Z-order**: This layer renders UNDERNEATH the road condition polyline
   - **Tooltip on hover**: "{name}: Pop. {population:,} | {density_per_km2:,.0f}/km²"
   - Use a clientside callback or the `hideout` pattern for styling — no server round-trips for hover

4. **Toggle**: Add a small checkbox or toggle in the map controls area: "☐ Population overlay". Default OFF. When toggled, show/hide the subcounty GeoJSON layer. Keep it simple — a `dcc.Checklist` that controls the layer's visibility via a clientside callback.

---

### Deliverable 3: Equity panel population summary

In the equity display area (where the "Who Benefits From This Road" panel lives), add a **population context section** ABOVE the existing camera-based equity narrative:

```
CORRIDOR POPULATION (UBOS 2014 Census)
───────────────────────────────────────
Total population served: 340,000
Households: 72,000
Subcounties along corridor: 5

┌──────────────────────┬───────────┬──────────┬──────────────┐
│ Subcounty            │ Population│ Households│ Density/km²  │
├──────────────────────┼───────────┼──────────┼──────────────┤
│ Kasangati TC         │   120,000 │   25,000 │        9,600 │
│ Kira TC              │    98,000 │   21,000 │        7,200 │
│ Nangabo              │    65,000 │   14,000 │        3,100 │
│ Namayumba            │    42,000 │    8,500 │          800 │
│ Wakiso TC            │    15,000 │    3,500 │        1,200 │
└──────────────────────┴───────────┴──────────┴──────────────┘
Source: Uganda Bureau of Statistics, 2014 National Population Census
```

Style this as an `html.Table` following TARA's design:
- Section label: 9px uppercase mono "CORRIDOR POPULATION · UBOS 2014 CENSUS"
- Table: compact, no heavy borders, monospace numbers right-aligned
- Attribution: 8px mono muted text at bottom
- Use the existing TARA color palette (text: #2c2a26, muted: #8a8578, borders: #ddd9d1)

This section should be generated from `subcounty-population-store` data via a callback. If the store is empty, don't render anything (return empty div).

---

### Deliverable 4: Feed subcounty data into equity narrative prompt

In `video/equity.py`, modify `generate_equity_narrative()` to accept an optional `subcounty_data` parameter:

```python
def generate_equity_narrative(sections_data, anthropic_client, model, subcounty_data=None):
```

If `subcounty_data` is provided (the list of corridor subcounty dicts), append this context to the prompt that Claude receives:

```
CORRIDOR POPULATION CONTEXT (UBOS Census Data):
This road corridor passes through {N} administrative subcounties:
{for each subcounty: "- {name}: population {pop:,}, {density:,.0f} people/km²"}
Total corridor population: {total:,}

Use this population data to enrich your equity narrative. Reference specific 
subcounty names and populations when discussing who benefits from this road.
Note that population data enables comparison between road investment schemes —
roads serving larger populations deliver greater per-km benefit.
```

In `video/video_pipeline.py`, where `generate_equity_narrative()` is called, pass in the subcounty data if available. Get it from the same source that populates `subcounty-population-store`. If not available, pass None — the function should work exactly as before without it.

---

## Rules

- Do NOT modify `engine/equity.py` or its WorldPop pipeline — leave the quantitative scoring untouched
- Do NOT modify the existing camera-based equity narrative structure — only enrich the prompt input
- Pre-filter the 30MB GeoJSON to Wakiso on first load, cache in memory. Never reload it per-request.
- All styling follows TARA UI Design Reference: no rounded corners, no neon, tables over cards, monospace for data
- If any UBOS data operation fails, fail silently (log a warning, return empty results). Never crash the app.
- Test that the app still starts and runs with the video pipeline even if the GeoJSON file is missing
