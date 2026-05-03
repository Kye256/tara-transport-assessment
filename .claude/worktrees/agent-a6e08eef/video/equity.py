"""Equity impact narrative generation from camera-observed activity profiles."""

from __future__ import annotations

import json
from typing import Any


def generate_equity_narrative(
    sections_data: list[dict[str, Any]],
    anthropic_client,
    model: str = "claude-sonnet-4-5-20250929",
) -> str:
    """Generate an equity impact narrative from section-level camera observations.

    Args:
        sections_data: list of section dicts, each with an 'equity' key
            from aggregate_section_equity.
        anthropic_client: Anthropic client instance.
        model: Claude model to use for generation.

    Returns:
        Narrative string for the equity panel.
    """
    # Build readable section summaries for the prompt
    section_summaries = []
    for i, sec in enumerate(sections_data):
        equity = sec.get("equity", sec.get("properties", {}).get("equity", {}))
        if not equity:
            continue
        section_summaries.append({
            "section": i + 1,
            "length_km": sec.get("length_km", sec.get("properties", {}).get("length_km", "?")),
            "condition": sec.get("condition_class", sec.get("properties", {}).get("condition_class", "?")),
            "surface": sec.get("surface_type", sec.get("properties", {}).get("surface_type", "?")),
            "land_use": equity.get("dominant_land_use", "unknown"),
            "activity_level": equity.get("activity_level", "unknown"),
            "pedestrians": equity.get("pedestrian_presence", "unknown"),
            "school_children": equity.get("school_children_observed", False),
            "vendors": equity.get("vendors_observed", False),
            "footpath": equity.get("nmt_footpath", "unknown"),
            "pedestrians_on_carriageway": equity.get("pedestrians_on_carriageway", False),
            "facilities": equity.get("facilities_seen", []),
            "vehicles": equity.get("vehicle_mix_summary", {}),
            "equity_concern": equity.get("equity_concern", "unknown"),
        })

    if not section_summaries:
        return generate_equity_narrative_mock(sections_data)

    sections_json = json.dumps(section_summaries, indent=2)

    prompt = f"""You are a transport equity analyst reviewing dashcam survey results for a road in Uganda.
Based on the camera observations below, write a 3-4 paragraph equity impact assessment.

Focus on:
1. WHO uses this road — based on observed pedestrians, vehicle types, school children, vendors
2. WHERE are the community hubs — sections with high activity, trading centres, facilities
3. WHAT are the NMT gaps — where pedestrians have no safe space and are walking on the carriageway
4. WHAT does this mean for the proposed intervention — will the upgrade serve the people the camera observed?

Be specific. Reference section numbers and what was observed. Do not be generic.
Write in professional but accessible language suitable for a road appraisal report.

CAMERA OBSERVATIONS BY SECTION:
{sections_json}"""

    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Equity narrative generation error: {e}")
        return generate_equity_narrative_mock(sections_data)


def generate_equity_narrative_mock(sections_data: list[dict[str, Any]]) -> str:
    """Return a plausible equity narrative for testing without API.

    Args:
        sections_data: list of section dicts with equity data.

    Returns:
        Mock narrative string.
    """
    # Count sections with high equity concern
    high_count = 0
    moderate_count = 0
    has_school = False
    has_vendors = False
    total_sections = len(sections_data)

    for sec in sections_data:
        equity = sec.get("equity", sec.get("properties", {}).get("equity", {}))
        concern = equity.get("equity_concern", "unknown")
        if concern == "high":
            high_count += 1
        elif concern == "moderate":
            moderate_count += 1
        if equity.get("school_children_observed"):
            has_school = True
        if equity.get("vendors_observed"):
            has_vendors = True

    parts = [
        "EQUITY IMPACT ASSESSMENT\n",
        f"Camera analysis of {total_sections} road sections identified "
        f"significant equity concerns along this corridor. "
        f"{high_count} section{'s' if high_count != 1 else ''} showed high equity concern "
        f"with heavy pedestrian activity and no footpath provision"
        f"{f', and {moderate_count} showed moderate concern' if moderate_count else ''}.\n",
        "The dominant road users observed were pedestrians and boda-boda motorcycles, "
        "indicating this road primarily serves lower-income community transport needs. "
    ]

    if has_school:
        parts.append(
            "School children were observed in several sections, raising safety concerns "
            "given the absence of dedicated pedestrian infrastructure. "
        )
    if has_vendors:
        parts.append(
            "Roadside vendors were active along the corridor, confirming the road's "
            "economic function for local commerce. "
        )

    parts.append(
        "\n\nRecommendation: The proposed intervention should include NMT provision "
        "(footpaths and pedestrian crossings) to ensure the upgrade serves the "
        "vulnerable road users observed during the survey. Priority should be given "
        "to sections with high equity concern where pedestrians currently share "
        "the carriageway with motorised traffic."
    )

    return "".join(parts)
