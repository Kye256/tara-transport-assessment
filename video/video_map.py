"""Map output and condition narrative generation."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from video.gps_utils import haversine, get_trackpoints_between

CONDITION_COLORS = {
    "good": "#2d5f4a",
    "fair": "#9a6b2f",
    "poor": "#c4652a",
    "bad": "#a83a2f",
}


def build_popup_html(frame: dict) -> str:
    """Build HTML string for a dash-leaflet popup with dashcam thumbnail and stats.

    Args:
        frame: assessed frame dict with assessment and image_base64 keys.

    Returns:
        HTML string for dl.Popup.
    """
    assessment = frame.get("assessment", {})
    condition = assessment.get("condition_class", "fair")
    color = CONDITION_COLORS.get(condition, "#9a6b2f")
    iri = assessment.get("iri_estimate", "?")
    surface = assessment.get("surface_type", "?")
    distress = assessment.get("distress_types", [])
    distress_str = ", ".join(d.replace("_", " ") for d in distress if d != "none") or "none"
    notes = assessment.get("notes", "")
    img_b64 = frame.get("image_base64", "")

    parts = [
        '<div style="font-family: \'Source Sans 3\', sans-serif; max-width: 320px;">',
    ]

    if img_b64:
        parts.append(
            f'<img src="data:image/jpeg;base64,{img_b64}" '
            f'style="width:300px; border-radius:3px;" />'
        )

    parts.append(
        f'<div style="margin-top:8px;">'
        f'<span style="background:{color}; color:white; padding:2px 8px; '
        f'border-radius:2px; font-size:11px; font-weight:600;">'
        f'{condition.upper()}</span>'
        f'<span style="color:#5c5950; font-size:12px; margin-left:8px;">'
        f'IRI ~{iri} m/km</span>'
        f'</div>'
    )

    parts.append(
        f'<div style="font-size:12px; color:#2c2a26; margin-top:6px;">'
        f'{surface.replace("_", " ").title()} surface &middot; {distress_str}'
        f'</div>'
    )

    if notes:
        parts.append(
            f'<div style="font-size:11px; color:#8a8578; margin-top:4px;">'
            f'{notes}</div>'
        )

    parts.append('</div>')
    return "\n".join(parts)


def frames_to_condition_geojson(
    assessed_frames: list[dict],
    trackpoints: list[dict] = None,
    video_start_time: str = None,
    all_frames: list[dict] = None,
) -> dict:
    """Convert assessed frames into color-coded LineString sections for the map.

    Groups consecutive frames into sections, breaking on condition_class change
    OR when cumulative section distance exceeds 1.0 km.  When GPX trackpoints
    are supplied, each section's LineString is densified with all intermediate
    trackpoints so the geometry follows the actual road.  When GPX has gaps,
    falls back to all_frames' interpolated GPS coordinates.

    Args:
        assessed_frames: list of frame dicts with assessment and GPS keys.
        trackpoints: optional GPX trackpoint list from parse_gpx / parse_gpx_folder.
            Each dict must have 'lat', 'lon', and 'time' (datetime) keys.
        video_start_time: optional local-time string "YYYY-MM-DD HH:MM:SS"
            (assumed UTC+3) used as the epoch base for computing frame times.
        all_frames: optional list of ALL extracted frames (including non-assessed)
            for GPS coordinate densification when GPX trackpoints are unavailable.

    Returns:
        GeoJSON FeatureCollection dict with LineString features.
    """
    # ------------------------------------------------------------------
    # 0.  Compute video start epoch (UTC) once, used for dense trackpoints
    # ------------------------------------------------------------------
    video_start_epoch: float | None = None
    if video_start_time is not None:
        tz_local = timezone(timedelta(hours=3))  # Uganda = UTC+3
        local_dt = datetime.strptime(video_start_time, "%Y-%m-%d %H:%M:%S")
        local_dt = local_dt.replace(tzinfo=tz_local)
        video_start_epoch = local_dt.astimezone(timezone.utc).timestamp()

    # ------------------------------------------------------------------
    # 1.  Filter to geo-tagged assessed frames
    # ------------------------------------------------------------------
    geo_frames = [
        f for f in assessed_frames
        if f.get("lat") is not None and f.get("lon") is not None
        and f.get("assessment")
    ]

    if not geo_frames:
        return {"type": "FeatureCollection", "features": []}

    # ------------------------------------------------------------------
    # Helper: epoch time for a frame
    # ------------------------------------------------------------------
    def _frame_epoch(frame: dict) -> float | None:
        """Return the UTC epoch seconds for *frame*, or None."""
        ts_sec = frame.get("timestamp_sec")
        if ts_sec is None:
            return None
        # Prefer the function-level video_start_time
        if video_start_epoch is not None:
            return video_start_epoch + ts_sec
        # Fall back to per-frame video_start_time field
        vst = frame.get("video_start_time")
        if vst:
            tz_local = timezone(timedelta(hours=3))
            local_dt = datetime.strptime(vst, "%Y-%m-%d %H:%M:%S")
            local_dt = local_dt.replace(tzinfo=tz_local)
            return local_dt.astimezone(timezone.utc).timestamp() + ts_sec
        return None

    # ------------------------------------------------------------------
    # 2.  Group frames into sections
    #     Break when (a) condition_class changes, or
    #                (b) cumulative section distance > 1.0 km
    # ------------------------------------------------------------------
    MAX_SECTION_KM = 1.0  # kilometres

    sections: list[list[dict]] = []
    current_section = [geo_frames[0]]
    current_condition = geo_frames[0]["assessment"]["condition_class"]
    section_distance_m = 0.0  # running distance in metres

    for frame in geo_frames[1:]:
        condition = frame["assessment"]["condition_class"]

        # Distance from previous frame to this frame
        prev = current_section[-1]
        dist_m = haversine(prev["lat"], prev["lon"], frame["lat"], frame["lon"])

        condition_changed = (condition != current_condition)
        distance_exceeded = ((section_distance_m + dist_m) > MAX_SECTION_KM * 1000)

        if condition_changed or distance_exceeded:
            sections.append(current_section)
            current_section = [frame]
            current_condition = condition
            section_distance_m = 0.0
        else:
            current_section.append(frame)
            section_distance_m += dist_m

    sections.append(current_section)

    # ------------------------------------------------------------------
    # 3.  Pre-compute epoch times for section boundary frames
    # ------------------------------------------------------------------
    section_epochs: list[tuple[float | None, float | None]] = []
    for sec_frames in sections:
        section_epochs.append((_frame_epoch(sec_frames[0]), _frame_epoch(sec_frames[-1])))

    # ------------------------------------------------------------------
    # 4.  Build GeoJSON features
    # ------------------------------------------------------------------
    features = []
    for idx, section_frames in enumerate(sections):
        condition = section_frames[0]["assessment"]["condition_class"]
        color = CONDITION_COLORS.get(condition, "#9a6b2f")

        # --- Dense LineString coordinates from trackpoints ---------------
        coords: list[list[float]] | None = None

        # Compute time window for this section (midpoints with neighbors)
        window_start: float | None = None
        window_end: float | None = None

        if section_epochs[idx][0] is not None:
            first_ep, last_ep = section_epochs[idx]

            if idx == 0:
                window_start = first_ep - 30.0
            else:
                prev_last = section_epochs[idx - 1][1]
                window_start = (prev_last + first_ep) / 2.0 if prev_last is not None else first_ep - 30.0

            if idx == len(sections) - 1:
                window_end = (last_ep or first_ep) + 30.0
            else:
                next_first = section_epochs[idx + 1][0]
                window_end = ((last_ep or first_ep) + next_first) / 2.0 if next_first is not None else (last_ep or first_ep) + 30.0

        # Try GPX trackpoints first (densest, follows actual road)
        if trackpoints and window_start is not None:
            dense = get_trackpoints_between(trackpoints, window_start, window_end)
            if dense:
                coords = dense

        # Fallback: use all_frames' GPS in the time window (for GPX gaps)
        if not coords and all_frames and window_start is not None:
            frame_coords = []
            for f in all_frames:
                if f.get("lat") is None or f.get("lon") is None:
                    continue
                ep = _frame_epoch(f)
                if ep is not None and window_start <= ep <= window_end:
                    frame_coords.append([f["lon"], f["lat"]])
            if len(frame_coords) >= 2:
                coords = frame_coords

        # Last fallback: section's own assessed frame GPS points
        if not coords:
            coords = [[f["lon"], f["lat"]] for f in section_frames]

        # Single-point section: duplicate with tiny offset for valid LineString
        if len(coords) == 1:
            lon, lat = coords[0]
            coords.append([lon + 0.00005, lat + 0.00005])

        # --- Section-level statistics ------------------------------------
        iris = [f["assessment"]["iri_estimate"] for f in section_frames]
        avg_iri = round(sum(iris) / len(iris), 1) if iris else 0

        surfaces = [f["assessment"]["surface_type"] for f in section_frames]
        surface_type = Counter(surfaces).most_common(1)[0][0] if surfaces else "unknown"

        all_distress: set[str] = set()
        for f in section_frames:
            for d in f["assessment"].get("distress_types", []):
                if d != "none":
                    all_distress.add(d)

        frame_indices = [f["frame_index"] for f in section_frames]
        rep_idx = len(section_frames) // 2
        rep_frame = section_frames[rep_idx]

        popup_html = build_popup_html(rep_frame)

        # Notes from representative frame
        notes = rep_frame["assessment"].get("notes", "")

        # Store representative image for Dash component popups
        rep_image = rep_frame.get("image_base64", "")

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "condition_class": condition,
                "color": color,
                "weight": 6,
                "avg_iri": avg_iri,
                "surface_type": surface_type,
                "distress_types": ", ".join(sorted(all_distress)) if all_distress else "none",
                "notes": notes,
                "section_index": idx,
                "frame_indices": frame_indices,
                "representative_frame_index": rep_frame["frame_index"],
                "representative_image": rep_image,
                "popup_html": popup_html,
            },
        }
        features.append(feature)

    # ------------------------------------------------------------------
    # 5.  Post-process: split sections exceeding MAX_SECTION_KM
    # ------------------------------------------------------------------
    split_limit = MAX_SECTION_KM * 1.5  # 1.5 km hard ceiling
    DENSIFY_RESOLUTION_KM = 0.25  # ensure enough points for any section >500m

    def _densify_coords(coords: list[list[float]]) -> list[list[float]]:
        """Insert intermediate points so no segment exceeds DENSIFY_RESOLUTION_KM."""
        dense = [coords[0]]
        for i in range(1, len(coords)):
            seg_km = haversine(coords[i - 1][1], coords[i - 1][0],
                               coords[i][1], coords[i][0]) / 1000
            if seg_km > DENSIFY_RESOLUTION_KM:
                n_parts = max(2, int(seg_km / DENSIFY_RESOLUTION_KM) + 1)
                for j in range(1, n_parts):
                    frac = j / n_parts
                    dense.append([
                        coords[i - 1][0] + frac * (coords[i][0] - coords[i - 1][0]),
                        coords[i - 1][1] + frac * (coords[i][1] - coords[i - 1][1]),
                    ])
            dense.append(coords[i])
        return dense

    final_features = []
    for feat in features:
        coords = _densify_coords(feat["geometry"]["coordinates"])
        feat["geometry"]["coordinates"] = coords

        total_km = 0.0
        for i in range(1, len(coords)):
            total_km += haversine(coords[i - 1][1], coords[i - 1][0],
                                  coords[i][1], coords[i][0]) / 1000

        if total_km <= split_limit:
            final_features.append(feat)
        else:

            # Split at MAX_SECTION_KM intervals
            sub_coords = [coords[0]]
            sub_dist = 0.0
            for i in range(1, len(coords)):
                seg_km = haversine(coords[i - 1][1], coords[i - 1][0],
                                   coords[i][1], coords[i][0]) / 1000
                if sub_dist + seg_km > MAX_SECTION_KM and len(sub_coords) >= 2:
                    new_feat = {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": list(sub_coords)},
                        "properties": dict(feat["properties"]),
                    }
                    final_features.append(new_feat)
                    sub_coords = [coords[i - 1]]  # overlap at boundary
                    sub_dist = 0.0
                sub_coords.append(coords[i])
                sub_dist += seg_km
            if len(sub_coords) >= 2:
                new_feat = {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": list(sub_coords)},
                    "properties": dict(feat["properties"]),
                }
                final_features.append(new_feat)

    # Re-index section_index sequentially
    for i, feat in enumerate(final_features):
        feat["properties"]["section_index"] = i

    return {"type": "FeatureCollection", "features": final_features}


def frames_to_geojson(assessed_frames: list[dict]) -> dict:
    """Convert assessed frames to GeoJSON FeatureCollection (Point features).

    Kept for backward compatibility. Prefer frames_to_condition_geojson for map display.
    """
    features = []
    for frame in assessed_frames:
        assessment = frame.get("assessment", {})
        condition = assessment.get("condition_class", "fair")
        color = CONDITION_COLORS.get(condition, "#9a6b2f")

        lat = frame.get("lat")
        lon = frame.get("lon")
        if lat is None or lon is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": {
                "condition_class": condition,
                "color": color,
                "iri_estimate": assessment.get("iri_estimate"),
                "surface_type": assessment.get("surface_type"),
                "distress_types": assessment.get("distress_types", []),
                "distress_severity": assessment.get("distress_severity"),
                "notes": assessment.get("notes", ""),
                "frame_index": frame.get("frame_index"),
                "timestamp_sec": frame.get("timestamp_sec"),
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def build_condition_summary_panel(summary: dict, total_distance_km: float = 0.0) -> dict:
    """Build data for the left panel condition display.

    Args:
        summary: pipeline summary dict from assess_road.
        total_distance_km: total GPS distance.

    Returns:
        Dict with panel display data.
    """
    condition_dist = summary.get("condition_distribution", {})
    total = summary.get("total_frames_assessed", 0) or 1

    condition_percentages = {
        cond: round(count / total * 100)
        for cond, count in condition_dist.items()
    }

    return {
        "total_distance_km": round(total_distance_km, 2),
        "average_iri": summary.get("average_iri", 0),
        "dominant_surface": summary.get("dominant_surface", "unknown"),
        "dominant_condition": summary.get("dominant_condition", "unknown"),
        "condition_percentages": condition_percentages,
        "key_issues": summary.get("distress_types_found", []),
    }


def generate_condition_narrative(summary: dict, anthropic_client, model: str = "claude-sonnet-4-5-20250929") -> str:
    """Send summary stats to Claude, get a 2-3 paragraph condition narrative."""
    prompt = f"""You are a road engineer writing a condition assessment for a road appraisal report.

Based on this dashcam analysis data, write a 2-3 paragraph professional road condition narrative suitable for inclusion in an investment appraisal report.

Data:
- Frames assessed: {summary.get('total_frames_assessed', 0)}
- Condition distribution: {summary.get('condition_distribution', {})}
- Average IRI: {summary.get('average_iri', 'N/A')}
- Dominant surface: {summary.get('dominant_surface', 'N/A')}
- Dominant condition: {summary.get('dominant_condition', 'N/A')}
- Distress types found: {', '.join(summary.get('distress_types_found', []))}

Write in third person, past tense. Be specific about the data. Do not use markdown headings."""

    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Narrative generation error: {e}")
        return generate_condition_narrative_mock(summary)


def generate_condition_narrative_mock(summary: dict) -> str:
    """Return a mock narrative for testing without API."""
    avg_iri = summary.get("average_iri", 8.0)
    surface = summary.get("dominant_surface", "gravel")
    condition = summary.get("dominant_condition", "fair")
    n_frames = summary.get("total_frames_assessed", 0)
    distress = summary.get("distress_types_found", [])
    dist_str = ", ".join(distress) if distress else "no significant distress"

    return (
        f"A dashcam survey of the road corridor was conducted, with {n_frames} frames "
        f"analysed along the route. The road presented predominantly {surface} surfacing "
        f"in {condition} condition, with an estimated average International Roughness "
        f"Index (IRI) of {avg_iri} m/km.\n\n"
        f"The principal forms of distress observed were {dist_str}. "
        f"The condition distribution indicated variation along the corridor, "
        f"with sections ranging from good to poor condition. "
        f"The findings suggest that targeted maintenance interventions would be "
        f"appropriate to arrest further deterioration and preserve the existing asset."
    )
