# TARA — Transport Appraisal & Risk Analysis

> From dashcam footage to investment decision — in hours, not weeks.

TARA is an AI-powered road appraisal tool that uses Claude Opus 4.6 to transform dashcam footage into complete economic appraisals with equity assessment. Built for the Anthropic Claude Code Hackathon (February 2026).

## What It Does

Upload dashcam footage and a GPS track from any road. TARA:
- Analyses every frame using Claude Opus 4.6 Vision (TMH12/ASTM D6433 standards)
- Segments the road into homogeneous sections by surface and condition
- Selects appropriate interventions with Uganda-calibrated costs
- Runs full cost-benefit analysis (NPV, EIRR, BCR, FYRR)
- Performs context-aware sensitivity analysis with AI interpretation
- Models road deterioration with and without intervention
- Assesses equity impact — who benefits from this road
- Generates a complete PDF report

## The Problem

Africa needs $181 billion annually in transport infrastructure. 80% of projects fail at feasibility. The bottleneck isn't money — it's project preparation. TARA makes road appraisal accessible to any engineer with a phone and a dashcam.

## Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API key (only needed for new video analysis — cached demo data included)

### Installation
```bash
git clone https://github.com/Kye256/tara-transport-assessment.git
cd tara-transport-assessment
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### Run
```bash
export ANTHROPIC_API_KEY=your_key_here  # optional if using cached data
venv/bin/python app.py
```
Open http://localhost:8050 in your browser.

### Demo Data
The repository includes pre-cached assessment results from roads near Kampala, Uganda. Select a dataset from the dropdown to explore the full workflow — no API key or dashcam footage needed.

To run a new analysis from scratch, you'll need an Anthropic API key and dashcam footage with a matching GPX track.

## How Claude Opus 4.6 Is Used

- **Vision API**: Frame-by-frame road condition assessment from dashcam footage
- **Condition narratives**: AI-written assessment of each road section
- **Sensitivity interpretation**: Context-aware analysis of project risks
- **Equity assessment**: Identifying who depends on the road from camera observations
- **Report generation**: Professional narrative for each section of the appraisal
- **Built with Claude Code**: Multi-agent development workflow with hooks

## Technology Stack

- **Framework**: Dash (Python)
- **AI**: Claude Opus 4.6 (Vision + Text) via Anthropic API
- **Map**: dash-leaflet with CartoDB Positron tiles
- **Data**: OpenStreetMap, WorldPop, UBOS Uganda census
- **Analysis**: Custom CBA engine calibrated with 2024 UNRA HDM-4 parameters

## Project Structure

```
tara-transport-assessment/
├── app.py                  # Main Dash application (7-step wizard + map)
├── agent/                  # Claude Opus 4.6 orchestrator
│   ├── orchestrator.py     # Agent loop with tool_use
│   ├── tools.py            # Tool definitions for the agent
│   └── prompts.py          # System prompts
├── skills/                 # Data gathering modules
│   ├── road_database.py    # Local road database (738 Uganda roads)
│   ├── osm_lookup.py       # OpenStreetMap road search
│   ├── osm_facilities.py   # Nearby facilities (health, education, markets)
│   ├── worldpop.py         # Population data from WorldPop
│   ├── kontur_population.py# Kontur population grid
│   └── dashcam.py          # Dashcam image analysis
├── engine/                 # Analysis modules
│   ├── cba.py              # Cost-benefit analysis (NPV, EIRR, BCR, FYRR)
│   ├── traffic.py          # Traffic forecasting (per-vehicle-class)
│   ├── sensitivity.py      # Sensitivity & scenario analysis
│   └── equity.py           # Equity scoring
├── video/                  # Video processing pipeline
│   ├── video_pipeline.py   # End-to-end dashcam → condition pipeline
│   ├── video_frames.py     # Frame extraction from video clips
│   ├── vision_assess.py    # Claude Vision frame assessment
│   ├── gps_utils.py        # GPX parsing and geo-matching
│   ├── video_map.py        # Condition map generation
│   ├── intervention.py     # Per-section intervention recommendations
│   ├── equity.py           # Equity narrative from video observations
│   ├── datasets.py         # Dataset discovery and cache management
│   └── test_pipeline.py    # Pipeline validation (12 checks)
├── output/                 # Report & chart generation
│   ├── report.py           # PDF report generator
│   ├── charts.py           # Plotly charts (tornado, waterfall, etc.)
│   └── maps.py             # dash-leaflet map components
├── config/
│   └── parameters.py       # Uganda-calibrated default parameters
├── data/
│   ├── uganda_main_roads.geojson          # 738 named roads
│   ├── uganda_main_roads_enriched.geojson # Roads with population data
│   └── videos/*/cache/     # Cached assessment results (for demo)
├── assets/
│   ├── style.css           # Custom styles
│   └── typing.js           # Typing animation
├── scripts/                # Data preprocessing scripts
│   ├── build_road_database.py
│   └── enrich_road_database.py
└── docs/                   # Specifications and planning documents
```

## License

MIT
