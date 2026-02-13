"""TARA dashcam video analysis pipeline — orchestrator."""

import copy
import hashlib
import json
import os
import time
from datetime import datetime

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
from video.intervention import recommend_interventions_for_route


# ── Cache helpers ──────────────────────────────────────────────────


def _get_cache_dir(video_path: str) -> str:
    """Get cache directory for a video dataset."""
    if os.path.isdir(video_path):
        basename = os.path.basename(video_path)
        if basename in ("clips", "clips_compressed"):
            parent = os.path.dirname(video_path)
        else:
            parent = video_path
    else:
        parent = os.path.dirname(video_path)
    return os.path.join(parent, "cache")


def _get_cache_path(video_path: str, gpx_path: str, frame_interval_meters: int) -> str:
    """Cache key includes paths and frame interval."""
    cache_dir = _get_cache_dir(video_path)
    key = f"{video_path}:{gpx_path}:{frame_interval_meters}"
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    return os.path.join(cache_dir, f"pipeline_{h}.json")


def _strip_base64_for_cache(result: dict) -> dict:
    """Remove large base64 image data from result before caching."""
    cached = copy.deepcopy(result)
    if "frames" in cached:
        for frame in cached["frames"]:
            if "image_base64" in frame:
                frame["image_base64"] = "[cached]"
    return cached


# ── Distance-based frame selection ─────────────────────────────────


def _select_frames_by_distance(
    matched_frames: list[dict],
    interval_meters: int = 25,
) -> list[dict]:
    """Select frames spaced by GPS distance, not time.

    Args:
        matched_frames: Frames with lat/lon from GPS matching.
        interval_meters: Minimum distance between selected frames.

    Returns:
        Subset of frames spaced at least *interval_meters* apart.
    """
    # Filter to only geo-tagged frames
    geo_frames = [f for f in matched_frames if f.get("lat") is not None]
    if not geo_frames:
        return matched_frames  # fallback to all frames

    selected = [geo_frames[0]]
    cumulative = 0.0

    for i in range(1, len(geo_frames)):
        prev = geo_frames[i - 1]
        curr = geo_frames[i]
        dist = haversine(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
        cumulative += dist

        if cumulative >= interval_meters:
            selected.append(curr)
            cumulative = 0.0

    # Always include last frame
    if selected[-1] is not geo_frames[-1]:
        selected.append(geo_frames[-1])

    return selected


# ── Main pipeline ──────────────────────────────────────────────────


def run_pipeline(
    video_path: str,
    gpx_path: str,
    video_start_time: str = None,
    frame_interval: int = 5,
    max_frames: int = 20,
    frame_interval_meters: int = None,
    use_mock: bool = False,
    api_key: str = None,
    progress_callback=None,
    skip_size_guards: bool = False,
    use_cache: bool = True,
) -> dict:
    """Run the full dashcam analysis pipeline.

    Args:
        video_path: path to MP4 file OR directory of MP4 clips.
        gpx_path: path to GPX file OR directory of GPX files.
        video_start_time: "2026-02-12 14:18:00" (local time, optional).
            Auto-detected from first clip filename if not provided.
        frame_interval: seconds between frame samples (legacy, used when
            *frame_interval_meters* is not provided).
        max_frames: cap on frames to send to Vision API (legacy, used when
            *frame_interval_meters* is not provided).
        frame_interval_meters: if provided, select frames by GPS distance
            instead of time.  Overrides *frame_interval* and *max_frames*.
        use_mock: if True, skip real API calls
        api_key: Anthropic API key (reads from env if not provided)
        progress_callback: optional callable(stage: int, message: str)
            for reporting progress to the UI.
        skip_size_guards: if True, skip size/count validation (for testing).
        use_cache: if True, check for and save cached results.

    Returns dict with frames, summary, geojson, narrative, metadata.
    """

    # --- Progress helper ---
    def progress(stage: int, message: str):
        if progress_callback:
            progress_callback(stage, message)
        print(message)

    t0 = time.time()
    is_dir = os.path.isdir(video_path)
    VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov")
    MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
    MAX_PER_CLIP_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_CLIP_COUNT = 100

    use_distance_mode = frame_interval_meters is not None
    effective_interval_meters = frame_interval_meters or 25

    # ── CACHE CHECK ──────────────────────────────────────────────────
    if use_cache and not use_mock:
        try:
            cache_path = _get_cache_path(video_path, gpx_path, effective_interval_meters)
            if os.path.exists(cache_path):
                progress(1, "Loading cached results...")
                with open(cache_path, "r") as f:
                    cached_result = json.load(f)
                sections_count = cached_result.get("metadata", {}).get("sections_count", "?")
                progress(7, f"Loaded from cache — {sections_count} sections")
                return cached_result
        except Exception as e:
            print(f"  Cache read failed, running pipeline: {e}")

    # ── SIZE GUARDS ──────────────────────────────────────────────────
    warnings = []
    size_mb = 0
    n_clips = 1

    if is_dir:
        video_files = sorted(
            f for f in os.listdir(video_path)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        )
        clip_count_check = len(video_files)
        total_size = sum(
            os.path.getsize(os.path.join(video_path, f)) for f in video_files
        )
        size_mb = total_size / (1024 ** 2)
        n_clips = clip_count_check

        if not skip_size_guards:
            # Clip count check
            if clip_count_check > MAX_CLIP_COUNT:
                return {
                    "error": True,
                    "message": f"Too many clips ({clip_count_check}). Maximum is {MAX_CLIP_COUNT}.",
                }

            # Total size check
            size_gb = total_size / (1024 ** 3)
            if total_size > MAX_TOTAL_SIZE:
                return {
                    "error": True,
                    "message": f"Total video size is {size_gb:.1f}GB. Maximum recommended is {MAX_TOTAL_SIZE // (1024**2)}MB. Please compress clips first.",
                }

            # Per-clip size check
            for vf in video_files:
                fsize = os.path.getsize(os.path.join(video_path, vf))
                if fsize > MAX_PER_CLIP_SIZE:
                    size_mb_clip = fsize / (1024 ** 2)
                    warnings.append(
                        f"Clip '{vf}' is {size_mb_clip:.0f}MB (>{MAX_PER_CLIP_SIZE // (1024 * 1024)}MB recommended). Consider compressing."
                    )
    else:
        # Single file
        if not os.path.isfile(video_path):
            return {"error": True, "message": f"Video path not found: {video_path}"}
        total_size = os.path.getsize(video_path)
        size_mb = total_size / (1024 ** 2)

        if not skip_size_guards:
            size_gb = total_size / (1024 ** 3)
            if total_size > MAX_TOTAL_SIZE:
                return {
                    "error": True,
                    "message": f"Total video size is {size_gb:.1f}GB. Maximum recommended is {MAX_TOTAL_SIZE // (1024**2)}MB. Please compress clips first.",
                }
            if total_size > MAX_PER_CLIP_SIZE:
                size_mb_clip = total_size / (1024 ** 2)
                return {
                    "error": True,
                    "message": f"Clip '{os.path.basename(video_path)}' is {size_mb_clip:.0f}MB (>{MAX_PER_CLIP_SIZE // (1024 * 1024)}MB). Please compress first.",
                }

    progress(1, f"Validating uploads... (checking {n_clips} clips, {size_mb:.0f}MB total)")

    # ── MAIN PIPELINE (wrapped for memory safety) ────────────────────
    try:
        print("\n[TARA Video Pipeline]")
        print("\u2500" * 21)
        if is_dir:
            mp4_count = len([f for f in os.listdir(video_path) if f.lower().endswith(VIDEO_EXTENSIONS)])
            print(f"Mode: Multi-clip ({mp4_count} files)")
        else:
            print(f"Mode: Single file")

        # --- Stage 2: Extract frames ---
        if is_dir:
            mp4_files = sorted(
                f for f in os.listdir(video_path)
                if f.lower().endswith(VIDEO_EXTENSIONS)
            )
            for i, mp4 in enumerate(mp4_files):
                progress(2, f"Extracting frames... (clip {i + 1}/{len(mp4_files)} — {mp4})")
        else:
            progress(2, f"Extracting frames... (clip 1/1 — {os.path.basename(video_path)})")

        frames = extract_frames(video_path, interval_seconds=frame_interval)
        if frames:
            duration_min = frames[-1]["timestamp_sec"] / 60
        else:
            duration_min = 0
        clip_count = len(set(f.get("clip_filename", "") for f in frames))
        print(f"  \u2192 Extracted {len(frames)} frames from {clip_count} clip(s) "
              f"(every {frame_interval}s, {duration_min:.1f} min total)")

        # --- Stage 3: Parse GPS & match ---
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

        progress(3, f"Matching GPS coordinates... ({len(frames)} frames \u2192 {len(trackpoints)} trackpoints)")

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
        # Distance-based frame selection (new) vs legacy time-based
        if use_distance_mode:
            frames_for_vision = _select_frames_by_distance(
                frames, interval_meters=frame_interval_meters,
            )
            n_to_assess = len(frames_for_vision)
            print(f"  \u2192 Distance-based selection: {n_to_assess} frames "
                  f"at {frame_interval_meters}m spacing")
        else:
            frames_for_vision = frames
            n_to_assess = min(len(frames), max_frames)

        progress(4, f"Analysing road condition... (frame 1/{n_to_assess})")

        anthropic_client = None
        if not use_mock:
            from anthropic import Anthropic
            anthropic_client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

        vision_max = None if use_distance_mode else max_frames
        result = assess_road(
            frames_for_vision,
            anthropic_client=anthropic_client,
            max_frames=vision_max,
            use_mock=use_mock,
        )
        assessed_frames = result["frames"]
        summary = result["summary"]

        # --- Stage 5: Generate outputs ---
        n_sections = summary.get("total_frames_assessed", 0)
        progress(5, f"Building condition map... ({n_sections} assessed, {total_dist_km:.1f}km)")

        geojson = frames_to_condition_geojson(
            assessed_frames,
            trackpoints=trackpoints,
            video_start_time=video_start_time,
            all_frames=frames,
        )
        print(f"  \u2192 GeoJSON with {len(geojson['features'])} sections")
        point_geojson = frames_to_geojson(assessed_frames)
        panel_data = build_condition_summary_panel(summary, total_distance_km=total_dist_km)

        # --- Stage 6: Recommend interventions ---
        progress(6, "Recommending interventions...")

        section_props = [feat["properties"] for feat in geojson["features"]]
        interventions = recommend_interventions_for_route(section_props)
        route_summary = interventions.get("route_summary", {})
        total_intervention_cost = route_summary.get("total_cost", 0)
        print(f"  \u2192 {len(interventions['sections'])} sections, "
              f"est. cost ${total_intervention_cost:,.0f}")

        # Generate narrative
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

        # Build metadata (enhanced — Change 7)
        if is_dir:
            dataset_name = os.path.basename(
                os.path.dirname(video_path)
                if os.path.basename(video_path) in ("clips", "clips_compressed")
                else video_path
            )
            video_label = f"{clip_count} clips"
        else:
            dataset_name = os.path.basename(os.path.dirname(video_path))
            video_label = os.path.basename(video_path)

        gpx_label = os.path.basename(gpx_path)
        n_sections_final = len(geojson["features"])

        progress(7, f"Complete \u2713 \u2014 {n_sections_final} sections, {total_dist_km:.1f}km, est. cost ${total_intervention_cost:,.0f}")

        result_dict = {
            "frames": assessed_frames,
            "summary": summary,
            "geojson": geojson,
            "point_geojson": point_geojson,
            "narrative": narrative,
            "panel_data": panel_data,
            "interventions": interventions,
            "metadata": {
                "dataset_name": dataset_name,
                "video_file": video_label,
                "gpx_file": gpx_label,
                "total_clips": clip_count,
                "total_frames_extracted": len(frames),
                "frames_sent_to_vision": summary["total_frames_assessed"],
                "frame_interval_meters": effective_interval_meters if use_distance_mode else None,
                "total_distance_km": round(total_dist_km, 2),
                "sections_count": n_sections_final,
                "processing_time_seconds": round(elapsed, 1),
                "model_used": "claude-opus-4-6",
                "gpx_trackpoints": len(trackpoints),
                "timestamp": datetime.now().isoformat(),
            },
        }

        if warnings:
            result_dict["warnings"] = warnings

        # ── SAVE CACHE ──────────────────────────────────────────────
        if use_cache and not use_mock:
            try:
                cache_dir = _get_cache_dir(video_path)
                os.makedirs(cache_dir, exist_ok=True)
                cache_path = _get_cache_path(video_path, gpx_path, effective_interval_meters)
                cache_result = _strip_base64_for_cache(result_dict)
                with open(cache_path, "w") as f:
                    json.dump(cache_result, f)
                print(f"  \u2192 Cache saved to {cache_path}")
            except Exception as e:
                print(f"  Warning: Could not save cache: {e}")

        return result_dict

    except (MemoryError, OverflowError) as e:
        return {
            "error": True,
            "message": f"Memory error during processing: {e}. Try compressing clips or reducing clip count.",
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
