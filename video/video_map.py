"""Map output and condition narrative generation."""

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


def frames_to_condition_geojson(assessed_frames: list[dict]) -> dict:
    """Convert assessed frames into color-coded LineString sections for the map.

    Groups consecutive frames with the same condition_class into sections.
    Each section becomes a GeoJSON LineString.

    Args:
        assessed_frames: list of frame dicts with assessment and GPS keys.

    Returns:
        GeoJSON FeatureCollection dict with LineString features.
    """
    # Filter to geo-tagged assessed frames
    geo_frames = [
        f for f in assessed_frames
        if f.get("lat") is not None and f.get("lon") is not None
        and f.get("assessment")
    ]

    if not geo_frames:
        return {"type": "FeatureCollection", "features": []}

    # Group consecutive frames by condition_class
    sections = []
    current_section = [geo_frames[0]]
    current_condition = geo_frames[0]["assessment"]["condition_class"]

    for frame in geo_frames[1:]:
        condition = frame["assessment"]["condition_class"]
        if condition == current_condition:
            current_section.append(frame)
        else:
            sections.append(current_section)
            current_section = [frame]
            current_condition = condition
    sections.append(current_section)

    # Build GeoJSON features
    features = []
    for idx, section_frames in enumerate(sections):
        condition = section_frames[0]["assessment"]["condition_class"]
        color = CONDITION_COLORS.get(condition, "#9a6b2f")

        # Coordinates for LineString [lon, lat]
        coords = [[f["lon"], f["lat"]] for f in section_frames]
        # Single-frame section: duplicate with tiny offset to make valid LineString
        if len(coords) == 1:
            lon, lat = coords[0]
            coords.append([lon + 0.00005, lat + 0.00005])

        # Section-level stats
        iris = [f["assessment"]["iri_estimate"] for f in section_frames]
        avg_iri = round(sum(iris) / len(iris), 1) if iris else 0

        surfaces = [f["assessment"]["surface_type"] for f in section_frames]
        from collections import Counter
        surface_type = Counter(surfaces).most_common(1)[0][0] if surfaces else "unknown"

        all_distress = set()
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

    return {"type": "FeatureCollection", "features": features}


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
