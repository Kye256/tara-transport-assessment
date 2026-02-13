# TARA — Equity Data Diagnostic & Section Fix
# Sequential — read first, then fix

Do NOT commit anything. Do NOT run git commands. I will test and commit manually.

---

## PROBLEM

The equity step shows all "?" and "—" for 145 sections. Three issues:
1. Activity profile data may not be in the cached pipeline result (old cache from before equity prompt)
2. 145 sections is far too many for a ~12km road — sectioning logic is breaking too aggressively
3. There is no UI option to re-run the pipeline or clear cache — user is stuck with stale data

---

## STEP 0: DIAGNOSE THE CACHE

Read the cached pipeline result file. Find it by searching for:
- Files matching `cache/pipeline_result.json` or similar in `data/videos/`
- Or search the pipeline code for where it saves/loads cache

Once you find the cache file, report:

1. How many frames are in the cached result?
2. Pick 3 frames at random — do they have an `activity_profile` key? If yes, what does it contain? If no, confirm it's missing.
3. How many sections are in the cached GeoJSON?
4. What are the section lengths? (list first 10)
5. Do any sections have an `equity` key in their properties?

Also read the pipeline code and report:
6. What is the cache key / cache file path?
7. What triggers a cache hit vs cache miss? (filename? hash? settings?)
8. Is there any way to force a re-run from the UI?

Report ALL findings before proceeding to fixes.

---

## STEP 1: FIX SECTIONING LOGIC

Find the function that groups frames into sections (likely in `video/video_map.py`).

The current logic is creating 145 sections for ~12km. The problem is likely one of:
- Breaking on EVERY condition_class change between adjacent frames (noisy — Claude Vision may assess adjacent frames differently)
- Breaking on EVERY surface_type change (also noisy)
- Distance threshold too small
- No minimum section length

**Fix the sectioning with these rules:**

**IMPORTANT: Sections are defined by SURFACE TYPE and CONDITION only.** Activity profile data (land use, pedestrians, facilities, NMT) does NOT affect section boundaries. The equity data is an overlay — it aggregates across whatever sections the condition logic produces. NEVER break sections because of activity changes.

1. **Minimum section length: 0.3 km.** Do not create a new section break if the current section is shorter than 300m. Instead, extend the current section even if condition changes.

2. **Smooth condition noise.** Only break on condition_class change if at least 2 consecutive frames agree on the new condition. A single frame disagreeing should not force a section break. Example: if frames are [poor, poor, fair, poor, poor], that's one "poor" section, not three.

3. **Always break on surface_type change.** Paved → gravel → earth are real physical boundaries. But still enforce the 0.3km minimum — if a surface change happens 100m into a section, extend anyway.

4. **Maximum section length: 2.0 km.** Force a break if a section exceeds 2km, even if condition is consistent.

5. **NEVER break on activity_profile changes.** A section doesn't end because the camera sees a market in one frame and farmland in the next. Activity data is aggregated per section AFTER sections are formed from surface/condition logic.

6. **Target: 5-15 sections for a 10-15km road.** If the result has more than 20 sections, the logic is still too aggressive.

**Implementation approach:** 

```python
def group_frames_into_sections(assessed_frames, min_length_km=0.3, max_length_km=2.0, smoothing_window=2):
    """
    Group assessed frames into homogeneous sections based on SURFACE TYPE and CONDITION only.
    Activity profile data does NOT affect section boundaries.
    
    Rules:
    1. Break on surface_type change (but respect min_length)
    2. Break on condition_class change only if sustained for smoothing_window consecutive frames
    3. Enforce min_length_km — don't break below this
    4. Enforce max_length_km — force break above this
    5. NEVER break on activity_profile, land_use, or equity data
    """
    sections = []
    current_section_frames = [assessed_frames[0]]
    
    for i in range(1, len(assessed_frames)):
        frame = assessed_frames[i]
        
        current_length = calculate_section_length(current_section_frames)
        
        should_break = False
        
        # Force break at max length
        if current_length >= max_length_km:
            should_break = True
        
        # Break on surface type change (if above min length)
        elif (current_length >= min_length_km and 
              frame.get("surface_type") != current_section_frames[0].get("surface_type")):
            should_break = True
        
        # Break on sustained condition change (if above min length)
        elif current_length >= min_length_km:
            current_condition = current_section_frames[0].get("condition_class")
            new_condition = frame.get("condition_class")
            if new_condition != current_condition:
                lookahead = assessed_frames[i:i+smoothing_window]
                if len(lookahead) >= smoothing_window and all(
                    f.get("condition_class") == new_condition for f in lookahead
                ):
                    should_break = True
        
        if should_break:
            sections.append(current_section_frames)
            current_section_frames = [frame]
        else:
            current_section_frames.append(frame)
    
    if current_section_frames:
        sections.append(current_section_frames)
    
    return sections

# THEN, after sections are formed, aggregate equity data per section:
for section_frames in sections:
    equity = aggregate_section_equity(section_frames)  # from equity integration build
    section_properties["equity"] = equity
```

Adapt this to fit the existing code structure. `calculate_section_length` should use GPS coordinates (haversine distance or sum of inter-frame distances).

**After fixing, verify:** How many sections does the existing cached data produce with the new logic? Report the count and section lengths.

---

## STEP 2: ADD RE-RUN CONTROL TO UI

The user needs a way to:
- **Use cached data** (fast, no API cost) — this should be the default
- **Re-run the pipeline** (slow, costs API credits) — needed when prompt changes or user wants fresh analysis

**Add a control to Step 2 (Condition) where the video dataset is selected.** After the dataset dropdown, add:

```
[Dataset dropdown: Kasangati-Matugga ▼]

Pipeline status: Cached result available (analysed 2026-02-13 15:30)
Frames: 48 assessed | Sections: 8

[ Use Cached Results ]    [ Re-analyse (uses API credits) ]
```

**Implementation:**

1. When a dataset is selected from the dropdown, check if a cache file exists for it
2. If cache exists: show "Cached result available" with timestamp and frame count. Show both buttons.
3. If no cache: show "No cached results. Analysis will use API credits." Show only the analyse button.
4. **"Use Cached Results" button** — loads the cached pipeline result into stores. This is the current default behavior.
5. **"Re-analyse" button** — deletes the cache file for this dataset, then runs the pipeline fresh. This triggers a full Vision API run.

**For the re-analyse button, add a confirmation:** Use a `dcc.ConfirmDialog` or similar:
"Re-analysing will use approximately $10-15 in API credits. The previous cached results will be replaced. Continue?"

**Show pipeline status after loading:** Whether from cache or fresh run, show:
- Number of frames assessed
- Number of sections formed  
- Date/time of analysis
- Whether equity data is available ("✓ Equity observations included" or "⚠ No equity data — re-analyse to include")

The equity data availability indicator is important — it tells the user whether the cache is from the old prompt (no equity) or the new prompt (has equity).

**Detection logic for equity data availability:**
```python
def cache_has_equity(pipeline_result):
    """Check if cached result includes equity observations."""
    frames = pipeline_result.get("frames", [])
    if not frames:
        return False
    # Check if any frame has activity_profile with actual data
    for frame in frames[:5]:  # check first 5
        profile = frame.get("activity_profile", {})
        if profile and profile.get("land_use") not in (None, "unknown", ""):
            return True
    return False
```

---

## STEP 3: VERIFY

After all changes:

1. [ ] Read the cache — does it have activity_profile data in frames? (report yes/no)
2. [ ] With the new sectioning logic, how many sections does the cached data produce?
3. [ ] Are section lengths between 0.3km and 2.0km?
4. [ ] Does the equity step table show the correct number of sections?
5. [ ] Does the dataset selector show cache status?
6. [ ] Does the re-analyse button exist with confirmation dialog?
7. [ ] Does the equity data availability indicator show correctly?
8. [ ] If cached data has no equity (old prompt), does the indicator say "re-analyse to include"?

Report results.

---

## DO NOT

- Do not delete any cache files
- Do not trigger a pipeline re-run (I will do that manually after testing)
- Do not change the Vision prompt (already updated in previous build)
- Do not change the CBA engine
- Do not add new pip dependencies
- Do not restructure app.py layout pattern

## FILE TOUCH MAP

- `video/video_map.py` — sectioning logic fix
- `video/video_pipeline.py` — cache detection helper
- `app.py` or `callbacks/` — re-run control UI, cache status display
- `layouts/` — if step 2 layout needs the new controls
