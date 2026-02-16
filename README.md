# TARA: Transport Assessment & Road Appraisal

> *From dash cam road data to investment decision — in minutes, not months.*

TARA is an AI powered dash app that gathers data from dashcam video and gpx files. It assesses road condition, runs economic analysis, and produces professional appraisal reports — with the engineer in the loop for decisions that require institutional knowledge.

## What TARA Does

1. **You upload dashcam video** → TARA analyses road condition using AI vision and suggests interventions including costs
2. **TARA gathers data** → Population, facilities, vehicle mix from the video
3. **TARA runs the appraisal** → Full cost-benefit analysis with sensitivity testing and equity scoring
4. **TARA produces the report** → Professional PDF with charts, maps, and narrative interpretation

## The Problem

Road project appraisal in developing countries takes 4-6 weeks:
- Days spent hunting for scattered data
- Hours setting up and running HDM-4
- Lengthy checks on inputs
- Reports formatted by hand
- Equity impacts ignored

TARA turns this into a 5-hour conversation.

## Tech Stack

- **AI:** Claude Opus 4.6 (Anthropic API with tool use)
- **UI:** Streamlit
- **Data:** OpenStreetMap, WorldPop, World Bank Open Data
- **Analysis:** Python (NumPy, Pandas)
- **Vision:** Claude Vision API (dashcam analysis)
- **Maps:** Folium
- **Charts:** Plotly

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Kye256/tara-transport-assessment.git
cd tara-transport-assessment

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Anthropic API key

# Run TARA
python run app.py
```

## Built for the Anthropic Claude Code Hackathon (Feb 2026)

**Team:** TARA
**License:** MIT  
**Open Source:** All components are fully open source
