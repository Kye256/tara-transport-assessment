# TARA Integration — Wire Video Pipeline to Full Demo Flow
# Paste into Claude Code. Read AUDIT_REPORT.md and CLAUDE.md first.

---

## CONTEXT

The app works. The video pipeline passes 12/12 validator. The CBA engine runs. But there are gaps preventing a seamless demo. This prompt closes those gaps.

**Read these files first:**
- `AUDIT_REPORT.md` (full app audit)
- `CLAUDE.md` (project context)
- `app.py` (the entire Dash app — all 1,579 lines, all callbacks)
- `video/video_pipeline.py` (pipeline orchestrator)
- `video/video_frames.py` (frame extraction)
- `video/vision_assess.py` (Claude Vision calls)
- `video/intervention.py` (cost recommendations)
- `config/parameters.py` (Uganda calibration)

**Do NOT break anything that currently works.** Run the app after each major change to verify.

---

## CHANGE 1: Auto-Scan Dataset Dropdown

**Problem:** The `video-preset-dropdown` is hardcoded with one preset. Adding new datasets requires editing app.py.

**Fix:** Scan `data/videos/` for valid datasets at app startup and populate the dropdown dynamically.

**A valid dataset folder contains:**
- A subfolder named `clips/` with at least one `.MP4` or `.mp4` file
- At least one `.gpx` file (either in the dataset folder root or in a `gpx/` subfolder)

**Expected folder structure:**
```
data/videos/
├── kasangati_matugga/
│   ├── clips/           ← compressed MP4s here
│   └── track.gpx        ← GPX file here (or in gpx/ subfolder)
├── matugga_kiteezi/
│   ├── clips/
│   └── track.gpx
└── demo2_kasangati_loop/
    ├── clips_compressed/ ← also accept clips_compressed/ as clip folder
    └── gpx/
        └── 12-Feb-2026-1537.gpx
```

**Implementation:**

Create a utility function (put it in `video/video_pipeline.py` or a new `video/datasets.py`):

```python
def scan_datasets(base_dir="data/videos"):
    """Scan for valid video datasets. Returns list of dicts."""
    datasets = []
    for entry in sorted(os.listdir(base_dir)):
        dataset_dir = os.path.join(base_dir, entry)
        if not os.path.isdir(dataset_dir):
            continue
        
        # Find clips folder
        clips_dir = None
        for candidate in ['clips', 'clips_compressed']:
            path = os.path.join(dataset_dir, candidate)
            if os.path.isdir(path):
                clips_dir = path
                break
        if not clips_dir:
            continue
        
        # Count clips
        clip_files = [f for f in os.listdir(clips_dir) if f.lower().endswith(('.mp4', '.avi', '.mov'))]
        if not clip_files:
            continue
        
        # Find GPX file(s)
        gpx_path = None
        # Check root
        gpx_files = [f for f in os.listdir(dataset_dir) if f.lower().endswith('.gpx')]
        if gpx_files:
            gpx_path = os.path.join(dataset_dir, gpx_files[0])
        # Check gpx/ subfolder
        gpx_subdir = os.path.join(dataset_dir, 'gpx')
        if not gpx_path and os.path.isdir(gpx_subdir):
            gpx_files = [f for f in os.listdir(gpx_subdir) if f.lower().endswith('.gpx')]
            if gpx_files:
                gpx_path = os.path.join(gpx_subdir, gpx_files[0])
        if not gpx_path:
            continue
        
        # Calculate total size
        total_size_mb = sum(os.path.getsize(os.path.join(clips_dir, f)) for f in clip_files) / (1024*1024)
        
        # Check for cached results
        cache_path = os.path.join(dataset_dir, 'cache', 'pipeline_result.json')
        has_cache = os.path.exists(cache_path)
        
        # Build label
        label = entry.replace('_', ' ').replace('-', ' ').title()
        label += f" ({len(clip_files)} clips, {total_size_mb:.0f}MB)"
        if has_cache:
            label += " [cached]"
        
        datasets.append({
            'label': label,
            'value': entry,
            'clips_dir': clips_dir,
            'gpx_path': gpx_path,
            'clip_count': len(clip_files),
            'total_size_mb': total_size_mb,
            'has_cache': has_cache,
        })
    
    return datasets
```

In `app.py`, replace the hardcoded dropdown options:
```python
# OLD
options=[{"label": "Kasangati loop (42 clips, compressed)", "value": "demo2"}]

# NEW
from video.datasets import scan_datasets
_DATASETS = scan_datasets()
options=[{"label": d['label'], "value": d['value']} for d in _DATASETS]
```

Update `populate_preset_paths()` to use `_DATASETS` instead of the hardcoded if/elif chain.

---

## CHANGE 2: Pipeline Caching

**Problem:** Every run reprocesses all frames from scratch. For demo, we need instant loading of previously processed roads.

**Fix:** After pipeline completes, save full result to `data/videos/{dataset}/cache/pipeline_result.json`. On next run, check cache first.

**In `video/video_pipeline.py`, modify `run_pipeline()`:**

```python
import json, hashlib

def _get_cache_dir(video_path):
    """Get cache directory for a video dataset."""
    # If video_path is a directory of clips, cache goes in parent/cache/
    if os.path.isdir(video_path):
        parent = os.path.dirname(video_path) if os.path.basename(video_path) in ('clips', 'clips_compressed') else video_path
    else:
        parent = os.path.dirname(video_path)
    return os.path.join(parent, 'cache')

def _get_cache_path(video_path, gpx_path, frame_interval_meters):
    """Cache key includes paths and frame interval."""
    cache_dir = _get_cache_dir(video_path)
    key = f"{video_path}:{gpx_path}:{frame_interval_meters}"
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    return os.path.join(cache_dir, f'pipeline_{h}.json')

def run_pipeline(..., use_cache=True, frame_interval_meters=25, ...):
    # Check cache FIRST
    if use_cache:
        cache_path = _get_cache_path(video_path, gpx_path, frame_interval_meters)
        if os.path.exists(cache_path):
            if progress_callback:
                progress_callback(1, "Loading cached results...")
            with open(cache_path, 'r') as f:
                result = json.load(f)
            if progress_callback:
                progress_callback(7, f"Loaded from cache — {result.get('metadata', {}).get('sections_count', '?')} sections")
            return result
    
    # ... existing pipeline logic ...
    
    # Save to cache at the end (before return)
    try:
        cache_dir = _get_cache_dir(video_path)
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = _get_cache_path(video_path, gpx_path, frame_interval_meters)
        # Remove base64 image data before caching (too large, not needed for display)
        cache_result = _strip_base64_for_cache(result)
        with open(cache_path, 'w') as f:
            json.dump(cache_result, f)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")
    
    return result
```

**Important:** Strip base64 frame images from the cache — they're huge and not needed for redisplaying results. Keep everything else (geojson, interventions, summary, narrative, panel_data).

```python
def _strip_base64_for_cache(result):
    """Remove large base64 image data, keep everything else."""
    import copy
    cached = copy.deepcopy(result)
    if 'frames' in cached:
        for frame in cached['frames']:
            if 'image_base64' in frame:
                frame['image_base64'] = '[cached]'
    return cached
```

---

## CHANGE 3: Distance-Based Frame Extraction

**Problem:** Pipeline uses `frame_interval=5` (seconds) and `max_frames=20`. This is arbitrary and sends too few frames to Vision.

**Fix:** Replace time-based interval with distance-based. Extract one frame every N meters based on GPS speed. Remove the artificial max_frames cap.

**New parameter: `frame_interval_meters`** (replaces `frame_interval` and `max_frames`)

**In `video/video_pipeline.py`:**

The pipeline currently extracts frames at fixed time intervals, then caps at max_frames. Change to:

1. Extract frames at 1fps from video (already happening with CRF 23 -r 1 compression)
2. After GPS matching, calculate cumulative distance between consecutive frames
3. Select frames where cumulative distance since last selected frame exceeds `frame_interval_meters`
4. Send ALL selected frames to Vision API (no cap)

```python
def _select_frames_by_distance(matched_frames, interval_meters=25):
    """Select frames spaced by distance, not time."""
    if not matched_frames:
        return []
    
    selected = [matched_frames[0]]  # Always include first frame
    cumulative = 0
    
    for i in range(1, len(matched_frames)):
        prev = matched_frames[i-1]
        curr = matched_frames[i]
        dist = haversine(prev['lat'], prev['lon'], curr['lat'], curr['lon'])
        cumulative += dist
        
        if cumulative >= interval_meters:
            selected.append(curr)
            cumulative = 0
    
    # Always include last frame
    if selected[-1] != matched_frames[-1]:
        selected.append(matched_frames[-1])
    
    return selected
```

**In `run_pipeline()`, replace the frame selection logic:**
```python
# OLD: frames = extracted_frames[::frame_interval][:max_frames]
# NEW:
frames_for_vision = _select_frames_by_distance(gps_matched_frames, interval_meters=frame_interval_meters)
```

**Batch Vision API calls:** Send frames in batches of up to 20 images per API call for efficiency.

```python
def _batch_assess_frames(frames, batch_size=20, use_mock=False, api_key=None, progress_callback=None):
    """Assess frames in batches. Returns list of assessed frames."""
    assessed = []
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        for j, frame in enumerate(batch):
            if progress_callback:
                progress_callback(4, f"Analysing condition... (frame {i+j+1}/{len(frames)})")
            if use_mock:
                result = assess_frame_mock(frame)
            else:
                result = assess_frame(frame, api_key=api_key)
            assessed.append(result)
    return assessed
```

**Keep the old `frame_interval` and `max_frames` parameters for backward compatibility** but make `frame_interval_meters` the primary control. If `frame_interval_meters` is provided, it takes precedence.

---

## CHANGE 4: Switch Vision to Opus 4.6

**Problem:** `vision_assess.py` uses `claude-sonnet-4-5-20250929`. Judging criteria allocates 25% to "Opus 4.6 Use."

**Fix:** Change the model string in `video/vision_assess.py`:

```python
# OLD
model = "claude-sonnet-4-5-20250929"

# NEW  
model = "claude-opus-4-6"
```

Also check `agent/orchestrator.py` — the audit notes it uses Sonnet too. Change both to `claude-opus-4-6`.

---

## CHANGE 5: Auto-Populate Costs from Video Pipeline

**Problem:** Video pipeline produces per-section intervention costs in `video-condition-store`, but CBA reads `total-cost-input` which requires manual entry.

**Fix:** When video analysis completes and user navigates to Step 4 (Costs), auto-fill the cost input from intervention data.

**Add a new callback or modify existing `run_cba_callback`:**

```python
@app.callback(
    Output('total-cost-input', 'value'),
    Input('video-condition-store', 'data'),
    Input('road-data-store', 'data'),
    prevent_initial_call=True
)
def auto_populate_costs(video_data, road_data):
    """Auto-fill construction cost from video pipeline interventions."""
    if not video_data or 'interventions' not in video_data:
        raise dash.exceptions.PreventUpdate
    
    interventions = video_data['interventions']
    if 'route_summary' in interventions and 'total_cost' in interventions['route_summary']:
        return interventions['route_summary']['total_cost']
    
    raise dash.exceptions.PreventUpdate
```

Also display the per-section breakdown in Step 4 so the engineer can see WHERE the cost comes from:

```
Section 1: 1.2km paved fair → Periodic Maintenance → $180,000
Section 2: 0.8km gravel poor → DBST Upgrade → $640,000  
Section 3: 2.1km earth bad → DBST Upgrade → $1,680,000
─────────────────────────────────────────────────────────
Total: 4.1km → $2,500,000 ($609,756/km)
```

This table should appear in Step 4 when video data exists. Use `html.Table` per the UI design reference (tables over cards, DM Mono for numbers).

---

## CHANGE 6: Frame Interval User Control in Step 2

**Problem:** Frame interval is hardcoded in the callback.

**Fix:** Add a dropdown in Step 2's video pipeline section:

```python
html.Div([
    html.Label("Survey Detail", style={'fontSize': '12px', 'fontFamily': 'DM Mono'}),
    dcc.Dropdown(
        id='frame-interval-dropdown',
        options=[
            {'label': 'Rapid Assessment (50m spacing)', 'value': 50},
            {'label': 'Standard Survey (25m spacing)', 'value': 25},
            {'label': 'Detailed Survey (10m spacing)', 'value': 10},
        ],
        value=25,
        clearable=False,
        style={'fontSize': '13px'}
    ),
], style={'marginBottom': '8px'})
```

Wire this into `run_video_pipeline()` callback — read `frame-interval-dropdown.value` as a State, pass as `frame_interval_meters` to `run_pipeline()`.

---

## CHANGE 7: Pipeline Metadata in Output

**Problem:** After pipeline runs, the metadata stored doesn't include enough info for the demo narrative.

**Fix:** Ensure `run_pipeline()` returns these in `metadata`:

```python
metadata = {
    'dataset_name': os.path.basename(os.path.dirname(video_path)),
    'total_clips': len(clip_files),
    'total_frames_extracted': len(all_frames),
    'frames_sent_to_vision': len(assessed_frames),
    'frame_interval_meters': frame_interval_meters,
    'total_distance_km': total_distance_km,
    'sections_count': len(sections),
    'processing_time_seconds': time.time() - start_time,
    'model_used': 'claude-opus-4-6',
    'gpx_trackpoints': len(trackpoints),
    'timestamp': datetime.now().isoformat(),
}
```

---

## TESTING

After all changes, verify:

1. **App starts:** `venv/bin/python app.py` — no import errors
2. **Dropdown shows datasets:** Check that all valid folders in `data/videos/` appear
3. **Cache works:** Run pipeline once → verify `cache/pipeline_result.json` created → run again → should load from cache instantly
4. **Distance-based frames:** For 12.5km road at 25m interval, pipeline should select ~500 frames (not 20)
5. **Opus model:** Check that vision_assess.py and orchestrator.py use `claude-opus-4-6`
6. **Cost auto-fill:** After video analysis, navigate to Step 4 → total cost should be pre-filled
7. **Validator still passes:** `venv/bin/python -m video.test_pipeline` → 12/12

**Run the app with mock mode first** to verify all wiring works before spending API credits.

---

## PRIORITY ORDER

If time is tight, implement in this order:
1. Change 1 (auto-scan datasets) — needed to load new data
2. Change 2 (caching) — needed for fast demo iteration
3. Change 4 (Opus model) — one-line change, big judging impact
4. Change 3 (distance-based frames) — core feature improvement
5. Change 5 (auto-populate costs) — closes the video→CBA loop
6. Change 6 (frame interval dropdown) — nice UX touch
7. Change 7 (metadata) — minor polish

---

## RULES

- Do NOT restructure app.py into multiple files — no time for that refactor
- Do NOT change the 7-step wizard structure
- Do NOT modify CSS or visual styling
- Do NOT break the existing OSM-first flow (Step 1 road search must still work)
- Run the app after each change to catch regressions
- Commit after each working change
