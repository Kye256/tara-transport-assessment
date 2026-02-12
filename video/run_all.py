"""Batch runner: process all dashcam clips into a single combined assessment."""

import json
import os
import time

from video.video_frames import extract_frames
from video.gps_utils import parse_gpx, match_frames_to_gps, haversine
from video.vision_assess import assess_road
from video.video_map import (
    frames_to_geojson,
    generate_condition_narrative,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(BASE, "data", "videos")
OUTPUT_DIR = os.path.join(BASE, "output")


def extract_start_time(filename: str) -> str:
    """Extract local start time from dashcam filename like 2026_02_12_144138_00.MP4."""
    ts = filename[11:17]  # HHMMSS
    return f"2026-02-12 {ts[:2]}:{ts[2:4]}:{ts[4:6]}"


def run_all(
    gpx_path: str = None,
    frame_interval: int = 10,
    max_frames: int = 40,
    use_mock: bool = False,
) -> dict:
    """Process all MP4 clips against a single GPX track."""
    t0 = time.time()

    if gpx_path is None:
        gpx_path = os.path.join(VIDEO_DIR, "12-Feb-2026-1537.gpx")

    mp4s = sorted(f for f in os.listdir(VIDEO_DIR) if f.endswith(".MP4"))

    print(f"\n[TARA Video Pipeline — Batch Mode]")
    print("=" * 35)
    print(f"Videos: {len(mp4s)} clips")
    print(f"GPX:    {os.path.basename(gpx_path)}")
    print(f"Frame interval: {frame_interval}s, max assessed: {max_frames}")
    print()

    # Stage 1: Extract frames from all clips
    print("Stage 1/5: Extracting frames from all clips...")
    all_frames = []
    for i, mp4 in enumerate(mp4s):
        video_path = os.path.join(VIDEO_DIR, mp4)
        start_time = extract_start_time(mp4)
        frames = extract_frames(
            video_path,
            interval_seconds=frame_interval,
            output_dir=f"/tmp/tara_frames/clip_{i:02d}",
        )
        # Tag each frame with its absolute start time for GPS matching
        for f in frames:
            f["video_file"] = mp4
            f["video_start_time"] = start_time
            # Compute absolute timestamp_sec from first clip's start
            # We'll handle this via per-clip GPS matching
        all_frames.extend(frames)
        print(f"  [{i+1}/{len(mp4s)}] {mp4}: {len(frames)} frames (start {start_time})")

    print(f"  → Total: {len(all_frames)} frames from {len(mp4s)} clips")

    # Stage 2: Parse GPS
    print("\nStage 2/5: Parsing GPS track...")
    trackpoints = parse_gpx(gpx_path)
    total_dist_m = sum(
        haversine(trackpoints[i-1]["lat"], trackpoints[i-1]["lon"],
                  trackpoints[i]["lat"], trackpoints[i]["lon"])
        for i in range(1, len(trackpoints))
    )
    total_dist_km = total_dist_m / 1000
    tp_dur = 0.0
    if len(trackpoints) >= 2 and trackpoints[0]["time"] and trackpoints[-1]["time"]:
        tp_dur = (trackpoints[-1]["time"] - trackpoints[0]["time"]).total_seconds() / 60
    print(f"  → {len(trackpoints)} trackpoints over {tp_dur:.1f} min, {total_dist_km:.2f} km")

    # Stage 3: GPS-match frames per clip
    print("\nStage 3/5: Matching frames to GPS...")
    # Group by video file and match each clip separately
    clips = {}
    for f in all_frames:
        clips.setdefault(f["video_file"], []).append(f)

    for video_file, clip_frames in clips.items():
        start_time = clip_frames[0]["video_start_time"]
        match_frames_to_gps(clip_frames, trackpoints, video_start_time=start_time)

    geo_count = sum(1 for f in all_frames if f.get("lat") is not None)
    print(f"  → {geo_count} frames geo-tagged")

    # Stage 4: Assess road condition
    print(f"\nStage 4/5: Analysing road condition ({max_frames} frames)...")
    anthropic_client = None
    if not use_mock:
        from anthropic import Anthropic
        anthropic_client = Anthropic()

    result = assess_road(
        all_frames,
        anthropic_client=anthropic_client,
        max_frames=max_frames,
        use_mock=use_mock,
        delay=0.5,
    )
    assessed_frames = result["frames"]
    summary = result["summary"]

    # Stage 5: Generate outputs
    print("\nStage 5/5: Generating outputs...")
    geojson = frames_to_geojson(assessed_frames)
    print(f"  → GeoJSON with {len(geojson['features'])} features")

    if use_mock:
        from video.video_map import generate_condition_narrative_mock
        narrative = generate_condition_narrative_mock(summary)
    else:
        narrative = generate_condition_narrative(summary, anthropic_client)
    print("  → Condition narrative generated")

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "condition.geojson"), "w") as f:
        json.dump(geojson, f, indent=2)
    with open(os.path.join(OUTPUT_DIR, "narrative.md"), "w") as f:
        f.write(narrative)
    with open(os.path.join(OUTPUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n✓ Pipeline complete in {elapsed:.1f}s")

    return {
        "frames": assessed_frames,
        "summary": summary,
        "geojson": geojson,
        "narrative": narrative,
        "metadata": {
            "video_files": len(mp4s),
            "gpx_file": os.path.basename(gpx_path),
            "total_frames_extracted": len(all_frames),
            "frames_assessed": summary["total_frames_assessed"],
            "total_distance_km": round(total_dist_km, 2),
            "processing_time_sec": round(elapsed, 1),
        },
    }


if __name__ == "__main__":
    result = run_all(use_mock=False, frame_interval=10, max_frames=40)
    print(f"\n--- SUMMARY ---")
    print(json.dumps(result["summary"], indent=2))
    print(f"\n--- METADATA ---")
    print(json.dumps(result["metadata"], indent=2))
    print(f"\n--- NARRATIVE ---")
    print(result["narrative"])
