"""
TARA Equity Scoring Engine
Calculates equity impact scores for road investments based on accessibility,
population benefit, poverty impact, and facility access.
"""

from typing import Optional
from config.parameters import (
    VEHICLE_SPEED_GRAVEL_KMH,
    VEHICLE_SPEED_PAVED_KMH,
    POVERTY_HEADCOUNT_RATIO,
    DENSITY_THRESHOLDS,
)


def calculate_equity_score(
    road_data: dict,
    facilities_data: Optional[dict] = None,
    population_data: Optional[dict] = None,
    cba_results: Optional[dict] = None,
) -> dict:
    """
    Calculate a composite equity score for a road project.

    Combines four indices (each 0-100):
    - Accessibility (30%): Time saved reaching facilities
    - Population benefit (25%): People served in corridor
    - Poverty impact (30%): Benefit to poor populations
    - Facility access (15%): Facilities per capita

    Args:
        road_data: Output from skills.osm_lookup.search_road()
        facilities_data: Output from skills.osm_facilities.find_facilities()
        population_data: Output from skills.worldpop.get_population()
        cba_results: Output from engine.cba.run_cba()

    Returns:
        Dict with overall score, individual indices, classification, and breakdown
    """
    road_length = road_data.get("total_length_km", 10.0) if road_data else 10.0
    classification = _get_classification(population_data)

    accessibility = _accessibility_index(road_length, facilities_data)
    population_benefit = _population_benefit_index(population_data, classification)
    poverty_impact = _poverty_impact_index(population_data, cba_results, classification)
    facility_access = _facility_access_index(facilities_data, population_data)

    # Weighted composite
    overall = (
        accessibility * 0.30
        + population_benefit * 0.25
        + poverty_impact * 0.30
        + facility_access * 0.15
    )
    overall = round(min(100, max(0, overall)))

    return {
        "overall_score": overall,
        "accessibility_index": round(accessibility),
        "population_benefit_index": round(population_benefit),
        "poverty_impact_index": round(poverty_impact),
        "facility_access_index": round(facility_access),
        "classification": _classify_score(overall),
        "area_type": classification,
        "breakdown": {
            "weights": {
                "accessibility": 0.30,
                "population_benefit": 0.25,
                "poverty_impact": 0.30,
                "facility_access": 0.15,
            },
            "road_length_km": road_length,
            "time_saving_description": _time_saving_description(road_length),
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
    area = equity_results.get("area_type", "unknown")

    lines = [
        f"## Equity Assessment",
        f"",
        f"**Overall Score: {score}/100** — {cls}",
        f"",
        f"| Index | Score | Weight |",
        f"|-------|-------|--------|",
        f"| Accessibility | {equity_results['accessibility_index']}/100 | 30% |",
        f"| Population Benefit | {equity_results['population_benefit_index']}/100 | 25% |",
        f"| Poverty Impact | {equity_results['poverty_impact_index']}/100 | 30% |",
        f"| Facility Access | {equity_results['facility_access_index']}/100 | 15% |",
        f"",
        f"**Area classification:** {area.title()}",
    ]

    breakdown = equity_results.get("breakdown", {})
    if breakdown.get("time_saving_description"):
        lines.append(f"")
        lines.append(f"**Travel time impact:** {breakdown['time_saving_description']}")

    return "\n".join(lines)


def _get_classification(population_data: Optional[dict]) -> str:
    """Determine area classification from population data."""
    if not population_data or not population_data.get("found"):
        return "rural"
    return population_data.get("classification", "rural")


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


def _population_benefit_index(
    population_data: Optional[dict],
    classification: str,
) -> float:
    """
    Population benefit index (0-100): people in 5km buffer.

    Scaled by classification: rural 0-50k, peri-urban 0-200k, urban 0-500k.
    """
    if not population_data or not population_data.get("found"):
        return 30.0  # Default for missing data

    # Get 5km buffer population
    buffers = population_data.get("buffers", {})
    buf_5km = buffers.get("5.0km", buffers.get("5km", {}))
    population = buf_5km.get("population", 0) if buf_5km else 0

    # Scale based on classification
    scales = {
        "rural": 50_000,
        "peri-urban": 200_000,
        "urban": 500_000,
    }
    max_pop = scales.get(classification, 50_000)

    return min(100, (population / max_pop) * 100)


def _poverty_impact_index(
    population_data: Optional[dict],
    cba_results: Optional[dict],
    classification: str,
) -> float:
    """
    Poverty impact index (0-100): poverty headcount x benefit per capita.

    Higher poverty ratio + more poor people = higher equity score.
    """
    if not population_data or not population_data.get("found"):
        # Use national average
        poverty_ratio = POVERTY_HEADCOUNT_RATIO.get("national", 0.21)
        poor_population = 10_000 * poverty_ratio
    else:
        poverty_est = population_data.get("poverty_estimate", {})
        poverty_ratio = poverty_est.get("poverty_ratio", POVERTY_HEADCOUNT_RATIO.get(classification, 0.21))
        poor_population = poverty_est.get("population_in_poverty", 0)

    # Poverty ratio score (higher poverty = higher equity need)
    ratio_score = min(100, (poverty_ratio / 0.40) * 100)

    # Scale by poor population count
    pop_scale = min(1.0, poor_population / 30_000)

    # Benefit per capita boost from CBA
    benefit_boost = 0.0
    if cba_results and cba_results.get("npv", 0) > 0:
        npv = cba_results["npv"]
        total_pop = poor_population / max(poverty_ratio, 0.01)
        benefit_per_capita = npv / max(total_pop, 1)
        # $0-100 benefit per capita -> 0-20 bonus
        benefit_boost = min(20, (benefit_per_capita / 100) * 20)

    return min(100, ratio_score * pop_scale + benefit_boost)


def _facility_access_index(
    facilities_data: Optional[dict],
    population_data: Optional[dict],
) -> float:
    """
    Facility access index (0-100): facilities within corridor per 10k population.

    0-10 facilities per 10k people -> 0-100 score.
    """
    if not facilities_data:
        return 30.0  # Default

    total_facilities = facilities_data.get("total_count", 0)

    # Get corridor population
    population = 10_000  # Default fallback
    if population_data and population_data.get("found"):
        buffers = population_data.get("buffers", {})
        buf_5km = buffers.get("5.0km", buffers.get("5km", {}))
        if buf_5km and buf_5km.get("population"):
            population = buf_5km["population"]

    if population <= 0:
        population = 10_000

    facilities_per_10k = (total_facilities / population) * 10_000

    # 0-10 facilities per 10k people -> 0-100
    # Inverse: fewer facilities = higher equity need (more benefit from road)
    # But more facilities also means more people benefit from improved access
    # Use a balanced approach: score peaks around 3-5 per 10k
    if facilities_per_10k <= 5:
        # Low facility density: high equity need, road helps access distant facilities
        return min(100, (5 - facilities_per_10k) / 5 * 50 + total_facilities * 2)
    else:
        # Higher density: still beneficial, many facilities get better access
        return min(100, 50 + min(50, total_facilities * 1.5))


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
