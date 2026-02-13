# TARA — Wire Video Analysis → Costs → CBA
# Paste into Claude Code.

---

## READ FIRST

Before making any changes, read these files completely:
- `app.py` — focus on: `run_video_pipeline` callback, `run_cba_callback`, `auto_populate_costs`, Step 4 builder, all `dcc.Store` definitions
- `video/intervention.py` — how interventions are structured
- `engine/cba.py` — what `run_cba()` expects as inputs
- `config/parameters.py` — Uganda-calibrated defaults

Then answer these diagnostic questions OUT LOUD before writing any code:
1. After video pipeline runs, what exactly is in `video-condition-store.data`? Print its keys and structure.
2. After video pipeline runs, what exactly is in `condition-store.data`? Print its keys.
3. Does `auto_populate_costs` callback exist? What does it output to?
4. In Step 4 UI, is there a div for the per-section intervention table? What's its ID?
5. When `run_cba_callback` fires, where does it read `construction_cost_total` from? Does it check `video-condition-store`?
6. Does the CBA engine receive IRI data? Where from?

---

## THE FULL DATA FLOW (what should happen)

```
Step 2: Video pipeline runs
  → video-condition-store gets: {summary, geojson, interventions, panel_data, narrative, metadata}
  → condition-store gets: {source: "video_pipeline", surface_type, condition_rating, iri, ...}

Step 4: User arrives at Costs
  → UI reads video-condition-store.interventions
  → Displays per-section table:
    | Section | Length | Surface | Condition | IRI  | Intervention        | Cost/km    | Section Cost |
    |---------|--------|---------|-----------|------|---------------------|------------|-------------|
    | 1       | 1.2km  | Paved   | Fair      | 7.2  | Periodic Maint.     | $150,000   | $180,000    |
    | 2       | 0.8km  | Gravel  | Poor      | 12.1 | DBST Upgrade        | $800,000   | $640,000    |
    | 3       | 2.1km  | Earth   | Bad       | 16.5 | DBST Upgrade        | $800,000   | $1,680,000  |
    |         | 4.1km  |         |           |      | TOTAL               |            | $2,500,000  |
  → total-cost-input auto-filled with $2,500,000
  → User can override any value

Step 5: User clicks Run Analysis
  → CBA receives:
    - construction_cost_total = sum of section costs (or user override)
    - road_length_km = sum of section lengths (from video) OR from road-data-store
    - IRI without project = weighted average IRI from video sections
    - IRI with project = estimated post-intervention IRI (good condition = 3.0 for paved, 6.0 for gravel)
  → CBA runs → NPV, EIRR, BCR displayed
```

---

## CHANGES NEEDED

### 1. Verify condition-store has IRI data from video

When `run_video_pipeline` callback stores to `condition-store`, ensure it includes:
```python
{
    'source': 'video_pipeline',
    'surface_type': summary['dominant_surface'],
    'condition_rating': summary['dominant_condition'],
    'iri': summary['average_iri'],           # weighted average IRI across all sections
    'overall_condition': ...,
    'sections': interventions['sections'],    # FULL per-section breakdown
}
```

The `sections` list is critical — it carries per-section IRI, surface, condition, and intervention data from Step 2 through to Step 5.

### 2. Build per-section cost table in Step 4

When Step 4 renders (or when video-condition-store updates), show an `html.Table` with the intervention breakdown. Style per TARA UI reference:
- Font: DM Mono for numbers, Source Sans 3 for labels
- Table borders: #ddd9d1
- Section cost column right-aligned
- Total row bold with top border
- Data attribution line below: "Source: TARA Vision Analysis (Claude Opus 4.6), 25m frame interval"

The table should be in a div that only appears when video data exists. If no video data, Step 4 shows the standard manual cost input only.

### 3. Auto-fill total cost input

If `auto_populate_costs` callback already exists, verify it works:
- Select Kasangati-Matugga from cache (should be instant)
- Navigate to Step 4
- Check if `total-cost-input` has a value

If it doesn't work, fix it. The value should be `interventions['route_summary']['total_cost']`.

### 4. Feed video data into CBA engine

In `run_cba_callback`, add logic to extract video-derived parameters:

```python
# Check if video analysis provides better data than manual inputs
video_data = video_condition_store_data  # from State('video-condition-store', 'data')
if video_data and 'interventions' in video_data:
    interventions = video_data['interventions']
    
    # Use video-derived road length if available
    if 'route_summary' in interventions:
        route = interventions['route_summary']
        video_road_length = route.get('total_length_km')
        video_total_cost = route.get('total_cost')
    
    # Use video-derived IRI for VOC calculations
    if 'summary' in video_data:
        video_iri = video_data['summary'].get('average_iri')
```

The CBA engine uses IRI indirectly through VOC rates — higher IRI means higher vehicle operating costs. Currently the VOC rates are static from `config/parameters.py`. 

For the hackathon, the simplest correct approach: use the video IRI to select the appropriate VOC rate tier rather than recalculating from first principles. The config already has VOC rates for "without project" (bad road) and "with project" (good road). Map:
- Video IRI > 10 → use config's "without project" VOC rates (these represent a rough road)
- Video IRI 6-10 → interpolate between without/with rates
- Video IRI < 6 → road is already decent, smaller benefit

This makes the CBA results responsive to what the dashcam actually saw.

### 5. Display road length from video in Step 4

The `road_length_km` in Step 4 should auto-fill from the video pipeline's measured distance, not just from the OSM road lookup. The video-measured distance is more accurate for the actual section driven.

---

## TESTING

After changes, test this exact flow:

1. Open app, go to Step 2
2. Select Kasangati-Matugga from dropdown (should load from cache instantly)
3. Verify condition map appears on the right
4. Click Next to Step 3 (Traffic) — enter 500 ADT, 3.5% growth
5. Click Next to Step 4 (Costs):
   - [ ] Per-section intervention table visible?
   - [ ] Total cost auto-filled?
   - [ ] Road length matches video route (~12.5km)?
6. Click Next to Step 5 (Results) — click Run Analysis:
   - [ ] CBA produces NPV, EIRR, BCR?
   - [ ] Numbers are plausible? (EIRR should be 15-35% for a typical Uganda road upgrade)
7. Click Next to Step 6 (Sensitivity):
   - [ ] Sensitivity analysis runs?
   - [ ] Construction cost is one of the tested variables?

**If any step fails, fix it before moving to the next.**

---

## DO NOT

- Do not restructure app.py
- Do not change the video pipeline (it's working and cached)
- Do not change CSS or visual styling beyond the new table
- Do not modify the CBA calculation methodology — only change what data feeds into it
- Do not break the manual input flow (user should still be able to override any auto-filled value)

## WHEN DONE

Report:
1. Does the full flow work: video → costs table → CBA results?
2. What are the actual CBA numbers for Kasangati-Matugga?
3. Are there any values that look wrong?

Commit with: `git commit -m "Wire video interventions to costs and CBA engine"`
