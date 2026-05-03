"""
TARA Sensitivity Analysis Engine
Tests how CBA results change when key input variables are varied.
"""

import copy
from typing import Optional
from config.parameters import SENSITIVITY_VARIABLES, EOCK
from engine.cba import run_cba, calculate_npv


def run_sensitivity_analysis(
    base_inputs: dict,
    variables_to_test: Optional[list[str]] = None,
) -> dict:
    """
    Run sensitivity analysis by varying key inputs and re-running CBA.

    Args:
        base_inputs: Dict of kwargs for run_cba() representing the base case
        variables_to_test: List of variable names to test.
            Defaults to all in SENSITIVITY_VARIABLES.

    Returns:
        Dict with single-variable results, switching values, and scenarios.
    """
    if variables_to_test is None:
        variables_to_test = list(SENSITIVITY_VARIABLES.keys())

    # Run base case
    base_result = run_cba(**base_inputs)
    base_npv = base_result["npv"]
    base_eirr = base_result["eirr"]
    base_bcr = base_result["bcr"]

    single_variable_results = {}
    switching_values = {}

    for var_name in variables_to_test:
        if var_name not in SENSITIVITY_VARIABLES:
            continue

        var_config = SENSITIVITY_VARIABLES[var_name]
        results = []

        if "test_range" in var_config:
            for change in var_config["test_range"]:
                modified_inputs = _apply_change(base_inputs, var_name, change, is_absolute=(var_name == "traffic_growth"))
                try:
                    result = run_cba(**modified_inputs)
                    results.append({
                        "change": change,
                        "change_pct": round(change * 100, 1) if var_name != "traffic_growth" else None,
                        "change_absolute": change if var_name == "traffic_growth" else None,
                        "npv": round(result["npv"], 0),
                        "eirr": round(result["eirr"], 4) if result["eirr"] is not None else None,
                        "bcr": round(result["bcr"], 2),
                    })
                except Exception:
                    continue

        elif "test_values" in var_config:
            for value in var_config["test_values"]:
                modified_inputs = _apply_value(base_inputs, var_name, value)
                try:
                    result = run_cba(**modified_inputs)
                    results.append({
                        "value": value,
                        "npv": round(result["npv"], 0),
                        "eirr": round(result["eirr"], 4) if result["eirr"] is not None else None,
                        "bcr": round(result["bcr"], 2),
                    })
                except Exception:
                    continue

        single_variable_results[var_name] = results

        # Find switching value
        sv = find_switching_value(var_name, base_inputs, base_npv)
        if sv is not None:
            switching_values[var_name] = round(sv, 4)

    # Run standard scenarios
    scenarios = {}
    for scenario_type in ["optimistic", "pessimistic", "worst_case"]:
        scenario_inputs = build_scenario(base_inputs, scenario_type)
        try:
            result = run_cba(**scenario_inputs)
            scenarios[scenario_type] = {
                "npv": round(result["npv"], 0),
                "eirr": round(result["eirr"], 4) if result["eirr"] is not None else None,
                "bcr": round(result["bcr"], 2),
                "viable": result["npv"] > 0,
            }
        except Exception:
            scenarios[scenario_type] = {"error": "Could not compute"}

    return {
        "base_case": {
            "npv": round(base_npv, 0),
            "eirr": round(base_eirr, 4) if base_eirr is not None else None,
            "bcr": round(base_bcr, 2),
        },
        "single_variable": single_variable_results,
        "switching_values": switching_values,
        "scenarios": scenarios,
        "summary": _build_summary(base_npv, switching_values, scenarios),
    }


def find_switching_value(
    variable_name: str,
    base_inputs: dict,
    base_npv: float,
) -> Optional[float]:
    """
    Find the change in a variable that makes NPV = 0 (switching value).

    Uses bisection search.

    Args:
        variable_name: Name of the variable to test
        base_inputs: Base case CBA inputs
        base_npv: Base case NPV

    Returns:
        The change value (fractional or absolute) where NPV switches sign,
        or None if not found.
    """
    if base_npv <= 0:
        return None  # Already negative

    # Determine search direction and bounds
    is_absolute = (variable_name == "traffic_growth")

    if variable_name in ["construction_cost", "construction_delay"]:
        # NPV decreases as these increase
        low, high = 0.0, 5.0
    elif variable_name in ["traffic_volume", "voc_savings", "traffic_growth"]:
        # NPV decreases as these decrease
        low, high = -0.99, 0.0
        if is_absolute:
            low, high = -0.035, 0.0  # Can't go below -base_growth
    elif variable_name == "discount_rate":
        return None  # Handled differently
    else:
        low, high = -0.99, 5.0

    # Check if switching value exists in range
    try:
        inputs_low = _apply_change(base_inputs, variable_name, low, is_absolute)
        inputs_high = _apply_change(base_inputs, variable_name, high, is_absolute)
        npv_low = run_cba(**inputs_low)["npv"]
        npv_high = run_cba(**inputs_high)["npv"]
    except Exception:
        return None

    if npv_low * npv_high > 0:
        return None  # No sign change in range

    # Bisection
    for _ in range(50):
        mid = (low + high) / 2
        try:
            inputs_mid = _apply_change(base_inputs, variable_name, mid, is_absolute)
            npv_mid = run_cba(**inputs_mid)["npv"]
        except Exception:
            break

        if abs(npv_mid) < 1000:  # Close enough to zero
            return mid

        if npv_mid * npv_low < 0:
            high = mid
        else:
            low = mid

    return (low + high) / 2


def build_scenario(base_inputs: dict, scenario_type: str) -> dict:
    """
    Build a modified input set for a named scenario.

    Args:
        base_inputs: Base case CBA inputs
        scenario_type: One of 'optimistic', 'pessimistic', 'worst_case'

    Returns:
        Modified inputs dict
    """
    inputs = copy.deepcopy(base_inputs)

    if scenario_type == "optimistic":
        # Lower costs, higher traffic
        if "construction_cost_total" in inputs:
            inputs["construction_cost_total"] *= 0.85
        if "base_adt" in inputs:
            inputs["base_adt"] *= 1.15
        if "growth_rate" in inputs and inputs["growth_rate"] is not None:
            inputs["growth_rate"] += 0.01

    elif scenario_type == "pessimistic":
        # Higher costs, lower traffic
        if "construction_cost_total" in inputs:
            inputs["construction_cost_total"] *= 1.20
        if "base_adt" in inputs:
            inputs["base_adt"] *= 0.85
        if "growth_rate" in inputs and inputs["growth_rate"] is not None:
            inputs["growth_rate"] -= 0.01

    elif scenario_type == "worst_case":
        # Much higher costs, much lower traffic, delays
        if "construction_cost_total" in inputs:
            inputs["construction_cost_total"] *= 1.30
        if "base_adt" in inputs:
            inputs["base_adt"] *= 0.70
        if "growth_rate" in inputs and inputs["growth_rate"] is not None:
            inputs["growth_rate"] -= 0.015
        if "construction_years" in inputs:
            inputs["construction_years"] += 2
            # Extend phasing
            cy = inputs["construction_years"]
            inputs["construction_phasing"] = {
                i + 1: 1.0 / cy for i in range(cy)
            }

    # Clear pre-computed traffic forecast so it gets recomputed
    inputs.pop("traffic_forecast", None)

    return inputs


def _apply_change(
    base_inputs: dict, variable_name: str, change: float, is_absolute: bool = False
) -> dict:
    """Apply a percentage or absolute change to a specific variable."""
    inputs = copy.deepcopy(base_inputs)
    inputs.pop("traffic_forecast", None)  # Force recompute

    if variable_name == "construction_cost":
        inputs["construction_cost_total"] = inputs.get(
            "construction_cost_total", 5_000_000
        ) * (1 + change)

    elif variable_name == "traffic_volume":
        inputs["base_adt"] = inputs.get("base_adt", 3000) * (1 + change)

    elif variable_name == "traffic_growth":
        base_growth = inputs.get("growth_rate", 0.035)
        if base_growth is None:
            base_growth = 0.035
        if is_absolute:
            inputs["growth_rate"] = base_growth + change
        else:
            inputs["growth_rate"] = base_growth * (1 + change)

    elif variable_name == "voc_savings":
        # Adjust the gap between with/without VOC rates
        voc_wo = copy.deepcopy(VOC_RATES["without_project"])
        voc_w = copy.deepcopy(VOC_RATES["with_project"])
        for vc in voc_wo:
            saving = voc_wo[vc] - voc_w[vc]
            new_saving = saving * (1 + change)
            voc_w[vc] = voc_wo[vc] - new_saving
        inputs["voc_with"] = voc_w
        inputs["voc_without"] = voc_wo

    elif variable_name == "construction_delay":
        extra_years = int(change) if not is_absolute else int(change)
        base_cy = inputs.get("construction_years", 3)
        inputs["construction_years"] = base_cy + extra_years
        cy = inputs["construction_years"]
        inputs["construction_phasing"] = {i + 1: 1.0 / cy for i in range(cy)}

    elif variable_name == "discount_rate":
        inputs["discount_rate"] = change  # Direct value, not change

    return inputs


def _apply_value(base_inputs: dict, variable_name: str, value: float) -> dict:
    """Apply a direct value for a variable (used for discount_rate, delay)."""
    inputs = copy.deepcopy(base_inputs)
    inputs.pop("traffic_forecast", None)

    if variable_name == "discount_rate":
        inputs["discount_rate"] = value

    elif variable_name == "construction_delay":
        base_cy = inputs.get("construction_years", 3)
        inputs["construction_years"] = base_cy + int(value)
        cy = inputs["construction_years"]
        inputs["construction_phasing"] = {i + 1: 1.0 / cy for i in range(cy)}

    return inputs


def _build_summary(
    base_npv: float, switching_values: dict, scenarios: dict
) -> dict:
    """Build a human-readable summary of sensitivity results."""
    most_sensitive = None
    min_sv = float("inf")
    for var, sv in switching_values.items():
        if abs(sv) < min_sv:
            min_sv = abs(sv)
            most_sensitive = var

    worst_viable = all(
        s.get("viable", False)
        for s in scenarios.values()
        if "error" not in s
    )

    return {
        "most_sensitive_variable": most_sensitive,
        "most_sensitive_switching_value": switching_values.get(most_sensitive) if most_sensitive else None,
        "viable_under_all_scenarios": worst_viable,
        "risk_assessment": (
            "LOW RISK: Project is viable under all tested scenarios."
            if worst_viable
            else "MODERATE/HIGH RISK: Project becomes non-viable under some scenarios."
        ),
    }


# Import VOC_RATES at module level for _apply_change
from config.parameters import VOC_RATES
