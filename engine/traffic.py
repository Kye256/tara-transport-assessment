"""
TARA Traffic Forecasting Engine
Forecasts traffic growth over the analysis period and calculates generalised cost changes.
"""

from typing import Optional
from config.parameters import (
    ANALYSIS_PERIOD,
    BASE_YEAR,
    DEFAULT_TRAFFIC_GROWTH_RATE,
    GDP_GROWTH_RATE,
    TRAFFIC_GDP_ELASTICITY,
    PRICE_ELASTICITY_DEMAND,
    ROAD_CAPACITY,
    VEHICLE_CLASSES,
    VOC_RATES,
    VOT_RATES,
    DEFAULT_CONSTRUCTION_YEARS,
)


def forecast_traffic(
    base_adt: float,
    growth_rate: Optional[float] = None,
    analysis_period: int = ANALYSIS_PERIOD,
    construction_years: int = DEFAULT_CONSTRUCTION_YEARS,
    road_length_km: float = 10.0,
    vehicle_split: Optional[dict[str, float]] = None,
    gdp_growth: Optional[float] = None,
    gdp_elasticity: Optional[float] = None,
    generated_traffic_pct: Optional[float] = None,
    road_type: str = "two_lane_paved",
    base_year: int = BASE_YEAR,
) -> dict:
    """
    Forecast traffic over the analysis period.

    Args:
        base_adt: Base-year Average Daily Traffic (all vehicles)
        growth_rate: Annual growth rate (decimal). If None, derived from GDP.
        analysis_period: Years of operation after construction
        construction_years: Number of construction years
        road_length_km: Road length in km
        vehicle_split: Dict of vehicle class → share (must sum to ~1.0).
            Defaults to Uganda typical split.
        gdp_growth: GDP growth rate for elasticity method
        gdp_elasticity: Traffic-GDP elasticity
        generated_traffic_pct: Override generated traffic as % of normal traffic
        road_type: Road type key for capacity check
        base_year: Calendar year for year 0

    Returns:
        Dict with yearly forecasts, vehicle-km, capacity warnings.
    """
    # Determine growth rate
    if growth_rate is None:
        gdp_g = gdp_growth if gdp_growth is not None else GDP_GROWTH_RATE
        elast = gdp_elasticity if gdp_elasticity is not None else TRAFFIC_GDP_ELASTICITY
        growth_rate = gdp_g * elast

    # Default vehicle split (Uganda typical)
    if vehicle_split is None:
        vehicle_split = {
            "Cars": 0.45,
            "Buses_LGV": 0.25,
            "HGV": 0.20,
            "Semi_Trailers": 0.10,
        }

    # Calculate generalised cost change for generated traffic
    gen_cost_change = calculate_generalised_cost_change(
        VOC_RATES["without_project"],
        VOC_RATES["with_project"],
        VOT_RATES["without_project"],
        VOT_RATES["with_project"],
    )

    # Total analysis years = construction + operation
    total_years = construction_years + analysis_period
    capacity = ROAD_CAPACITY.get(road_type, 8000)

    yearly_forecasts = []
    capacity_warnings = []

    for year_idx in range(total_years):
        calendar_year = base_year + year_idx
        is_construction = year_idx < construction_years
        operation_year = year_idx - construction_years if not is_construction else None

        # Normal traffic growth (compounds from base year)
        normal_adt = base_adt * (1 + growth_rate) ** year_idx

        # Generated traffic only applies after project completion
        if is_construction or generated_traffic_pct is not None:
            gen_pct = generated_traffic_pct if generated_traffic_pct is not None and not is_construction else 0.0
        else:
            gen_pct = abs(PRICE_ELASTICITY_DEMAND * gen_cost_change)

        generated_adt = normal_adt * gen_pct if not is_construction else 0.0
        total_adt = normal_adt + generated_adt

        # Vehicle-km
        total_vkm = total_adt * road_length_km * 365

        # Per-class breakdown
        class_data = {}
        for vc in VEHICLE_CLASSES:
            share = vehicle_split.get(vc, 0.0)
            class_data[vc] = {
                "adt": round(total_adt * share, 1),
                "annual_vkm": round(total_vkm * share, 0),
            }

        # Capacity check
        vc_ratio = total_adt / capacity if capacity > 0 else 0
        if vc_ratio > 0.8:
            capacity_warnings.append({
                "year": calendar_year,
                "adt": round(total_adt, 0),
                "vc_ratio": round(vc_ratio, 2),
                "warning": "congested" if vc_ratio > 1.0 else "approaching capacity",
            })

        yearly_forecasts.append({
            "year_index": year_idx,
            "calendar_year": calendar_year,
            "is_construction": is_construction,
            "operation_year": operation_year,
            "normal_adt": round(normal_adt, 1),
            "generated_adt": round(generated_adt, 1),
            "total_adt": round(total_adt, 1),
            "total_annual_vkm": round(total_vkm, 0),
            "by_class": class_data,
            "vc_ratio": round(vc_ratio, 2),
        })

    return {
        "base_adt": base_adt,
        "growth_rate": growth_rate,
        "analysis_period": analysis_period,
        "construction_years": construction_years,
        "road_length_km": road_length_km,
        "vehicle_split": vehicle_split,
        "road_type": road_type,
        "capacity": capacity,
        "generated_traffic_cost_change": round(gen_cost_change, 4),
        "yearly": yearly_forecasts,
        "capacity_warnings": capacity_warnings,
        "summary": {
            "base_year_adt": base_adt,
            "final_year_adt": round(yearly_forecasts[-1]["total_adt"], 0),
            "total_vkm_over_period": round(
                sum(y["total_annual_vkm"] for y in yearly_forecasts), 0
            ),
            "years_with_capacity_issues": len(capacity_warnings),
        },
    }


def calculate_generalised_cost_change(
    voc_without: dict[str, float],
    voc_with: dict[str, float],
    vot_without: dict[str, float],
    vot_with: dict[str, float],
) -> float:
    """
    Calculate the weighted average generalised cost change (fractional).

    Generalised cost = VOC + VoT. A negative change means costs decreased
    (improvement), positive means costs increased.

    Args:
        voc_without: VOC rates by vehicle class without project
        voc_with: VOC rates by vehicle class with project
        vot_without: VoT rates by vehicle class without project
        vot_with: VoT rates by vehicle class with project

    Returns:
        Weighted average fractional cost change (negative = improvement)
    """
    total_without = 0.0
    total_with = 0.0

    for vc in VEHICLE_CLASSES:
        gc_without = voc_without.get(vc, 0) + vot_without.get(vc, 0)
        gc_with = voc_with.get(vc, 0) + vot_with.get(vc, 0)
        total_without += gc_without
        total_with += gc_with

    if total_without == 0:
        return 0.0

    return (total_with - total_without) / total_without
