"""
TARA Agent Orchestrator
Manages the Opus 4.6 agent loop: API calls, tool execution, and state management.
Uses the synchronous Anthropic client for Streamlit compatibility.
"""

import json
import os
from typing import Optional, Any, Callable
import anthropic

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool


MAX_ITERATIONS = 10
MODEL = "claude-sonnet-4-5-20250929"

TOOL_LABELS = {
    "search_road": "Searching for road on OpenStreetMap",
    "find_facilities": "Finding nearby facilities",
    "get_population": "Getting population data from WorldPop",
    "forecast_traffic": "Forecasting traffic",
    "run_cba": "Running cost-benefit analysis",
    "run_sensitivity": "Running sensitivity analysis",
    "create_map": "Creating map",
    "validate_inputs": "Validating inputs",
    "calculate_equity": "Calculating equity score",
    "generate_report": "Generating report",
    "analyze_dashcam": "Analysing road condition",
}


def _emit(on_progress: Optional[Callable], event_type: str, data: dict) -> None:
    """Safely call the progress callback if provided."""
    if on_progress:
        on_progress(event_type, data)


def _tool_input_summary(tool_name: str, tool_input: dict) -> str:
    """Build a human-readable summary of what a tool call is doing."""
    label = TOOL_LABELS.get(tool_name, tool_name.replace("_", " ").title())

    if tool_name == "search_road":
        road = tool_input.get("road_name", "")
        country = tool_input.get("country", "")
        detail = f": {road}" + (f", {country}" if country else "")
    elif tool_name == "find_facilities":
        detail = ""
    elif tool_name == "get_population":
        detail = ""
    elif tool_name == "run_cba":
        parts = []
        if tool_input.get("road_length_km"):
            parts.append(f"{tool_input['road_length_km']}km")
        if tool_input.get("total_cost_usd"):
            cost_m = tool_input["total_cost_usd"] / 1_000_000
            parts.append(f"${cost_m:.1f}M cost")
        if tool_input.get("adt"):
            parts.append(f"{tool_input['adt']} ADT")
        detail = f": {', '.join(parts)}" if parts else ""
    elif tool_name == "run_sensitivity":
        detail = ""
    elif tool_name == "generate_report":
        detail = ""
    elif tool_name == "analyze_dashcam":
        detail = ""
    else:
        detail = ""

    return f"{label}{detail}"


def create_agent() -> dict:
    """
    Initialize agent state.

    Returns:
        Dict containing messages list, tool definitions, and metadata.
    """
    return {
        "messages": [],
        "tools": TOOL_DEFINITIONS,
        "system_prompt": SYSTEM_PROMPT,
        "model": MODEL,
        "road_data": None,
        "facilities_data": None,
        "population_data": None,
        "cba_results": None,
        "sensitivity_results": None,
        "equity_results": None,
        "condition_data": None,
        "report_pdf": None,
        "maps": [],
    }


def process_message_sync(
    agent_state: dict,
    user_message: str,
    api_key: Optional[str] = None,
    on_progress: Optional[Callable] = None,
) -> tuple[str, dict, list]:
    """
    Process a user message through the agent loop.

    Uses the synchronous Anthropic client. Loops: call API → if tool_use,
    execute tools and append results → repeat until end_turn or max iterations.

    Args:
        agent_state: Current agent state dict
        user_message: The user's message text
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        on_progress: Optional callback(event_type, data) for live UI updates

    Returns:
        Tuple of (response_text, updated_agent_state, list_of_maps)
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "I need an Anthropic API key to function. Please set the ANTHROPIC_API_KEY environment variable.",
            agent_state,
            [],
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Add user message to history
    agent_state["messages"].append({
        "role": "user",
        "content": user_message,
    })

    maps_collected: list = []
    response_text = ""

    for iteration in range(MAX_ITERATIONS):
        # Call the API
        _emit(on_progress, "thinking", {"iteration": iteration})
        try:
            response = client.messages.create(
                model=agent_state["model"],
                max_tokens=4096,
                system=agent_state["system_prompt"],
                tools=agent_state["tools"],
                messages=agent_state["messages"],
            )
        except anthropic.APIError as e:
            error_msg = f"API error: {str(e)}"
            agent_state["messages"].append({
                "role": "assistant",
                "content": error_msg,
            })
            return error_msg, agent_state, maps_collected

        # Process the response
        assistant_content = response.content
        agent_state["messages"].append({
            "role": "assistant",
            "content": assistant_content,
        })

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract text from response
            response_text = _extract_text(assistant_content)
            break

        if response.stop_reason == "tool_use":
            # Execute all tool calls and collect results
            tool_results = []

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Inject agent state for tools that need it
                    if tool_name == "generate_report":
                        tool_input["_road_data"] = agent_state.get("road_data")
                        tool_input["_facilities_data"] = agent_state.get("facilities_data")
                        tool_input["_population_data"] = agent_state.get("population_data")
                        tool_input["_cba_results"] = agent_state.get("cba_results")
                        tool_input["_sensitivity_results"] = agent_state.get("sensitivity_results")
                        tool_input["_equity_results"] = agent_state.get("equity_results")
                        tool_input["_condition_data"] = agent_state.get("condition_data")
                    elif tool_name == "analyze_dashcam":
                        tool_input["_road_data"] = agent_state.get("road_data")

                    # Execute the tool
                    _emit(on_progress, "tool_start", {
                        "tool": tool_name,
                        "input_summary": _tool_input_summary(tool_name, tool_input),
                    })
                    result = execute_tool(tool_name, tool_input)

                    # Collect maps
                    if "map" in result:
                        maps_collected.append(result["map"])

                    # Store key data in agent state
                    _update_agent_state(agent_state, tool_name, result)

                    _emit(on_progress, "tool_done", {
                        "tool": tool_name,
                        "summary": result.get("summary", "Done"),
                    })

                    # Build tool result content for the API
                    # Send the summary + truncated result (not full data)
                    api_result = result.get("summary", "")
                    if result.get("error"):
                        api_result = f"Error: {result['error']}"
                    elif result.get("result"):
                        # Include the result data for the model to reference
                        result_json = json.dumps(
                            result["result"], default=str, indent=2
                        )
                        # Truncate if too long
                        if len(result_json) > 8000:
                            result_json = result_json[:8000] + "\n... (truncated)"
                        api_result = f"{result.get('summary', '')}\n\nData:\n{result_json}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": api_result,
                    })

            # Add tool results to messages
            agent_state["messages"].append({
                "role": "user",
                "content": tool_results,
            })
            _emit(on_progress, "continuing", {"iteration": iteration})
        else:
            # Unknown stop reason — extract text and return
            response_text = _extract_text(assistant_content)
            break
    else:
        # Max iterations reached
        response_text = _extract_text(assistant_content)
        if not response_text:
            response_text = "I've reached the maximum number of steps. Here's what I have so far — please ask me to continue if needed."

    return response_text, agent_state, maps_collected


def _extract_text(content: list) -> str:
    """Extract text blocks from an API response content list."""
    text_parts = []
    for block in content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return "\n".join(text_parts)


def _update_agent_state(agent_state: dict, tool_name: str, result: dict) -> None:
    """Update agent state with key data from tool results."""
    if tool_name == "search_road" and "_road_data" in result:
        agent_state["road_data"] = result["_road_data"]

    elif tool_name == "find_facilities" and "_facilities_data" in result:
        agent_state["facilities_data"] = result["_facilities_data"]

    elif tool_name == "get_population" and "_population_data" in result:
        agent_state["population_data"] = result["_population_data"]

    elif tool_name == "run_cba" and "_full_result" in result:
        agent_state["cba_results"] = result["_full_result"]

    elif tool_name == "run_sensitivity":
        agent_state["sensitivity_results"] = result.get("result")

    elif tool_name == "calculate_equity" and "_equity_results" in result:
        agent_state["equity_results"] = result["_equity_results"]

    elif tool_name == "analyze_dashcam" and "_condition_data" in result:
        agent_state["condition_data"] = result["_condition_data"]

    elif tool_name == "generate_report" and "_report_data" in result:
        report_data = result["_report_data"]
        if report_data.get("_pdf_bytes"):
            agent_state["report_pdf"] = report_data["_pdf_bytes"]

    if "map" in result:
        agent_state["maps"].append(result["map"])
