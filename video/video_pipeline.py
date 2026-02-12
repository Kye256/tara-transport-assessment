"""TARA dashcam video analysis pipeline — orchestrator."""

import json
import os
import time

from video.video_frames import extract_frames
from video.gps_utils import parse_gpx, match_frames_to_gps, haversine
from video.vision_assess import assess_road
from video.video_map import (
    frames_to_geojson,
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
        video_path: path to MP4 file
        gpx_path: path to GPX file
        video_start_time: "2026-02-12 14:18:00" (local time, optional)
        frame_interval: seconds between frame samples
        max_frames: cap on frames to send to Vision API
        use_mock: if True, skip real API calls
        api_key: Anthropic API key (reads from env if not provided)

    Returns dict with frames, summary, geojson, narrative, metadata.
    """
    t0 = time.time()

    print("\n[TARA Video Pipeline]")
    print("\u2500" * 21)

    # --- Stage 1: Extract frames ---
    print("Stage 1/5: Extracting frames...")
    frames = extract_frames(video_path, interval_seconds=frame_interval)
    duration_min = frames[-1]["timestamp_sec"] / 60 if frames else 0
    print(f"  \u2192 Extracted {len(frames)} frames (every {frame_interval}s from {duration_min:.1f} min video)")

    # --- Stage 2: Parse GPS ---
    print("Stage 2/5: Parsing GPS track...")
    trackpoints = parse_gpx(gpx_path)
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
    geojson = frames_to_geojson(assessed_frames)
    print(f"  \u2192 GeoJSON with {len(geojson['features'])} features")

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

    return {
        "frames": assessed_frames,
        "summary": summary,
        "geojson": geojson,
        "narrative": narrative,
        "metadata": {
            "video_file": os.path.basename(video_path),
            "gpx_file": os.path.basename(gpx_path),
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

    # Use first available MP4 and GPX
    mp4s = sorted([f for f in os.listdir(video_dir) if f.endswith(".MP4")])
    gpxs = sorted([f for f in os.listdir(video_dir) if f.endswith(".gpx")])

    if not mp4s or not gpxs:
        print("No MP4 or GPX files found in data/videos/")
        sys.exit(1)

    video_path = os.path.join(video_dir, mp4s[0])
    gpx_path = os.path.join(video_dir, gpxs[0])

    print(f"Video: {mp4s[0]}")
    print(f"GPX:   {gpxs[0]}")

    result = run_pipeline(
        video_path=video_path,
        gpx_path=gpx_path,
        video_start_time="2026-02-12 14:41:38",
        use_mock=True,
    )
    print(f"\nSummary: {json.dumps(result['summary'], indent=2)}")
