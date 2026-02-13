# TARA — App Status Audit
# Run this first. Do NOT make any changes. Just report.

Read the entire codebase and report the following. Be thorough — this output will be used to plan the next 6 hours of work.

## 1. FILE INVENTORY

List every Python file with:
- Path
- Line count  
- One-line purpose
- Key functions/classes defined
- Imports from other TARA modules

## 2. VIDEO PIPELINE STATUS

Read all files in `video/` and answer:
- Does `video_pipeline.py` exist? What does `run_pipeline()` accept and return?
- Does `video_frames.py` extract frames from a folder of clips or a single file?
- Does `gps_utils.py` have `get_trackpoints_between()`? Does it interpolate or snap-to-nearest?
- Does `video_map.py` accept trackpoints? Does it include intermediate GPS points in LineStrings?
- Does `vision_assess.py` have mock mode? What does the mock return?
- Does `video/intervention.py` exist?
- Does `video/test_pipeline.py` exist?
- Is there any caching?

## 3. DASH APP STRUCTURE

Read `app.py` and everything in `layouts/` and `callbacks/`:
- How are the 7 steps structured? (separate files per step? one big file?)
- How does Step 2 (condition) currently work? Upload or dropdown?
- What `dcc.Store` IDs exist and what data flows between steps?
- How does the video pipeline connect to the Dash callbacks?
- Is there a video dataset dropdown already? What does it look like?

## 4. DATA FLOW

Trace the full path:
- Step 1 (road selection) → what gets stored?
- Step 2 (condition) → what gets stored? How does video feed into it?
- Step 3 (traffic) → reads from what stores?
- Step 4 (costs) → reads from what stores?
- Step 5 (CBA results) → what does the CBA engine need as input?
- Step 6 (sensitivity) → reads from what?
- Step 7 (report) → reads from what?

## 5. CBA ENGINE

Read the CBA calculation module:
- What inputs does it expect? (list each parameter)
- Does it accept per-section interventions or one intervention for whole road?
- What outputs does it produce? (NPV, EIRR, BCR, FYRR?)
- Where are the Uganda-calibrated parameters? (VOC rates, discount rate, etc.)

## 6. AVAILABLE TEST DATA

Check these directories and report what's there:
- `data/videos/` — list all subdirectories and their contents (clip counts, GPX files)
- `data/` — any GeoJSON, cache files, or other data?
- `output/` — any previously generated outputs?

## 7. DEPENDENCIES

Run: `pip list | grep -i "dash\|anthropic\|opencv\|plotly\|pandas\|numpy\|folium\|leaflet\|fpdf\|reportlab"`

And check: `cat requirements.txt` if it exists.

## 8. GIT STATUS

Run:
```
git branch -a
git log --oneline -10
git status --short
```

## 9. KNOWN ISSUES

Read CLAUDE.md and list:
- Current TODO items
- Known bugs
- Any notes about what's working vs broken

## 10. CRITICAL QUESTIONS

After reading everything, answer:
- Can I run `python app.py` right now and get a working app?
- If the video pipeline produces a GeoJSON + intervention recommendations, what's the gap to display it on the map in Step 2?
- If the pipeline produces per-section cost estimates, what's the gap to feed those into the CBA engine?
- What's the single biggest blocker to a working demo?

## OUTPUT FORMAT

Write your findings to `AUDIT_REPORT.md` in the project root. Print a summary to stdout.
