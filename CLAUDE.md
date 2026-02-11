# TARA: Transport Assessment & Road Appraisal

## Project Overview
TARA is an AI agent for road project appraisal, built for the Anthropic Claude Code Hackathon (Feb 10-16, 2026). It autonomously gathers data, assesses road condition, runs economic analysis, and produces professional reports.

**Tagline:** "From road data to investment decision — in minutes, not months."

## Architecture
- **Frontend:** Streamlit with chat interface
- **Agent:** Claude Opus 4.6 via Anthropic API with tool_use
- **Data Skills:** OSM (Overpass API), WorldPop, World Bank
- **Analysis Engine:** Python (NumPy/Pandas) — CBA, sensitivity, equity
- **Vision:** Claude Vision API for dashcam road condition analysis
- **Maps:** Folium
- **Charts:** Plotly

## Key Files
- `app.py` — Main Streamlit application
- `skills/` — Data gathering modules (OSM, WorldPop, etc.)
- `engine/` — Analysis modules (CBA, traffic, sensitivity)
- `agent/` — Opus 4.6 orchestrator with tool definitions
- `output/` — Maps, charts, report generation
- `config/parameters.py` — Uganda-calibrated default parameters
- `docs/` — Specifications and planning documents

## Demo Road
Kasangati-Matugga road, Wakiso District, Uganda (part of Kira-Kasangati-Matugga UNRA project, ~10-20km, currently under construction by CICO)

## Current Build Status
- [x] Project scaffolding
- [x] OSM road lookup skill
- [x] OSM facilities skill  
- [x] Map display (Folium)
- [x] Streamlit chat interface
- [x] Uganda default parameters
- [x] Agent orchestrator (Opus 4.6 tool_use)
- [x] CBA calculation engine
- [x] Traffic forecasting
- [x] Sensitivity analysis
- [ ] Dashcam video analysis
- [ ] Equity scoring
- [ ] Report generation
- [ ] WorldPop integration

## Build Priority
1. Test OSM lookup works for Kasangati-Matugga road
2. Build agent orchestrator with tool_use
3. CBA engine (NPV, EIRR, BCR)
4. Sensitivity analysis
5. Dashcam video pipeline (Thursday)
6. Equity scoring
7. Report generation

## Conventions
- Python 3.11+
- Type hints on all functions
- Docstrings on all public functions
- Config values in config/parameters.py, not hardcoded
- All costs in USD, distances in km
- Economic parameters: EOCK 12%, FEP 7.5%, NTP 1%
