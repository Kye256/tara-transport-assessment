"""Frame extraction from dashcam video using OpenCV."""

import base64
import os
import re
import shutil

import cv2


def extract_start_time_from_filename(filename: str) -> str | None:
    """Extract local start time from dashcam filename like 2026_02_12_144138_00.MP4.

    Returns time string like "2026-02-12 14:41:38" or None if pattern doesn't match.
    """
    match = re.match(r"(\d{4})_(\d{2})_(\d{2})_(\d{2})(\d{2})(\d{2})_\d+\.\w+", filename)
    if match:
        y, mo, d, h, mi, s = match.groups()
        return f"{y}-{mo}-{d} {h}:{mi}:{s}"
    return None


def _extract_from_single_file(
    video_path: str,
    interval_seconds: int,
    output_dir: str,
    max_width: int,
    frame_offset: int = 0,
    cumulative_time: float = 0.0,
    clip_index: int | None = None,
    total_clips: int | None = None,
) -> tuple[list[dict], float]:
    """Extract frames from a single video file.

    Args:
        video_path: path to video file
        interval_seconds: seconds between frame samples
        output_dir: directory to save frames
        max_width: resize frames to this max width
        frame_offset: starting frame_index counter (for multi-clip)
        cumulative_time: cumulative seconds offset (for multi-clip)
        clip_index: 0-based clip index (for progress display)
        total_clips: total number of clips (for progress display)

    Returns:
        (frames_list, clip_duration_seconds)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    frame_skip = int(fps * interval_seconds)

    expected = int(duration_sec // interval_seconds) + 1
    clip_label = f"[Clip {clip_index + 1}/{total_clips}] " if clip_index is not None else ""

    results = []
    frame_num = 0
    extracted = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % frame_skip == 0:
            local_ts = frame_num / fps
            cumulative_ts = cumulative_time + local_ts

            # Resize preserving aspect ratio
            h, w = frame.shape[:2]
            if w > max_width:
                scale = max_width / w
                frame = cv2.resize(frame, (max_width, int(h * scale)))

            # Save as JPEG
            global_idx = frame_offset + extracted
            filename = f"frame_{global_idx:03d}.jpg"
            image_path = os.path.join(output_dir, filename)
            cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Base64 encode
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            mins, secs = divmod(int(cumulative_ts), 60)
            print(f"  {clip_label}Extracted frame {extracted + 1}/{expected} at {mins}:{secs:02d} (cumulative)")

            frame_data = {
                "frame_index": global_idx,
                "timestamp_sec": cumulative_ts,
                "image_path": image_path,
                "image_base64": image_base64,
                "clip_filename": os.path.basename(video_path),
            }

            # Add clip start time from filename if available
            clip_ts = extract_start_time_from_filename(os.path.basename(video_path))
            if clip_ts:
                frame_data["clip_timestamp"] = clip_ts
                frame_data["video_start_time"] = clip_ts

            results.append(frame_data)
            extracted += 1

        frame_num += 1

    cap.release()
    return results, duration_sec


def extract_frames(
    video_path: str,
    interval_seconds: int = 5,
    output_dir: str = None,
    max_width: int = 1280,
) -> list[dict]:
    """Extract frames from video at interval.

    Args:
        video_path: path to a single video file OR a directory of MP4 files.
            If directory, all .MP4/.mp4 files are sorted and processed sequentially
            with cumulative timestamps.
        interval_seconds: seconds between frame samples
        output_dir: directory to save extracted frame images
        max_width: resize frames to this max width

    Returns list of dicts with frame_index, timestamp_sec, image_path, image_base64,
    clip_filename, and optionally clip_timestamp/video_start_time.
    """
    if output_dir is None:
        output_dir = "/tmp/tara_frames"

    # Clear and recreate output dir
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Single file mode
    if os.path.isfile(video_path):
        frames, _ = _extract_from_single_file(
            video_path, interval_seconds, output_dir, max_width,
        )
        return frames

    # Directory mode — find all MP4 files
    if not os.path.isdir(video_path):
        raise FileNotFoundError(f"Video path not found: {video_path}")

    mp4_files = sorted(
        f for f in os.listdir(video_path)
        if f.lower().endswith((".mp4", ".avi", ".mov"))
    )

    if not mp4_files:
        raise FileNotFoundError(f"No video files found in: {video_path}")

    print(f"  Found {len(mp4_files)} video clips in {video_path}")

    all_frames = []
    cumulative_time = 0.0
    frame_offset = 0

    for i, mp4 in enumerate(mp4_files):
        full_path = os.path.join(video_path, mp4)
        frames, clip_duration = _extract_from_single_file(
            full_path, interval_seconds, output_dir, max_width,
            frame_offset=frame_offset,
            cumulative_time=cumulative_time,
            clip_index=i,
            total_clips=len(mp4_files),
        )
        all_frames.extend(frames)
        frame_offset += len(frames)
        cumulative_time += clip_duration

    return all_frames
