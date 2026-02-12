# TARA Video Pipeline — Autonomous Fix & Validate
# Paste this into Claude Code. It will orchestrate sub-agents to fix, test, and iterate.

---

## ORCHESTRATOR INSTRUCTIONS

You are the orchestrator agent for fixing TARA's dashcam video pipeline. You will dispatch sub-agents using the Task tool for parallel work, then validate and iterate until all checks pass.

**Read these files first before doing anything:**
- `CLAUDE.md` (project context)
- `video/video_frames.py`
- `video/gps_utils.py`
- `video/vision_assess.py`
- `video/video_map.py`
- `video/video_pipeline.py`

**Do NOT modify any Dash UI files (app.py, layouts/, callbacks/).** Only touch files in `video/`.

---

## PROBLEM STATEMENT

The video pipeline runs but produces bad GeoJSON output:
1. Sections don't form a continuous line — gaps, jumps, or one straight line
2. All frames get grouped into one giant section (one color, one popup)
3. The polyline doesn't follow the road — it draws straight lines between frame GPS points
4. App crashes with `allocation size overflow` on large/uncompressed video uploads
5. User sees only a loading spinner with no progress feedback during processing

**Test data:**
- Compressed clips: `data/videos/demo2_kasangati_loop/clips_compressed/`
- GPX file: `data/videos/12-Feb-2026-1537.gpx` (895 trackpoints, 14:19–15:37 local)
- Timezone: UTC+3. GPX = UTC. Clip filenames = local time.

---

## EXECUTION PLAN

### Phase 1: Build Validator (do this yourself, don't delegate)

Create `video/test_pipeline.py` that runs the pipeline in mock mode and checks GeoJSON output against 11 criteria. This is your test harness for the entire task.

**Validation checks — ALL must pass:**

| # | Check | Pass Criteria |
|---|-------|--------------|
| 1 | CONTINUITY | Each section starts within 50m of previous section's end |
| 2 | SECTION LENGTH | No section > 1.5km. Target ~1km, shorter OK on condition change |
| 3 | MINIMUM SECTIONS | At least 6 sections for 8.35km route |
| 4 | GPS DENSITY | Every section has 2+ coordinate pairs in its LineString |
| 5 | COORDINATES IN BOUNDS | All coords within lat 0.35-0.42, lon 32.60-32.67 |
| 6 | NO STRAIGHT LINES | Sections > 500m must have 3+ coordinate pairs |
| 7 | PROPERTIES | Every feature has: condition_class, color, avg_iri, surface_type, section_index |
| 8 | TEMPORAL ORDER | Section indices sequential, matching travel direction |
| 9 | POPUP HTML | Every feature has popup_html with `<img>` tag |
| 10 | TOTAL DISTANCE | Sum of sections within 20% of 8.35km |
| 11 | SIZE GUARDS | Pipeline rejects total >500MB, per-clip >50MB, count >30; catches MemoryError/OverflowError gracefully |

Output format:
```
[PASS] Continuity: All 9 sections connected (max gap: 12m)
[FAIL] Section length: Section 3 is 2.4km (max 1.5km)
...
7/11 checks passed
```

Run with: `python -m video.test_pipeline`

### Phase 2: Dispatch Sub-Agents (in parallel via Task tool)

After building the validator and running it once to see which checks fail, dispatch these sub-agents simultaneously:

---

**Sub-Agent A: Fix GPS Matching** — file: `video/gps_utils.py`
```
Task: Fix GPS utilities so frames map to continuous road-following coordinates.

Problems to fix:
1. GPS matching snaps to nearest trackpoint instead of interpolating between two nearest by timestamp → causes jumps
2. No function to retrieve all intermediate GPX trackpoints between two timestamps

Required changes:
- Fix match_frames_to_gps() to interpolate lat/lon linearly between the two bracketing trackpoints
- Add function: get_trackpoints_between(trackpoints, start_time, end_time) → returns all GPX points in that time window, inclusive
- This function is critical — video_map.py will use it to build dense LineStrings
- Ensure haversine() distance function exists in this file

Test: The matched GPS coordinates should form a smooth path when plotted, not a zigzag.

Do NOT modify any other files. Only touch video/gps_utils.py.
```

---

**Sub-Agent B: Fix Section Grouping** — file: `video/video_map.py`
```
Task: Fix GeoJSON section builder so sections follow the actual road and break at proper intervals.

Problems to fix:
1. Sections only break on condition_class change — need to ALSO break when cumulative distance exceeds 1km
2. LineStrings only contain frame GPS points — need ALL intermediate GPX trackpoints for road-following curves
3. Need to import and use get_trackpoints_between() from gps_utils

Required changes to frames_to_condition_geojson():
- Accept trackpoints list as parameter (the full GPX track)
- For each section, build LineString from ALL GPX trackpoints between first and last frame timestamps in that section
- Break sections when: (a) condition_class changes, OR (b) cumulative distance exceeds 1.0km
- Each section's properties must include: condition_class, color, avg_iri, surface_type, section_index, popup_html

Color mapping: good=#2d5f4a, fair=#9a6b2f, poor=#c4652a, bad=#a83a2f

Do NOT modify any other files. Only touch video/video_map.py.
```

---

**Sub-Agent C: Add Size Guards & Progress** — files: `video/video_pipeline.py` + `video/video_frames.py`
```
Task: Add input validation and progress reporting to the video pipeline.

SIZE GUARDS (in video_pipeline.py, before processing starts):
- Check total size of all clips. If > 500MB: return error dict with message "Total video size is X.XGB. Maximum recommended is 500MB. Please compress clips first."
- Check each clip. If any > 50MB: return warning in result about which clips are oversized
- Check clip count. If > 30: return error with message about too many clips
- Wrap entire pipeline in try/except catching MemoryError and OverflowError → return error dict, never crash

MEMORY MANAGEMENT (in video/video_frames.py):
- Process ONE clip at a time in extract_frames()
- Call cap.release() explicitly after extracting frames from each clip
- Never accumulate raw video data in memory — only keep the extracted JPEG frames

PROGRESS CALLBACK (in video/video_pipeline.py):
- Add optional progress_callback parameter to run_pipeline()
- progress_callback(stage, message) where stage is 1-7
- Call it at each stage:
  1. "Validating uploads... (checking {n} clips, {size}MB total)"
  2. "Extracting frames... (clip {i}/{n} — {filename})" — call once per clip
  3. "Matching GPS coordinates... ({n_frames} frames → {n_points} trackpoints)"
  4. "Analysing road condition... (frame {i}/{n})" — call once per frame
  5. "Building condition map... ({n_sections} sections, {distance}km)"
  6. "Generating assessment narrative..."
  7. "Complete ✓ — {n_sections} sections assessed over {distance}km"
- If no callback provided, print to stdout instead

Only touch video/video_pipeline.py and video/video_frames.py.
```

---

### Phase 3: Integrate & Validate (do this yourself after sub-agents complete)

1. Review all sub-agent changes for conflicts
2. Ensure video_map.py correctly imports get_trackpoints_between from gps_utils
3. Ensure video_pipeline.py passes trackpoints to video_map functions
4. Run: `python -m video.test_pipeline`
5. Read output carefully. Fix any remaining failures.
6. **Repeat steps 4-5 until 11/11 pass.** Do not stop at partial passes.

### Phase 4: Test with Real Vision API (only after 11/11 in mock mode)

1. Run pipeline with `use_mock=False` on 5 frames only to verify API integration
2. Confirm GeoJSON still passes validator
3. Save final GeoJSON to `output/test_condition.geojson`

---

## THE CRITICAL FIX (read this carefully)

The root cause of straight lines is that LineStrings only contain frame GPS points:
```
Frame 1 at GPS A → Frame 2 at GPS B → Frame 3 at GPS C
Current:  LineString([A, B, C])  ← straight lines between frames
```

The fix is to include ALL GPX trackpoints between frames:
```
GPX track between A→B has points: A, t1, t2, t3, t4, B
GPX track between B→C has points: B, t5, t6, t7, C
Fixed:    LineString([A, t1, t2, t3, t4, B, t5, t6, t7, C])  ← follows road
```

This requires:
1. `gps_utils.py` provides `get_trackpoints_between(trackpoints, start_time, end_time)`
2. `video_map.py` calls this for each section to get dense coordinates
3. The full `trackpoints` list must be passed through the pipeline to `video_map.py`

---

## MOCK MODE SPEC

The mock vision assessor (used during testing) should:
- Cycle conditions: good, good, fair, fair, poor, good, good, fair, poor, bad (repeat)
- IRI values: good=3-5, fair=6-9, poor=10-14, bad=15+
- Surface types cycling: paved_asphalt, paved_asphalt, gravel, earth (repeat)
- Placeholder image: "MOCK_IMAGE_DATA"

---

## STOP CONDITION

When `python -m video.test_pipeline` outputs:
```
11/11 checks passed ✓
```

Then update CLAUDE.md with:
- [x] Video pipeline validator: 11/11 passing
- List any API or function signature changes made
- Note the test command

You are done. Do not continue making changes after all checks pass.

---

## RULES

- Do NOT touch Dash UI files (app.py, layouts/, callbacks/, assets/)
- Do NOT make real API calls until Phase 4
- Do NOT add dependencies — use only what's already installed + stdlib
- Run the validator after EVERY change, not just at the end
- If a sub-agent's output breaks another module, fix the integration yourself — don't re-dispatch
- Keep functions short. No god-objects.
