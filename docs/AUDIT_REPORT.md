# TARA App Status Audit Report
**Date:** 2026-02-13
**Branch:** `video-integration`
**Auditor:** Claude Opus 4.6

---

## 1. FILE INVENTORY

### Root Level
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `app.py` | ~1,579 | Main Dash application — 7-step wizard + persistent map | `build_step1-7`, `select_road`, `run_video_pipeline`, `run_cba_callback`, `update_sensitivity`, `ai_interpretation`, `generate_pdf_report`, `export_csv` + 22 callbacks | config.parameters, skills.road_database, output.maps, skills.osm_facilities, video.video_pipeline, output.charts, engine.cba, engine.equity, output.report, agent.orchestrator, agent.tools |

### config/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `config/parameters.py` | ~181 | Uganda-calibrated default parameters (EOCK, VOC, VoT, maintenance, equity) | Module-level constants only | None |

### agent/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `agent/__init__.py` | 0 | Package init | — | — |
| `agent/orchestrator.py` | ~290 | Opus 4.6 agent loop — API calls, tool execution, state management | `create_agent`, `process_message_sync`, `_extract_text`, `_update_agent_state` | agent.prompts, agent.tools |
| `agent/prompts.py` | ~134 | System prompt + decision flow templates for agent | SYSTEM_PROMPT, VALIDATION_PROMPT, NARRATIVE_PROMPT | None |
| `agent/tools.py` | ~794 | 11 tool definitions (Anthropic format) + execution dispatcher | `execute_tool`, `_exec_search_road`, `_exec_run_cba`, etc. | skills.osm_lookup, skills.osm_facilities, skills.worldpop, skills.dashcam, output.maps, engine.traffic, engine.cba, engine.sensitivity, engine.equity, output.report, config.parameters |

### engine/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `engine/__init__.py` | 0 | Package init | — | — |
| `engine/cba.py` | ~398 | Cost-Benefit Analysis — NPV, EIRR, BCR, FYRR, cashflows | `run_cba`, `financial_to_economic`, `calculate_npv`, `calculate_eirr`, `_eirr_iterative`, `_annual_maintenance_cost`, `_get_recommendation` | config.parameters, engine.traffic |
| `engine/traffic.py` | ~160 | Traffic forecasting — per-class ADT projections, generated traffic, capacity warnings | `forecast_traffic`, `calculate_generalised_cost_change` | config.parameters |
| `engine/sensitivity.py` | ~299 | Sensitivity analysis — single-variable, switching values, scenarios | `run_sensitivity_analysis`, `find_switching_value`, `build_scenario`, `_apply_change`, `_apply_value`, `_build_summary` | config.parameters, engine.cba |
| `engine/equity.py` | ~268 | Equity scoring — composite 0-100 index from 4 sub-indices | `calculate_equity_score`, `get_equity_summary`, `_accessibility_index`, `_population_benefit_index`, `_poverty_impact_index`, `_facility_access_index` | config.parameters |

### skills/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `skills/__init__.py` | 0 | Package init | — | — |
| `skills/road_database.py` | ~296 | Local road database — 738 Uganda main roads from HOT Export GeoJSON | `load_road_network`, `search_roads`, `get_road_by_id`, `list_all_roads` | None |
| `skills/osm_lookup.py` | ~470 | OSM road lookup via Overpass API + Nominatim fallback | `search_road`, `search_roads_multi`, `load_road_by_ids`, `get_road_summary` | None |
| `skills/osm_facilities.py` | ~313 | OSM facilities (health, education, market, water) via Overpass with retry/backoff | `find_facilities`, `get_facilities_summary`, `calculate_distances_to_road` | None |
| `skills/worldpop.py` | ~555 | WorldPop population via REST API + local GeoTIFF raster fallback | `get_population`, `get_population_summary`, `_build_corridor_polygon`, `_query_worldpop_api` | config.parameters |
| `skills/kontur_population.py` | ~224 | Kontur H3 hexagon population — fast local spatial joins (replaces WorldPop) | `_load_kontur`, `get_population` | config.parameters |
| `skills/dashcam.py` | ~339 | Dashcam analysis — single image/video condition assessment via Claude Vision | `analyze_dashcam_media`, `get_dashcam_summary`, `_extract_video_frames`, `_analyze_frame_with_vision` | None |

### video/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `video/__init__.py` | ~18 | Package init + public API exports | — | video.video_pipeline, video.gps_utils, video.video_map |
| `video/video_pipeline.py` | ~265 | Main pipeline orchestrator — frame extraction, GPS match, Vision, GeoJSON, interventions | `run_pipeline` | video.video_frames, video.gps_utils, video.vision_assess, video.video_map, video.intervention |
| `video/video_frames.py` | ~182 | Frame extraction from MP4/AVI/MOV — single file or directory of clips | `extract_frames`, `extract_start_time_from_filename`, `_extract_from_single_file` | None |
| `video/gps_utils.py` | ~218 | GPX parsing, frame-to-GPS matching, trackpoint retrieval | `haversine`, `parse_gpx`, `parse_gpx_folder`, `get_trackpoints_between`, `match_frames_to_gps`, `_interpolate_gps` | None |
| `video/vision_assess.py` | ~168 | Claude Vision assessment — real API + deterministic mock mode | `assess_frame`, `assess_frame_mock`, `assess_road` | None |
| `video/video_map.py` | ~487 | GeoJSON section builder — condition segments, popups, narratives | `build_popup_html`, `frames_to_condition_geojson`, `frames_to_geojson`, `build_condition_summary_panel`, `generate_condition_narrative`, `generate_condition_narrative_mock` | video.gps_utils |
| `video/intervention.py` | ~311 | Uganda-calibrated intervention recommendations per section | `get_intervention`, `get_all_interventions`, `recommend_intervention`, `recommend_interventions_for_route` | None |
| `video/test_pipeline.py` | ~312 | Validator — 12 checks on pipeline output | `run_checks`, `main`, `haversine`, `linestring_length_km` | video.video_pipeline, video.vision_assess |
| `video/run_all.py` | ~74 | Batch runner for multi-clip processing | `run_all`, `extract_start_time` | video.video_pipeline, video.video_frames |

### output/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `output/__init__.py` | 0 | Package init | — | — |
| `output/charts.py` | ~366 | Plotly charts — tornado, waterfall, cashflow, traffic, scenarios | `create_tornado_chart`, `create_waterfall_chart`, `create_traffic_growth_chart`, `create_cashflow_chart`, `create_scenario_chart` | None |
| `output/maps.py` | ~377 | Dash-leaflet interactive maps — road alignment, facilities, condition overlays | `create_road_map`, `build_condition_layer`, `_build_road_segments`, `_build_facilities` | skills.osm_facilities |
| `output/report.py` | ~744 | Report generation — markdown + PDF with embedded charts | `generate_report_markdown`, `generate_report_pdf`, `get_report_summary` + 15 `_section_*` and `_pdf_*` helpers | output.charts |

### scripts/
| File | Lines | Purpose | Key Functions | TARA Imports |
|------|-------|---------|---------------|-------------|
| `scripts/build_road_database.py` | ~50 | One-time: HOT Export shapefile to filtered GeoJSON | `main` | None |
| `scripts/enrich_road_database.py` | ~100 | One-time: add Kontur population + HeiGIT surface predictions | `check_dependencies`, `load_base_geojson` | None |

### Other
| File | Purpose |
|------|---------|
| `assets/typing.js` | Clientside JS — typing animation + fitBounds for dash-leaflet |
| `assets/style.css` | Custom CSS for TARA UI |

**Total:** 33 Python files (excluding venv/, __pycache__)

---

## 2. VIDEO PIPELINE STATUS

### Does `video_pipeline.py` exist?
**YES.** `run_pipeline()` signature:
```python
def run_pipeline(
    video_path: str,              # MP4 file OR directory of clips
    gpx_path: str,                # GPX file OR directory of GPX files
    video_start_time: str = None, # "2026-02-12 14:18:00" (auto-detected from filename)
    frame_interval: int = 5,      # seconds between frame samples
    max_frames: int = 20,         # cap on frames sent to Vision API
    use_mock: bool = False,       # skip real API calls
    api_key: str = None,          # Anthropic key (reads env if None)
    progress_callback = None,     # callable(stage: int, message: str)
    skip_size_guards: bool = False,
) -> dict:
```
**Returns:** `{frames, summary, geojson, point_geojson, narrative, panel_data, interventions, metadata}` (or `{error, message}`)

**Size guards:** MAX_CLIP_COUNT=100, MAX_TOTAL_SIZE=2GB, MAX_PER_CLIP_SIZE=100MB

### Does `video_frames.py` extract from folder or single file?
**BOTH.** `extract_frames()` checks if `video_path` is a file or directory:
- **File:** processes single MP4/AVI/MOV
- **Directory:** finds all video files, sorts, processes sequentially with cumulative timestamps
- Accepts `cumulative_time` and `frame_offset` for multi-clip tracking
- Base64 encodes frames as JPEG (quality 85), resizes to max_width=1280

### Does `gps_utils.py` have `get_trackpoints_between()`?
**YES.** Returns exact trackpoints whose time falls between `start_epoch` and `end_epoch` (inclusive). **Neither interpolation nor snap-to-nearest** — returns all matching trackpoints as `[lon, lat]` pairs (GeoJSON order).

Other key functions:
- `parse_gpx()` — single GPX file
- `parse_gpx_folder()` — single file OR directory of GPX files, combined chronologically
- `match_frames_to_gps()` — matches frames to GPS via **linear interpolation** (`_interpolate_gps`)
- `haversine()` — distance in meters

### Does `video_map.py` accept trackpoints?
**YES.** `frames_to_condition_geojson(assessed_frames, trackpoints=None, video_start_time=None, all_frames=None)`:
- When trackpoints provided: uses `get_trackpoints_between()` to retrieve **all intermediate GPS points** between section start/end
- These densify LineString coordinates (actual road path from GPX)
- Fallback chain: GPX trackpoints → all_frames GPS → assessed frame GPS → duplicate with offset
- Post-processing: `_densify_coords()` inserts points so no segment exceeds 0.25km
- Sections split at 1.0km intervals (max 1.5km), break on surface_type or condition_class change
- Adds `length_km` to feature properties

### Does `vision_assess.py` have mock mode?
**YES.** `assess_frame_mock()` uses deterministic cycling (global `_MOCK_COUNTER`):
- Conditions cycle: `[good, good, fair, fair, poor, good, good, fair, poor, bad]`
- Surfaces cycle: `[paved_asphalt, paved_asphalt, gravel, earth]`
- IRI ranges per condition: good 3-5, fair 6-9, poor 10-14, bad 15-20
- 8 distress types, 6 note templates
- Real mode uses `claude-sonnet-4-5-20250929` Vision API

**DEFAULT_ASSESSMENT on error:** `{surface_type: "unknown", condition_class: "fair", iri_estimate: 8.0, ...}`

### Does `video/intervention.py` exist?
**YES.** 8 Uganda-calibrated interventions:

| Code | Name | Cost/km (USD) | Design Life |
|------|------|---------------|-------------|
| REG | Regravelling | $60,000 | 5 yr |
| DBST | Upgrade to DBST | $800,000 | 10 yr |
| AC | Asphalt Concrete | $1,000,000 | 15 yr |
| REHAB | Rehabilitation | $600,000 | 12 yr |
| PM | Periodic Maintenance (Overlay) | $150,000 | 8 yr |
| RM | Routine Maintenance Only | $5,000 | 1 yr |
| DUAL | Dualling | $2,000,000 | 20 yr |
| DUAL_NMT | Dualling + NMT | $2,500,000 | 20 yr |

Decision logic:
- Unpaved → DBST (alternatives: AC, REG)
- Paved good → RM (alternatives: PM)
- Paved fair → PM (alternatives: RM, REHAB)
- Paved poor/bad → REHAB (alternatives: AC, PM)

`recommend_interventions_for_route()` returns per-section results + route_summary with total_cost, dominant_intervention, narrative.

### Does `video/test_pipeline.py` exist?
**YES.** 12 validation checks:
1. CONTINUITY — all sections connected (max gap ≤50m)
2. SECTION LENGTH — longest ≤1.5km
3. MINIMUM SECTIONS — need 6+ sections
4. GPS DENSITY — all sections have 2+ coordinate pairs
5. COORDINATES IN BOUNDS — all coords within Uganda route bounds
6. NO STRAIGHT LINES — long sections (>500m) have 3+ coords
7. PROPERTIES — all features have required keys (condition_class, color, avg_iri, surface_type, section_index, length_km)
8. TEMPORAL ORDER — section indices sequential 0-N
9. POPUP HTML — all features have popup_html with `<img>` tag
10. TOTAL DISTANCE — total ±20% of expected (8.35km demo route)
11. SIZE GUARDS — rejects oversized inputs
12. INTERVENTION — all sections have intervention recommendations

Run: `venv/bin/python -m video.test_pipeline` — **all 12/12 passing**

### Is there any caching?
**NO.** Pipeline is completely stateless — recomputes everything on each invocation:
- `extract_frames()` recreates `/tmp/tara_frames` each run
- `assess_road()` makes fresh API calls (no memoization)
- `match_frames_to_gps()` recomputes interpolations each call
- No disk cache, no result persistence between runs

---

## 3. DASH APP STRUCTURE

### How are the 7 steps structured?
**All in ONE file (`app.py`).** No `layouts/` or `callbacks/` directories exist.

Each step has a builder function:
- `build_step1()` (lines 140-152) — Select Road
- `build_step2()` (lines 155-245) — Condition
- `build_step3()` (lines 248-291) — Traffic
- `build_step4()` (lines 294-334) — Costs
- `build_step5()` (lines 337-344) — Results
- `build_step6()` (lines 347-357) — Sensitivity
- `build_step7()` (lines 360-374) — Report

All steps pre-built into `ALL_STEPS` dict (lines 378-386), rendered as hidden divs with CSS display toggling.

### How does Step 2 (condition) currently work?
**THREE input methods:**
1. **Manual Entry:** Surface type dropdown + condition rating dropdown + optional IRI override
2. **Dashcam Upload:** Single file upload (jpg/png/mp4) → Claude Vision API analysis
3. **Full Video Pipeline:** Preset dropdown OR manual path inputs for video folder + GPX file → "Run Video Analysis" button

### What `dcc.Store` IDs exist?
```
current-step-store      → Active step number (1-7)
road-data-store         → Road geometry, name, length, segments, attributes
facilities-data-store   → OSM facilities (health, education, market, water, transport, worship)
condition-store         → Road surface/IRI condition (from manual, dashcam, or video)
traffic-store           → [Not actively used — traffic inputs captured as States in CBA callback]
cost-store              → [Not actively used — cost inputs captured as States in CBA callback]
results-store           → Full CBA results (NPV, EIRR, BCR, cashflows, summary)
sensitivity-store       → Sensitivity analysis output (tornado, switching values, scenarios)
population-store        → WorldPop/Kontur demographic data
equity-store            → Equity scoring results (composite score, 4 sub-indices)
cba-inputs-store        → Serialized CBA input params (for sensitivity re-runs)
ai-narrative-store      → AI interpretation text + target element ID
map-bounds-store        → Bounds array for fitBounds() clientside callback
video-condition-store   → Detailed video pipeline output (summary, geojson, panel_data)
```

### How does the video pipeline connect to Dash callbacks?
1. User selects preset or enters custom video/GPX paths
2. `populate_preset_paths()` auto-fills path inputs from preset
3. `update_video_upload_status()` validates paths, enables "Run Video Analysis" button
4. `run_video_pipeline()` calls `video.video_pipeline.run_pipeline()` with `frame_interval=5, max_frames=20, use_mock=False`
5. Results map to 5 outputs:
   - `video-pipeline-result.children` ← metrics UI + condition bar
   - `condition-store.data` ← condition summary
   - `video-condition-store.data` ← detailed output
   - `main-map.children` ← condition layers via `build_condition_layer()`
   - `map-bounds-store.data` ← triggers fitBounds

### Is there a video dataset dropdown?
**YES.** `video-preset-dropdown` with ONE preset:
```python
options=[{"label": "Kasangati loop (42 clips, compressed)", "value": "demo2"}]
```
Maps to: `data/videos/demo2_kasangati_loop/clips_compressed` + `data/videos/12-Feb-2026-1537.gpx`

### Overall layout structure
```
┌─ HEADER (TARA wordmark + badge) ─────────────────────────────┐
├─ TWO-PANEL LAYOUT ───────────────────────────────────────────┤
│  ┌─ LEFT PANEL (wizard) ────────┬─ RIGHT PANEL (map+results)┐
│  │  Step indicator bar          │  dash-leaflet map (45vh)   │
│  │  (1-7, clickable bubbles)    │  Results summary area      │
│  │  Active step panel           │                            │
│  │  Back / Next buttons         │                            │
│  └──────────────────────────────┴────────────────────────────┘
└──────────────────────────────────────────────────────────────┘
```

### Complete callback registry (22 Python + 2 clientside)

**Navigation:** `navigate_steps`, `update_step_display`
**Clientside:** `typeText` (typing animation), `fitBounds` (map zoom)
**Step 1:** `select_road`
**Step 2:** `prefill_surface`, `store_manual_condition`, `handle_dashcam_upload`, `populate_preset_paths`, `update_video_upload_status`, `run_video_pipeline`
**Step 4:** `update_cost_per_km`
**Validation:** `validate_traffic`, `validate_costs`
**Step 5:** `run_cba_callback`
**Step 6:** `build_sensitivity_controls`, `update_sensitivity`, `ai_interpretation`, `ai_interpretation_error_fallback`
**Step 7:** `generate_pdf_report`, `export_csv`, `show_report_summary`

---

## 4. DATA FLOW

### Step 1 (Road Selection) → What gets stored?
- **`road-data-store`:** road_name, total_length_km, segment_count, center, bbox, coordinates_all, attributes (surface_types, highway_types, width, lanes), segments array
- **`facilities-data-store`:** facilities dict (category → items with distances), total_count
- **Map rendered** with road geometry + facility markers + endpoint markers

### Step 2 (Condition) → What gets stored?
**Manual entry → `condition-store`:**
```python
{source: "manual", surface_type, condition_rating, iri, overall_condition (0-100)}
```
**Video pipeline → `condition-store`:**
```python
{source: "video_pipeline", surface_type, condition_rating, iri, overall_condition, defects, drainage_condition}
```
**Video pipeline → `video-condition-store`:**
```python
{summary: {average_iri, dominant_surface, dominant_condition, total_frames_assessed, distress_types_found},
 geojson: {...}, panel_data: {condition_percentages: {good, fair, poor, bad}}}
```

### Step 3 (Traffic) → Reads from what?
No upstream store dependency. Manual inputs captured as States in CBA callback:
- `total-adt-input`, `growth-rate-input`, per-class traffic percentages

### Step 4 (Costs) → Reads from what?
- **`road-data-store`** — for total_length_km (cost/km calculation)
- Manual inputs: total-cost, construction-years, discount-rate, analysis-period, base-year

### Step 5 (CBA Results) → What does CBA need?
Collects from stores + UI inputs:
```python
{base_adt, growth_rate, road_length_km, construction_cost_total,
 construction_years, discount_rate, analysis_period, base_year, vehicle_split}
```
→ Calls `engine.cba.run_cba()` → Also fetches population (Kontur) + equity score
→ Outputs: `results-store`, `cba-inputs-store`, `population-store`, `equity-store`

### Step 6 (Sensitivity) → Reads from what?
- **`cba-inputs-store`** — base inputs for re-running CBA with variations
- **`results-store`** — base CBA results for comparison
- Live sliders modify inputs → re-run CBA → display delta NPV/BCR/EIRR
- Full run: `engine.sensitivity.run_sensitivity_analysis()` → **`sensitivity-store`**

### Step 7 (Report) → Reads from what?
All stores: `road-data-store`, `facilities-data-store`, `population-store`, `results-store`, `sensitivity-store`, `equity-store`, `condition-store`

---

## 5. CBA ENGINE

### Inputs (`run_cba()` parameters)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `traffic_forecast` | `Optional[dict]` | None | Pre-computed forecast OR auto-computed |
| `road_length_km` | `float` | 10.0 | Road length in km |
| `construction_cost_total` | `float` | 5,000,000 | Total financial cost (USD) |
| `construction_years` | `int` | 3 | Number of construction years |
| `construction_phasing` | `Optional[dict]` | {1:0.4, 2:0.3, 3:0.3} | Year → share mapping |
| `discount_rate` | `float` | 0.12 | EOCK |
| `analysis_period` | `int` | 20 | Years after construction |
| `base_year` | `int` | 2025 | Calendar year |
| `base_adt` | `Optional[float]` | None | Base ADT (if no forecast) |
| `growth_rate` | `Optional[float]` | None | Growth rate (if no forecast) |
| `vehicle_split` | `Optional[dict]` | Cars 45%, Buses 25%, HGV 20%, Semi 10% | Class shares |
| `voc_without/with` | `Optional[dict]` | From config | VOC rates by class |
| `vot_without/with` | `Optional[dict]` | From config | VoT rates by class |
| `accident_without/with` | `Optional[dict]` | From config | Accident rates by class |
| `maintenance_without/with` | `Optional[dict]` | From config | Maintenance costs |
| `include_generated_traffic` | `bool` | True | Include generated traffic benefits |
| `residual_value_factor` | `float` | 0.75 | Residual value at end |

### Per-section interventions or whole road?
**Whole road.** CBA takes single `construction_cost_total`. The video pipeline produces per-section interventions (`video/intervention.py`), but these are **not yet integrated** into the CBA loop. Per-section costs are currently used for visualization and appraisal guidance only.

**Gap:** Sum per-section costs → feed into CBA as `construction_cost_total`.

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| `npv` | float | Net Present Value (USD) |
| `eirr` | float/None | Economic Internal Rate of Return |
| `bcr` | float | Benefit-Cost Ratio |
| `fyrr` | float/None | First Year Rate of Return |
| `npv_per_km` | float | NPV / road_length_km |
| `economic_construction_cost` | float | Shadow-priced construction cost |
| `pv_benefits` | float | Present Value of all benefits |
| `pv_costs` | float | Present Value of all costs |
| `yearly_cashflows` | list[dict] | Year-by-year breakdown |
| `traffic_forecast` | dict | Full traffic forecast |
| `summary` | dict | Quick reference (npv_usd, eirr_pct, bcr, fyrr_pct, economically_viable, recommendation) |

### Uganda-calibrated parameters (`config/parameters.py`)
- **EOCK:** 12%, **FEP:** 7.5%, **NTP:** 1%, **SCF:** 0.930
- **VOC rates:** Cars $0.180→$0.126, HGV $0.930→$0.650 (with project)
- **VoT rates:** Cars $0.040→$0.028, Semi $0.353→$0.247
- **Traffic growth:** 3.5% (GDP-linked, elasticity 1.0)
- **Maintenance:** Without $2,560/km/yr routine + $600k/km major every 10yr; With $4,500/km/yr + $91.1k/km periodic every 10yr
- **Construction benchmarks:** Gravel→paved rural $250k-$600k/km, urban $500k-$1.5M/km
- **Road capacity:** 2-lane paved 8,000 vpd, dual 25,000 vpd
- **IRI:** Paved good 2-4, fair 4-6, poor 6-10; Gravel good 6-10, fair 10-14, poor 14-20

---

## 6. AVAILABLE TEST DATA

### data/videos/

| Directory | Contents | Size |
|-----------|----------|------|
| `13-Feb-2026/` | 136 MP4 clips (dashcam 2026-02-13) | ~11.7 GB |
| `demo1_kira_kasangati/clips/` | 18 MP4 clips | ~1.8 GB |
| `demo1_kira_kasangati/clips_compressed/` | 18 compressed clips | ~0.77 GB |
| `demo1_kira_kasangati/gpx/` | 1 GPX (`12-Feb-2026-1418.gpx`, 15KB) | 15 KB |
| `demo2_kasangati_loop/clips/` | 44 MP4 clips | ~7.4 GB |
| `demo2_kasangati_loop/clips_compressed/` | 45 compressed clips | ~1.8 GB |
| `demo2_kasangati_loop/gpx/` | 1 GPX (`12-Feb-2026-1537.gpx`, 130KB) | 130 KB |
| `myTracks/` | 10 GPX files from 2026-02-13 | ~1.4 MB |
| `Screenshots/` | 3 PNG screenshots | ~24 MB |
| Root GPX files | `12-Feb-2026-1418.gpx`, `12-Feb-2026-1537.gpx` | 145 KB |

### data/
| File | Size | Description |
|------|------|-------------|
| `uganda_main_roads.geojson` | 3.1 MB | 738 named roads from HOT Export |
| `uganda_main_roads_enriched.geojson` | 3.3 MB | + population + surface predictions |
| `unra_road_network.geojson` | 10 KB | UNRA project roads |
| `kontur_uganda_population.gpkg` | 34 MB | Kontur H3 hexagon population |
| `kontur_population_UG_20231101.gpkg.gz` | 12 MB | Compressed Kontur data |
| `heigit_uga_roadsurface_lines.gpkg` | 453 MB | Road surface predictions |
| `UgandaTravelTimes.zip` | 1.2 GB | Travel time data |
| `hotosm_uga_roads.zip` | 157 MB | OSM roads export |
| `travel_times/` | ~1.2 GB | AllRoads shapefile components |

### output/
| File | Size | Description |
|------|------|-------------|
| `condition.geojson` | 7.0 MB | Previous dashcam analysis output |
| `test_condition.geojson` | 1.1 MB | Test pipeline output |
| `narrative.md` | 1.4 KB | Condition narrative |
| `summary.json` | 345 B | Condition summary |

---

## 7. DEPENDENCIES

### requirements.txt
```
dash>=2.14.0, dash-bootstrap-components>=1.5.0, dash-leaflet>=1.0.0, dash-extensions>=1.0.0
anthropic>=0.40.0
numpy>=1.24.0, pandas>=2.0.0, scipy>=1.11.0
geopy>=2.4.0, rasterio>=1.3.0
plotly>=5.18.0, matplotlib>=3.8.0, kaleido>=0.2.0
requests>=2.31.0, httpx>=0.25.0
opencv-python-headless>=4.8.0
fpdf2>=2.7.0, python-docx>=1.0.0
python-dotenv>=1.0.0, Pillow>=10.0.0
```

### Installed versions (key packages)
```
anthropic          0.79.0
dash               4.0.0
dash-leaflet       1.1.3
dash-bootstrap     2.0.4
plotly             6.5.2
numpy              2.4.2
pandas             3.0.0
opencv-python-headless  4.13.0.92
fpdf2              2.8.5
geopy              2.4.1
pillow             12.1.1
```

---

## 8. GIT STATUS

### Branches
```
  dash-migration
  main
* video-integration          (active)
  remotes/origin/main
  remotes/origin/video-integration
```

### Recent commits (video-integration)
```
0a7acb0 working video pipline with preprocessing on server
8cfcf65 Raise size guard limits: 100 clips, 2GB total, 100MB/clip
72c202c Video pipeline: 12/12 validator passing, per-section interventions
20dcf60 Ingesting of Multiple large video files fixed
2eb0f05 Replace browser upload with preset dropdown and path inputs
5d931fe Raise size guard limits for real dashcam data
5b88062 Fix video pipeline: 11/11 validator checks passing
4c6acf6 Video import working v1
dafc5b4 Importing multiple videos
d5176ae Add multi-file/directory upload support for video pipeline
```

### Working tree
```
?? docs/TARA_13_FEB_2026_AUDIT_PROMPT.md    (untracked audit prompt)
```
**Clean otherwise.**

---

## 9. KNOWN ISSUES

### From CLAUDE.md — Current TODO items
All items checked off. No unchecked TODOs remaining:
- [x] Project scaffolding through [x] Intervention recommendation per section

### Known gaps (not bugs, but incomplete integrations)
1. **Per-section interventions not fed into CBA** — video pipeline produces per-section costs, but CBA uses single whole-road `construction_cost_total`
2. **No caching in video pipeline** — every run reprocesses all frames from scratch
3. **Only 1 preset dataset** — `demo2` (Kasangati loop, 42 compressed clips)
4. **New 13-Feb-2026 dataset not integrated** — 136 clips + 10 GPX files in `data/videos/13-Feb-2026/` and `myTracks/` not added as a preset
5. **Agent model mismatch** — `agent/orchestrator.py` uses `claude-sonnet-4-5-20250929` but CLAUDE.md says "Opus 4.6"

---

## 10. CRITICAL QUESTIONS

### Can I run `python app.py` right now and get a working app?
**YES, very likely.** All dependencies installed, working tree clean, all video pipeline tests passing 12/12. The app should start on port 8050 with the full 7-step wizard. The only potential issue is the `ANTHROPIC_API_KEY` environment variable — needed for real Vision API calls and AI interpretation (Steps 2 video analysis, Step 6 AI interpretation).

### If the video pipeline produces GeoJSON + interventions, what's the gap to display on map in Step 2?
**ALREADY DONE.** The `run_video_pipeline` callback (lines 840-1039) already:
- Calls `run_pipeline()` → gets GeoJSON
- Calls `build_condition_layer(geojson)` → creates dash-leaflet components
- Appends condition layers to `main-map.children`
- Sets `map-bounds-store.data` → triggers fitBounds
- Displays intervention summary in `video-pipeline-result.children`

**What could be improved:**
- Intervention cost breakdown per section not shown on map popups
- No intervention legend on map
- No way to drill into individual section interventions from the UI

### If pipeline produces per-section costs, what's the gap to feed into CBA?
**SMALL but IMPORTANT gap.** Currently:
- Video pipeline stores interventions in `video-condition-store.data["interventions"]`
- CBA callback reads `total-cost-input` (manual entry) for `construction_cost_total`
- **Missing bridge:** auto-populate `total-cost-input` from intervention route_summary.total_cost
- Or better: modify CBA callback to check `video-condition-store` and sum per-section costs if available

### What's the single biggest blocker to a working demo?
**There is no blocker — the app works.** The biggest *enhancement opportunity* is:
1. **Adding the new 13-Feb-2026 dataset** (136 clips + 10 GPX tracks) as a preset — this is fresh, real-world data
2. **Auto-feeding video intervention costs into Step 4** — closing the video→CBA loop so the demo flows seamlessly from dashcam video to investment decision without manual cost entry
3. **Processing speed** — no caching means re-running the pipeline takes time; for a live demo, pre-computed results or caching would help

---

## ARCHITECTURE SUMMARY

```
User → Dash UI (app.py, 1,579 lines, 22 callbacks)
    ↓
Agent (orchestrator.py) + Opus 4.6 API
    ↓
Tool Dispatcher (tools.py, 11 tools)
    ↓
    ├─ Skills Layer
    │  ├─ road_database.py (738 local roads)
    │  ├─ osm_lookup.py (Overpass API)
    │  ├─ osm_facilities.py (Overpass + retry)
    │  ├─ worldpop.py / kontur_population.py
    │  └─ dashcam.py (single-file Vision)
    │
    ├─ Engine Layer
    │  ├─ cba.py (NPV, EIRR, BCR, FYRR)
    │  ├─ traffic.py (per-class ADT forecast)
    │  ├─ sensitivity.py (tornado, switching, scenarios)
    │  └─ equity.py (composite 0-100 score)
    │
    ├─ Video Pipeline (self-contained)
    │  ├─ video_pipeline.py (orchestrator)
    │  ├─ video_frames.py (OpenCV extraction)
    │  ├─ gps_utils.py (GPX parsing + interpolation)
    │  ├─ vision_assess.py (Claude Vision + mock)
    │  ├─ video_map.py (GeoJSON sections)
    │  └─ intervention.py (Uganda-calibrated)
    │
    └─ Output Layer
       ├─ charts.py (5 Plotly chart types)
       ├─ maps.py (dash-leaflet)
       └─ report.py (markdown + PDF)
```

---

*End of audit. This report covers all 10 sections requested in the audit prompt.*
