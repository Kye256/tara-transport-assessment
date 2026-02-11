# TARA: Transport Assessment & Road Appraisal

> *From road data to investment decision — in minutes, not months.*

TARA is an AI agent that autonomously gathers data, assesses road condition, runs economic analysis, and produces professional appraisal reports — with the engineer in the loop for decisions that require institutional knowledge.

## What TARA Does

1. **You name a road** → TARA finds it on OpenStreetMap, extracts geometry, identifies nearby facilities
2. **TARA gathers data** → Population, poverty, accessibility from open datasets
3. **TARA generates a drive plan** → Tells you where to drive and what to look for
4. **You upload dashcam video** → TARA analyses road condition using AI vision
5. **TARA runs the appraisal** → Full cost-benefit analysis with sensitivity testing and equity scoring
6. **TARA produces the report** → Professional PDF with charts, maps, and narrative interpretation

## The Problem

Road project appraisal in developing countries takes 4-6 weeks:
- Days spent hunting for scattered data
- Hours setting up and running HDM-4
- No quality checks on inputs
- Sensitivity analysis done mechanically
- Reports formatted by hand
- Equity and environmental impacts ignored

TARA turns this into a 5-minute conversation.

## Tech Stack

- **Agent:** Claude Opus 4.6 (Anthropic API with tool use)
- **UI:** Streamlit
- **Data:** OpenStreetMap, WorldPop, World Bank Open Data
- **Analysis:** Python (NumPy, Pandas)
- **Vision:** Claude Vision API (dashcam analysis)
- **Maps:** Folium
- **Charts:** Plotly

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/tara-transport-assessment.git
cd tara-transport-assessment

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Anthropic API key

# Run TARA
streamlit run app.py
```

## Built for the Anthropic Claude Code Hackathon (Feb 2026)

**Team:** [Your name]  
**License:** MIT  
**Open Source:** All components are fully open source
