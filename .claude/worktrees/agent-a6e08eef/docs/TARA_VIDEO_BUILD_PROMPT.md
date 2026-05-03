# TARA Dashcam Video Pipeline — Build Prompt
## Orchestrator Instructions for Claude Code

---

## CONTEXT

You are building the **dashcam video analysis pipeline** for TARA (Transport Assessment & Road Appraisal), a Dash web app for road appraisal in Uganda. TARA is being built for the Anthropic Claude Code Hackathon (deadline: Monday Feb 16, 3PM EST).

The app is a 7-step Dash wizard with a dash-leaflet map. The codebase is ~7,000 lines across ~16 Python files. The video pipeline is a **new module** that will integrate into Step 2 (Condition Assessment).

**CRITICAL PRINCIPLES:**
- **Lean code.** No bloat. Every function earns its place.
- **End-to-end first.** Get the full pipeline working with the simplest possible implementation, then improve.
- **Modular.** The video module must work standalone AND integrate into the Dash app.
- **Test with real data.** We have actual dashcam footage (MP4) and GPX files from today's drive in the Kira-Kasangati area, Wakiso District, Uganda.

---

## ARCHITECTURE — SUB-AGENT TASKS

Delegate these as **separate sub-agent tasks**. Each agent works on its own file(s). No file conflicts.

### Sub-Agent 1: Frame Extraction (`video_frames.py`)

**Scope:** Extract frames from a folder of dashcam video clips at a configurable interval.

**Context:** The Yesido dashcam saves 1-minute clips (~95MB each) with filenames like `2026_02_12_HHMMSS_00.MP4`. A typical drive produces 15-20 clips. We process them as one continuous video.

**Build this:**
```python
def extract_frames(video_dir: str, interval_seconds: int = 5, output_dir: str = None, max_width: int = 1280) -> list[dict]:
    """
    Extract frames from all MP4 clips in a directory at interval.
    
    Clips are processed in filename order (filenames contain timestamps,
    e.g., 2026_02_12_144138_00.MP4, so alphabetical = chronological).
    
    Treats all clips as one continuous video — frame timestamps are 
    cumulative across clips.
    
    Args:
        video_dir: path to folder containing MP4 clips
        interval_seconds: seconds between frame samples
        output_dir: where to save extracted frames (default: /tmp/tara_frames/)
        max_width: resize frames to this width (preserves aspect ratio)
    
    Returns: [
        {
            "frame_index": 0,
            "timestamp_sec": 0.0,
            "clip_filename": "2026_02_12_144138_00.MP4",
            "clip_timestamp": "14:41:38",
            "image_path": "/tmp/tara_frames/frame_000.jpg",
            "image_base64": "...",
        },
        ...
    ]
    """
```

**Requirements:**
- Use OpenCV (`cv2`)
- Find all `.MP4` and `.mp4` files in `video_dir`, sort alphabetically (= chronological)
- Process clips sequentially — cumulative timestamp tracks position across all clips
- Extract clip start time from filename pattern: `2026_02_12_HHMMSS_00.MP4` → parse HHMMSS
- Resize frames to `max_width` (preserve aspect ratio) before saving
- Save as JPEG quality 85
- Store base64 version in the dict (used later for Vision API)
- Default output_dir: `/tmp/tara_frames/` (create if not exists, clear old frames first)
- Print progress: `"[Clip 3/18] Extracted frame 5 at 2:35 (cumulative)"`
- Handle errors (corrupt clip, missing dir) gracefully — skip bad clips, continue
- Also support single file: if `video_dir` points to a file instead of a directory, process just that file

**Dependencies:** `opencv-python` (install with `pip install opencv-python --break-system-packages`)

---

### Sub-Agent 2: GPX Parser & GPS Matching (`gps_utils.py`)

**Scope:** Parse a folder of GPX files and match video frames to GPS coordinates.

**Context:** Open GPX Tracker may produce multiple GPX files for one drive (user stops/starts recording). We combine all trackpoints in chronological order.

**Build this:**
```python
def parse_gpx_folder(gpx_dir: str) -> list[dict]:
    """
    Parse all GPX files in a directory, combine trackpoints in chronological order.
    
    If gpx_dir is a file path instead of directory, parse just that file.
    
    Returns: [
        {"lat": 0.367, "lon": 32.625, "elevation": 1215.0, "time": datetime_obj},
        ...
    ]
    Sorted by time.
    """

def parse_gpx(gpx_path: str) -> list[dict]:
    """
    Parse a single GPX file, extract trackpoints.
    
    Returns: [
        {"lat": 0.367, "lon": 32.625, "elevation": 1215.0, "time": datetime_obj},
        ...
    ]
    """

def match_frames_to_gps(frames: list[dict], trackpoints: list[dict], 
                          video_start_time: str = None,
                          utc_offset_hours: int = 3) -> list[dict]:
    """
    Match each frame to a GPS coordinate by timestamp.
    
    Args:
        frames: output from extract_frames()
        trackpoints: output from parse_gpx()
        video_start_time: dashcam timestamp string "2026-02-12 14:18:00" (local time)
                         If None, use first trackpoint time + utc_offset as start
        utc_offset_hours: local timezone offset from UTC (Uganda = 3)
    
    Returns: frames list with added keys: lat, lon, elevation
    """
```

**Requirements:**
- Parse GPX using `xml.etree.ElementTree` (stdlib — NO external dependencies needed, do not use gpxpy)
- Handle GPX namespace (`{http://www.topografix.com/GPX/1/1}`)
- `match_frames_to_gps`: for each frame, calculate its absolute time = video_start_time + timestamp_sec, then find the nearest GPX trackpoint by time. Linear interpolate lat/lon between the two nearest points.
- The dashcam records in local time (UTC+3), GPX stores UTC. The function must handle this offset.
- Include a `haversine(lat1, lon1, lat2, lon2)` helper that returns distance in metres.

**Test with our actual GPX files:**
- `12-Feb-2026-1418.gpx` (Track 1: 98 points, 17 min, ~4.66 km)
- `12-Feb-2026-1537.gpx` (Track 2: 895 points, 79 min, ~8.35 km)
- GPX start times are UTC. Dashcam timestamps are UTC+3.

---

### Sub-Agent 3: Claude Vision Assessment (`vision_assess.py`)

**Scope:** Send frames to Claude Opus 4.6 Vision API and get structured road condition assessments.

**Build this:**
```python
def assess_frame(image_base64: str, anthropic_client, model: str = "claude-opus-4-6-20250204") -> dict:
    """
    Send one frame to Claude Vision, get condition assessment.
    
    Returns: {
        "surface_type": "paved|gravel|earth|mixed|under_construction",
        "condition_class": "good|fair|poor|bad",
        "iri_estimate": 8.5,  # single midpoint estimate
        "distress_types": ["pothole", "cracking"],
        "distress_severity": "moderate",
        "roadside_environment": "peri_urban",
        "notes": "Laterite surface with moderate potholing..."
    }
    """

def assess_road(frames_with_gps: list[dict], anthropic_client, 
                 max_frames: int = None, delay: float = 1.0) -> dict:
    """
    Assess all (or sampled) frames. Returns results dict.
    
    Args:
        frames_with_gps: output from match_frames_to_gps()
        max_frames: if set, evenly sample this many frames
        delay: seconds between API calls (rate limiting)
    
    Returns: {
        "frames": [...],  # each frame dict now has "assessment" key
        "summary": {
            "total_frames_assessed": 12,
            "condition_distribution": {"good": 2, "fair": 4, "poor": 5, "bad": 1},
            "average_iri": 9.3,
            "dominant_surface": "gravel",
            "dominant_condition": "poor",
            "distress_types_found": ["pothole", "cracking", "edge_break"]
        }
    }
    """
```

**The Vision prompt (use exactly this):**
```
You are a road condition assessment expert analysing dashcam footage from Uganda.

Look at this road image and assess the visible road condition. Respond ONLY with valid JSON, no markdown, no backticks, no explanation:

{"surface_type":"paved or gravel or earth or mixed or under_construction","condition_class":"good or fair or poor or bad","iri_estimate":8.5,"distress_types":["list","of","visible","issues"],"distress_severity":"none or low or moderate or high or severe","roadside_environment":"urban or peri_urban or rural","notes":"One sentence observation max 20 words"}

Valid distress_types: pothole, cracking, rutting, edge_break, patching, raveling, corrugation, erosion, none
IRI ranges: good paved 2-4, fair paved 4-6, poor paved 6-10, good gravel 6-8, fair gravel 8-12, poor gravel 12-16, bad any 16+
```

**Requirements:**
- Use `from anthropic import Anthropic` 
- Parse JSON response. If parsing fails, retry once. If still fails, return a default "error" dict — do NOT crash.
- `assess_road` prints progress: `"Assessing frame 3/12... [poor, IRI ~11]"`
- If `max_frames` is set, sample evenly (e.g., 20 frames from 60 = every 3rd frame)
- Respect the delay between calls

**For development/testing without API:** Include a mock mode:
```python
def assess_frame_mock(image_base64: str) -> dict:
    """Return random plausible assessment for testing without API."""
```

---

### Sub-Agent 4: Map Output & Integration (`video_map.py`)

**Scope:** Convert assessed frames to map-ready GeoJSON for dash-leaflet, with popup interaction.

**Build this:**
```python
def frames_to_condition_geojson(assessed_frames: list[dict]) -> dict:
    """
    Convert assessed frames into color-coded LineString sections for the map.
    
    Logic:
    1. Group consecutive frames with the same condition_class into sections
    2. Each section becomes a GeoJSON LineString (start coord → end coord)
    3. If only one frame in a section, make a very short LineString 
       (duplicate the point with tiny offset)
    
    Color mapping:
        good  → #2d5f4a  (TARA green)
        fair  → #9a6b2f  (TARA amber) 
        poor  → #c4652a  (orange)
        bad   → #a83a2f  (TARA red)
    
    Each feature's properties:
        condition_class, color, weight (line thickness: 6px),
        avg_iri, surface_type, distress_types (joined as string),
        notes, section_index,
        frame_indices (list of frame indices in this section),
        representative_frame_index (middle frame of the section),
        popup_html (pre-built HTML string for dl.Popup — see below)
    
    Returns: GeoJSON FeatureCollection dict
    """

def build_popup_html(frame: dict) -> str:
    """
    Build HTML string for a dash-leaflet popup when user clicks a section.
    
    The popup shows:
    - Dashcam frame thumbnail (base64 img tag, max 300px wide)
    - Condition badge (colored pill: green/amber/orange/red)
    - Key stats: surface type, IRI estimate, distress types
    - Claude's notes
    
    Example output:
    <div style="font-family: 'Source Sans 3', sans-serif; max-width: 320px;">
      <img src="data:image/jpeg;base64,..." style="width:300px; border-radius:3px;" />
      <div style="margin-top:8px;">
        <span style="background:#a83a2f; color:white; padding:2px 8px; 
              border-radius:2px; font-size:11px; font-weight:600;">POOR</span>
        <span style="color:#5c5950; font-size:12px; margin-left:8px;">IRI ~12 m/km</span>
      </div>
      <div style="font-size:12px; color:#2c2a26; margin-top:6px;">
        Gravel surface · Pothole, edge break
      </div>
      <div style="font-size:11px; color:#8a8578; margin-top:4px;">
        Laterite surface with moderate potholing, no drainage visible
      </div>
    </div>
    
    Returns: HTML string
    """

def generate_condition_narrative(summary: dict, anthropic_client, use_mock: bool = False) -> str:
    """
    Send summary stats to Claude, get a 2-3 paragraph condition narrative.
    This is displayed in TARA's AI analysis panel with typing animation.
    
    Returns: narrative string
    """

def build_condition_summary_panel(summary: dict) -> dict:
    """
    Build the data needed for the left panel condition display.
    
    Returns: {
        "total_distance_km": 4.66,
        "average_iri": 9.3,
        "dominant_surface": "gravel",
        "dominant_condition": "poor",
        "condition_percentages": {"good": 15, "fair": 25, "poor": 45, "bad": 15},
        "key_issues": ["pothole", "edge_break", "erosion"],
        "worst_section_notes": "Section 3 near km 2.5 shows severe..."
    }
    """
```

**Map interaction (how it works in dash-leaflet):**
- The GeoJSON is rendered as `dl.GeoJSON` with `style` function reading `color` and `weight` from feature properties
- Each LineString feature has a `dl.Popup` child containing the `popup_html`
- User clicks a colored section → popup appears with dashcam frame + assessment
- No server callback needed for the popup — it's all in the GeoJSON properties

**Left panel after processing shows:**
- Condition bar: horizontal stacked bar (div with colored segments proportional to %)
- Stats table: distance, avg IRI, surface, key issues
- AI narrative with typing animation (existing pattern from the app)
- "Use for CBA →" button to proceed to Step 3

**Design rules (from TARA UI spec):**
- Border radius: 3px max
- Colors: use the TARA palette (see color mapping above)
- Typography: Source Sans 3 for text, DM Mono for data/numbers
- Tables over cards for data display
- Data attribution: 8-9px mono below tables

---

### Sub-Agent 5: Pipeline Runner (`video_pipeline.py`)

**Scope:** Wire everything together into a single entry point.

**Build this:**
```python
def run_pipeline(video_dir: str, gpx_dir: str, 
                  video_start_time: str = None,
                  frame_interval: int = 5,
                  max_frames: int = 20,
                  use_mock: bool = False,
                  api_key: str = None) -> dict:
    """
    Run the full dashcam analysis pipeline.
    
    Args:
        video_dir: path to folder of MP4 clips (or single MP4 file)
        gpx_dir: path to folder of GPX files (or single GPX file)
        video_start_time: "2026-02-12 14:18:00" (local time, optional — 
                         auto-detected from first clip filename if not provided)
        frame_interval: seconds between frame samples
        max_frames: cap on frames to send to Vision API
        use_mock: if True, skip real API calls (for testing)
        api_key: Anthropic API key (reads from env if not provided)
    
    Returns: {
        "frames": [...],          # all frame data with GPS + assessments
        "summary": {...},         # condition statistics
        "geojson": {...},         # map-ready GeoJSON with LineString sections + popup HTML
        "narrative": "...",       # AI condition narrative (for typing animation)
        "panel_data": {...},      # pre-built data for left panel (from build_condition_summary_panel)
        "metadata": {
            "video_file": "...",
            "gpx_file": "...",
            "total_frames_extracted": 48,
            "frames_assessed": 20,
            "total_distance_km": 4.66,
            "processing_time_sec": 45.2
        }
    }
    """
```

**Requirements:**
- Import from the other 4 modules
- Time the full pipeline run
- Calculate total distance from GPS points
- Print clear progress through each stage:
  ```
  [TARA Video Pipeline]
  ─────────────────────
  Stage 1/5: Extracting frames...
    → Extracted 48 frames (every 5s from 4:02 video)
  Stage 2/5: Parsing GPS track...
    → 98 trackpoints over 17.3 minutes, 4.66 km
  Stage 3/5: Matching frames to GPS...
    → 48 frames geo-tagged
  Stage 4/5: Analysing road condition...
    → Assessing frame 1/20... [fair, IRI ~7]
    → Assessing frame 2/20... [poor, IRI ~11]
    ...
  Stage 5/5: Generating outputs...
    → GeoJSON with 20 features
    → Condition narrative generated
  
  ✓ Pipeline complete in 42.3s
  ```
- Save outputs to `output/` directory:
  - `output/condition.geojson`
  - `output/narrative.md`
  - `output/summary.json`

**Test script at the bottom of the file:**
```python
if __name__ == "__main__":
    # Run with mock mode for testing
    result = run_pipeline(
        video_dir="data/dashcam/",      # folder of MP4 clips
        gpx_dir="data/gpx/",            # folder of GPX files
        use_mock=True
    )
    print(f"\nResults: {result['summary']}")
```

---

## FILE STRUCTURE

```
video/
├── video_frames.py      # Sub-Agent 1: frame extraction from clip folder
├── gps_utils.py         # Sub-Agent 2: GPX folder parsing & matching  
├── vision_assess.py     # Sub-Agent 3: Claude Vision calls
├── video_map.py         # Sub-Agent 4: GeoJSON & narrative output
├── video_pipeline.py    # Sub-Agent 5: orchestrator / entry point
└── __init__.py          # exports run_pipeline

data/
├── dashcam/             # User puts MP4 clips here (gitignored)
│   ├── 2026_02_12_144138_00.MP4
│   ├── 2026_02_12_144238_00.MP4
│   └── ...
└── gpx/                 # User puts GPX files here (gitignored)
    ├── 12-Feb-2026-1418.gpx
    └── 12-Feb-2026-1537.gpx
```

All video-related code lives in the `video/` directory. Data folders are gitignored (large video files). Add `data/dashcam/` and `data/gpx/` to `.gitignore`.

---

## BUILD ORDER

1. **First pass: Get end-to-end working in mock mode.** No API calls. Synthetic/mock data where needed. Verify the pipeline runs from video → frames → GPS match → mock assessments → GeoJSON → mock narrative.

2. **Second pass: Wire up real Claude Vision API.** Replace mocks with actual API calls. Test on a few frames from the real dashcam footage.

3. **Third pass (later): Integrate into Dash app.** Wire into Step 2 with `dcc.Upload` for video/GPX files and display results on map. This is NOT part of this prompt — we'll do it separately.

---

## DEPENDENCIES

Only these. Nothing else:
```
opencv-python    # frame extraction
anthropic        # Claude Vision API (already in project)
```

Install: `pip install opencv-python --break-system-packages`

Do NOT add: gpxpy, pillow, numpy (unless already in project). Keep it minimal.

---

## WHAT SUCCESS LOOKS LIKE

After this build, we can run:
```bash
python video/video_pipeline.py
```

And get:
- Frames extracted from the dashcam video
- Each frame matched to a GPS coordinate from the GPX file
- Each frame assessed for road condition (mock or real API)
- A GeoJSON file with color-coded condition points
- A narrative summary of the road condition

That's the foundation. Everything else (section segmentation, annotated frames, Dash integration) builds on top of this.

---

## REMINDERS

- Uganda timezone is UTC+3. GPX stores UTC. Dashcam timestamps are local time.
- Our GPX files: `12-Feb-2026-1418.gpx` and `12-Feb-2026-1537.gpx` (in `data/gpx/`)
- Dashcam clips are 1-minute each, ~95MB, filename pattern: `2026_02_12_HHMMSS_00.MP4` (in `data/dashcam/`)
- The Yesido dashcam watermarks timestamp in bottom-left of frames: `2026-02-12 14:48:45`
- Video start time can be auto-detected from first clip filename (parse HHMMSS)
- Use `xml.etree.ElementTree` for GPX parsing (stdlib, no extra dependency)
- Frames should be resized to max 1280px wide before base64 encoding (saves tokens)
- Claude Vision API: same endpoint as regular messages, just include image content block
- Model string: `claude-opus-4-6-20250204`
- Add `data/dashcam/` and `data/gpx/` to `.gitignore`
- Keep functions short. Keep files short. No god-objects. No over-engineering.
