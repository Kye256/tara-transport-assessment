"""TMH12/ASTM D6433 Visual Condition Index computation.

Weights, VCI calculation, IRI conversion, condition classification,
and section aggregation using median VCI.
"""

import math

UNPAVED_WEIGHTS = {
    "unpaved_potholes": 0.20,
    "unpaved_corrugation": 0.15,
    "unpaved_erosion": 0.15,
    "unpaved_loose_material": 0.10,
    "unpaved_gravel_condition": 0.10,
    "drainage": 0.15,
    "road_profile": 0.05,
    "riding_quality": 0.10,
}

PAVED_WEIGHTS = {
    "paved_surface_distress": 0.30,
    "paved_deformation": 0.20,
    "paved_edge_condition": 0.15,
    "paved_patching": 0.10,
    "drainage": 0.15,
    "riding_quality": 0.10,
}


def compute_vci(assessment: dict) -> float:
    """Compute Visual Condition Index (0-100) from TMH12 distress scores.

    0 = perfect condition, 100 = worst possible.
    Only components scored >= 0 are included (handles partial visibility).
    Scores of -1 are excluded from the computation.

    Args:
        assessment: dict with surface_type and distress component scores.

    Returns:
        VCI score 0-100, or 50.0 as fallback if nothing scored.
    """
    surface = assessment.get("surface_type", "gravel")

    if surface in ("paved_asphalt", "paved_concrete"):
        weights = PAVED_WEIGHTS
    else:
        weights = UNPAVED_WEIGHTS

    weighted_sum = 0.0
    total_weight = 0.0

    for component, weight in weights.items():
        score = assessment.get(component, -1)
        if isinstance(score, (int, float)) and score >= 0:
            weighted_sum += score * weight
            total_weight += weight

    if total_weight == 0:
        return 50.0  # fallback if nothing scored

    vci = (weighted_sum / (5.0 * total_weight)) * 100.0
    return round(vci, 1)


def vci_to_iri(vci_score: float, surface_type: str) -> tuple[float, float, float]:
    """Convert VCI to IRI estimate using published PCI-IRI relationships.

    Sources:
        Paved: Egypt/Iran PCI-IRI exponential (R² 0.75-0.82)
        Gravel: HDM-4 gravel deterioration ranges
        Earth: World Bank TP46 reference scale

    Args:
        vci_score: Visual Condition Index 0-100.
        surface_type: road surface type string.

    Returns:
        Tuple of (iri_low, iri_mid, iri_high).
    """
    if surface_type in ("paved_asphalt", "paved_concrete"):
        pci_equiv = 100.0 - vci_score
        iri_mid = 16.07 * math.exp(-0.026 * pci_equiv)
        uncertainty = 0.25

    elif surface_type == "surface_treatment":
        pci_equiv = 100.0 - vci_score
        iri_mid = 18.0 * math.exp(-0.024 * pci_equiv)
        uncertainty = 0.30

    elif surface_type == "gravel":
        iri_mid = 6.0 + (vci_score / 100.0) * 14.0
        uncertainty = 0.35

    elif surface_type == "earth":
        iri_mid = 8.0 + (vci_score / 100.0) * 16.0
        uncertainty = 0.40

    else:
        iri_mid = 12.0
        uncertainty = 0.50

    iri_low = max(1.0, round(iri_mid * (1.0 - uncertainty), 1))
    iri_mid = round(iri_mid, 1)
    iri_high = min(24.0, round(iri_mid * (1.0 + uncertainty), 1))

    return (iri_low, iri_mid, iri_high)


def classify_condition(iri_mid: float) -> str:
    """Convert IRI to 6-class condition classification.

    Args:
        iri_mid: mid-estimate IRI in m/km.

    Returns:
        One of: very_good, good, fair, poor, very_poor, impassable.
    """
    if iri_mid <= 3.0:
        return "very_good"
    elif iri_mid <= 5.0:
        return "good"
    elif iri_mid <= 8.0:
        return "fair"
    elif iri_mid <= 12.0:
        return "poor"
    elif iri_mid <= 16.0:
        return "very_poor"
    else:
        return "impassable"


def condition_to_ui_class(condition_class: str) -> str:
    """Map 6-class condition to 4-class UI condition for backward compatibility.

    Args:
        condition_class: 6-class condition string.

    Returns:
        One of: good, fair, poor, bad (4-class for UI/section breaking).
    """
    mapping = {
        "very_good": "good",
        "good": "good",
        "fair": "fair",
        "poor": "poor",
        "very_poor": "bad",
        "impassable": "bad",
    }
    return mapping.get(condition_class, "fair")


def aggregate_section(frame_assessments: list[dict]) -> dict | None:
    """Aggregate per-frame assessments into section-level summary.

    Uses median VCI (robust to outlier frames).

    Args:
        frame_assessments: list of raw tool_use assessment dicts.

    Returns:
        Section summary dict, or None if no assessments.
    """
    if not frame_assessments:
        return None

    vcis = [compute_vci(a) for a in frame_assessments]
    vci_median = sorted(vcis)[len(vcis) // 2]

    # Dominant surface type (mode)
    surfaces = [a.get("surface_type", "gravel") for a in frame_assessments]
    surface_mode = max(set(surfaces), key=surfaces.count)

    iri_low, iri_mid, iri_high = vci_to_iri(vci_median, surface_mode)
    condition = classify_condition(iri_mid)

    # Per-component averages for the report
    if surface_mode in ("paved_asphalt", "paved_concrete"):
        components = list(PAVED_WEIGHTS.keys())
    else:
        components = list(UNPAVED_WEIGHTS.keys())

    distress_summary = {}
    for comp in components:
        scores = [a.get(comp, -1) for a in frame_assessments]
        valid = [s for s in scores if s >= 0]
        distress_summary[comp] = round(sum(valid) / len(valid), 1) if valid else None

    # Equity aggregation from flat fields
    total_peds = sum(a.get("pedestrian_count", 0) for a in frame_assessments)
    peds_on_road = sum(1 for a in frame_assessments if a.get("pedestrians_on_road"))
    total_cyclists = sum(a.get("cyclist_motorcycle_count", 0) for a in frame_assessments)

    all_facilities: list[str] = []
    for a in frame_assessments:
        fac = a.get("facilities_visible", [])
        all_facilities.extend([f for f in fac if f != "none"])

    all_vehicles: list[str] = []
    for a in frame_assessments:
        vt = a.get("vehicle_types", [])
        all_vehicles.extend([v for v in vt if v != "none"])

    nmt_provisions = [a.get("nmt_infrastructure", "not_visible") for a in frame_assessments]
    nmt_worst = "no_provision" if "no_provision" in nmt_provisions else (
        "usable_shoulder" if "usable_shoulder" in nmt_provisions else "separated_footpath"
    )

    return {
        "vci": vci_median,
        "iri_low": iri_low,
        "iri_mid": iri_mid,
        "iri_high": iri_high,
        "condition_class": condition,
        "surface_type": surface_mode,
        "n_frames": len(frame_assessments),
        "distress_summary": distress_summary,
        "equity_summary": {
            "total_pedestrians": total_peds,
            "frames_with_pedestrians_on_road": peds_on_road,
            "total_cyclists_motorcycles": total_cyclists,
            "facilities_observed": list(set(all_facilities)),
            "vehicle_types_observed": list(set(all_vehicles)),
            "nmt_provision": nmt_worst,
        },
    }
