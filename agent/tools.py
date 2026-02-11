"""
TARA Agent Tool Definitions & Dispatcher
Defines the 7 tools available to the Opus 4.6 agent and routes execution.
"""

import json
import traceback
from typing import Any

from skills.osm_lookup import search_road, get_road_summary
from skills.osm_facilities import find_facilities, get_facilities_summary, calculate_distances_to_road
from output.maps import create_road_map
from engine.traffic import forecast_traffic
from engine.cba import run_cba
from engine.sensitivity import run_sensitivity_analysis
from config.parameters import (
    CONSTRUCTION_COST_BENCHMARKS,
    ROAD_CAPACITY,
    IRI_BENCHMARKS,
    DEFAULT_TRAFFIC_GROWTH_RATE,
    VEHICLE_CLASSES,
)


# --- Tool Definitions (Anthropic tool_use format) ---

TOOL_DEFINITIONS = [
    {
        "name": "search_road",
        "description": (
            "Search for a road by name on OpenStreetMap. Returns geometry, length, "
            "surface type, and other attributes. Use this as the first step in any road appraisal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_name": {
                    "type": "string",
                    "description": "Name of the road (e.g., 'Kasangati-Matugga road')",
                },
                "country": {
                    "type": "string",
                    "description": "Country to search in (default: Uganda)",
                    "default": "Uganda",
                },
            },
            "required": ["road_name"],
        },
    },
    {
        "name": "find_facilities",
        "description": (
            "Find health facilities, schools, markets, and other amenities near a road corridor. "
            "Requires a bounding box (typically from search_road results)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "bbox": {
                    "type": "object",
                    "description": "Bounding box with south, north, west, east coordinates",
                    "properties": {
                        "south": {"type": "number"},
                        "north": {"type": "number"},
                        "west": {"type": "number"},
                        "east": {"type": "number"},
                    },
                    "required": ["south", "north", "west", "east"],
                },
                "buffer_km": {
                    "type": "number",
                    "description": "Buffer distance around corridor in km (default: 3.0)",
                    "default": 3.0,
                },
            },
            "required": ["bbox"],
        },
    },
    {
        "name": "forecast_traffic",
        "description": (
            "Forecast traffic over the analysis period. Calculates yearly ADT, "
            "vehicle-km by class, generated traffic, and capacity warnings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "base_adt": {
                    "type": "number",
                    "description": "Base-year Average Daily Traffic (all vehicles)",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Annual growth rate as decimal (e.g., 0.035 for 3.5%). Default: GDP-linked 3.5%",
                },
                "road_length_km": {
                    "type": "number",
                    "description": "Road length in km",
                },
                "construction_years": {
                    "type": "integer",
                    "description": "Number of construction years (default: 3)",
                    "default": 3,
                },
                "road_type": {
                    "type": "string",
                    "description": "Road type for capacity check: single_lane_gravel, two_lane_gravel, two_lane_paved, dual_carriageway",
                    "default": "two_lane_paved",
                },
            },
            "required": ["base_adt", "road_length_km"],
        },
    },
    {
        "name": "run_cba",
        "description": (
            "Run a full cost-benefit analysis. Internally forecasts traffic, then calculates "
            "NPV, EIRR, BCR, FYRR, and year-by-year cashflows. Returns economic viability assessment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_length_km": {
                    "type": "number",
                    "description": "Road length in km",
                },
                "construction_cost_total": {
                    "type": "number",
                    "description": "Total construction cost in USD",
                },
                "base_adt": {
                    "type": "number",
                    "description": "Base-year Average Daily Traffic (all vehicles)",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Annual traffic growth rate as decimal (default: 0.035)",
                },
                "construction_years": {
                    "type": "integer",
                    "description": "Construction period in years (default: 3)",
                    "default": 3,
                },
                "discount_rate": {
                    "type": "number",
                    "description": "Economic discount rate (default: 0.12 = 12%)",
                    "default": 0.12,
                },
            },
            "required": ["road_length_km", "construction_cost_total", "base_adt"],
        },
    },
    {
        "name": "run_sensitivity",
        "description": (
            "Run sensitivity analysis on CBA results. Tests how NPV, EIRR, and BCR change "
            "when construction cost, traffic volume, growth rate, VOC savings, and discount rate are varied. "
            "Also finds switching values and runs optimistic/pessimistic/worst-case scenarios."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_length_km": {
                    "type": "number",
                    "description": "Road length in km",
                },
                "construction_cost_total": {
                    "type": "number",
                    "description": "Total construction cost in USD",
                },
                "base_adt": {
                    "type": "number",
                    "description": "Base-year Average Daily Traffic",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Annual traffic growth rate as decimal",
                },
                "construction_years": {
                    "type": "integer",
                    "description": "Construction period in years (default: 3)",
                    "default": 3,
                },
                "variables_to_test": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Which variables to test. Options: construction_cost, traffic_volume, "
                        "traffic_growth, voc_savings, discount_rate, construction_delay. Default: all."
                    ),
                },
            },
            "required": ["road_length_km", "construction_cost_total", "base_adt"],
        },
    },
    {
        "name": "create_map",
        "description": (
            "Create an interactive map showing the road alignment and nearby facilities. "
            "Returns a Folium map object for display in the UI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "road_data": {
                    "type": "object",
                    "description": "Road data from search_road (pass the full result)",
                },
                "facilities_data": {
                    "type": "object",
                    "description": "Facilities data from find_facilities (optional)",
                },
            },
            "required": ["road_data"],
        },
    },
    {
        "name": "validate_inputs",
        "description": (
            "Validate road appraisal inputs against Uganda benchmarks. Checks construction cost "
            "per km, traffic volume, growth rate, and road condition."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "construction_cost_per_km": {
                    "type": "number",
                    "description": "Construction cost per km in USD",
                },
                "base_adt": {
                    "type": "number",
                    "description": "Base Average Daily Traffic",
                },
                "growth_rate": {
                    "type": "number",
                    "description": "Traffic growth rate as decimal",
                },
                "road_type": {
                    "type": "string",
                    "description": "Type of road improvement (e.g., gravel_to_paved_rural)",
                },
                "iri": {
                    "type": "number",
                    "description": "International Roughness Index (m/km)",
                },
            },
            "required": [],
        },
    },
]


# --- Tool Execution Dispatcher ---

def execute_tool(tool_name: str, tool_input: dict) -> dict[str, Any]:
    """
    Execute a tool and return its result.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        Dict with 'result' (the data) and optionally 'map' (Folium map object),
        or 'error' string on failure.
    """
    try:
        if tool_name == "search_road":
            return _exec_search_road(tool_input)
        elif tool_name == "find_facilities":
            return _exec_find_facilities(tool_input)
        elif tool_name == "forecast_traffic":
            return _exec_forecast_traffic(tool_input)
        elif tool_name == "run_cba":
            return _exec_run_cba(tool_input)
        elif tool_name == "run_sensitivity":
            return _exec_run_sensitivity(tool_input)
        elif tool_name == "create_map":
            return _exec_create_map(tool_input)
        elif tool_name == "validate_inputs":
            return _exec_validate_inputs(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": f"Tool '{tool_name}' failed: {str(e)}\n{traceback.format_exc()}"}


# --- Individual Tool Implementations ---

def _exec_search_road(tool_input: dict) -> dict:
    road_name = tool_input["road_name"]
    country = tool_input.get("country", "Uganda")

    road_data = search_road(road_name, country)

    if not road_data.get("found"):
        return {
            "result": road_data,
            "summary": f"Could not find '{road_name}' on OpenStreetMap. Try a more specific name.",
        }

    summary = get_road_summary(road_data)
    return {
        "result": road_data,
        "summary": f"Found {road_name}: {road_data['total_length_km']}km, "
                   f"{road_data['segment_count']} segments.\n{summary}",
        "_road_data": road_data,  # For internal use by orchestrator
    }


def _exec_find_facilities(tool_input: dict) -> dict:
    bbox = tool_input["bbox"]
    buffer_km = tool_input.get("buffer_km", 3.0)

    facilities_data = find_facilities(bbox, buffer_km=buffer_km)
    summary = get_facilities_summary(facilities_data)

    return {
        "result": _truncate_facilities(facilities_data),
        "summary": summary,
        "_facilities_data": facilities_data,  # Full data for map
    }


def _exec_forecast_traffic(tool_input: dict) -> dict:
    result = forecast_traffic(
        base_adt=tool_input["base_adt"],
        growth_rate=tool_input.get("growth_rate"),
        road_length_km=tool_input.get("road_length_km", 10.0),
        construction_years=tool_input.get("construction_years", 3),
        road_type=tool_input.get("road_type", "two_lane_paved"),
    )

    # Truncate yearly data for API response
    return {
        "result": _truncate_traffic(result),
        "summary": (
            f"Traffic forecast: Base ADT={result['base_adt']}, "
            f"Final year ADT={result['summary']['final_year_adt']}, "
            f"Growth={result['growth_rate']:.1%}, "
            f"Capacity warnings: {result['summary']['years_with_capacity_issues']}"
        ),
        "_full_result": result,
    }


def _exec_run_cba(tool_input: dict) -> dict:
    result = run_cba(
        road_length_km=tool_input["road_length_km"],
        construction_cost_total=tool_input["construction_cost_total"],
        base_adt=tool_input["base_adt"],
        growth_rate=tool_input.get("growth_rate"),
        construction_years=tool_input.get("construction_years", 3),
        discount_rate=tool_input.get("discount_rate", 0.12),
    )

    # Truncate for API
    return {
        "result": _truncate_cba(result),
        "summary": (
            f"CBA Results:\n"
            f"  NPV: ${result['npv']:,.0f}\n"
            f"  EIRR: {result['summary']['eirr_pct']}%\n"
            f"  BCR: {result['bcr']:.2f}\n"
            f"  FYRR: {result['summary']['fyrr_pct']}%\n"
            f"  NPV/km: ${result['npv_per_km']:,.0f}\n"
            f"  Recommendation: {result['summary']['recommendation']}"
        ),
        "_full_result": result,
    }


def _exec_run_sensitivity(tool_input: dict) -> dict:
    base_inputs = {
        "road_length_km": tool_input["road_length_km"],
        "construction_cost_total": tool_input["construction_cost_total"],
        "base_adt": tool_input["base_adt"],
        "growth_rate": tool_input.get("growth_rate"),
        "construction_years": tool_input.get("construction_years", 3),
    }
    variables = tool_input.get("variables_to_test")

    result = run_sensitivity_analysis(base_inputs, variables)

    return {
        "result": result,
        "summary": (
            f"Sensitivity Analysis:\n"
            f"  Base NPV: ${result['base_case']['npv']:,.0f}\n"
            f"  Most sensitive to: {result['summary']['most_sensitive_variable']}\n"
            f"  Viable under all scenarios: {result['summary']['viable_under_all_scenarios']}\n"
            f"  Risk: {result['summary']['risk_assessment']}\n"
            f"  Switching values: {json.dumps(result['switching_values'], indent=2)}"
        ),
    }


def _exec_create_map(tool_input: dict) -> dict:
    road_data = tool_input["road_data"]
    facilities_data = tool_input.get("facilities_data")

    road_map = create_road_map(road_data, facilities_data)

    return {
        "result": {"map_created": True},
        "summary": "Interactive map created showing road alignment and facilities.",
        "map": road_map,
    }


def _exec_validate_inputs(tool_input: dict) -> dict:
    warnings = []
    info = []

    cost_per_km = tool_input.get("construction_cost_per_km")
    base_adt = tool_input.get("base_adt")
    growth_rate = tool_input.get("growth_rate")
    road_type = tool_input.get("road_type", "gravel_to_paved_rural")
    iri = tool_input.get("iri")

    # Validate construction cost
    if cost_per_km is not None:
        benchmarks = CONSTRUCTION_COST_BENCHMARKS.get(road_type, {})
        if benchmarks:
            if cost_per_km < benchmarks.get("low", 0):
                warnings.append(
                    f"Construction cost (${cost_per_km:,.0f}/km) is below the typical "
                    f"low range for {road_type} (${benchmarks['low']:,.0f}/km). "
                    "This may be unrealistically low."
                )
            elif cost_per_km > benchmarks.get("high", float("inf")):
                warnings.append(
                    f"Construction cost (${cost_per_km:,.0f}/km) exceeds the typical "
                    f"high range for {road_type} (${benchmarks['high']:,.0f}/km). "
                    "Verify this is correct."
                )
            else:
                info.append(
                    f"Construction cost (${cost_per_km:,.0f}/km) is within the typical "
                    f"range for {road_type} (${benchmarks['low']:,.0f}-${benchmarks['high']:,.0f}/km)."
                )

    # Validate ADT
    if base_adt is not None:
        if base_adt < 50:
            warnings.append(
                f"ADT of {base_adt} is very low. Verify this is correct — "
                "most roads considered for investment have ADT > 200."
            )
        elif base_adt > 30000:
            warnings.append(
                f"ADT of {base_adt:,.0f} is very high for a single road. "
                "Verify this is not a multi-road corridor aggregate."
            )
        else:
            info.append(f"ADT of {base_adt:,.0f} is plausible.")

    # Validate growth rate
    if growth_rate is not None:
        if growth_rate < 0.01:
            warnings.append(
                f"Growth rate of {growth_rate:.1%} is below 1%. "
                "Uganda's typical range is 2-5%."
            )
        elif growth_rate > 0.07:
            warnings.append(
                f"Growth rate of {growth_rate:.1%} exceeds 7%. "
                "This is aggressive — verify with traffic study data."
            )
        else:
            info.append(f"Growth rate of {growth_rate:.1%} is within typical Uganda range.")

    # Validate IRI
    if iri is not None:
        if iri < 2:
            warnings.append(f"IRI of {iri} m/km is unusually smooth for Uganda conditions.")
        elif iri > 25:
            warnings.append(f"IRI of {iri} m/km exceeds typical range. Road may be impassable.")
        else:
            info.append(f"IRI of {iri} m/km noted.")

    return {
        "result": {
            "valid": len(warnings) == 0,
            "warnings": warnings,
            "info": info,
        },
        "summary": (
            "All inputs look reasonable."
            if not warnings
            else "Input validation warnings:\n" + "\n".join(f"- {w}" for w in warnings)
        ),
    }


# --- Truncation Helpers ---

def _truncate_facilities(data: dict) -> dict:
    """Truncate facility data for API response (keep counts, drop individual items)."""
    truncated = {
        "total_count": data["total_count"],
        "buffer_km": data.get("buffer_km"),
        "by_category": {
            cat: len(items) for cat, items in data.get("facilities", {}).items()
        },
    }
    return truncated


def _truncate_traffic(data: dict) -> dict:
    """Truncate traffic forecast — keep summary + first/last 3 years."""
    yearly = data.get("yearly", [])
    truncated_yearly = yearly[:3] + yearly[-3:] if len(yearly) > 6 else yearly

    return {
        "summary": data["summary"],
        "growth_rate": data["growth_rate"],
        "capacity": data["capacity"],
        "capacity_warnings": data.get("capacity_warnings", []),
        "yearly_sample": truncated_yearly,
    }


def _truncate_cba(data: dict) -> dict:
    """Truncate CBA — keep summary metrics + first/last years of cashflows."""
    cashflows = data.get("yearly_cashflows", [])
    truncated_cf = cashflows[:3] + cashflows[-3:] if len(cashflows) > 6 else cashflows

    return {
        "npv": data["npv"],
        "eirr": data["eirr"],
        "bcr": data["bcr"],
        "fyrr": data["fyrr"],
        "npv_per_km": data["npv_per_km"],
        "discount_rate": data["discount_rate"],
        "economic_construction_cost": data["economic_construction_cost"],
        "pv_benefits": data["pv_benefits"],
        "pv_costs": data["pv_costs"],
        "summary": data["summary"],
        "yearly_cashflows_sample": truncated_cf,
        "traffic_summary": data.get("traffic_forecast", {}).get("summary", {}),
    }
