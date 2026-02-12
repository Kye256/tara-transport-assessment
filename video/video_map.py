"""Map output and condition narrative generation."""

CONDITION_COLORS = {
    "good": "#2d5f4a",
    "fair": "#9a6b2f",
    "poor": "#c4652a",
    "bad": "#a83a2f",
}


def frames_to_geojson(assessed_frames: list[dict]) -> dict:
    """Convert assessed frames to GeoJSON FeatureCollection for dash-leaflet."""
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
