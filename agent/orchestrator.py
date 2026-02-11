"""
TARA Agent Orchestrator
Manages the Opus 4.6 agent loop: API calls, tool execution, and state management.
Uses the synchronous Anthropic client for Streamlit compatibility.
"""

import json
import os
from typing import Optional, Any
import anthropic

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool


MAX_ITERATIONS = 10
MODEL = "claude-opus-4-6-20250610"


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
        "cba_results": None,
        "sensitivity_results": None,
        "maps": [],
    }


def process_message_sync(
    agent_state: dict,
    user_message: str,
    api_key: Optional[str] = None,
) -> tuple[str, dict, list]:
    """
    Process a user message through the agent loop.

    Uses the synchronous Anthropic client. Loops: call API → if tool_use,
    execute tools and append results → repeat until end_turn or max iterations.

    Args:
        agent_state: Current agent state dict
        user_message: The user's message text
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

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

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)

                    # Collect maps
                    if "map" in result:
                        maps_collected.append(result["map"])

                    # Store key data in agent state
                    _update_agent_state(agent_state, tool_name, result)

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

    elif tool_name == "run_cba" and "_full_result" in result:
        agent_state["cba_results"] = result["_full_result"]

    elif tool_name == "run_sensitivity":
        agent_state["sensitivity_results"] = result.get("result")

    if "map" in result:
        agent_state["maps"].append(result["map"])
