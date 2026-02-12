"""Frame extraction from dashcam video using OpenCV."""

import base64
import os
import shutil

import cv2


def extract_frames(
    video_path: str,
    interval_seconds: int = 5,
    output_dir: str = None,
    max_width: int = 1280,
) -> list[dict]:
    """Extract frames from video at interval.

    Returns list of dicts with frame_index, timestamp_sec, image_path, image_base64.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_dir is None:
        output_dir = "/tmp/tara_frames"

    # Clear and recreate output dir
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    frame_skip = int(fps * interval_seconds)

    # Calculate expected frame count
    expected = int(duration_sec // interval_seconds) + 1

    results = []
    frame_num = 0
    extracted = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % frame_skip == 0:
            timestamp_sec = frame_num / fps

            # Resize preserving aspect ratio
            h, w = frame.shape[:2]
            if w > max_width:
                scale = max_width / w
                frame = cv2.resize(frame, (max_width, int(h * scale)))

            # Save as JPEG
            filename = f"frame_{extracted:03d}.jpg"
            image_path = os.path.join(output_dir, filename)
            cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Base64 encode
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            mins, secs = divmod(int(timestamp_sec), 60)
            print(f"  Extracted frame {extracted + 1}/{expected} at {mins}:{secs:02d}")

            results.append({
                "frame_index": extracted,
                "timestamp_sec": timestamp_sec,
                "image_path": image_path,
                "image_base64": image_base64,
            })
            extracted += 1

        frame_num += 1

    cap.release()
    return results
