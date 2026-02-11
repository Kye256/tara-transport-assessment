# TARA: Transport Assessment & Road Appraisal

## Project Overview
TARA is an AI agent for road project appraisal, built for the Anthropic Claude Code Hackathon (Feb 10-16, 2026). It autonomously gathers data, assesses road condition, runs economic analysis, and produces professional reports.

**Tagline:** "From road data to investment decision — in minutes, not months."

## Architecture
- **Frontend:** Dash (Plotly) with 7-step wizard + persistent map
- **Agent:** Claude Opus 4.6 via Anthropic API with tool_use
- **Data Skills:** OSM (Overpass API), WorldPop, World Bank
- **Analysis Engine:** Python (NumPy/Pandas) — CBA, sensitivity, equity
- **Vision:** Claude Vision API for dashcam road condition analysis
- **Maps:** dash-leaflet (Leaflet.js via Dash)
- **Charts:** Plotly (native in Dash)

## Key Files
- `app.py` — Main Dash application (wizard + map layout)
- `skills/road_database.py` — Local road database (pre-processed Uganda GeoJSON)
- `skills/` — Data gathering modules (OSM facilities, WorldPop, dashcam, etc.)
- `engine/` — Analysis modules (CBA, traffic, sensitivity)
- `agent/` — Opus 4.6 orchestrator with tool definitions
- `output/` — Maps (dash-leaflet), charts (Plotly), report generation
- `config/parameters.py` — Uganda-calibrated default parameters
- `data/uganda_main_roads.geojson` — Processed road network (738 named roads)
- `docs/` — Specifications and planning documents

## Demo Road
Kasangati-Matugga road, Wakiso District, Uganda (part of Kira-Kasangati-Matugga UNRA project, ~10-20km, currently under construction by CICO)

## Current Build Status
- [x] Project scaffolding
- [x] Local road database (738 Uganda main roads from HOT Export)
- [x] Road search dropdown (searchable, local database)
- [x] OSM facilities skill (with retry/backoff)
- [x] Map display (dash-leaflet)
- [x] Dash wizard interface (7-step)
- [x] Uganda default parameters
- [x] Agent orchestrator (Opus 4.6 tool_use)
- [x] CBA calculation engine (per-vehicle-class VOC/VoT)
- [x] Traffic forecasting (per-class breakdown)
- [x] Sensitivity analysis
- [x] Dashcam video analysis
- [x] Manual condition entry (stored in condition-store)
- [x] Equity scoring
- [x] Report generation
- [x] Plotly charts (tornado, waterfall, cashflow, traffic, scenarios)
- [x] WorldPop integration
- [x] Input validation warnings (ADT, cost/km, discount rate, analysis period)

## Conventions
- Python 3.11+
- Type hints on all functions
- Docstrings on all public functions
- Config values in config/parameters.py, not hardcoded
- All costs in USD, distances in km
- Economic parameters: EOCK 12%, FEP 7.5%, NTP 1%
- Python venv: `venv/bin/python` (create with `python3 -m venv venv && venv/bin/pip install -r requirements.txt`)
- Run with: `venv/bin/python app.py` (port 8050)
