# TARA Video Pipeline — Claude Code Build Prompt

## Context
You are building TARA (Transport Assessment & Road Appraisal), a Dash app for road appraisal in Uganda. The app has a 7-step wizard with a dash-leaflet map. We need to add **dashcam video analysis** — the user uploads a video recorded from their phone while driving a road, along with a GPX file from a GPS tracker app. TARA extracts frames, matches them to GPS coordinates, sends frames to Claude Vision for road condition assessment, and displays results on the map.

This is for the Anthropic Claude Code Hackathon. We're using Claude Opus 4.6 Vision API. The app is Python/Dash with dash-leaflet.

---

## What to Build

### Module: `video_analysis.py`

A self-contained module with the following functions:

### 1. `extract_frames(video_path, interval_seconds=5)`
- Takes an MP4 video file path and a sampling interval
- Uses OpenCV to extract frames at the given interval
- Returns a list of dicts: `[{"frame_index": 0, "timestamp_sec": 0.0, "image_path": "/tmp/tara_frames/frame_000.jpg", "image_base64": "..."}, ...]`
- Save frames as JPEGs (quality 85) to a temp directory
- Also store base64-encoded versions for API calls
- Print progress: "Extracted frame 1/N at 0:00..."

### 2. `parse_gpx(gpx_path)`
- Parses a GPX file and extracts trackpoints
- Returns a list of dicts: `[{"lat": 0.123, "lon": 32.456, "elevation": 1200, "time": datetime_obj}, ...]`
- Use `gpxpy` library (pip install gpxpy)
- Handle both single-track and multi-track GPX files

### 3. `match_frames_to_gps(frames, trackpoints, video_start_time=None)`
- Takes the frames list and trackpoints list
- If `video_start_time` is provided (datetime), use it to align video timestamps to GPS timestamps
- If not provided, assume video and GPX recording started at the same time (use the first trackpoint's time as video start)
- For each frame, find the nearest GPS trackpoint by timestamp
- Interpolate lat/lon between the two nearest trackpoints for better accuracy
- Returns the frames list with added keys: `{"lat": ..., "lon": ..., "elevation": ...}`

### 4. `assess_frame_condition(frame_base64, frame_index, anthropic_client)`
- Sends a single frame to Claude Opus 4.6 Vision API
- Uses this system prompt:

```
You are a road condition assessment expert. Analyse this dashcam frame and provide a structured assessment.

Respond ONLY with valid JSON (no markdown, no backticks):
{
  "surface_type": "paved|gravel|earth|mixed|under_construction",
  "condition_class": "good|fair|poor|bad",
  "iri_estimate_low": <number>,
  "iri_estimate_high": <number>,
  "distress_types": ["pothole", "cracking", "rutting", "edge_break", "patching", "raveling", "corrugation", "none"],
  "distress_severity": "none|low|moderate|high|severe",
  "road_width_estimate_m": <number or null>,
  "has_shoulders": <boolean>,
  "has_drainage": <boolean>,
  "has_markings": <boolean>,
  "roadside_environment": "urban|peri_urban|rural",
  "construction_activity": <boolean>,
  "notes": "<brief observation about this section, max 30 words>"
}

IRI reference ranges:
- Good paved: 2-4 m/km
- Fair paved: 4-6 m/km  
- Poor paved: 6-10 m/km
- Good gravel: 6-8 m/km
- Fair gravel: 8-12 m/km
- Poor gravel: 12-16 m/km
- Bad (any): 16+ m/km
```

- Parse the JSON response, handle errors gracefully
- Return the parsed dict with `frame_index` added
- Include retry logic (max 2 retries) for API failures

### 5. `assess_batch(frames_with_gps, anthropic_client, batch_size=3, max_frames=None)`
- Takes the geo-tagged frames list
- If `max_frames` is set, sample that many frames evenly across the video
- Process frames through `assess_frame_condition` 
- Add a short delay between calls (0.5s) to avoid rate limiting
- Print progress: "Analysing frame 3/15..."
- Returns the frames list with condition assessment added to each frame dict
- Also computes summary statistics:
  ```python
  summary = {
      "total_frames": N,
      "surface_types": {"paved": 5, "gravel": 8, ...},
      "condition_distribution": {"good": 3, "fair": 5, "poor": 4, "bad": 1},
      "average_iri_estimate": 8.5,
      "most_common_distress": ["pothole", "cracking"],
      "sections": [...]  # see below
  }
  ```

### 6. `segment_into_sections(assessed_frames, min_section_length=3)`
- Groups consecutive frames with the same `condition_class` into sections
- Each section: `{"section_id": 1, "condition_class": "poor", "start_frame": 3, "end_frame": 7, "start_lat": ..., "start_lon": ..., "end_lat": ..., "end_lon": ..., "avg_iri": 11.5, "length_km": 2.3, "distress_types": [...], "representative_frame_index": 5}`
- Estimate section length from GPS coordinates (haversine distance)
- Pick the middle frame as representative

### 7. `generate_condition_geojson(sections)`
- Converts sections to a GeoJSON FeatureCollection
- Each section is a LineString from start to end coordinates
- Properties include condition_class, avg_iri, distress_types, color
- Color mapping:
  - good → `#2d5f4a` (TARA primary green)
  - fair → `#9a6b2f` (TARA amber)
  - poor → `#c4652a` (orange)
  - bad → `#a83a2f` (TARA red)
- Returns GeoJSON dict ready for dash-leaflet `dl.GeoJSON`

### 8. `generate_ai_summary(sections, summary_stats, anthropic_client)`
- Sends the section data and summary stats to Claude Opus 4.6 (text, not vision)
- Asks it to write a 3-4 paragraph condition assessment narrative
- Prompt should ask Claude to:
  - Summarise overall condition
  - Highlight the worst sections and what's wrong
  - Estimate an overall IRI for the corridor
  - Recommend whether condition data supports upgrade/rehab investment
  - Reference specific sections by their approximate chainage/location
- Returns the narrative string

---

## Dependencies
```
opencv-python
gpxpy
anthropic
```

Install with: `pip install opencv-python gpxpy anthropic --break-system-packages`

---

## File Structure
```
video_analysis.py          # The module above
test_video_pipeline.py     # Test script (see below)
```

## Test Script: `test_video_pipeline.py`

Create a test script that:
1. Generates a **synthetic test video** (10 seconds, 30fps) using OpenCV — just colored frames with text overlays saying "Frame at 0s", "Frame at 5s", etc. Alternate colors (green frames, then yellow, then red) to simulate condition changes.
2. Generates a **synthetic GPX file** — a straight line of trackpoints along a known Uganda road (e.g., from lat 0.391, lon 32.600 to lat 0.410, lon 32.580), one trackpoint per second for 10 seconds.
3. Runs `extract_frames` on the synthetic video
4. Runs `parse_gpx` on the synthetic GPX
5. Runs `match_frames_to_gps`
6. **Skips** the Claude Vision API call (mock it — return plausible hardcoded JSON)
7. Runs `segment_into_sections`
8. Runs `generate_condition_geojson`
9. Saves the GeoJSON to `test_output/test_condition.geojson`
10. Prints a summary of what was processed

This lets us validate the entire pipeline end-to-end WITHOUT needing real video or API access.

---

## Important Notes

- **No network calls needed for the test** — mock the API responses
- Use the Anthropic Python SDK (`from anthropic import Anthropic`) for real API calls
- All file paths should use `os.path` for cross-platform compatibility
- Frame extraction should handle videos of any resolution — resize frames to max 1280px wide before sending to Vision API (saves tokens)
- The module should be importable: `from video_analysis import extract_frames, parse_gpx, ...`
- Add docstrings to all functions
- Print informative progress messages (this will run in a terminal)

---

## How This Fits Into TARA

This module will later be wired into Step 2 (Condition Assessment) of the Dash wizard:
- User uploads video + GPX file via `dcc.Upload`
- Dash callback calls these functions
- Results displayed as:
  - Color-coded `dl.GeoJSON` overlay on the map (condition segments)
  - AI narrative in the analysis panel (typing animation)
  - Condition summary table in left panel
  - Frame gallery (stretch goal — annotated frames with defect highlights)

But for now, just build the standalone module and test script. We'll integrate into Dash later.
