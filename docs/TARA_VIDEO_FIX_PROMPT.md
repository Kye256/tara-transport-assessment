# TARA Video Pipeline — Autonomous Fix & Validate
# Paste into Claude Code. Runs autonomously with sub-agents via Task tool.

---

## ORCHESTRATOR INSTRUCTIONS

You are the orchestrator. You will:
1. Read the codebase
2. Build a test harness
3. Run it to see what's broken
4. Dispatch sub-agents to fix things in parallel
5. Integrate their work
6. Run tests again
7. Iterate until all 12 checks pass

**FIRST ACTION — read these files before doing anything else:**
- `CLAUDE.md`
- `video/video_frames.py`
- `video/gps_utils.py`
- `video/vision_assess.py`
- `video/video_map.py`
- `video/video_pipeline.py`

**BOUNDARIES — do NOT touch these:**
- `app.py`, anything in `layouts/`, `callbacks/`, `assets/`
- Only modify files in `video/`

---

## WHAT'S BROKEN

1. GeoJSON sections don't form a continuous line — gaps, jumps, or one straight line
2. All frames grouped into one giant section (one color, one popup for whole route)
3. Polyline doesn't follow road — straight lines between GPS points instead of following GPX track
4. App crashes with `allocation size overflow` on large video uploads (browser-side, but server should validate)
5. No progress feedback during processing — just a spinner
6. No automatic intervention recommendation based on condition assessment
7. Sections don't break on surface type change — a gravel section and paved section get lumped together

**Test data:**
- Compressed clips: `data/videos/demo2_kasangati_loop/clips_compressed/`
- GPX: `data/videos/12-Feb-2026-1537.gpx` (895 trackpoints, 14:19–15:37 local time)
- Timezone: UTC+3. GPX stores UTC. Clip filenames are local time.

---

## PHASE 1: BUILD VALIDATOR (you do this, don't delegate)

Create `video/test_pipeline.py`. This runs the pipeline in mock mode (no API calls) and validates the GeoJSON output.

```
python -m video.test_pipeline
```

**12 validation checks — ALL must pass:**

| # | Check | Criteria |
|---|-------|----------|
| 1 | CONTINUITY | Each section starts within 50m of previous section's end |
| 2 | SECTION LENGTH | No section > 1.5km |
| 3 | MINIMUM SECTIONS | At least 6 sections for 8.35km route |
| 4 | GPS DENSITY | Every LineString has 2+ coordinate pairs |
| 5 | COORDS IN BOUNDS | All points within lat 0.35–0.42, lon 32.60–32.67 |
| 6 | NO STRAIGHT LINES | Sections > 500m have 3+ coordinate pairs |
| 7 | PROPERTIES | Every feature has: condition_class, color, avg_iri, surface_type, section_index, length_km |
| 8 | TEMPORAL ORDER | Section indices sequential |
| 9 | POPUP HTML | Every feature has popup_html with `<img>` tag |
| 10 | TOTAL DISTANCE | Sum of sections within 20% of 8.35km |
| 11 | SIZE GUARDS | Pipeline returns error (not crash) for: total >500MB, clip >50MB, count >30 |
| 12 | INTERVENTION | Every section in pipeline output has intervention with: code, name, cost_per_km, design_life, reasoning |

**After building the validator, run it immediately.** Read the output. Note which checks fail. You need this information before dispatching sub-agents.

---

## PHASE 2: DISPATCH SUB-AGENTS (parallel via Task tool)

Dispatch ALL FOUR sub-agents simultaneously. They work on separate files so there are no conflicts.

### Sub-Agent A → `video/gps_utils.py` ONLY

```
Fix GPS utilities for continuous road-following coordinates.

Read video/gps_utils.py first.

Problems:
1. GPS matching snaps to nearest trackpoint instead of interpolating → causes coordinate jumps
2. No function to get intermediate GPX trackpoints between two timestamps

Changes needed:
- Fix match_frames_to_gps(): interpolate lat/lon linearly between the two bracketing trackpoints by timestamp
- Add new function get_trackpoints_between(trackpoints, start_time, end_time):
  Returns all GPX trackpoints where start_time <= time <= end_time, inclusive.
  This is critical — video_map.py will call it to build dense LineStrings.
- Ensure haversine(lat1, lon1, lat2, lon2) exists and returns distance in meters

ONLY touch video/gps_utils.py. Do not modify any other file.
```

### Sub-Agent B → `video/video_map.py` ONLY

```
Fix GeoJSON section builder for proper road sectioning.

Read video/video_map.py and video/gps_utils.py first.

Problems:
1. Sections only break on condition_class change
2. LineStrings only have frame GPS points — missing intermediate trackpoints

Changes to frames_to_condition_geojson():
- Add trackpoints parameter (the full parsed GPX track, list of dicts with lat/lon/time)
- Break sections when ANY of: (a) condition_class changes, (b) surface_type changes, (c) cumulative distance > 1.0km
- Surface type change is the highest priority break
- For each section, build LineString using ALL GPX trackpoints between that section's first and last frame timestamps. Import and call get_trackpoints_between() from gps_utils for this.
- Each feature properties must include: condition_class, color, avg_iri, surface_type, section_index, length_km, popup_html

Color mapping: good=#2d5f4a, fair=#9a6b2f, poor=#c4652a, bad=#a83a2f

THE KEY FIX explained:
Currently:  LineString([frameA_gps, frameB_gps])  ← straight line
Should be:  LineString([frameA_gps, trackpt1, trackpt2, ..., frameB_gps])  ← follows road

ONLY touch video/video_map.py. Do not modify any other file.
```

### Sub-Agent C → `video/video_frames.py` ONLY

```
Fix memory management in frame extraction.

Read video/video_frames.py first.

Changes to extract_frames():
- Process ONE clip at a time. Open clip, extract frames, call cap.release(), then next clip.
- Never hold multiple video captures open simultaneously.
- Only accumulate the small JPEG frame data, not raw video.

ONLY touch video/video_frames.py. Do not modify any other file.
```

### Sub-Agent D → CREATE `video/intervention.py` (new file)

```
Create intervention recommendation module.

This is a NEW file: video/intervention.py

INTERVENTION TABLE (Uganda-calibrated costs):

| Code | Name | Cost/km USD | Design Life yr | Maintenance/km/yr USD |
|------|------|-------------|----------------|----------------------|
| REG  | Regravelling | 60,000 | 5 | 5,000 |
| DBST | Upgrade to DBST | 800,000 | 10 | 8,000 |
| AC   | Upgrade to Asphalt Concrete | 1,000,000 | 15 | 10,000 |
| REHAB| Rehabilitation | 600,000 | 12 | 10,000 |
| PM   | Periodic Maintenance (Overlay) | 150,000 | 8 | 8,000 |
| DUAL | Dualling | 2,000,000 | 20 | 15,000 |
| DUAL_NMT | Dualling + NMT Facilities | 2,500,000 | 20 | 18,000 |
| RM   | Routine Maintenance Only | 5,000 | 1 | 5,000 |

SELECTION LOGIC per section:

Unpaved (earth/gravel):
  any condition → DBST (regravelling is false economy for most traffic levels)
  
Paved (asphalt/dbst/paved):
  good → RM
  fair → PM
  poor → REHAB
  bad → REHAB
  
Unknown → DBST (safe default)

Create these functions:

1. get_intervention(code) → dict with all fields for that intervention
2. get_all_interventions() → list of all intervention dicts
3. recommend_intervention(section) → dict:
   section has: surface_type, condition_class, avg_iri, length_km
   Returns: {
     'code': 'DBST',
     'name': 'Upgrade to DBST', 
     'cost_per_km': 800000,
     'design_life': 10,
     'maintenance_per_km_yr': 8000,
     'section_cost': 960000,  # cost_per_km × length_km
     'reasoning': '...',  # 1-2 sentences explaining why
     'alternatives': ['AC', 'REG']
   }

4. recommend_interventions_for_route(sections) → dict:
   {
     'sections': [
       {'section_index': 0, 'length_km': 1.2, 'surface': 'paved', 'condition': 'fair', 'intervention': {...}},
       ...
     ],
     'route_summary': {
       'total_length_km': 8.3,
       'total_cost': 5_200_000,
       'dominant_intervention': 'DBST',
       'narrative': 'The route comprises N distinct sections...'
     }
   }

ONLY create video/intervention.py. Do not modify any other file.
```

---

## PHASE 3: INTEGRATE (you do this yourself)

After all 4 sub-agents complete:

1. **Wire intervention into pipeline.** Edit `video/video_pipeline.py`:
   - Import recommend_interventions_for_route from video.intervention
   - After vision assessment and section building, call it with the sections
   - Include intervention results in pipeline output
   - Add progress_callback support:
     - Accept optional `progress_callback(stage, message)` parameter
     - Call at stages 1-7 (see stage list below)
     - If no callback, print to stdout

2. **Wire trackpoints into video_map.** Edit `video/video_pipeline.py`:
   - Pass the parsed trackpoints list to frames_to_condition_geojson()

3. **Add size guards to pipeline.** Edit `video/video_pipeline.py`:
   - Before processing: check total size >500MB, per-clip >50MB, count >30
   - Return error dict on failure, never crash
   - Wrap pipeline in try/except for MemoryError/OverflowError

4. **Verify imports work:**
   ```
   python -c "from video.intervention import recommend_intervention; print('OK')"
   python -c "from video.gps_utils import get_trackpoints_between; print('OK')"
   ```

**Progress stages for callback:**
```
1. "Validating uploads... ({n} clips, {size}MB)"
2. "Extracting frames... (clip {i}/{n})"  ← per clip
3. "Matching GPS... ({n_frames} frames → {n_points} trackpoints)"
4. "Analysing condition... (frame {i}/{n})"  ← per frame  
5. "Building sections... ({n} sections, {dist}km)"
6. "Recommending interventions..."
7. "Complete ✓ — {n} sections, {dist}km, est. cost ${total}"
```

---

## PHASE 4: VALIDATE & ITERATE (the loop)

```
python -m video.test_pipeline
```

Read output. If any check fails:
1. Identify which file has the bug
2. Fix it yourself (don't re-dispatch sub-agents for small fixes)
3. Run validator again
4. Repeat until: **12/12 checks passed ✓**

**Do not proceed to Phase 5 until 12/12 pass.**

---

## PHASE 5: REAL API TEST (only after 12/12 in mock)

1. Run pipeline with `use_mock=False`, `max_frames=5`
2. Confirm GeoJSON still passes validator
3. Confirm intervention recommendations are present per section
4. Save output to `output/test_condition.geojson`

---

## THE CRITICAL FIX (reference for all agents)

Why sections are straight lines:
```
Current:  Frame1→Frame2→Frame3 = LineString([GPS_A, GPS_B, GPS_C])
          Three points, straight lines between them.

Fixed:    Between Frame1 and Frame2, GPX has trackpoints t1,t2,t3,t4
          LineString([GPS_A, t1, t2, t3, t4, GPS_B, t5, t6, GPS_C])
          Dense points following the actual road path.
```

Requires: gps_utils.get_trackpoints_between() → video_map uses it per section.

---

## MOCK MODE SPEC

Mock vision assessor cycles through realistic variation:
- Conditions: good, good, fair, fair, poor, good, good, fair, poor, bad (repeat)
- Surface types: paved_asphalt, paved_asphalt, gravel, earth (repeat)  
- IRI: good=3-5, fair=6-9, poor=10-14, bad=15+
- Image: "MOCK_IMAGE_DATA" placeholder

This ensures sections break on both condition AND surface type changes.

---

## STOP CONDITION

When validator outputs `12/12 checks passed ✓`:

1. Update CLAUDE.md:
   - [x] Video pipeline: 12/12 validator checks passing
   - [x] Intervention recommendation per section
   - Note any function signature changes
   
2. Commit: `git add video/ && git commit -m "Video pipeline: 12/12 validator passing, per-section interventions"`

3. **Stop. Do not make further changes.**

---

## RULES

- Do NOT touch app.py, layouts/, callbacks/, assets/
- Do NOT make real API calls until Phase 5
- Do NOT add new dependencies
- Run validator after EVERY code change
- Fix integration issues yourself — don't re-dispatch for small bugs
- Sub-agents touch ONLY their assigned files
- Keep functions short, no god-objects
