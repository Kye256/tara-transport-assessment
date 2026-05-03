# TARA — Equity Integration Build Prompt
# Sequential execution — changes touch shared files

Do NOT commit anything. Do NOT run git commands. I will test and commit manually.

---

## CONTEXT

TARA's video pipeline currently analyses dashcam frames for road surface condition (surface type, IRI estimate, distress). We are extending the Vision prompt to ALSO capture equity-relevant observations: who uses the road, what community activity is visible, and whether NMT infrastructure exists.

**Camera is primary evidence. OSM is supplementary.** OSM data in peri-urban Uganda is sparse. The camera sees ground truth — trading centres, pedestrians, boda-bodas, school children, missing footpaths — that no database captures.

**This is a sequential build.** Changes flow through the pipeline: Vision prompt → frame data → section aggregation → equity narrative → UI display. Each step depends on the previous one.

---

## STEP 0: AUDIT BEFORE CHANGING ANYTHING

Read these files and report their current state. Do NOT change anything yet.

1. `video/vision_assess.py` — Find the Vision prompt string (the system prompt sent to Claude with each frame). Copy the exact current prompt text into your report.
2. `video/video_map.py` — Find `frames_to_condition_geojson()` or equivalent. How does it group frames into sections? What properties does each section have?
3. `video/video_pipeline.py` — Find `run_pipeline()`. What does it return? Is there a cache? Where is the cache file?
4. `app.py` or `callbacks/` — Find where the video pipeline result is displayed. Is there an AI narrative panel? Where does it get its text?

Report all findings before proceeding.

---

## STEP 1: Extend the Vision Prompt (vision_assess.py)

Find the system prompt string in `vision_assess.py` that is sent to Claude Vision with each dashcam frame. It currently asks for surface_type, condition_class, iri_estimate, distress_types, etc.

**Add an `activity_profile` section to the JSON schema in the prompt.** The new fields go ALONGSIDE the existing condition fields — do not remove or modify any existing fields.

Add this to the JSON schema that the prompt asks Claude to return:

```
"activity_profile": {
  "land_use": "trading_centre|residential|agricultural|institutional|mixed|open",
  "activity_level": "high|moderate|low|none",
  "people_observed": {
    "pedestrians": "many|some|few|none",
    "school_children": true|false,
    "vendors_roadside": true|false,
    "people_carrying_loads": true|false
  },
  "vehicles_observed": {
    "boda_bodas": "many|some|few|none",
    "bicycles": "many|some|few|none",
    "minibus_taxi": "many|some|few|none",
    "cars": "many|some|few|none",
    "trucks": "many|some|few|none"
  },
  "facilities_visible": ["shops", "market_stalls", "school", "church", "mosque", "health_facility", "fuel_station", "none"],
  "nmt_infrastructure": {
    "footpath": "good|poor|none",
    "shoulder_usable": true|false,
    "pedestrians_on_carriageway": true|false
  }
}
```

**Also add this guidance to the prompt text** (near the IRI reference ranges or at the end):

```
Activity profile guidance:
- land_use: What is the dominant land use VISIBLE from the road? trading_centre = shops/stalls/commercial, residential = houses/compounds, agricultural = farmland/open, institutional = school/hospital/government, mixed = combination, open = undeveloped
- activity_level: How much human activity is visible? high = many people, vehicles, commerce. moderate = some activity. low = few people. none = empty.
- people_observed: What kinds of people can you see? Look for pedestrians on or near the road, children in school uniforms, roadside vendors/sellers, people carrying goods/water/firewood on their heads or by bicycle.
- vehicles_observed: What vehicle types are visible? boda_bodas = motorcycle taxis (very common in Uganda). Look at the MIX — a road dominated by boda-bodas and pedestrians serves different users than one dominated by trucks and cars.
- facilities_visible: List ALL facility types you can see or identify from signs. Include shops, market stalls, schools (look for signs, uniforms, playgrounds), churches, mosques, health facilities (look for signs), fuel stations. Report "none" if no facilities visible.
- nmt_infrastructure: Is there a footpath/sidewalk alongside the road? Is the road shoulder wide and smooth enough for pedestrians to walk on safely? Are pedestrians walking ON the carriageway (the road surface where vehicles drive)?
```

**CRITICAL:** 
- Do NOT remove or rename any existing fields in the prompt
- Do NOT change the model string or API call structure
- The activity_profile is ADDITIONAL data — the condition assessment continues as before
- If the response JSON parsing fails, the activity_profile should default to null/empty — do NOT let a missing activity_profile crash the pipeline

**Test:** After making the change, verify the prompt is valid by reading it back. Check that the JSON schema example in the prompt is valid JSON.

---

## STEP 2: Handle Activity Profile in Frame Processing

Find where the Vision API response is parsed (in `vision_assess.py` or wherever `assess_frame` / `assess_frame_condition` processes the JSON response).

**Add safe extraction of the activity_profile:**

```python
# After parsing the response JSON as `result`:
activity = result.get("activity_profile", {})

# Add to the frame dict that gets returned:
frame_data["activity_profile"] = {
    "land_use": activity.get("land_use", "unknown"),
    "activity_level": activity.get("activity_level", "unknown"),
    "people_observed": activity.get("people_observed", {}),
    "vehicles_observed": activity.get("vehicles_observed", {}),
    "facilities_visible": activity.get("facilities_visible", []),
    "nmt_infrastructure": activity.get("nmt_infrastructure", {})
}
```

**CRITICAL:** If the model returns a response WITHOUT activity_profile (e.g., from cached old results), the code must not crash. Always use `.get()` with defaults.

---

## STEP 3: Aggregate Activity Profile Per Section (video_map.py)

Find the function that groups frames into sections (likely `frames_to_condition_geojson` or similar). Each section already aggregates condition data across its frames.

**Add equity aggregation for each section.** After grouping frames into a section, compute:

```python
def aggregate_section_equity(section_frames):
    """Aggregate activity profiles across frames in a section."""
    profiles = [f.get("activity_profile", {}) for f in section_frames if f.get("activity_profile")]
    
    if not profiles:
        return {
            "activity_level": "unknown",
            "dominant_land_use": "unknown",
            "pedestrian_presence": "unknown",
            "nmt_footpath": "unknown",
            "pedestrians_on_carriageway": False,
            "school_children_observed": False,
            "vendors_observed": False,
            "facilities_seen": [],
            "vehicle_mix_summary": {},
            "equity_concern": "unknown"
        }
    
    # Most common land_use across frames
    land_uses = [p.get("land_use", "unknown") for p in profiles]
    dominant_land_use = max(set(land_uses), key=land_uses.count)
    
    # Highest activity level observed
    level_order = {"high": 3, "moderate": 2, "low": 1, "none": 0, "unknown": -1}
    activity_levels = [p.get("activity_level", "unknown") for p in profiles]
    highest_activity = max(activity_levels, key=lambda x: level_order.get(x, -1))
    
    # Pedestrian presence — take the highest observed
    ped_levels = [p.get("people_observed", {}).get("pedestrians", "none") for p in profiles]
    presence_order = {"many": 3, "some": 2, "few": 1, "none": 0}
    pedestrian_presence = max(ped_levels, key=lambda x: presence_order.get(x, 0))
    
    # School children — true if seen in ANY frame
    school_children = any(
        p.get("people_observed", {}).get("school_children", False) for p in profiles
    )
    
    # Vendors — true if seen in ANY frame
    vendors = any(
        p.get("people_observed", {}).get("vendors_roadside", False) for p in profiles
    )
    
    # NMT — worst case across frames (if ANY frame has no footpath, section has no footpath)
    footpath_values = [p.get("nmt_infrastructure", {}).get("footpath", "none") for p in profiles]
    footpath_order = {"good": 2, "poor": 1, "none": 0}
    nmt_footpath = min(footpath_values, key=lambda x: footpath_order.get(x, 0))
    
    # Pedestrians on carriageway — true if seen in ANY frame
    peds_on_road = any(
        p.get("nmt_infrastructure", {}).get("pedestrians_on_carriageway", False) for p in profiles
    )
    
    # Collect all unique facilities seen across frames
    all_facilities = []
    for p in profiles:
        facs = p.get("facilities_visible", [])
        if isinstance(facs, list):
            all_facilities.extend(facs)
    facilities_seen = sorted(set(f for f in all_facilities if f != "none"))
    
    # Vehicle mix — count dominant type across frames
    vehicle_types = ["boda_bodas", "bicycles", "minibus_taxi", "cars", "trucks"]
    vehicle_summary = {}
    for vtype in vehicle_types:
        levels = [p.get("vehicles_observed", {}).get(vtype, "none") for p in profiles]
        highest = max(levels, key=lambda x: presence_order.get(x, 0))
        if highest != "none":
            vehicle_summary[vtype] = highest
    
    # Equity concern flag
    # HIGH: many pedestrians + no footpath + high activity
    # MODERATE: some pedestrians + poor footpath, or school children observed
    # LOW: few pedestrians, good footpath, low activity
    equity_concern = "low"
    if pedestrian_presence in ("many", "some") and nmt_footpath == "none":
        equity_concern = "high"
    elif school_children or (pedestrian_presence == "some" and nmt_footpath == "poor"):
        equity_concern = "moderate"
    elif pedestrian_presence == "many":
        equity_concern = "moderate"
    
    return {
        "activity_level": highest_activity,
        "dominant_land_use": dominant_land_use,
        "pedestrian_presence": pedestrian_presence,
        "nmt_footpath": nmt_footpath,
        "pedestrians_on_carriageway": peds_on_road,
        "school_children_observed": school_children,
        "vendors_observed": vendors,
        "facilities_seen": facilities_seen,
        "vehicle_mix_summary": vehicle_summary,
        "equity_concern": equity_concern
    }
```

**Add the equity data to each section's GeoJSON properties.** Find where section properties are built (the dict that goes into `feature["properties"]`) and add:

```python
equity = aggregate_section_equity(section_frames)
properties["equity"] = equity
properties["equity_concern"] = equity["equity_concern"]
```

**Also update the popup HTML** for each section to include equity info. Find where popup_html is built and add a line like:

```python
# Add equity info to popup after condition info
if equity["equity_concern"] in ("high", "moderate"):
    equity_color = "#a83a2f" if equity["equity_concern"] == "high" else "#9a6b2f"
    popup_parts.append(
        f'<div style="margin-top:6px;padding:4px 8px;background:{equity_color}15;'
        f'border-left:3px solid {equity_color};font-size:11px;">'
        f'<b style="color:{equity_color}">⚠ Equity: {equity["equity_concern"].upper()}</b><br>'
        f'{equity["dominant_land_use"].replace("_"," ").title()} area · '
        f'Pedestrians: {equity["pedestrian_presence"]}'
        f'{"  · School children observed" if equity["school_children_observed"] else ""}'
        f'{"  · No footpath" if equity["nmt_footpath"] == "none" else ""}'
        f'</div>'
    )
```

Adapt the popup building approach to match whatever pattern is already used in the codebase. Do NOT break existing popup content — add equity info below it.

---

## STEP 4: Generate Equity Narrative (new function)

Add a function to generate the equity narrative. This can go in `video/video_map.py` or a new file `video/equity.py` — your choice based on where it fits best.

```python
def generate_equity_narrative(sections_data: list, anthropic_client) -> str:
    """
    Generate an equity impact narrative from section-level camera observations.
    
    sections_data: list of section dicts, each with 'equity' key from Step 3
    anthropic_client: Anthropic client instance
    
    Returns: narrative string for the AI analysis panel
    """
```

**The prompt to Claude should be:**

```
You are a transport equity analyst reviewing dashcam survey results for a road in Uganda. 
Based on the camera observations below, write a 3-4 paragraph equity impact assessment.

Focus on:
1. WHO uses this road — based on observed pedestrians, vehicle types, school children, vendors
2. WHERE are the community hubs — sections with high activity, trading centres, facilities
3. WHAT are the NMT gaps — where pedestrians have no safe space and are walking on the carriageway
4. WHAT does this mean for the proposed intervention — will the upgrade serve the people the camera observed?

Be specific. Reference section numbers and what was observed. Do not be generic.
Write in professional but accessible language suitable for a road appraisal report.

CAMERA OBSERVATIONS BY SECTION:
{sections_json}
```

Where `{sections_json}` is the equity data from each section formatted as readable text.

**Include a mock version** for testing without API:

```python
def generate_equity_narrative_mock(sections_data: list) -> str:
    """Return a plausible equity narrative for testing."""
    return (
        "EQUITY IMPACT ASSESSMENT\n\n"
        "Camera analysis identified significant equity concerns along this corridor. "
        f"{len([s for s in sections_data if s.get('equity', {}).get('equity_concern') == 'high'])} "
        "sections showed high equity concern with heavy pedestrian activity and no footpath provision.\n\n"
        "The dominant road users observed were pedestrians and boda-boda motorcycles, "
        "indicating this road primarily serves lower-income community transport needs. "
        "School children were observed in several sections, raising safety concerns.\n\n"
        "Recommendation: The proposed intervention should include NMT provision "
        "(footpaths and pedestrian crossings) to ensure the upgrade serves the "
        "vulnerable road users observed during the survey."
    )
```

---

## STEP 5: Wire Equity Narrative into Pipeline Output

Find `run_pipeline()` in `video/video_pipeline.py`. It currently returns a dict with keys like `frames`, `summary`, `geojson`, `narrative`, `metadata`, etc.

**Add the equity narrative to the pipeline output:**

1. After sections are built and the condition narrative is generated, call `generate_equity_narrative()` with the section data
2. Add `"equity_narrative"` to the returned dict
3. If API call fails, fall back to the mock narrative

```python
# In run_pipeline(), after condition narrative is generated:
try:
    equity_narrative = generate_equity_narrative(sections_data, client)
except Exception as e:
    print(f"Equity narrative generation failed: {e}")
    equity_narrative = generate_equity_narrative_mock(sections_data)

result["equity_narrative"] = equity_narrative
```

**CRITICAL — CACHING:** The pipeline caches results. If a cache exists from a PREVIOUS run (without equity data), the code must handle this gracefully:
- Option A: Check if cached result has `equity_narrative` key. If not, regenerate equity data from the cached frames (which have activity_profile if they were assessed with the new prompt) or return a placeholder.
- Option B: Add a cache version number. If the cache version doesn't match the current version, re-run the pipeline.
- Pick whichever is simpler given the existing cache implementation. Do NOT delete existing caches — they cost real API money to regenerate.

---

## STEP 6: Display Equity in the UI

Find where the condition narrative / AI analysis panel is displayed in the Dash app (likely in `callbacks/` or `app.py`).

**Add an equity narrative panel BELOW the existing condition narrative.** Use the same styling pattern as the condition panel but with a different accent color:

- Left border: `#3a5a80` (TARA blue) instead of green
- Label: "EQUITY IMPACT ASSESSMENT" in 9px uppercase mono
- Body: the equity_narrative text from the pipeline output

**Implementation approach — match whatever pattern the condition panel uses.** If it's a `dcc.Store` → clientside callback typing animation, do the same for equity. If it's a simple `html.Div`, do the same. Do NOT invent a new pattern.

The equity panel should:
- Only appear if `equity_narrative` exists in the pipeline result
- Appear BELOW the condition narrative, not replace it
- Use the same typography and spacing as the condition panel

---

## STEP 7: Verify

After all changes, verify:

1. **Read back the Vision prompt** — confirm activity_profile fields are present alongside existing condition fields
2. **Check JSON schema** — is the example JSON in the prompt valid?
3. **Check frame processing** — does the code safely handle responses with AND without activity_profile?
4. **Check section aggregation** — does aggregate_section_equity handle empty/missing data?
5. **Check popup HTML** — is equity info added without breaking existing popups?
6. **Check pipeline output** — does run_pipeline() return equity_narrative?
7. **Check UI** — is there an equity panel in the layout?
8. **Check cache handling** — what happens if old cache (without equity data) is loaded?

Report the results of each check.

---

## DO NOT

- Do not remove or rename any existing fields, functions, or files
- Do not change the CBA engine or sensitivity analysis
- Do not change CSS styling beyond what's needed for the equity panel
- Do not restructure app.py or change the step navigation
- Do not delete cached pipeline results (they cost API money)
- Do not add new pip dependencies
- Do not change the model string or API configuration
- Do not add `dcc.Interval` components

## FILE TOUCH MAP

These are the ONLY files this build should modify:
- `video/vision_assess.py` — Steps 1-2 (Vision prompt + response parsing)
- `video/video_map.py` — Step 3 (section equity aggregation + popup)
- `video/equity.py` (NEW) or added to `video/video_map.py` — Step 4 (narrative generation)
- `video/video_pipeline.py` — Step 5 (wire equity into pipeline output)
- `app.py` or `callbacks/` or `layouts/` — Step 6 (UI display, one file only)

If you find you need to modify other files, STOP and explain why before proceeding.
