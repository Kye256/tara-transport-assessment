# Phase 2 — Population Pipeline

## Context

TARA needs to answer one question for any selected road:
"How many people live within X km of this road?"

This feeds the equity module — population served is a core input to the
economic appraisal and equity scoring. The current implementation has a
`get_population()` function that is either broken or returns truncated results.

All data is already local. No downloads needed.

---

## Local data available

```
Kontur H3 grid:   data/kontur_uganda_population.gpkg
                  182,094 H3 hexagons, field: h3, population
                  Use for runtime buffer queries — pre-gridded, fast

WorldPop raster:  data/worldpop/uga_ppp_2020.tif
                  6515×6856 pixels, ~100m resolution, 2020 UN-adjusted
                  Use for validation only

UBOS subcounties: data/GoU_Data/2017/2018/Admin/Subcounties_2014_v3_UBOS.shp
                  1,378 polygons, fields: SNAME2014, Population, Households, Urban_Stat
                  Use for cross-validation against known totals

UBOS districts:   data/GoU_Data/2017/2018/Admin/Districts_2016_UBOS.shp
                  116 polygons, fields: DNAME2016, Population, Households
                  Use for validation benchmarks
```

---

## TASK 1: Inspect before writing anything

1. Load `kontur_uganda_population.gpkg` — confirm it loads, print:
   - CRS
   - Column names and dtypes
   - Total population (sum of population field)
   - Sample 3 rows
   - Bounding box

2. Load `uga_ppp_2020.tif` — confirm it loads, print:
   - CRS
   - Resolution
   - Approximate total population (sum all pixel values, ignore nodata)
   - Bounding box

3. Load `Districts_2016_UBOS.shp` — print:
   - CRS
   - Column names
   - Top 10 districts by population
   - Total population (sum)

4. Find the current `get_population()` function in the codebase:
   - Which file is it in?
   - Show me the complete current implementation
   - What does it return?
   - Where is it called from?

Do not write any code yet. Report findings first.

---

## TASK 2: Validate the data sources

Run these checks and report results:

1. **Kontur total vs UBOS total**
   - Sum Kontur population field → total A
   - Sum UBOS Districts population field → total B
   - Uganda 2020 population should be approximately 45-47 million
   - Are A and B in the same ballpark? Report both.

2. **Kontur spatial test — Kampala district**
   - Find all Kontur hexagons that intersect Kampala district polygon
   - Sum their population
   - Kampala district population should be roughly 1.5-2 million
   - Report what Kontur gives

3. **Kontur corridor test — Matugga-Kasangati road**
   - The road geometry is in `data/uganda_roads.geojson`
   - Find road with name containing "Matugga" or road_ref = "C194"
   - Create a 5km buffer around the road geometry
   - Sum Kontur hexagon populations that intersect the buffer
   - Report the result (should be a large number — this is peri-urban Kampala)

Report all three results before proceeding.

---

## TASK 3: Write get_population_in_buffer()

Write a new function in `skills/population.py` (create this file):

```python
def get_population_in_buffer(geometry, radius_km=5.0):
    """
    Returns population within radius_km of a road geometry.
    
    Args:
        geometry: GeoJSON geometry dict or shapely geometry (LineString/MultiLineString)
        radius_km: buffer radius in km (default 5.0)
    
    Returns:
        dict with keys:
            total_population: int — total people within buffer
            area_km2: float — buffer area in km²
            density_per_km2: float — people per km²
            source: str — data source description
    """
```

Implementation requirements:
- Load Kontur GeoPackage at module level (once at import, not per call)
- Project geometry to UTM 36N (EPSG:32636) to create accurate km buffer
- Reproject buffer back to WGS84 for spatial intersection with Kontur
- Use GeoPandas spatial intersection to find overlapping hexagons
- For partial overlaps: weight population by proportion of hexagon area inside buffer
- Return the dict above
- Handle edge cases: empty geometry, no hexagons found, projection errors

Also write a second function:

```python
def get_population_by_subcounty(road_geometry, radius_km=5.0):
    """
    Returns list of subcounties within buffer with population figures.
    Used for equity reporting — shows which communities the road serves.
    
    Returns:
        list of dicts, each with:
            subcounty: str
            district: str  
            population: int
            urban: bool
    Sorted by population descending.
    """
```

Show me both functions before saving.

---

## TASK 4: Test both functions

Test against three roads from `data/uganda_roads.geojson`:

1. **Matugga - Kasangati (C194)** — peri-urban, ~9.5km
2. **Kampala - Jinja** or similar A-road — major national corridor
3. **A rural C-road** — pick any C-road in northern Uganda

For each road report:
- total_population within 5km buffer
- area_km2
- density_per_km2
- Top 3 subcounties by population (from get_population_by_subcounty)

Sanity check:
- Urban/peri-urban roads should return higher density than rural roads
- National corridors should show high total populations
- Rural C-roads should show lower density but still meaningful numbers

---

## TASK 5: Wire into the existing population flow

1. Find where `get_population()` is currently called in the app
2. Show me the call site and what the result is used for
3. Replace the call with `get_population_in_buffer(geometry, radius_km=5.0)`
4. Confirm the return dict provides everything the downstream code needs
   - If the current code expects a different format, show me before changing anything

---

## TASK 6: Pre-compute subcounty lookup (optional but recommended)

If the subcounty query is slow (>2 seconds), pre-compute it:

Write a script `scripts/prepare_population.py` that:
- For every subcounty polygon in `Subcounties_2014_v3_UBOS.shp`
- Sums the Kontur population within that subcounty
- Saves result as `data/subcounty_population.json`
  ```json
  {
    "Bukoto": {"population": 45000, "district": "Kampala", "urban": true},
    ...
  }
  ```
- Runtime lookup from this file replaces the spatial join at query time

---

## Rules for this session

- Show Task 1 findings before writing any code
- Show Task 2 validation results before writing get_population_in_buffer()
- Show both functions before saving them
- If Kontur totals are wildly off (< 30M or > 70M), stop and tell me before proceeding
- Do not modify app.py until Task 5 — understand the call site first
- If the Kontur file takes >30 seconds to load, tell me and we will discuss caching
