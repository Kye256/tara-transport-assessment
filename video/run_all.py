"""Batch runner: process all dashcam clips into a single combined assessment.

Delegates to the main pipeline which now handles multi-clip directories natively.
"""

import json
import os

from video.video_pipeline import run_pipeline
from video.video_frames import extract_start_time_from_filename

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(BASE, "data", "videos")
OUTPUT_DIR = os.path.join(BASE, "output")


def extract_start_time(filename: str) -> str:
    """Extract local start time from dashcam filename like 2026_02_12_144138_00.MP4.

    Kept for backward compatibility. Delegates to extract_start_time_from_filename.
    """
    result = extract_start_time_from_filename(filename)
    if result is None:
        # Fallback: try the original fixed-offset approach
        ts = filename[11:17]  # HHMMSS
        return f"2026-02-12 {ts[:2]}:{ts[2:4]}:{ts[4:6]}"
    return result


def run_all(
    video_dir: str = None,
    gpx_path: str = None,
    frame_interval: int = 10,
    max_frames: int = 40,
    use_mock: bool = False,
) -> dict:
    """Process all MP4 clips against GPX track(s).

    Args:
        video_dir: directory containing MP4 clips (defaults to data/videos/)
        gpx_path: path to GPX file or directory (defaults to first .gpx in video_dir)
        frame_interval: seconds between frame samples
        max_frames: cap on frames to send to Vision API
        use_mock: if True, skip real API calls
    """
    if video_dir is None:
        video_dir = VIDEO_DIR

    if gpx_path is None:
        # Find first GPX file in video_dir
        gpx_files = sorted(f for f in os.listdir(video_dir) if f.lower().endswith(".gpx"))
        if gpx_files:
            gpx_path = os.path.join(video_dir, gpx_files[0])
        else:
            raise FileNotFoundError(f"No GPX files found in {video_dir}")

    return run_pipeline(
        video_path=video_dir,
        gpx_path=gpx_path,
        frame_interval=frame_interval,
        max_frames=max_frames,
        use_mock=use_mock,
    )


if __name__ == "__main__":
    result = run_all(use_mock=False, frame_interval=10, max_frames=40)
    print(f"\n--- SUMMARY ---")
    print(json.dumps(result["summary"], indent=2))
    print(f"\n--- METADATA ---")
    print(json.dumps(result["metadata"], indent=2))
    print(f"\n--- NARRATIVE ---")
    print(result["narrative"])
