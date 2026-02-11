# TARA Fix & Rebuild Session

Read CLAUDE.md first. You are the orchestrator agent for fixing and improving TARA. Work through these issues in strict priority order. Use sub-agents (Task tool) for independent fixes that touch different files, but handle anything involving app.py sequentially since multiple fixes touch that file.

## Current Status

The app is a Dash (Plotly) 7-step wizard with dash-leaflet map. ~7,000 lines across 16 Python files. Run with `venv/bin/python app.py` on port 8050. Most modules are complete but there are critical bugs, the biggest being that road search (Step 1) does not work.

---

## Priority 1: CRITICAL — Replace Live OSM Search with Local Road Database

The current Overpass API search returns no results. Instead of fixing it, we are replacing it with a pre-downloaded local road database.

### Step 1A: Convert the Road Data

The raw shapefile has already been downloaded and placed at `data/hotosm_uga_roads.zip`. Do NOT re-download it. This is a zipped shapefile containing ALL roads in Uganda (~313,000 km). We only want main roads.

Install dependencies if needed:
```bash
pip install geopandas fiona shapely
```

Write a one-time conversion script `scripts/build_road_database.py` that:
1. Unzips and reads the shapefile using geopandas
2. Filters to main roads only: `highway` in (`trunk`, `primary`, `secondary`, `tertiary`) — this should give a few thousand roads, not hundreds of thousands
3. Keeps only named roads (filter out features where `name` is null/empty)
4. For each road, extract: `osm_id`, `name`, `highway` class, `surface`, `width`, `lanes`, `smoothness`, `bridge`, geometry
5. Saves as `data/uganda_main_roads.geojson` — this is the file the app will use at runtime
6. Print summary: how many roads total, breakdown by highway class, how many have names

Run the script and verify the output. The resulting GeoJSON should be a manageable size (a few MB, not hundreds).

**IMPORTANT:** Do NOT commit the raw shapefile zip to git (it's huge). Add `data/hotosm_uga_roads.zip` to `.gitignore`. Only the processed `data/uganda_main_roads.geojson` goes in the repo.

### Step 1B: Build the Road Database Loader

Create `skills/road_database.py` with these functions:

```python
def load_road_network() -> dict:
    """Load the processed GeoJSON and return parsed data."""
    # Load from data/uganda_main_roads.geojson
    # Cache in memory after first load (module-level variable)

def search_roads(query: str) -> list[dict]:
    """Search roads by name. Case-insensitive fuzzy matching."""
    # Return list of matches with: id, name, highway_class, surface, length_km, geometry
    # Sort by relevance (exact match first, then starts-with, then contains)
    # Limit results to top 50 to keep dropdown responsive

def get_road_by_id(road_id: str) -> dict:
    """Get a single road's full data including geometry."""
    # Return complete road record for display on map and use in analysis

def list_all_roads() -> list[dict]:
    """Return summary of all roads (name, id, class) for dropdown population."""
    # Lightweight list WITHOUT geometry, for UI dropdowns
    # Sort alphabetically by name
    # Format label as "Road Name (highway class, Xkm)" for the dropdown
```

Requirements:
- Type hints on all functions, docstrings on all public functions
- Calculate length_km from geometry using haversine formula
- Handle both LineString and MultiLineString geometry types
- Generate a stable ID for each road (use osm_id if available, or index)
- Road names in Uganda often include the format "Town A - Town B Road" — preserve these

### Step 1C: Rewire Step 1 in app.py

Replace the current Overpass-based search with the local database:
- Replace the search text input + search button with a **searchable dropdown** (`dcc.Dropdown` with `searchable=True`, `placeholder="Type to search roads..."`)
- Populate dropdown options from `list_all_roads()` on app startup
- When user selects a road, call `get_road_by_id()` to get full data
- Display the road on the dash-leaflet map using the GeoJSON geometry
- Show road attributes in the info panel: name, class, surface, length, width, lanes
- Store the road data in the existing `road-data-store` dcc.Store
- Also trigger `osm_facilities.py` to find nearby facilities (this still uses Overpass for facilities, which is fine — wrap in try/except with retry)

### Step 1D: Test end-to-end

- App starts without errors
- Dropdown shows roads from the database
- User can search/filter by typing (e.g. typing "Kasangati" shows matching roads)
- Selecting a road shows it on the map with correct geometry
- Road data is stored correctly for use in later steps (verify by clicking through to Step 2)
- Facilities load for the selected road (or fail gracefully)

Do NOT move to other fixes until Step 1 works end-to-end.

---

## Priority 2: Must-Fix Bugs

After Step 1 is working, fix these. Bugs B and F touch independent files and CAN be done as sub-agents in parallel. Bugs A and C both touch app.py so must be sequential.

### Bug A: Manual condition not stored (app.py Step 2)
- Step 2 has `surface-type-select` and `condition-rating-select` dropdowns
- Their values are NEVER written to `condition-store`
- Only the dashcam upload populates `condition-store`
- Fix: add a callback that stores manual condition selections into `condition-store`
- Make sure the CBA in Step 5 reads condition data from `condition-store` regardless of whether it came from manual entry or dashcam
- Also: pre-fill the surface type from the road database data if available (the GeoJSON may have `surface` property)

### Bug C: Traffic class inputs disconnected (app.py Step 3 + engine/cba.py)
- Step 3 has per-vehicle-class ADT inputs (cars, buses, HGV, semi-trailers) with percentage splits
- These are IGNORED — the CBA only reads `total-adt-input`
- Fix: wire the per-class inputs through to CBA so it uses class-specific VOC/VoT rates from config/parameters.py
- OR at minimum sync the per-class inputs with the total ADT so the breakdown is consistent
- Check `engine/cba.py` to see if it already supports per-class traffic — it might just need the data passed in

### Bug B: WorldPop possibly truncated (skills/worldpop.py) — CAN BE SUB-AGENT
- The `get_population()` function may be cut off / incomplete
- Read the entire file and verify the function is complete with proper return statements
- If truncated, complete it properly
- Add logging so we know if it fails (currently wrapped in silent try/except)

### Fix F: Overpass retry logic (skills/osm_facilities.py) — CAN BE SUB-AGENT
- Add retry with exponential backoff (3 attempts, 2s/4s/8s delays) to all Overpass API calls
- On final failure, return empty results with a clear error message instead of silent failure
- osm_facilities.py IS still used for finding facilities near the selected road

---

## Priority 3: Polish

Only after Priorities 1 and 2 are done.

### Fix D: Inconsistent road_data key
- Step 7 callbacks use `road_data.get('name')` in some places and `road_data.get('road_name')` in others
- Find ALL occurrences across the entire codebase and standardise to whichever key is set in Step 1 when road data is stored from the new road_database.py
- Verify by running Step 7 (report generation) and checking that the road name appears correctly in PDF and CSV filenames

### Fix E: Input validation
- Add basic sanity checks with user-friendly warnings (not blocking):
  - ADT > 50,000: "Traffic seems very high — please verify"
  - ADT < 10: "Traffic seems very low — please verify"
  - Construction cost < $50k/km or > $2M/km: flag as unusual for Uganda
  - Discount rate outside 6-18%: flag
  - Analysis period > 30 years or < 10 years: flag
- Show warnings as `dbc.Alert` components in the UI, yellow/warning colour
- Do not block the user from proceeding

---

## Rules

- Test every fix before moving on — run `venv/bin/python app.py` and verify in browser
- Do not modify the overall architecture or framework (Dash/Plotly)
- Keep all config values in `config/parameters.py`, not hardcoded
- Type hints on all new functions, docstrings on all public functions
- All costs in USD, distances in km
- Update CLAUDE.md build status when fixes are complete
- When creating road_database.py, keep osm_lookup.py intact — don't delete it
- Add `data/hotosm_uga_roads.zip` and `data/*.shp` to .gitignore — only the processed GeoJSON goes in the repo
