"""TARA dashcam video analysis pipeline — orchestrator."""

import json
import os
import time

from video.video_frames import extract_frames, extract_start_time_from_filename
from video.gps_utils import parse_gpx_folder, match_frames_to_gps, haversine
from video.vision_assess import assess_road
from video.video_map import (
    frames_to_geojson,
    frames_to_condition_geojson,
    build_condition_summary_panel,
    generate_condition_narrative,
    generate_condition_narrative_mock,
)


def run_pipeline(
    video_path: str,
    gpx_path: str,
    video_start_time: str = None,
    frame_interval: int = 5,
    max_frames: int = 20,
    use_mock: bool = False,
    api_key: str = None,
) -> dict:
    """Run the full dashcam analysis pipeline.

    Args:
        video_path: path to MP4 file OR directory of MP4 clips.
        gpx_path: path to GPX file OR directory of GPX files.
        video_start_time: "2026-02-12 14:18:00" (local time, optional).
            Auto-detected from first clip filename if not provided.
        frame_interval: seconds between frame samples
        max_frames: cap on frames to send to Vision API
        use_mock: if True, skip real API calls
        api_key: Anthropic API key (reads from env if not provided)

    Returns dict with frames, summary, geojson, narrative, metadata.
    """
    t0 = time.time()
    is_dir = os.path.isdir(video_path)

    print("\n[TARA Video Pipeline]")
    print("\u2500" * 21)
    if is_dir:
        mp4_count = len([f for f in os.listdir(video_path) if f.lower().endswith((".mp4", ".avi", ".mov"))])
        print(f"Mode: Multi-clip ({mp4_count} files)")
    else:
        print(f"Mode: Single file")

    # --- Stage 1: Extract frames ---
    print("Stage 1/5: Extracting frames...")
    frames = extract_frames(video_path, interval_seconds=frame_interval)
    if frames:
        duration_min = frames[-1]["timestamp_sec"] / 60
    else:
        duration_min = 0
    clip_count = len(set(f.get("clip_filename", "") for f in frames))
    print(f"  \u2192 Extracted {len(frames)} frames from {clip_count} clip(s) "
          f"(every {frame_interval}s, {duration_min:.1f} min total)")

    # --- Stage 2: Parse GPS ---
    print("Stage 2/5: Parsing GPS track...")
    trackpoints = parse_gpx_folder(gpx_path)
    total_dist_m = 0.0
    for i in range(1, len(trackpoints)):
        total_dist_m += haversine(
            trackpoints[i - 1]["lat"], trackpoints[i - 1]["lon"],
            trackpoints[i]["lat"], trackpoints[i]["lon"],
        )
    total_dist_km = total_dist_m / 1000
    tp_duration = 0.0
    if len(trackpoints) >= 2 and trackpoints[0]["time"] and trackpoints[-1]["time"]:
        tp_duration = (trackpoints[-1]["time"] - trackpoints[0]["time"]).total_seconds() / 60
    print(f"  \u2192 {len(trackpoints)} trackpoints over {tp_duration:.1f} minutes, {total_dist_km:.2f} km")

    # --- Stage 3: Match frames to GPS ---
    print("Stage 3/5: Matching frames to GPS...")

    # Auto-detect video_start_time from first clip filename if not provided
    if video_start_time is None and frames:
        first_clip = frames[0].get("clip_filename", "")
        auto_time = extract_start_time_from_filename(first_clip)
        if auto_time:
            video_start_time = auto_time
            print(f"  Auto-detected start time from filename: {video_start_time}")

    # For multi-clip, match per-clip using each clip's own start time
    clips = {}
    for f in frames:
        clips.setdefault(f.get("clip_filename", ""), []).append(f)

    if len(clips) > 1:
        # Per-clip GPS matching
        for clip_filename, clip_frames in clips.items():
            clip_start = clip_frames[0].get("video_start_time")
            if clip_start is None:
                clip_start = video_start_time
            # Temporarily reset timestamps to clip-local for matching
            original_ts = [f["timestamp_sec"] for f in clip_frames]
            base_ts = clip_frames[0]["timestamp_sec"]
            for f in clip_frames:
                f["timestamp_sec"] = f["timestamp_sec"] - base_ts
            match_frames_to_gps(clip_frames, trackpoints, video_start_time=clip_start)
            # Restore cumulative timestamps
            for f, orig_ts in zip(clip_frames, original_ts):
                f["timestamp_sec"] = orig_ts
    else:
        # Single clip — use the standard matching
        frames = match_frames_to_gps(frames, trackpoints, video_start_time=video_start_time)

    geo_count = sum(1 for f in frames if f.get("lat") is not None)
    print(f"  \u2192 {geo_count} frames geo-tagged")

    # --- Stage 4: Assess road condition ---
    print("Stage 4/5: Analysing road condition...")
    anthropic_client = None
    if not use_mock:
        from anthropic import Anthropic
        anthropic_client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    result = assess_road(
        frames,
        anthropic_client=anthropic_client,
        max_frames=max_frames,
        use_mock=use_mock,
    )
    assessed_frames = result["frames"]
    summary = result["summary"]

    # --- Stage 5: Generate outputs ---
    print("Stage 5/5: Generating outputs...")
    geojson = frames_to_condition_geojson(assessed_frames)
    print(f"  \u2192 GeoJSON with {len(geojson['features'])} sections")
    point_geojson = frames_to_geojson(assessed_frames)
    panel_data = build_condition_summary_panel(summary, total_distance_km=total_dist_km)

    if use_mock:
        narrative = generate_condition_narrative_mock(summary)
    else:
        narrative = generate_condition_narrative(summary, anthropic_client)
    print("  \u2192 Condition narrative generated")

    # Save outputs
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "condition.geojson"), "w") as f:
        json.dump(geojson, f, indent=2)
    with open(os.path.join(output_dir, "narrative.md"), "w") as f:
        f.write(narrative)
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n\u2713 Pipeline complete in {elapsed:.1f}s")

    # Build metadata
    if is_dir:
        video_label = f"{clip_count} clips"
    else:
        video_label = os.path.basename(video_path)

    gpx_label = os.path.basename(gpx_path)

    return {
        "frames": assessed_frames,
        "summary": summary,
        "geojson": geojson,
        "point_geojson": point_geojson,
        "narrative": narrative,
        "panel_data": panel_data,
        "metadata": {
            "video_file": video_label,
            "gpx_file": gpx_label,
            "total_clips": clip_count,
            "total_frames_extracted": len(frames),
            "frames_assessed": summary["total_frames_assessed"],
            "total_distance_km": round(total_dist_km, 2),
            "processing_time_sec": round(elapsed, 1),
        },
    }


if __name__ == "__main__":
    import sys

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    video_dir = os.path.join(base, "data", "videos")

    # Check if directory has MP4s, otherwise fall back to single file
    if os.path.isdir(video_dir):
        mp4s = sorted(f for f in os.listdir(video_dir) if f.lower().endswith(".mp4"))
        gpxs = sorted(f for f in os.listdir(video_dir) if f.lower().endswith(".gpx"))
    else:
        mp4s, gpxs = [], []

    if not mp4s or not gpxs:
        print("No MP4 or GPX files found in data/videos/")
        sys.exit(1)

    # If multiple MP4s, pass directory; if single, pass file
    if len(mp4s) > 1:
        video_path = video_dir
    else:
        video_path = os.path.join(video_dir, mp4s[0])

    if len(gpxs) > 1:
        gpx_path = video_dir
    else:
        gpx_path = os.path.join(video_dir, gpxs[0])

    print(f"Video: {video_path}")
    print(f"GPX:   {gpx_path}")

    result = run_pipeline(
        video_path=video_path,
        gpx_path=gpx_path,
        use_mock=True,
    )
    print(f"\nSummary: {json.dumps(result['summary'], indent=2)}")
