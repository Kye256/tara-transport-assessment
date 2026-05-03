"""
TARA Validation Engine
Pure-function validators that flag implausible or out-of-range inputs.
Each function returns a list of issue dicts (level, code, message) or empty list.

Validators are independent of UI and Dash — they can be imported anywhere.
All thresholds sourced from config/parameters.py (per D-05).
"""

from config.parameters import (
    VALIDATION_THRESHOLDS,
    ROAD_CAPACITY,
    IRI_BENCHMARKS,
    CONSTRUCTION_COST_BENCHMARKS,
    GDP_GROWTH_RATE,
    SURFACE_TO_CAPACITY_KEY,
    SURFACE_TO_COST_BENCHMARK,
)


# ── VALD-01 ───────────────────────────────────────────────────────────────────

def validate_traffic_population(
    adt: float | None,
    pop_data: dict | None,
) -> list[dict]:
    """VALD-01: Flag when ADT seems implausibly high relative to catchment population.

    Compares base ADT against the 2km-buffer population. A ratio of
    ADT > population_2km * 0.5 is suspiciously high for a rural road.

    Args:
        adt: Average Daily Traffic (all vehicles, base year).
        pop_data: Dict from WorldPop skill, expected to contain 'population_2km'.
            If None or missing key, validation is skipped.

    Returns:
        List of issue dicts with keys 'level', 'code', 'message'. Empty list if OK.
    """
    if adt is None or pop_data is None:
        return []

    pop_2km = pop_data.get("population_2km")
    if pop_2km is None or pop_2km <= 0:
        return []

    ratio_high = VALIDATION_THRESHOLDS["adt_pop_ratio_high"]

    if adt > pop_2km * ratio_high:
        return [
            {
                "level": "warning",
                "code": "VALD-01",
                "message": (
                    f"ADT of {adt:,.0f} vpd is suspiciously high relative to "
                    f"the 2km catchment population of {pop_2km:,.0f} people "
                    f"(ratio: {adt / pop_2km:.2f}, threshold: >{ratio_high}). "
                    "Check traffic count source."
                ),
            }
        ]

    return []


# ── VALD-02 ───────────────────────────────────────────────────────────────────

def validate_traffic_capacity(
    adt: float | None,
    road_type: str = "two_lane_paved",
) -> list[dict]:
    """VALD-02: Flag capacity exceedance based on road class.

    Uses V/C ratio against ROAD_CAPACITY thresholds. Unknown road types
    default to two_lane_paved capacity. Two thresholds:
      - warning: V/C > 0.8 (approaching capacity)
      - error:   V/C > 1.0 (exceeds capacity)

    Args:
        adt: Average Daily Traffic (vpd).
        road_type: Road capacity key (e.g. 'single_lane_gravel', 'two_lane_paved').
            Unknown keys default to 'two_lane_paved'.

    Returns:
        List of issue dicts. Empty list if within capacity.
    """
    if adt is None:
        return []

    capacity = ROAD_CAPACITY.get(road_type, ROAD_CAPACITY["two_lane_paved"])
    vc_ratio = adt / capacity if capacity > 0 else 0

    error_threshold = VALIDATION_THRESHOLDS["capacity_error_ratio"]
    warning_threshold = VALIDATION_THRESHOLDS["capacity_warning_ratio"]

    if vc_ratio > error_threshold:
        multiplier = adt / capacity
        return [
            {
                "level": "error",
                "code": "VALD-02",
                "message": (
                    f"ADT of {adt:,.0f} exceeds {road_type.replace('_', ' ')} capacity "
                    f"({capacity:,} vpd) by {multiplier:.1f}x "
                    f"(V/C ratio: {vc_ratio:.2f}). Road type or traffic count may be wrong."
                ),
            }
        ]

    if vc_ratio > warning_threshold:
        return [
            {
                "level": "warning",
                "code": "VALD-02",
                "message": (
                    f"ADT of {adt:,.0f} is approaching {road_type.replace('_', ' ')} capacity "
                    f"({capacity:,} vpd) — V/C ratio: {vc_ratio:.2f} "
                    f"(threshold: >{warning_threshold}). Consider upgrading road class."
                ),
            }
        ]

    return []


# ── VALD-03 ───────────────────────────────────────────────────────────────────

# Surface groups for IRI plausibility
_PAVED_SURFACES = {"asphalt", "concrete", "paved"}
_GRAVEL_SURFACES = {"gravel", "compacted", "unpaved"}
_EARTH_SURFACES = {"earth", "dirt"}


def validate_iri_surface(
    surface_type: str,
    iri: float | None,
) -> list[dict]:
    """VALD-03: Flag IRI values that are physically impossible or extreme for the surface type.

    Uses TMH12/HDM-4 IRI benchmarks. Minimum physically possible IRI values:
      - paved: ~2 m/km (brand new asphalt)
      - gravel: ~6 m/km (well-graded compacted gravel)
      - earth: ~12 m/km (formed earth track)

    Args:
        surface_type: OSM surface tag (e.g. 'gravel', 'asphalt', 'earth').
        iri: International Roughness Index in m/km.

    Returns:
        List of issue dicts. Empty list if IRI is plausible.
    """
    if iri is None:
        return []

    surface_lower = surface_type.lower() if surface_type else ""

    gravel_min = VALIDATION_THRESHOLDS["gravel_iri_min"]
    earth_min = VALIDATION_THRESHOLDS["earth_iri_min"]
    paved_max_warn = VALIDATION_THRESHOLDS["paved_iri_max_warning"]
    gravel_max_warn = VALIDATION_THRESHOLDS["gravel_iri_max_warning"]

    if surface_lower in _GRAVEL_SURFACES:
        if iri < gravel_min:
            return [
                {
                    "level": "error",
                    "code": "VALD-03",
                    "message": (
                        f"IRI of {iri:.1f} m/km is physically impossible for a {surface_type} road "
                        f"(minimum is {gravel_min:.0f} m/km per TMH12/HDM-4). "
                        "Check condition assessment source."
                    ),
                }
            ]
        if iri > gravel_max_warn:
            return [
                {
                    "level": "warning",
                    "code": "VALD-03",
                    "message": (
                        f"IRI of {iri:.1f} m/km is extreme for a {surface_type} road "
                        f"(warning threshold: >{gravel_max_warn:.0f} m/km). Verify measurement."
                    ),
                }
            ]

    elif surface_lower in _EARTH_SURFACES:
        if iri < earth_min:
            return [
                {
                    "level": "error",
                    "code": "VALD-03",
                    "message": (
                        f"IRI of {iri:.1f} m/km is physically impossible for an {surface_type} road "
                        f"(minimum is {earth_min:.0f} m/km per TMH12/HDM-4). "
                        "Check condition assessment source."
                    ),
                }
            ]

    elif surface_lower in _PAVED_SURFACES:
        if iri > paved_max_warn:
            return [
                {
                    "level": "warning",
                    "code": "VALD-03",
                    "message": (
                        f"IRI of {iri:.1f} m/km is unusually high for a {surface_type} road "
                        f"(threshold: >{paved_max_warn:.0f} m/km). "
                        "Verify road surface classification or condition assessment."
                    ),
                }
            ]

    return []


# ── VALD-04 ───────────────────────────────────────────────────────────────────

def validate_cost_benchmarks(
    total_cost: float | None,
    road_length_km: float | None,
    road_type: str = "gravel",
) -> list[dict]:
    """VALD-04: Flag project costs outside Uganda benchmark ranges for the road type.

    Compares cost per km against CONSTRUCTION_COST_BENCHMARKS. Uses a
    tolerance factor so estimates don't need to hit the benchmark exactly:
      - warning if cost_per_km < benchmark.low * 0.5 (suspiciously cheap)
      - warning if cost_per_km > benchmark.high * 2.0 (suspiciously expensive)

    Args:
        total_cost: Total project construction cost in USD.
        road_length_km: Road length in km.
        road_type: Surface type tag (e.g. 'gravel', 'asphalt'). Mapped to
            CONSTRUCTION_COST_BENCHMARKS key via SURFACE_TO_COST_BENCHMARK.

    Returns:
        List of issue dicts. Empty list if cost is within tolerable range.
    """
    if total_cost is None or road_length_km is None:
        return []

    if road_length_km <= 0:
        return []

    cost_per_km = total_cost / road_length_km

    # Map surface type to benchmark key
    benchmark_key = SURFACE_TO_COST_BENCHMARK.get(
        road_type.lower() if road_type else "gravel",
        "gravel_to_paved_rural",
    )
    benchmark = CONSTRUCTION_COST_BENCHMARKS.get(benchmark_key, CONSTRUCTION_COST_BENCHMARKS["gravel_to_paved_rural"])

    low_threshold = benchmark["low"] * VALIDATION_THRESHOLDS["cost_low_factor"]
    high_threshold = benchmark["high"] * VALIDATION_THRESHOLDS["cost_high_factor"]

    if cost_per_km < low_threshold:
        return [
            {
                "level": "warning",
                "code": "VALD-04",
                "message": (
                    f"Cost per km of ${cost_per_km:,.0f} is below the minimum Uganda benchmark "
                    f"(${low_threshold:,.0f}/km = {benchmark['low']:,} × 0.5) for "
                    f"{benchmark_key.replace('_', ' ')}. Verify cost estimate."
                ),
            }
        ]

    if cost_per_km > high_threshold:
        return [
            {
                "level": "warning",
                "code": "VALD-04",
                "message": (
                    f"Cost per km of ${cost_per_km:,.0f} exceeds 2× the Uganda benchmark high "
                    f"(${high_threshold:,.0f}/km = {benchmark['high']:,} × 2.0) for "
                    f"{benchmark_key.replace('_', ' ')}. Verify cost estimate."
                ),
            }
        ]

    return []


# ── VALD-05 ───────────────────────────────────────────────────────────────────

def validate_voc_proportionality(
    iri_before: float | None,
    iri_after: float | None,
    voc_savings_pct: float | None,
) -> list[dict]:
    """VALD-05: Flag disproportionate VOC savings relative to IRI improvement.

    A small IRI improvement (< 2 m/km) should not produce large VOC savings
    (> 20% of total benefits). If it does, the VOC rates or IRI values may be wrong.

    Args:
        iri_before: IRI before project (m/km).
        iri_after: IRI after project (m/km).
        voc_savings_pct: VOC savings as a fraction of total economic benefits (0–1).

    Returns:
        List of issue dicts. Empty list if proportionality is reasonable.
    """
    if iri_before is None or iri_after is None or voc_savings_pct is None:
        return []

    iri_delta = iri_before - iri_after
    delta_threshold = VALIDATION_THRESHOLDS["iri_delta_threshold"]
    voc_max = VALIDATION_THRESHOLDS["voc_savings_max_pct"]

    if iri_delta < delta_threshold and voc_savings_pct > voc_max:
        return [
            {
                "level": "warning",
                "code": "VALD-05",
                "message": (
                    f"VOC savings of {voc_savings_pct:.0%} of total benefits seem disproportionate "
                    f"for an IRI improvement of only {iri_delta:.1f} m/km "
                    f"(threshold: delta < {delta_threshold} m/km with VOC savings > {voc_max:.0%}). "
                    "Verify VOC rates or IRI values."
                ),
            }
        ]

    return []


# ── VALD-06 ───────────────────────────────────────────────────────────────────

def validate_growth_elasticity(
    growth_rate_pct: float | None,
) -> list[dict]:
    """VALD-06: Flag traffic growth rates implying a GDP elasticity outside the normal range.

    Uganda nominal GDP growth ~3.5%/year (GDP_GROWTH_RATE). The implied
    traffic-GDP elasticity should be 1.0–1.5 for Uganda. Outside this range
    suggests the growth rate may be unrealistic.

    Args:
        growth_rate_pct: Annual traffic growth rate as a percentage (e.g. 7.0 for 7%).

    Returns:
        List of issue dicts. Empty list if elasticity is within normal range.
    """
    if growth_rate_pct is None or growth_rate_pct == 0:
        return []

    gdp_pct = GDP_GROWTH_RATE * 100  # Convert to percentage for comparison
    elasticity = round(growth_rate_pct / gdp_pct, 4)

    elast_min = VALIDATION_THRESHOLDS["elasticity_min"]
    elast_max = VALIDATION_THRESHOLDS["elasticity_max"]

    if elasticity < elast_min or elasticity > elast_max:
        return [
            {
                "level": "warning",
                "code": "VALD-06",
                "message": (
                    f"Implied traffic-GDP elasticity of {elasticity:.1f} is outside the typical "
                    f"Uganda range ({elast_min}–{elast_max}). "
                    f"Growth rate: {growth_rate_pct}%, GDP growth: {gdp_pct}%. "
                    "Verify traffic growth assumption."
                ),
            }
        ]

    return []


# ── VALD-07 ───────────────────────────────────────────────────────────────────

def validate_eirr_reasonableness(
    eirr_pct: float | None,
) -> list[dict]:
    """VALD-07: Flag exceptionally high EIRR values for verification.

    An EIRR above 40% is unusual for Uganda road projects and may indicate
    an input error (e.g. traffic counts, costs, or benefit duration).

    Args:
        eirr_pct: Economic Internal Rate of Return as a percentage (e.g. 45.0 for 45%).

    Returns:
        List of issue dicts. Empty list if EIRR is within normal range or not set.
    """
    if eirr_pct is None:
        return []

    threshold = VALIDATION_THRESHOLDS["eirr_high_threshold"]

    if eirr_pct > threshold:
        return [
            {
                "level": "warning",
                "code": "VALD-07",
                "message": (
                    f"EIRR of {eirr_pct:.1f}% is exceptionally high — please verify inputs "
                    f"(threshold: >{threshold:.0f}%). "
                    "Check traffic volumes, cost estimates, and benefit assumptions."
                ),
            }
        ]

    return []


# ── Migrated from app.py: validate_adt_range ──────────────────────────────────

def validate_adt_range(
    adt: float | None,
) -> list[dict]:
    """Migrated from app.py: flag extreme ADT values (>50,000 or <10 vpd).

    These thresholds come from the original app.py validate_traffic function
    and are now unified here for consistent reuse.

    Args:
        adt: Average Daily Traffic in vehicles per day.

    Returns:
        List of issue dicts. Empty list if ADT is in plausible range.
    """
    if adt is None:
        return []

    extreme_high = VALIDATION_THRESHOLDS["adt_extreme_high"]
    extreme_low = VALIDATION_THRESHOLDS["adt_extreme_low"]

    if adt > extreme_high:
        return [
            {
                "level": "warning",
                "code": "VALD-ADT",
                "message": (
                    f"ADT of {adt:,.0f} vpd is very high (threshold: >{extreme_high:,}). "
                    "Verify traffic count — this exceeds dual carriageway capacity."
                ),
            }
        ]

    if adt < extreme_low:
        return [
            {
                "level": "warning",
                "code": "VALD-ADT",
                "message": (
                    f"ADT of {adt:.0f} vpd is very low (threshold: <{extreme_low}). "
                    "Verify traffic count — this is lower than a typical footpath."
                ),
            }
        ]

    return []
