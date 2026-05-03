"""
TARA Cost-Benefit Analysis Engine
Calculates NPV, EIRR, BCR, and year-by-year cashflows for road investment appraisal.
"""

from typing import Optional
from config.parameters import (
    EOCK,
    ANALYSIS_PERIOD,
    BASE_YEAR,
    RESIDUAL_VALUE_FACTOR,
    VEHICLE_CLASSES,
    VOC_RATES,
    VOT_RATES,
    ACCIDENT_RATES,
    MAINTENANCE_COSTS,
    ECONOMIC_CONVERSION,
    DEFAULT_CONSTRUCTION_YEARS,
    DEFAULT_CONSTRUCTION_PHASING,
    SCF,
)
from engine.traffic import forecast_traffic


def run_cba(
    traffic_forecast: Optional[dict] = None,
    road_length_km: float = 10.0,
    construction_cost_total: float = 5_000_000.0,
    construction_years: int = DEFAULT_CONSTRUCTION_YEARS,
    construction_phasing: Optional[dict[int, float]] = None,
    discount_rate: float = EOCK,
    analysis_period: int = ANALYSIS_PERIOD,
    base_year: int = BASE_YEAR,
    base_adt: Optional[float] = None,
    growth_rate: Optional[float] = None,
    vehicle_split: Optional[dict[str, float]] = None,
    voc_without: Optional[dict[str, float]] = None,
    voc_with: Optional[dict[str, float]] = None,
    vot_without: Optional[dict[str, float]] = None,
    vot_with: Optional[dict[str, float]] = None,
    accident_without: Optional[dict[str, float]] = None,
    accident_with: Optional[dict[str, float]] = None,
    maintenance_without: Optional[dict] = None,
    maintenance_with: Optional[dict] = None,
    include_generated_traffic: bool = True,
    residual_value_factor: float = RESIDUAL_VALUE_FACTOR,
) -> dict:
    """
    Run a full cost-benefit analysis for a road project.

    Args:
        traffic_forecast: Pre-computed forecast from engine.traffic.forecast_traffic().
            If None, will be computed from base_adt and growth_rate.
        road_length_km: Road length in km
        construction_cost_total: Total financial construction cost (USD)
        construction_years: Number of construction years
        construction_phasing: Dict {year_number: share}, e.g. {1: 0.4, 2: 0.3, 3: 0.3}
        discount_rate: Economic discount rate (default: EOCK = 12%)
        analysis_period: Years of operation
        base_year: Calendar base year
        base_adt: Base ADT (used if traffic_forecast is None)
        growth_rate: Traffic growth rate (used if traffic_forecast is None)
        vehicle_split: Vehicle class shares
        voc_without/with: VOC rates (USD/veh-km) by class
        vot_without/with: VoT rates (USD/veh-km) by class
        accident_without/with: Accident rates (USD/veh-km) by class
        maintenance_without/with: Maintenance cost dicts
        include_generated_traffic: Whether to include generated traffic benefits
        residual_value_factor: Fraction of construction cost as residual value

    Returns:
        Dict with NPV, EIRR, BCR, FYRR, year-by-year cashflows, summary.
    """
    # Generate traffic forecast if not provided
    if traffic_forecast is None:
        if base_adt is None:
            raise ValueError("Either traffic_forecast or base_adt must be provided")
        traffic_forecast = forecast_traffic(
            base_adt=base_adt,
            growth_rate=growth_rate,
            analysis_period=analysis_period,
            construction_years=construction_years,
            road_length_km=road_length_km,
            vehicle_split=vehicle_split,
            base_year=base_year,
        )

    # Apply defaults
    if construction_phasing is None:
        construction_phasing = DEFAULT_CONSTRUCTION_PHASING
    voc_wo = voc_without or VOC_RATES["without_project"]
    voc_w = voc_with or VOC_RATES["with_project"]
    vot_wo = vot_without or VOT_RATES["without_project"]
    vot_w = vot_with or VOT_RATES["with_project"]
    acc_wo = accident_without or ACCIDENT_RATES["without_project"]
    acc_w = accident_with or ACCIDENT_RATES["with_project"]
    maint_wo = maintenance_without or MAINTENANCE_COSTS["without_project"]
    maint_w = maintenance_with or MAINTENANCE_COSTS["with_project"]

    # Convert construction cost to economic prices
    econ_construction_cost = financial_to_economic(construction_cost_total)

    total_years = construction_years + analysis_period
    yearly_cashflows = []

    for year_data in traffic_forecast["yearly"]:
        year_idx = year_data["year_index"]
        calendar_year = year_data["calendar_year"]
        is_construction = year_data["is_construction"]

        # --- COSTS ---

        # Construction costs (during construction years only)
        construction_cost_year = 0.0
        if is_construction:
            phase_year = year_idx + 1  # 1-indexed
            phase_share = construction_phasing.get(phase_year, 0.0)
            construction_cost_year = econ_construction_cost * phase_share

        # Maintenance costs
        maint_cost_without = _annual_maintenance_cost(
            maint_wo, road_length_km, year_idx, construction_years, is_project=False
        )
        maint_cost_with = _annual_maintenance_cost(
            maint_w, road_length_km, year_idx, construction_years, is_project=True
        )
        # Net maintenance = with_project - without_project (incremental cost)
        net_maintenance = maint_cost_with - maint_cost_without

        total_cost = construction_cost_year + net_maintenance

        # --- BENEFITS ---
        benefits_voc = 0.0
        benefits_vot = 0.0
        benefits_accident = 0.0
        benefits_generated = 0.0

        if not is_construction:
            # User benefits for normal traffic (per vehicle class)
            for vc in VEHICLE_CLASSES:
                normal_vkm = year_data["by_class"][vc]["annual_vkm"]
                share = traffic_forecast["vehicle_split"].get(vc, 0)
                # Recalculate normal_vkm from normal_adt
                normal_adt = year_data["normal_adt"] * share
                normal_annual_vkm = normal_adt * road_length_km * 365

                # VOC savings
                voc_saving_per_vkm = voc_wo.get(vc, 0) - voc_w.get(vc, 0)
                benefits_voc += normal_annual_vkm * voc_saving_per_vkm

                # VoT savings
                vot_saving_per_vkm = vot_wo.get(vc, 0) - vot_w.get(vc, 0)
                benefits_vot += normal_annual_vkm * vot_saving_per_vkm

                # Accident savings
                acc_saving_per_vkm = acc_wo.get(vc, 0) - acc_w.get(vc, 0)
                benefits_accident += normal_annual_vkm * acc_saving_per_vkm

            # Generated traffic benefits (rule of half)
            if include_generated_traffic and year_data["generated_adt"] > 0:
                for vc in VEHICLE_CLASSES:
                    share = traffic_forecast["vehicle_split"].get(vc, 0)
                    gen_adt = year_data["generated_adt"] * share
                    gen_annual_vkm = gen_adt * road_length_km * 365

                    total_saving_per_vkm = (
                        (voc_wo.get(vc, 0) - voc_w.get(vc, 0))
                        + (vot_wo.get(vc, 0) - vot_w.get(vc, 0))
                        + (acc_wo.get(vc, 0) - acc_w.get(vc, 0))
                    )
                    # Rule of half: generated traffic benefits = 50% of saving
                    benefits_generated += gen_annual_vkm * total_saving_per_vkm * 0.5

        total_benefits = benefits_voc + benefits_vot + benefits_accident + benefits_generated

        # Residual value in final year
        residual_value = 0.0
        if year_idx == total_years - 1:
            residual_value = econ_construction_cost * residual_value_factor

        net_benefit = total_benefits - total_cost + residual_value

        yearly_cashflows.append({
            "year_index": year_idx,
            "calendar_year": calendar_year,
            "is_construction": is_construction,
            "costs": {
                "construction": round(construction_cost_year, 0),
                "net_maintenance": round(net_maintenance, 0),
                "total": round(total_cost, 0),
            },
            "benefits": {
                "voc_savings": round(benefits_voc, 0),
                "vot_savings": round(benefits_vot, 0),
                "accident_savings": round(benefits_accident, 0),
                "generated_traffic": round(benefits_generated, 0),
                "residual_value": round(residual_value, 0),
                "total": round(total_benefits + residual_value, 0),
            },
            "net_benefit": round(net_benefit, 0),
        })

    # Extract net benefit stream for NPV/EIRR
    net_benefits = [cf["net_benefit"] for cf in yearly_cashflows]

    npv = calculate_npv(net_benefits, discount_rate)
    eirr = calculate_eirr(net_benefits)

    # BCR = PV(benefits) / PV(costs)
    pv_benefits = calculate_npv(
        [cf["benefits"]["total"] for cf in yearly_cashflows], discount_rate
    )
    pv_costs = calculate_npv(
        [cf["costs"]["total"] for cf in yearly_cashflows], discount_rate
    )
    bcr = pv_benefits / pv_costs if pv_costs > 0 else float("inf")

    # FYRR = net benefit in first full year of operation / remaining investment
    fyrr = None
    first_op_cf = next(
        (cf for cf in yearly_cashflows if not cf["is_construction"]), None
    )
    if first_op_cf and econ_construction_cost > 0:
        fyrr = first_op_cf["net_benefit"] / econ_construction_cost

    npv_per_km = npv / road_length_km if road_length_km > 0 else 0

    return {
        "npv": round(npv, 0),
        "eirr": round(eirr, 4) if eirr is not None else None,
        "bcr": round(bcr, 2),
        "fyrr": round(fyrr, 4) if fyrr is not None else None,
        "npv_per_km": round(npv_per_km, 0),
        "discount_rate": discount_rate,
        "economic_construction_cost": round(econ_construction_cost, 0),
        "pv_benefits": round(pv_benefits, 0),
        "pv_costs": round(pv_costs, 0),
        "yearly_cashflows": yearly_cashflows,
        "traffic_forecast": traffic_forecast,
        "summary": {
            "npv_usd": round(npv, 0),
            "eirr_pct": round(eirr * 100, 1) if eirr is not None else None,
            "bcr": round(bcr, 2),
            "fyrr_pct": round(fyrr * 100, 1) if fyrr is not None else None,
            "npv_per_km_usd": round(npv_per_km, 0),
            "economically_viable": npv > 0 and (eirr is None or eirr > discount_rate),
            "recommendation": _get_recommendation(npv, eirr, bcr, discount_rate),
        },
    }


def financial_to_economic(
    financial_cost: float,
    conversion_factors: Optional[dict] = None,
) -> float:
    """
    Convert financial cost to economic cost using shadow pricing.

    Applies:
    - SCF to imported materials
    - Shadow wage factor to unskilled labour
    - Removes taxes
    - Passes through skilled labour at market rate

    Args:
        financial_cost: Financial cost in USD
        conversion_factors: Override conversion factor shares

    Returns:
        Economic cost in USD
    """
    cf = conversion_factors or ECONOMIC_CONVERSION

    imported = financial_cost * cf["imported_materials_share"] * SCF
    local = financial_cost * cf["local_materials_share"] * SCF
    skilled = financial_cost * cf["skilled_labour_share"] * cf["skilled_labour_factor"]
    unskilled = financial_cost * cf["unskilled_labour_share"] * cf["shadow_wage_unskilled"]
    # Taxes are removed (not included in economic cost)

    return imported + local + skilled + unskilled


def calculate_npv(cashflows: list[float], discount_rate: float) -> float:
    """
    Calculate Net Present Value of a cashflow stream.

    Args:
        cashflows: List of annual cashflows (year 0 first)
        discount_rate: Annual discount rate (decimal)

    Returns:
        NPV in same currency units as cashflows
    """
    npv = 0.0
    for t, cf in enumerate(cashflows):
        npv += cf / (1 + discount_rate) ** t
    return npv


def calculate_eirr(cashflows: list[float]) -> Optional[float]:
    """
    Calculate Economic Internal Rate of Return.

    Uses scipy.optimize.brentq to find the rate where NPV = 0.

    Args:
        cashflows: List of annual net benefit cashflows

    Returns:
        EIRR as decimal, or None if cannot be calculated
    """
    try:
        from scipy.optimize import brentq
    except ImportError:
        # Fallback: simple iterative search
        return _eirr_iterative(cashflows)

    def npv_at_rate(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))

    # Check if there's a sign change (required for IRR to exist)
    try:
        npv_low = npv_at_rate(0.001)
        npv_high = npv_at_rate(2.0)
    except (OverflowError, ZeroDivisionError):
        return None

    if npv_low * npv_high > 0:
        # No sign change — try wider range
        try:
            npv_neg = npv_at_rate(5.0)
            if npv_low * npv_neg > 0:
                return None
            npv_high = npv_neg
            upper = 5.0
        except (OverflowError, ZeroDivisionError):
            return None
    else:
        upper = 2.0

    try:
        eirr = brentq(npv_at_rate, 0.001, upper, xtol=1e-6, maxiter=200)
        return eirr
    except (ValueError, RuntimeError):
        return None


def _eirr_iterative(cashflows: list[float]) -> Optional[float]:
    """Fallback EIRR calculation without scipy."""
    best_rate = None
    best_npv = float("inf")

    for rate_pct in range(1, 200):
        rate = rate_pct / 100.0
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
        if abs(npv) < abs(best_npv):
            best_npv = npv
            best_rate = rate

    if best_rate is not None and abs(best_npv) < abs(cashflows[0]) * 0.01:
        return best_rate
    return None


def _annual_maintenance_cost(
    maint_params: dict,
    road_length_km: float,
    year_idx: int,
    construction_years: int,
    is_project: bool,
) -> float:
    """Calculate annual maintenance cost for a given year."""
    if year_idx < construction_years:
        # During construction: without-project maintenance continues on existing road
        if not is_project:
            return maint_params.get("routine_annual", 0) * road_length_km
        return 0.0

    operation_year = year_idx - construction_years

    # Routine annual maintenance
    cost = maint_params.get("routine_annual", 0) * road_length_km

    if is_project:
        # Periodic maintenance
        freq = maint_params.get("periodic_frequency_years", 10)
        if freq > 0 and operation_year > 0 and operation_year % freq == 0:
            cost += maint_params.get("periodic", 0) * road_length_km
    else:
        # Without project: major periodic
        freq = maint_params.get("major_frequency_years", 10)
        if freq > 0 and operation_year > 0 and operation_year % freq == 0:
            cost += maint_params.get("major_periodic", 0) * road_length_km

    return cost


def _get_recommendation(
    npv: float, eirr: Optional[float], bcr: float, discount_rate: float
) -> str:
    """Generate a recommendation based on CBA results."""
    if npv <= 0:
        return "NOT VIABLE: NPV is negative. The project costs exceed its benefits at the given discount rate."

    if eirr is not None and eirr < discount_rate:
        return "MARGINAL: EIRR is below the discount rate. Consider re-scoping or cost reduction."

    if bcr < 1.0:
        return "NOT VIABLE: BCR is below 1.0."

    if bcr >= 2.0:
        return "HIGHLY VIABLE: Strong economic returns. Recommend proceeding."
    elif bcr >= 1.5:
        return "VIABLE: Good economic returns. Recommend proceeding subject to sensitivity analysis."
    else:
        return "VIABLE: Positive returns but modest. Proceed with caution and verify key assumptions."
