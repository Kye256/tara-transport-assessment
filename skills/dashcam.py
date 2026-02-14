# TODO: This module uses a separate Sonnet-based assessment path for the agent API.
# Consider migrating to the TMH12/VCI methodology from video/vision_assess.py.
"""
TARA Dashcam Analysis
Analyses road condition from dashcam video or images using Claude Vision API.
Extracts frames from video, sends to Vision API, aggregates condition scores.
"""

import base64
import io
import os
import tempfile
from typing import Optional

import anthropic


def analyze_dashcam_media(
    file_path: str,
    media_type: str = "image",
    road_data: Optional[dict] = None,
    sample_interval_sec: float = 5.0,
    api_key: Optional[str] = None,
) -> dict:
    """
    Analyse road condition from a dashcam image or video.

    Args:
        file_path: Path to the image or video file
        media_type: "image" or "video"
        road_data: Optional road data for context
        sample_interval_sec: Seconds between frame samples (video only)
        api_key: Anthropic API key (defaults to env var)

    Returns:
        Dict with condition scores, surface type, defects, IRI estimate
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"found": False, "error": "No API key provided"}

    road_context = ""
    if road_data and road_data.get("found"):
        road_context = (
            f"This is the {road_data.get('name', 'unknown')} road, "
            f"{road_data.get('total_length_km', 'unknown')} km long, "
            f"surface: {', '.join(road_data.get('attributes', {}).get('surface_types', ['unknown']))}."
        )

    if media_type == "video":
        frames = _extract_video_frames(file_path, sample_interval_sec)
        if not frames:
            return {"found": False, "error": "Could not extract frames from video"}
    else:
        # Single image
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        frames = [image_bytes]

    # Analyse each frame
    segments = []
    for i, frame_bytes in enumerate(frames):
        result = _analyze_frame_with_vision(frame_bytes, api_key, road_context, i, len(frames))
        if result:
            segments.append(result)

    if not segments:
        return {"found": False, "error": "Vision analysis returned no results"}

    aggregated = _aggregate_results(segments)

    return {
        "found": True,
        "source": media_type,
        "frame_count": len(frames),
        "segments_analyzed": len(segments),
        "overall_condition": aggregated["overall_condition"],
        "overall_iri_estimate": aggregated["iri_estimate"],
        "surface_type": aggregated["surface_type"],
        "defects": aggregated["defects"],
        "drainage_condition": aggregated["drainage_condition"],
        "segments": segments,
        "summary": _build_summary(aggregated, media_type, len(frames)),
    }


def get_dashcam_summary(results: dict) -> str:
    """
    Generate a markdown summary of dashcam analysis results.

    Args:
        results: Output from analyze_dashcam_media()

    Returns:
        Markdown string
    """
    if not results.get("found"):
        return f"Dashcam analysis failed: {results.get('error', 'unknown error')}"

    score = results["overall_condition"]
    iri = results["overall_iri_estimate"]
    surface = results["surface_type"]
    defects = results.get("defects", [])
    drainage = results.get("drainage_condition", "unknown")

    condition_label = _condition_label(score)

    lines = [
        "## Road Condition Assessment (Dashcam)",
        "",
        f"**Overall Condition: {score}/100** ({condition_label})",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Surface Type | {surface.title()} |",
        f"| IRI Estimate | {iri['min']}-{iri['max']} m/km |",
        f"| Drainage | {drainage.title()} |",
        f"| Frames Analysed | {results.get('frame_count', 0)} |",
        "",
    ]

    if defects:
        lines.append(f"**Defects observed:** {', '.join(defects)}")
    else:
        lines.append("**No significant defects observed.**")

    return "\n".join(lines)


def _extract_video_frames(
    video_path: str,
    interval_sec: float = 5.0,
    max_frames: int = 20,
) -> list[bytes]:
    """
    Extract frames from a video at regular intervals.

    Args:
        video_path: Path to video file
        interval_sec: Seconds between frame samples
        max_frames: Maximum frames to extract

    Returns:
        List of JPEG-encoded frame bytes
    """
    try:
        import cv2
    except ImportError:
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps

    frame_interval = int(fps * interval_sec)
    if frame_interval < 1:
        frame_interval = 1

    frames = []
    frame_idx = 0

    while len(frames) < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for API efficiency (max 1024px width)
        h, w = frame.shape[:2]
        if w > 1024:
            scale = 1024 / w
            frame = cv2.resize(frame, (1024, int(h * scale)))

        # Encode as JPEG
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frames.append(buffer.tobytes())

        frame_idx += frame_interval

    cap.release()
    return frames


def _analyze_frame_with_vision(
    frame_bytes: bytes,
    api_key: str,
    road_context: str = "",
    frame_index: int = 0,
    total_frames: int = 1,
) -> Optional[dict]:
    """
    Analyse a single frame using Claude Vision API.

    Returns dict with condition_score, surface_type, defects, iri_estimate, drainage, notes.
    """
    prompt = f"""Analyse this road image for condition assessment. {road_context}

You are an experienced road engineer assessing pavement condition.

Respond with ONLY a JSON object (no markdown, no explanation) with these fields:
{{
    "condition_score": <0-100, where 100=perfect, 0=impassable>,
    "surface_type": "<asphalt|gravel|earth|concrete|mixed>",
    "defects": ["<list of observed defects: potholes, rutting, cracking, raveling, edge_break, etc.>"],
    "iri_estimate": {{"min": <number>, "max": <number>}},
    "drainage_condition": "<good|fair|poor|blocked>",
    "notes": "<brief observation>"
}}

IRI guidelines: new asphalt 2-3, good paved 3-5, fair paved 5-8, poor paved 8-12, gravel 8-16, earth 12-25.
Frame {frame_index + 1} of {total_frames}."""

    image_b64 = base64.b64encode(frame_bytes).decode("utf-8")

    # Detect media type from bytes
    media_type = "image/jpeg"
    if frame_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        media_type = "image/png"

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }],
        )
    except Exception:
        return None

    # Parse JSON response
    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        import json
        result = json.loads(text)
        # Validate required fields
        result.setdefault("condition_score", 50)
        result.setdefault("surface_type", "unknown")
        result.setdefault("defects", [])
        result.setdefault("iri_estimate", {"min": 8, "max": 14})
        result.setdefault("drainage_condition", "fair")
        result.setdefault("notes", "")
        return result
    except (json.JSONDecodeError, ValueError):
        return None


def _aggregate_results(segments: list[dict]) -> dict:
    """Aggregate multiple frame analysis results into an overall assessment."""
    if not segments:
        return {
            "overall_condition": 50,
            "surface_type": "unknown",
            "defects": [],
            "iri_estimate": {"min": 8, "max": 14},
            "drainage_condition": "fair",
        }

    # Average condition score
    scores = [s.get("condition_score", 50) for s in segments]
    avg_condition = round(sum(scores) / len(scores))

    # Most common surface type
    surface_counts: dict[str, int] = {}
    for s in segments:
        st = s.get("surface_type", "unknown")
        surface_counts[st] = surface_counts.get(st, 0) + 1
    surface_type = max(surface_counts, key=surface_counts.get)

    # Union of all defects
    all_defects: set[str] = set()
    for s in segments:
        all_defects.update(s.get("defects", []))

    # Average IRI estimates
    iri_mins = [s.get("iri_estimate", {}).get("min", 8) for s in segments]
    iri_maxs = [s.get("iri_estimate", {}).get("max", 14) for s in segments]
    avg_iri_min = round(sum(iri_mins) / len(iri_mins), 1)
    avg_iri_max = round(sum(iri_maxs) / len(iri_maxs), 1)

    # Most common drainage
    drainage_counts: dict[str, int] = {}
    for s in segments:
        d = s.get("drainage_condition", "fair")
        drainage_counts[d] = drainage_counts.get(d, 0) + 1
    drainage = max(drainage_counts, key=drainage_counts.get)

    return {
        "overall_condition": avg_condition,
        "surface_type": surface_type,
        "defects": sorted(all_defects),
        "iri_estimate": {"min": avg_iri_min, "max": avg_iri_max},
        "drainage_condition": drainage,
    }


def _condition_label(score: int) -> str:
    """Convert condition score to label."""
    if score >= 80:
        return "Good"
    elif score >= 60:
        return "Fair"
    elif score >= 40:
        return "Poor"
    elif score >= 20:
        return "Bad"
    else:
        return "Very Bad"


def _build_summary(aggregated: dict, media_type: str, frame_count: int) -> str:
    """Build a text summary for the agent."""
    condition = aggregated["overall_condition"]
    label = _condition_label(condition)
    iri = aggregated["iri_estimate"]

    return (
        f"Road condition: {condition}/100 ({label}). "
        f"Surface: {aggregated['surface_type']}. "
        f"IRI estimate: {iri['min']}-{iri['max']} m/km. "
        f"Defects: {', '.join(aggregated['defects']) or 'none observed'}. "
        f"Drainage: {aggregated['drainage_condition']}. "
        f"Analysed {frame_count} {'frames' if media_type == 'video' else 'image(s)'}."
    )
