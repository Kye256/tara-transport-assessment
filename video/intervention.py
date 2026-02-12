"""Intervention recommendation module for road condition assessment.

Provides Uganda-calibrated intervention selection based on surface type
and condition class, with cost estimates and design life parameters.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


# ---------------------------------------------------------------------------
# Intervention table (Uganda-calibrated costs)
# ---------------------------------------------------------------------------

INTERVENTIONS: dict[str, dict[str, Any]] = {
    "REG": {
        "code": "REG",
        "name": "Regravelling",
        "cost_per_km": 60_000,
        "design_life": 5,
        "maintenance_per_km_yr": 5_000,
    },
    "DBST": {
        "code": "DBST",
        "name": "Upgrade to DBST",
        "cost_per_km": 800_000,
        "design_life": 10,
        "maintenance_per_km_yr": 8_000,
    },
    "AC": {
        "code": "AC",
        "name": "Upgrade to Asphalt Concrete",
        "cost_per_km": 1_000_000,
        "design_life": 15,
        "maintenance_per_km_yr": 10_000,
    },
    "REHAB": {
        "code": "REHAB",
        "name": "Rehabilitation",
        "cost_per_km": 600_000,
        "design_life": 12,
        "maintenance_per_km_yr": 10_000,
    },
    "PM": {
        "code": "PM",
        "name": "Periodic Maintenance (Overlay)",
        "cost_per_km": 150_000,
        "design_life": 8,
        "maintenance_per_km_yr": 8_000,
    },
    "DUAL": {
        "code": "DUAL",
        "name": "Dualling",
        "cost_per_km": 2_000_000,
        "design_life": 20,
        "maintenance_per_km_yr": 15_000,
    },
    "DUAL_NMT": {
        "code": "DUAL_NMT",
        "name": "Dualling + NMT Facilities",
        "cost_per_km": 2_500_000,
        "design_life": 20,
        "maintenance_per_km_yr": 18_000,
    },
    "RM": {
        "code": "RM",
        "name": "Routine Maintenance Only",
        "cost_per_km": 5_000,
        "design_life": 1,
        "maintenance_per_km_yr": 5_000,
    },
}

# ---------------------------------------------------------------------------
# Surface-type classification helpers
# ---------------------------------------------------------------------------

_UNPAVED_SURFACES = {"earth", "gravel"}
_PAVED_SURFACES = {"asphalt", "dbst", "paved", "paved_asphalt"}

# ---------------------------------------------------------------------------
# Reasoning templates
# ---------------------------------------------------------------------------

_REASONING_UNPAVED = (
    "Unpaved {surface} surface warrants upgrade to DBST to reduce vehicle "
    "operating costs and provide all-weather access."
)

_REASONING_PAVED: dict[str, str] = {
    "good": (
        "Paved {surface} surface in good condition requires only routine "
        "maintenance to preserve the existing asset."
    ),
    "fair": (
        "Paved {surface} surface in fair condition benefits from a periodic "
        "maintenance overlay to arrest deterioration before costly rehabilitation "
        "is needed."
    ),
    "poor": (
        "Paved {surface} surface in poor condition requires rehabilitation to "
        "restore structural integrity and ride quality."
    ),
    "bad": (
        "Paved {surface} surface in bad condition requires rehabilitation to "
        "restore structural integrity and prevent further asset loss."
    ),
}

_REASONING_UNKNOWN = (
    "Surface type is unknown; DBST upgrade is recommended as a safe default "
    "to ensure all-weather passability."
)

# ---------------------------------------------------------------------------
# Alternative suggestions
# ---------------------------------------------------------------------------

_ALTERNATIVES_UNPAVED: list[str] = ["AC", "REG"]
_ALTERNATIVES_PAVED: dict[str, list[str]] = {
    "good": ["PM"],
    "fair": ["RM", "REHAB"],
    "poor": ["AC", "PM"],
    "bad": ["AC", "PM"],
}
_ALTERNATIVES_UNKNOWN: list[str] = ["AC", "REG"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_intervention(code: str) -> dict[str, Any]:
    """Return the intervention dict for a given code.

    Args:
        code: Intervention code (e.g. ``'DBST'``, ``'REHAB'``).

    Returns:
        A dict containing ``code``, ``name``, ``cost_per_km``,
        ``design_life``, and ``maintenance_per_km_yr``.

    Raises:
        KeyError: If *code* is not a recognised intervention code.
    """
    code_upper = code.strip().upper()
    if code_upper not in INTERVENTIONS:
        raise KeyError(
            f"Unknown intervention code '{code}'. "
            f"Valid codes: {', '.join(sorted(INTERVENTIONS))}"
        )
    return dict(INTERVENTIONS[code_upper])


def get_all_interventions() -> list[dict[str, Any]]:
    """Return a list of all available intervention dicts.

    Returns:
        List of dicts, each containing ``code``, ``name``,
        ``cost_per_km``, ``design_life``, and ``maintenance_per_km_yr``.
    """
    return [dict(v) for v in INTERVENTIONS.values()]


def recommend_intervention(section: dict[str, Any]) -> dict[str, Any]:
    """Recommend an intervention for a single road section.

    Args:
        section: Dict with keys ``surface_type``, ``condition_class``,
            ``avg_iri``, and ``length_km``.

    Returns:
        Dict with keys ``code``, ``name``, ``cost_per_km``,
        ``design_life``, ``maintenance_per_km_yr``, ``section_cost``,
        ``reasoning``, and ``alternatives``.
    """
    surface = (section.get("surface_type") or "").strip().lower()
    condition = (section.get("condition_class") or "").strip().lower()
    length_km = float(section.get("length_km", 0))

    # --- Selection logic ---------------------------------------------------

    if surface in _UNPAVED_SURFACES:
        code = "DBST"
        reasoning = _REASONING_UNPAVED.format(surface=surface)
        alternatives = list(_ALTERNATIVES_UNPAVED)

    elif surface in _PAVED_SURFACES:
        condition_map: dict[str, str] = {
            "good": "RM",
            "fair": "PM",
            "poor": "REHAB",
            "bad": "REHAB",
        }
        code = condition_map.get(condition, "PM")
        reasoning = _REASONING_PAVED.get(condition, _REASONING_PAVED["fair"]).format(
            surface=surface
        )
        alternatives = list(_ALTERNATIVES_PAVED.get(condition, _ALTERNATIVES_PAVED["fair"]))

    else:
        # Unknown surface type
        code = "DBST"
        reasoning = _REASONING_UNKNOWN
        alternatives = list(_ALTERNATIVES_UNKNOWN)

    # --- Build result ------------------------------------------------------

    intervention = INTERVENTIONS[code]
    section_cost = round(intervention["cost_per_km"] * length_km, 2)

    return {
        "code": intervention["code"],
        "name": intervention["name"],
        "cost_per_km": intervention["cost_per_km"],
        "design_life": intervention["design_life"],
        "maintenance_per_km_yr": intervention["maintenance_per_km_yr"],
        "section_cost": section_cost,
        "reasoning": reasoning,
        "alternatives": alternatives,
    }


def recommend_interventions_for_route(
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Recommend interventions for every section along a route.

    Args:
        sections: List of section dicts from GeoJSON feature properties.
            Each must contain ``surface_type``, ``condition_class``,
            ``avg_iri``, ``length_km``, and ``section_index``.

    Returns:
        Dict with ``sections`` (list of per-section results) and
        ``route_summary`` containing ``total_length_km``,
        ``total_cost``, ``dominant_intervention``, and ``narrative``.
    """
    results: list[dict[str, Any]] = []
    total_length = 0.0
    total_cost = 0.0
    intervention_counter: Counter[str] = Counter()

    for sec in sections:
        intervention = recommend_intervention(sec)
        length_km = float(sec.get("length_km", 0))
        total_length += length_km
        total_cost += intervention["section_cost"]
        intervention_counter[intervention["code"]] += 1

        results.append(
            {
                "section_index": sec.get("section_index", 0),
                "length_km": length_km,
                "surface": (sec.get("surface_type") or "unknown").strip().lower(),
                "condition": (sec.get("condition_class") or "unknown").strip().lower(),
                "intervention": intervention,
            }
        )

    # --- Dominant intervention ---------------------------------------------

    if intervention_counter:
        dominant_code = intervention_counter.most_common(1)[0][0]
    else:
        dominant_code = "RM"

    dominant_name = INTERVENTIONS[dominant_code]["name"]

    # --- Narrative ---------------------------------------------------------

    n_sections = len(sections)
    total_length_rounded = round(total_length, 1)
    total_cost_rounded = round(total_cost, 2)

    unique_interventions = len(intervention_counter)
    if unique_interventions == 1:
        narrative = (
            f"The route comprises {n_sections} distinct "
            f"section{'s' if n_sections != 1 else ''} spanning "
            f"{total_length_rounded} km. A uniform {dominant_name} "
            f"strategy is recommended across all sections, with an "
            f"estimated total cost of USD {total_cost_rounded:,.2f}."
        )
    else:
        intervention_summary_parts: list[str] = []
        for code, count in intervention_counter.most_common():
            name = INTERVENTIONS[code]["name"]
            intervention_summary_parts.append(f"{name} ({count} section{'s' if count != 1 else ''})")
        interventions_text = ", ".join(intervention_summary_parts)

        narrative = (
            f"The route comprises {n_sections} distinct "
            f"section{'s' if n_sections != 1 else ''} spanning "
            f"{total_length_rounded} km. The recommended interventions "
            f"include {interventions_text}, with an estimated total "
            f"cost of USD {total_cost_rounded:,.2f}."
        )

    return {
        "sections": results,
        "route_summary": {
            "total_length_km": round(total_length, 1),
            "total_cost": round(total_cost, 2),
            "dominant_intervention": dominant_code,
            "narrative": narrative,
        },
    }
