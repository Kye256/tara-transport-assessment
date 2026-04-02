# Phase 3 — Replace Live Overpass API with Local Facility Files

## Context

TARA currently makes a live HTTP call to overpass-api.de every time a user
selects a road. This is fragile, slow, and fails silently. We have all the
facility data we need sitting locally. This session replaces the live call
entirely with local file queries.

The app behaviour must be identical after this change. Same facility dots
on the map, same categories, same colours. No regressions.

---

## What exists today (do not change these files without showing me first)

- `skills/osm_facilities.py` — contains `find_facilities(bbox, buffer_km, categories, timeout)`
  - Lines 138-145: live Overpass HTTP call — THIS IS WHAT WE ARE REPLACING
  - The function takes a bbox and returns facilities grouped by category
- `output/maps.py` — contains `_build_facilities()` at lines 132-181
  - Renders each facility as a `dl.CircleMarker` with category-based colours
  - DO NOT CHANGE THIS FILE — the output of find_facilities() must match what it expects
- `app.py` — lines 773-785 call `find_facilities(bbox, buffer_km=3.0)`
  - DO NOT CHANGE THIS FILE

---

## Source files (all local — confirm paths exist before using)

```
Health:   data/GoU_Data/uganda-260331-free.shp/gis_osm_pois_free_1.shp
          fclass IN ('hospital', 'clinic', 'doctors')

Schools:  data/GoU_Data/uganda-260331-free.shp/gis_osm_pois_free_1.shp
          fclass = 'school'

Markets:  data/GoU_Data/2017/2018/Settlements/Trading_Centres_UBOS.shp
          All features — these are official UBOS trading centres
          CRS unknown/non-standard — must reproject to EPSG:4326

Water:    data/GoU_Data/uganda-260331-free.shp/gis_osm_pois_free_1.shp
          fclass IN ('drinking_water', 'water_well')
```

Adjust paths if needed — the Geofabrik shapefile may be at a slightly
different path. Search the repo for `gis_osm_pois_free_1.shp` to confirm.

---

## TASK 1: Inspect before writing anything

Read the following and report back before making any changes:

1. Show me the complete current `find_facilities()` function
2. Show me the complete current `_build_facilities()` function  
3. Show me exactly what data structure `_build_facilities()` expects
   (what keys, what format, what category names)
4. Confirm the exact paths of:
   - `gis_osm_pois_free_1.shp`
   - `Trading_Centres_UBOS.shp`
5. For `Trading_Centres_UBOS.shp`: what CRS is it in? What columns does it have?
6. For `gis_osm_pois_free_1.shp`: what are ALL unique fclass values? Count features per fclass.

Do not write any code yet. Report findings first.

---

## TASK 2: Extract and save facility GeoJSONs (one-time preprocessing)

Write a script `scripts/prepare_facilities.py` that:

1. Loads `gis_osm_pois_free_1.shp`
2. Extracts and saves four files to `data/`:
   - `uganda_health_facilities.geojson`
     - fclass IN ('hospital', 'clinic', 'doctors', 'pharmacy')
     - Keep fields: osm_id, name, fclass
     - Add field: category = 'health'
   - `uganda_schools.geojson`
     - fclass IN ('school', 'college', 'university', 'kindergarten')
     - Keep fields: osm_id, name, fclass
     - Add field: category = 'education'
   - `uganda_water_points.geojson`
     - fclass IN ('drinking_water', 'water_well', 'water_tower')
     - Keep fields: osm_id, name, fclass
     - Add field: category = 'water'
   - `uganda_markets.geojson` — from Trading_Centres_UBOS.shp NOT from OSM
     - All features
     - Keep fields: NAME (→ rename to 'name'), DISTRICT, POPULATION
     - Add field: category = 'market'
     - Add field: source = 'UBOS Trading Centres 2018'
     - Reproject to EPSG:4326

3. For each file saved, print:
   - Feature count
   - Bounding box
   - Sample 3 rows

Run this script. Confirm all four files are saved successfully.

---

## TASK 3: Rewrite find_facilities()

Rewrite `skills/osm_facilities.py` to:

1. At module load time, load all four GeoJSON files into memory as
   GeoDataFrames. Use a try/except — if a file is missing, log a warning
   and continue (do not crash the app).

2. Replace the `find_facilities(bbox, buffer_km, categories, timeout)` function:
   - Keep the exact same function signature
   - Instead of calling Overpass, filter the in-memory GeoDataFrames by bbox
   - bbox is (min_lon, min_lat, max_lon, max_lat) — confirm this matches
     the current usage in app.py before assuming
   - Expand bbox by buffer_km before filtering (same as current behaviour)
   - Return the exact same data structure as the current function

3. The return structure must be identical to what `_build_facilities()` expects.
   Do not change the return format.

4. Add a comment at the top of the file:
   ```
   # Facilities loaded from local files at startup.
   # Overpass API removed — see TARA Data Pipeline Plan.
   # Sources:
   #   Health:  gis_osm_pois_free_1.shp (Geofabrik OSM, 2026)
   #   Schools: gis_osm_pois_free_1.shp (Geofabrik OSM, 2026)
   #   Markets: Trading_Centres_UBOS.shp (UBOS, 2018)
   #   Water:   gis_osm_pois_free_1.shp (Geofabrik OSM, 2026)
   ```

Show me the complete rewritten file before saving it.

---

## TASK 4: Test

1. Start the app: `venv/bin/python app.py`
2. Confirm it starts without errors
3. Select a road (e.g. "Matugga - Kasangati")
4. Confirm facility dots appear on the map
5. Confirm no Overpass calls in the terminal output
6. Report: how many facilities of each type were returned for that road?

---

## TASK 5: Cleanup

1. Delete or clearly archive the old Overpass code — do not leave dead code
2. Check if there are any other files that import from or reference
   the Overpass URL — search for 'overpass' across the entire repo
3. Report any other Overpass references found

---

## Rules for this session

- Show me Task 1 findings before writing any code
- Show me the complete rewritten `find_facilities()` before saving it
- Do not modify `output/maps.py` or `app.py`
- Do not change the return structure of `find_facilities()`
- If Trading_Centres_UBOS.shp CRS cannot be determined, ask me before assuming
