"""
TARA: Transport Assessment & Road Appraisal
Main Streamlit Application

"From road data to investment decision — in minutes, not months."
"""

import streamlit as st
import json
import os
import tempfile
from datetime import datetime
from dotenv import load_dotenv

from skills.osm_lookup import search_road, get_road_summary
from skills.osm_facilities import find_facilities, get_facilities_summary, calculate_distances_to_road
from output.maps import create_road_map

load_dotenv()

# Check if agent mode is enabled (default: True)
USE_AGENT = os.environ.get("USE_AGENT", "true").lower() in ("true", "1", "yes")

if USE_AGENT:
    from agent.orchestrator import create_agent, process_message_sync

# --- Page Config ---
st.set_page_config(
    page_title="TARA — Transport Assessment & Road Appraisal",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "road_data" not in st.session_state:
    st.session_state.road_data = None
if "facilities_data" not in st.session_state:
    st.session_state.facilities_data = None
if "analysis_inputs" not in st.session_state:
    st.session_state.analysis_inputs = {}
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "stage" not in st.session_state:
    st.session_state.stage = "start"  # start -> road_found -> inputs -> analysis -> report
if USE_AGENT and "agent_state" not in st.session_state:
    st.session_state.agent_state = create_agent()


# ============================================================
# Handler Functions (defined before use)
# ============================================================

def _handle_agent_message(prompt: str):
    """Process a message through the Opus 4.6 agent."""
    with st.chat_message("assistant"):
        with st.status("TARA is working...", expanded=True) as status:

            def on_progress(event_type, data):
                if event_type == "thinking":
                    status.update(label="TARA is thinking...")
                elif event_type == "tool_start":
                    st.write(f"\u23f3 {data['input_summary']}")
                elif event_type == "tool_done":
                    summary = data.get("summary", "Done")
                    st.write(f"\u2705 {summary[:120]}")
                elif event_type == "continuing":
                    status.update(label="TARA is thinking...")

            response_text, updated_state, maps = process_message_sync(
                st.session_state.agent_state,
                prompt,
                on_progress=on_progress,
            )
            status.update(label="Analysis complete", state="complete", expanded=False)

        st.markdown(response_text)

        # Display any maps returned
        if maps:
            from streamlit_folium import st_folium
            for m in maps:
                st_folium(m, width=700, height=450, returned_objects=[])

        # Display charts if CBA/sensitivity results are available
        charts = []
        if updated_state.get("cba_results") and updated_state.get("sensitivity_results"):
            try:
                from output.charts import (
                    create_waterfall_chart,
                    create_cashflow_chart,
                    create_traffic_growth_chart,
                    create_tornado_chart,
                    create_scenario_chart,
                )
                cba = updated_state["cba_results"]
                sens = updated_state["sensitivity_results"]

                charts = [
                    create_waterfall_chart(cba),
                    create_tornado_chart(sens),
                    create_traffic_growth_chart(cba),
                    create_scenario_chart(sens),
                    create_cashflow_chart(cba),
                ]
            except Exception:
                pass

        if charts:
            st.markdown("### Analysis Charts")
            cols = st.columns(2)
            for i, chart in enumerate(charts):
                with cols[i % 2]:
                    st.plotly_chart(chart, use_container_width=True)

        # PDF download inline
        if updated_state.get("report_pdf"):
            road_name = "Road"
            if updated_state.get("road_data", {}).get("name"):
                road_name = updated_state["road_data"]["name"].replace(" ", "_")
            date_str = datetime.now().strftime("%Y%m%d")
            st.download_button(
                "Download Full Report (PDF)",
                data=updated_state["report_pdf"],
                file_name=f"TARA_Report_{road_name}_{date_str}.pdf",
                mime="application/pdf",
            )

        # Update session state from agent state
        st.session_state.agent_state = updated_state

        if updated_state.get("road_data"):
            st.session_state.road_data = updated_state["road_data"]
            st.session_state.stage = "road_found"
        if updated_state.get("facilities_data"):
            st.session_state.facilities_data = updated_state["facilities_data"]
        if updated_state.get("population_data"):
            st.session_state.population_data = updated_state["population_data"]
        if updated_state.get("cba_results"):
            st.session_state.analysis_results = updated_state["cba_results"]
            st.session_state.stage = "analysis"
        if updated_state.get("report_pdf"):
            st.session_state.stage = "report"

        # Store message
        msg_data = {"role": "assistant", "content": response_text}
        if maps:
            msg_data["maps"] = maps
        if charts:
            msg_data["charts"] = charts
        st.session_state.messages.append(msg_data)


def _handle_road_search(prompt: str):
    """Handle a road search request (legacy mode)."""
    with st.chat_message("assistant"):
        road_name = _extract_road_name(prompt)

        st.markdown(f"🔍 Searching for **{road_name}** on OpenStreetMap...")

        with st.spinner("Querying OpenStreetMap..."):
            road_data = search_road(road_name, "Uganda")

        if not road_data.get("found"):
            msg = (
                f"I couldn't find **{road_name}** on OpenStreetMap. "
                "Could you try:\n"
                "- A more specific name (e.g., 'Kira-Kasangati-Matugga road')\n"
                "- Including nearby towns\n"
                "- The road number if it has one"
            )
            st.markdown(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})
            return

        st.session_state.road_data = road_data

        summary = get_road_summary(road_data)
        st.markdown("✅ **Road found!**\n\n" + summary)

        st.markdown("\n🏥 Searching for nearby facilities...")
        with st.spinner("Finding health centres, schools, markets..."):
            facilities_data = find_facilities(road_data["bbox"], buffer_km=3.0)

            for cat, items in facilities_data["facilities"].items():
                if items and road_data.get("coordinates_all"):
                    facilities_data["facilities"][cat] = calculate_distances_to_road(
                        items, road_data["coordinates_all"]
                    )

        st.session_state.facilities_data = facilities_data

        fac_summary = get_facilities_summary(facilities_data)
        st.markdown(fac_summary)

        road_map = create_road_map(road_data, facilities_data)
        from streamlit_folium import st_folium
        st_folium(road_map, width=700, height=450, returned_objects=[])

        next_msg = (
            "\n---\n"
            "### What I found\n"
            f"I've identified the road ({road_data['total_length_km']}km) and "
            f"found {facilities_data['total_count']} facilities within 3km of the corridor.\n\n"
            "### What I need from you\n"
            "To run the economic appraisal, I need:\n"
            "1. **Traffic count** — Average Daily Traffic by vehicle class (or total ADT)\n"
            "2. **Construction cost** — Total cost or cost per km for the proposed improvement\n"
            "3. **Current condition** — Road roughness (IRI) or general condition (good/fair/poor)\n\n"
            "You can provide these now, or I can estimate them and you validate.\n\n"
            "*Or upload a dashcam video/image and I'll assess the condition for you.*"
        )
        st.markdown(next_msg)

        full_msg = f"✅ **Road found!**\n\n{summary}\n\n{fac_summary}\n{next_msg}"
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_msg,
            "map": road_map,
        })

        st.session_state.stage = "road_found"


def _handle_input_response(prompt: str):
    """Handle user providing analysis inputs (legacy mode)."""
    with st.chat_message("assistant"):
        st.markdown("Thank you! Let me process those inputs and run the analysis...")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Thank you! Processing inputs... (Use agent mode for full analysis)"
        })


def _handle_general_message(prompt: str):
    """Handle general conversation (legacy mode)."""
    with st.chat_message("assistant"):
        msg = "I'm ready to help with road appraisal. Tell me a road name to get started!"
        st.markdown(msg)
        st.session_state.messages.append({"role": "assistant", "content": msg})


def _extract_road_name(prompt: str) -> str:
    """Extract road name from a natural language prompt."""
    lower = prompt.lower()
    for prefix in ["appraise the", "appraise", "assess the", "assess",
                    "find the", "find", "search for", "look up", "analyse the",
                    "analyze the"]:
        if lower.startswith(prefix):
            prompt = prompt[len(prefix):].strip()
            break

    for suffix in [" road upgrade", " upgrade", " improvement", " project",
                   " rehabilitation", " please", " for me"]:
        if prompt.lower().endswith(suffix):
            prompt = prompt[:-len(suffix)].strip()
            break

    if "road" not in prompt.lower() and "highway" not in prompt.lower():
        prompt = prompt + " road"

    return prompt.strip()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/road.png", width=60)
    st.title("TARA")
    st.caption("Transport Assessment & Road Appraisal")
    st.markdown("---")

    if USE_AGENT:
        st.markdown("### Mode")
        st.success("AI Agent (Opus 4.6)")

    st.markdown("### Current Stage")
    stages = {
        "start": "🔍 Waiting for road name...",
        "road_found": "🗺️ Road found — gathering data",
        "inputs": "📝 Collecting inputs",
        "analysis": "📊 Running analysis",
        "report": "📄 Report ready",
    }
    st.info(stages.get(st.session_state.stage, "Unknown"))

    if st.session_state.road_data and st.session_state.road_data.get("found"):
        st.markdown("### Road Summary")
        rd = st.session_state.road_data
        st.metric("Length", f"{rd['total_length_km']} km")
        st.metric("Segments", rd["segment_count"])
        if rd["attributes"].get("surface_types"):
            st.metric("Surface", ", ".join(rd["attributes"]["surface_types"]))

    if st.session_state.facilities_data:
        fd = st.session_state.facilities_data
        st.markdown("### Nearby Facilities")
        for cat, items in fd["facilities"].items():
            if items:
                st.metric(cat.title(), len(items))

    if st.session_state.get("population_data") and st.session_state.population_data.get("found"):
        pd_data = st.session_state.population_data
        st.markdown("### Population (WorldPop)")
        buf_5km = pd_data["buffers"].get("5.0km", pd_data["buffers"].get("5km"))
        if buf_5km and buf_5km.get("population"):
            st.metric("Corridor (5km)", f"{buf_5km['population']:,}")
            st.metric("Density", f"{buf_5km['density_per_km2']:,.0f}/km²")
        st.metric("Classification", pd_data.get("classification", "unknown").title())
        pov = pd_data.get("poverty_estimate", {})
        if pov.get("population_in_poverty"):
            st.metric("Est. in Poverty", f"{pov['population_in_poverty']:,}")

    # Equity score in sidebar
    if USE_AGENT and st.session_state.get("agent_state", {}).get("equity_results"):
        eq = st.session_state.agent_state["equity_results"]
        st.markdown("### Equity Score")
        st.metric("Overall", f"{eq['overall_score']}/100")
        st.caption(eq.get("classification", ""))

    # Condition score in sidebar
    if USE_AGENT and st.session_state.get("agent_state", {}).get("condition_data"):
        cd = st.session_state.agent_state["condition_data"]
        if cd.get("found"):
            st.markdown("### Road Condition")
            st.metric("Score", f"{cd['overall_condition']}/100")
            st.caption(f"Surface: {cd.get('surface_type', 'unknown').title()}")

    # PDF download button
    if USE_AGENT and st.session_state.get("agent_state", {}).get("report_pdf"):
        st.markdown("### Report")
        road_name = "Road"
        if st.session_state.road_data and st.session_state.road_data.get("name"):
            road_name = st.session_state.road_data["name"].replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        st.download_button(
            "Download Report (PDF)",
            data=st.session_state.agent_state["report_pdf"],
            file_name=f"TARA_Report_{road_name}_{date_str}.pdf",
            mime="application/pdf",
        )

    st.markdown("---")
    st.markdown(
        "Built for the [Anthropic Claude Code Hackathon](https://cerebralvalley.ai/e/claude-code-hackathon) "
        "| Feb 2026"
    )


# ============================================================
# Main Chat Interface
# ============================================================

st.title("🛣️ TARA")
st.markdown("*Transport Assessment & Road Appraisal — From road data to investment decision in minutes.*")
st.markdown("---")

# Display welcome message
if not st.session_state.messages:
    welcome = (
        "Hello! I'm **TARA**, your Transport Assessment & Road Appraisal assistant.\n\n"
        "Tell me the name of a road you'd like to appraise, and I'll:\n"
        "1. Find it on OpenStreetMap and extract its geometry\n"
        "2. Identify nearby health facilities, schools, and markets\n"
        "3. Gather population and poverty data for the corridor\n"
        "4. Run a full economic appraisal with sensitivity analysis\n"
        "5. Assess equity impact and generate a professional report\n\n"
        "**Try:** *\"Appraise the Kasangati-Matugga road\"*"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display maps if attached to message
        if message.get("maps"):
            from streamlit_folium import st_folium
            for m in message["maps"]:
                st_folium(m, width=700, height=450, returned_objects=[])
        elif message.get("map"):
            from streamlit_folium import st_folium
            st_folium(message["map"], width=700, height=450, returned_objects=[])

        # Display charts if attached to message
        if message.get("charts"):
            cols = st.columns(2)
            for i, chart in enumerate(message["charts"]):
                with cols[i % 2]:
                    st.plotly_chart(chart, use_container_width=True)


# --- Chat Input ---
if prompt := st.chat_input("Name a road to appraise (e.g., 'Kasangati-Matugga road')"):

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if USE_AGENT:
        _handle_agent_message(prompt)
    else:
        # Legacy direct-call flow
        if st.session_state.stage == "start" or "appraise" in prompt.lower() or "road" in prompt.lower():
            _handle_road_search(prompt)
        elif st.session_state.stage == "inputs":
            _handle_input_response(prompt)
        else:
            _handle_general_message(prompt)


# --- File Upload for Dashcam ---
if st.session_state.stage in ["road_found", "inputs", "analysis"]:
    st.markdown("---")
    uploaded_file = st.file_uploader(
        "📹 Upload dashcam video or image for condition assessment",
        type=["mp4", "avi", "mov", "mkv", "jpg", "jpeg", "png"],
        help="Upload a drive-through video or road photo. TARA will analyse road condition using Vision AI."
    )
    if uploaded_file:
        # Determine media type
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext in ("jpg", "jpeg", "png"):
            media_type = "image"
        else:
            media_type = "video"

        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        st.info(f"📹 {media_type.title()} uploaded! Triggering condition analysis...")

        if USE_AGENT:
            # Inject a message to trigger dashcam analysis
            dashcam_prompt = (
                f"Please analyse this dashcam {media_type} for road condition. "
                f"The file is saved at: {tmp_path}"
            )
            st.session_state.messages.append({"role": "user", "content": f"[Uploaded {media_type}: {uploaded_file.name}]"})
            _handle_agent_message(dashcam_prompt)
