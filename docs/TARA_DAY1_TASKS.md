# TARA — Day 1 Task List (Tuesday Feb 10)
## Goal: Project scaffolding + OSM data skill + Dash wizard app

---

## TASK 1: Project Setup (30 min)
- [ ] Create GitHub repo: `tara-transport-assessment`
- [ ] Set up project structure:
```
tara/
├── app.py                  # Dash main app (7-step wizard + map)
├── requirements.txt        # Dependencies
├── README.md              # Project description
├── LICENSE                # MIT
├── .env.example           # API key template
├── config/
│   └── parameters.py      # Uganda calibration defaults (EOCK, FEP, NTP, etc.)
├── skills/
│   ├── __init__.py
│   ├── osm_lookup.py      # OpenStreetMap road finder
│   ├── osm_facilities.py  # Nearby facilities finder
│   ├── worldpop.py        # Population data (Day 2)
│   ├── dashcam.py         # Video analysis (Day 3)
│   └── worldbank.py       # Benchmarks (stretch)
├── engine/
│   ├── __init__.py
│   ├── cba.py             # Cost-benefit analysis
│   ├── traffic.py         # Traffic forecasting
│   ├── sensitivity.py     # Sensitivity analysis
│   └── equity.py          # Equity scoring (Day 4)
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py    # Main agent logic (Opus 4.6 tool use)
│   ├── tools.py           # Tool definitions for Claude API
│   └── prompts.py         # System prompts
├── output/
│   ├── __init__.py
│   ├── report.py          # PDF/DOCX generation
│   ├── charts.py          # Plotly/Matplotlib charts
│   └── maps.py            # dash-leaflet map generation
└── data/
    └── uganda_defaults.json  # Default parameters from UNRA calibration
```
- [ ] Install core dependencies
- [ ] Test that Dash app runs

## TASK 2: OSM Road Lookup Skill (1.5 hrs)
- [ ] Build `skills/osm_lookup.py`:
  - Input: road name + optional location context (e.g., "Kasangati-Matugga road, Uganda")
  - Overpass API query to find the road
  - Extract: geometry (lat/lon points), length, surface type, width, lanes, bridges
  - Return structured data + GeoJSON for map display
- [ ] Test on Kasangati-Matugga road
- [ ] Handle edge cases: road not found, multiple matches, incomplete data

## TASK 3: OSM Facilities Skill (1 hr)
- [ ] Build `skills/osm_facilities.py`:
  - Input: road geometry (buffer zone around corridor)
  - Query OSM for: health facilities, schools, markets, water points
  - Return: list of facilities with name, type, location, distance from road
- [ ] Test on Kasangati-Matugga corridor

## TASK 4: Map Display (45 min)
- [ ] Build `output/maps.py`:
  - dash-leaflet map showing: road alignment, facilities as markers, corridor buffer zone
  - Color-coded by facility type
  - Popup info for each feature
- [ ] Integrate with Dash layout (persistent map panel)

## TASK 5: Dash Wizard Interface (1 hr)
- [ ] Build basic `app.py`:
  - 7-step wizard: Select Road → Condition → Traffic → Costs → Results → Sensitivity → Report
  - Step 1: Search bar with multi-result road selection (user picks from candidates)
  - Persistent map panel (dash-leaflet) beside wizard
  - Each step collects inputs via forms, stored in dcc.Store
- [ ] Connect to OSM skills (search_roads_multi + load_road_by_ids)

## TASK 6: Agent Orchestrator Skeleton (1 hr)
- [ ] Build `agent/orchestrator.py`:
  - Claude Opus 4.6 API call with tool use
  - Define tools: `search_road`, `find_facilities`, `run_cba` (stub), `analyse_video` (stub)
  - Agent decides which tools to call based on user message
  - Return structured response to Dash callbacks
- [ ] Build `agent/tools.py` — tool definitions in Anthropic API format
- [ ] Build `agent/prompts.py` — TARA system prompt

## TASK 7: Config & Default Parameters (30 min)
- [ ] Build `config/parameters.py`:
  - EOCK: 12%
  - FEP: 7.5%
  - NTP: 1%
  - Analysis period: 20 years
  - Vehicle classes + default VOC/VoT/Accident rates from Highway-1 model
  - Default growth rates
  - Default maintenance costs
- [ ] Build `data/uganda_defaults.json`

---

## END OF DAY CHECK
Can we demonstrate this flow?
1. ✅ User types "Appraise the Kasangati-Matugga road"
2. ✅ TARA finds the road on OSM and shows it on a map
3. ✅ TARA shows nearby facilities (health, schools, markets)
4. ✅ TARA presents what it found and what it still needs
5. ⬜ (Tomorrow) User provides inputs → CBA runs → results shown

If tasks 1-5 work, we're on track. Task 6-7 are foundational for tomorrow.

---

## CLAUDE CODE USAGE NOTES

### For building (our development process):
- Use Claude Code to build modules in parallel where possible
- Example: "Build osm_lookup.py and osm_facilities.py in parallel using subagents"
- Use `/agents` to create a TARA-builder subagent if helpful

### For the product (TARA itself at runtime):
- TARA uses Anthropic API with tool_use — NOT Claude Code subagents
- The agent orchestrator calls Claude API with tools defined
- Python functions execute when Claude calls tools
- Results return to Claude for interpretation

### API cost management:
- Use Sonnet for testing/development where possible
- Switch to Opus 4.6 for final demo and production
- Cache OSM/WorldPop results — don't re-fetch every run
- Monitor token usage daily
