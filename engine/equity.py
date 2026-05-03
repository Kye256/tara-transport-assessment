"""
TARA Equity Scoring Engine
Calculates equity impact scores for road investments based on accessibility
and facility access.
"""

from typing import Optional
from config.parameters import VEHICLE_SPEED_GRAVEL_KMH, VEHICLE_SPEED_PAVED_KMH


def calculate_equity_score(
    road_data: dict,
    facilities_data: Optional[dict] = None,
    population_data: Optional[dict] = None,
    cba_results: Optional[dict] = None,
) -> dict:
    """
    Calculate a composite equity score for a road project.

    Combines two indices (each 0-100):
    - Accessibility (70%): Time saved reaching facilities
    - Facility access (30%): Facilities along the corridor

    Args:
        road_data: Output from skills.osm_lookup.search_road()
        facilities_data: Output from skills.osm_facilities.find_facilities()
        population_data: Deferred and ignored pending verified methodology.
        cba_results: Output from engine.cba.run_cba()

    Returns:
        Dict with overall score, active indices, classification, and breakdown
    """
    road_length = road_data.get("total_length_km", 10.0) if road_data else 10.0

    accessibility = _accessibility_index(road_length, facilities_data)
    facility_access = _facility_access_index(facilities_data)

    # Weighted composite
    overall = (
        accessibility * 0.70
        + facility_access * 0.30
    )
    overall = round(min(100, max(0, overall)))

    return {
        "overall_score": overall,
        "accessibility_index": round(accessibility),
        "facility_access_index": round(facility_access),
        "classification": _classify_score(overall),
        "breakdown": {
            "weights": {
                "accessibility": 0.70,
                "facility_access": 0.30,
            },
            "road_length_km": road_length,
            "time_saving_description": _time_saving_description(road_length),
            "population_methodology": "Deferred pending verified Uganda population methodology.",
        },
    }


def get_equity_summary(equity_results: dict) -> str:
    """
    Generate a markdown summary of equity results.

    Args:
        equity_results: Output from calculate_equity_score()

    Returns:
        Markdown string summarising the equity assessment
    """
    score = equity_results["overall_score"]
    cls = equity_results["classification"]
    lines = [
        f"## Equity Assessment",
        f"",
        f"**Overall Score: {score}/100** — {cls}",
        f"",
        f"| Index | Score | Weight |",
        f"|-------|-------|--------|",
        f"| Accessibility | {equity_results['accessibility_index']}/100 | 70% |",
        f"| Facility Access | {equity_results['facility_access_index']}/100 | 30% |",
        f"",
        f"*Population-based equity metrics are deferred pending a verified Uganda population methodology.*",
    ]

    breakdown = equity_results.get("breakdown", {})
    if breakdown.get("time_saving_description"):
        lines.append(f"")
        lines.append(f"**Travel time impact:** {breakdown['time_saving_description']}")

    return "\n".join(lines)

def _accessibility_index(
    road_length_km: float,
    facilities_data: Optional[dict],
) -> float:
    """
    Accessibility index (0-100): time saved reaching facilities.

    Based on speed improvement from gravel to paved road.
    Longer roads and more facilities = higher score.
    """
    # Time to traverse on gravel vs paved
    time_gravel_min = (road_length_km / VEHICLE_SPEED_GRAVEL_KMH) * 60
    time_paved_min = (road_length_km / VEHICLE_SPEED_PAVED_KMH) * 60
    time_saved_min = time_gravel_min - time_paved_min

    # Normalize: 0-30 minutes saved -> 0-100
    time_score = min(100, (time_saved_min / 30) * 100)

    # Bonus for facilities served
    facility_count = 0
    if facilities_data:
        facility_count = facilities_data.get("total_count", 0)

    facility_bonus = min(20, facility_count * 0.5)

    return min(100, time_score + facility_bonus)

def _facility_access_index(
    facilities_data: Optional[dict],
) -> float:
    """
    Facility access index (0-100): facilities within corridor.
    """
    if not facilities_data:
        return 30.0  # Default

    total_facilities = facilities_data.get("total_count", 0)
    return min(100, total_facilities * 2)


def _classify_score(score: int) -> str:
    """Classify the overall equity score."""
    if score >= 80:
        return "Very high positive equity impact"
    elif score >= 60:
        return "High positive equity impact"
    elif score >= 40:
        return "Moderate positive equity impact"
    elif score >= 20:
        return "Low positive equity impact"
    else:
        return "Minimal equity impact"


def _time_saving_description(road_length_km: float) -> str:
    """Generate a human-readable time saving description."""
    time_gravel = (road_length_km / VEHICLE_SPEED_GRAVEL_KMH) * 60
    time_paved = (road_length_km / VEHICLE_SPEED_PAVED_KMH) * 60
    saving = time_gravel - time_paved

    return (
        f"Travel time reduced from {time_gravel:.0f} min to {time_paved:.0f} min "
        f"(saving {saving:.0f} min per trip on {road_length_km:.1f} km)"
    )
