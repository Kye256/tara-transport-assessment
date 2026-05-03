"""TARA video dataset scanner — discovers valid dashcam datasets in data/videos/."""

import os
from typing import Any


def scan_datasets(base_dir: str = "data/videos") -> list[dict[str, Any]]:
    """Scan for valid video datasets.

    A valid dataset folder contains:
      - A subfolder named ``clips/`` or ``clips_compressed/`` with at least one
        .mp4/.avi/.mov file.
      - At least one ``.gpx`` file in the dataset folder root or in a ``gpx/``
        subfolder.

    Args:
        base_dir: Root directory to scan (default ``data/videos``).

    Returns:
        List of dicts with keys: label, value, clips_dir, gpx_path,
        clip_count, total_size_mb, has_cache.
    """
    if not os.path.isdir(base_dir):
        return []

    datasets: list[dict[str, Any]] = []
    video_extensions = (".mp4", ".avi", ".mov")

    for entry in sorted(os.listdir(base_dir)):
        dataset_dir = os.path.join(base_dir, entry)
        if not os.path.isdir(dataset_dir):
            continue

        # Find clips folder
        clips_dir = None
        for candidate in ("clips", "clips_compressed"):
            path = os.path.join(dataset_dir, candidate)
            if os.path.isdir(path):
                clips_dir = path
                break
        if not clips_dir:
            continue

        # Count clips
        clip_files = [
            f for f in os.listdir(clips_dir)
            if f.lower().endswith(video_extensions)
        ]
        if not clip_files:
            continue

        # Find GPX file(s) — check dataset root first, then gpx/ subfolder
        gpx_path = None
        gpx_files = sorted(
            f for f in os.listdir(dataset_dir)
            if f.lower().endswith(".gpx")
        )
        if gpx_files:
            gpx_path = os.path.join(dataset_dir, gpx_files[0])

        gpx_subdir = os.path.join(dataset_dir, "gpx")
        if not gpx_path and os.path.isdir(gpx_subdir):
            gpx_files = sorted(
                f for f in os.listdir(gpx_subdir)
                if f.lower().endswith(".gpx")
            )
            if gpx_files:
                gpx_path = os.path.join(gpx_subdir, gpx_files[0])

        if not gpx_path:
            continue

        # Calculate total size
        total_size_mb = sum(
            os.path.getsize(os.path.join(clips_dir, f))
            for f in clip_files
        ) / (1024 * 1024)

        # Check for cached results
        cache_dir = os.path.join(dataset_dir, "cache")
        has_cache = (
            os.path.isdir(cache_dir)
            and any(f.endswith(".json") for f in os.listdir(cache_dir))
        )

        # Build human-readable label
        label = entry.replace("_", " ").replace("-", " ").title()
        label += f" ({len(clip_files)} clips, {total_size_mb:.0f}MB)"
        if has_cache:
            label += " [cached]"

        datasets.append({
            "label": label,
            "value": entry,
            "clips_dir": clips_dir,
            "gpx_path": gpx_path,
            "clip_count": len(clip_files),
            "total_size_mb": round(total_size_mb, 1),
            "has_cache": has_cache,
        })

    return datasets
