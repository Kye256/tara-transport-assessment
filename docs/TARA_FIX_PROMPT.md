# TARA Fix & Rebuild Session

Read CLAUDE.md first. You are the orchestrator agent for fixing and improving TARA. Work through these issues in strict priority order. Use sub-agents (Task tool) for independent fixes that touch different files, but handle anything involving app.py sequentially since multiple fixes touch that file.

## Current Status

The app is a Dash (Plotly) 7-step wizard with dash-leaflet map. ~7,000 lines across 16 Python files. Run with `venv/bin/python app.py` on port 8050. Most modules are complete but there are critical bugs, the biggest being that road search (Step 1) does not work.

---

## Priority 1: CRITICAL — Replace Live OSM Search with Local UNRA Road Database

The current Overpass API search returns no results. Instead of fixing it, we are replacing it with a local road database using the official UNRA road network published on the Humanitarian Data Exchange.

### Step 1A: Download the UNRA GeoJSON

Download this file and save it to `data/unra_road_network.geojson`:
```
https://data.humdata.org/dataset/1958a079-7496-4403-8364-f404e79fdc1b/resource/de808dbe-0b37-46ca-899f-51dd6dd83f74/download/unra_road_network.geojson
```

After downloading, inspect the file:
- How many road features are there?
- What properties does each feature have? (name, road class, surface, length, etc.)
- What does the geometry look like? (LineString, MultiLineString?)
- Print a sample of 5 road features with their properties

### Step 1B: Build the Road Database Loader

Create `skills/road_database.py` with these functions:

```python
def load_road_network() -> dict:
    """Load the UNRA GeoJSON file and return parsed data."""
    # Load from data/unra_road_network.geojson
    # Cache in memory after first load (module-level variable)

def search_roads(query: str) -> list[dict]:
    """Search roads by name. Case-insensitive fuzzy matching."""
    # Return list of matches with: id, name, road_class, surface, length_km, geometry
    # Sort by relevance (exact match first, then starts-with, then contains)

def get_road_by_id(road_id: str) -> dict:
    """Get a single road's full data including geometry."""
    # Return complete road record for display on map and use in analysis

def list_all_roads() -> list[dict]:
    """Return all roads (name, id, class) for dropdown population."""
    # Lightweight list without geometry, for UI dropdowns
```

Requirements:
- Type hints on all functions, docstrings on all public functions
- Calculate length_km from geometry if not in properties (use haversine)
- Handle both LineString and MultiLineString geometry types
- Extract all available properties: name, ref, highway class, surface, width, lanes
- Generate a stable ID for each road (use OSM ID if available, or hash of name + geometry)

### Step 1C: Rewire Step 1 in app.py

Replace the current Overpass-based search with the local database:
- Replace the search text input + search button with a **searchable dropdown** (dcc.Dropdown with `searchable=True`) populated from `list_all_roads()`
- When user selects a road, call `get_road_by_id()` to get full data
- Display the road on the dash-leaflet map using the GeoJSON geometry
- Show road attributes in the info panel: name, class, surface, length, width, lanes
- Store the road data in the existing `road-data-store` dcc.Store
- Also trigger `osm_facilities.py` to find nearby facilities (this still uses Overpass, which is fine — it's a one-time background fetch, not the critical path)

### Step 1D: Test end-to-end

- App starts without errors
- Dropdown shows roads from the UNRA network
- User can search/filter by typing
- Selecting a road shows it on the map
- Road data is stored correctly for use in later steps

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
- Also: pre-fill the surface type from the road database data if available

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

### Fix F: Overpass retry logic (skills/osm_lookup.py + skills/osm_facilities.py) — CAN BE SUB-AGENT
- Add retry with exponential backoff (3 attempts, 2s/4s/8s delays) to all Overpass API calls
- On final failure, return empty results with a clear error message instead of silent failure
- Note: osm_lookup.py is no longer used for Step 1 road search, but keep it functional as a fallback and for potential future use. osm_facilities.py IS still used for finding facilities near the selected road.

---

## Priority 3: Polish

Only after Priorities 1 and 2 are done.

### Fix D: Inconsistent road_data key
- Step 7 callbacks use `road_data.get('name')` in some places and `road_data.get('road_name')` in others
- Find ALL occurrences across the entire codebase and standardise to whichever key is set in Step 1 when road data is stored
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
