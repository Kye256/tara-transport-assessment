# TARA Repository — README Overhaul & Polish

## Context
TARA won the "Keep Thinking" Prize at the Anthropic Claude Code Hackathon (February 2026). The repo needs a professional, visually appealing README that reflects this. Currently the README is functional but plain — no screenshots, no demo video, no badges, no visual appeal.

Reference style: https://github.com/nicekid1/obsidian-agent-client — clean, badges at top, demo video embedded, professional presentation.

## Task 1: Update README.md

Replace the current README with a polished version. Structure:

### Header Section
```markdown
# TARA — Transport Appraisal & Risk Analysis

🏆 **Winner — "Keep Thinking" Prize, Anthropic Claude Code Hackathon 2026**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20Opus%204.6-blueviolet)](https://www.anthropic.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Dash](https://img.shields.io/badge/Framework-Dash-00cc96.svg)](https://dash.plotly.com)

> From dashcam footage to investment decision — in hours, not weeks.

TARA is an AI-powered road appraisal tool that transforms dashcam footage into complete economic appraisals with equity assessment. A $56 dashcam doing the job of an $800,000 survey van.
```

### Demo Video
Embed the YouTube demo video right after the header:
```markdown
## Demo

[![TARA Demo](https://img.youtube.com/vi/GFCrXehS1DE/maxresdefault.jpg)](https://www.youtube.com/watch?v=GFCrXehS1DE)

*3-minute demo: dashcam footage → condition assessment → economic analysis → equity scoring → PDF report*
```

### Screenshots Section
Take 3-4 screenshots from the running app and save them in a `docs/screenshots/` directory. If the app can be run locally, start it and capture:
1. The condition map with colour-coded sections and a frame popup
2. The CBA results showing NPV, EIRR, BCR metric cards
3. The equity assessment cards
4. The sensitivity analysis with AI interpretation

If you cannot run the app, create placeholder references:
```markdown
## Screenshots

| Condition Assessment | Economic Analysis |
|---|---|
| ![Condition Map](docs/screenshots/condition-map.png) | ![CBA Results](docs/screenshots/cba-results.png) |

| Equity Assessment | Sensitivity Analysis |
|---|---|
| ![Equity](docs/screenshots/equity.png) | ![Sensitivity](docs/screenshots/sensitivity.png) |
```

### What It Does section
Keep the current bullet list but add a brief intro paragraph:
```markdown
## What It Does

Upload dashcam footage and a GPS track from any road. TARA:

- 📹 Analyses every frame using Claude Opus 4.6 Vision (TMH12/ASTM D6433 standards)
- 🗺️ Segments the road into homogeneous sections by surface and condition
- 🔧 Selects appropriate interventions with Uganda-calibrated costs
- 📊 Runs full cost-benefit analysis (NPV, EIRR, BCR, FYRR)
- 🤖 Performs context-aware sensitivity analysis with AI interpretation
- 📉 Models road deterioration with and without intervention
- 👥 Assesses equity impact — who benefits from this road
- 📄 Generates a complete PDF report
```

### The Problem section
Keep brief — 3-4 sentences max:
```markdown
## The Problem

Africa needs $181 billion annually in transport infrastructure. 80% of projects fail at feasibility — not because of money, but because project preparation takes weeks of specialist work most agencies can't afford. Road appraisal requires expensive software, trained specialists, and months of data gathering. TARA reduces this to hours using AI and a phone dashcam.
```

### How Claude Opus 4.6 Is Used
```markdown
## How Claude Opus 4.6 Is Used

- **Vision API** — Frame-by-frame road condition assessment from dashcam footage
- **Condition narratives** — AI-written assessment grounded in what the camera observed
- **Sensitivity interpretation** — Context-aware analysis of which variables matter for this specific road
- **Equity assessment** — Identifying who depends on the road from camera observations
- **Report generation** — Professional narrative for each section of the appraisal
- **Built with Claude Code** — Multi-agent development with hooks for autonomous operation
```

### Quick Start section
Fix the current errors. Use the ACTUAL tech stack and commands:
```markdown
## Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API key (optional — cached demo data included)
- ffmpeg (for video processing): `brew install ffmpeg` (Mac) or `sudo apt install ffmpeg` (Ubuntu)

### Installation
```bash
git clone https://github.com/Kye256/tara-transport-assessment.git
cd tara-transport-assessment
pip install -r requirements.txt
```

### Run
```bash
export ANTHROPIC_API_KEY=your_key_here  # optional if using cached data
python app.py
```
Open http://localhost:8050

### Demo Data
Pre-cached assessment results are included. Select a dataset from the dropdown to explore the full workflow without an API key.
```

### Tech Stack section
```markdown
## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | Dash (Python) |
| **AI** | Claude Opus 4.6 (Vision + Text) via Anthropic API |
| **Map** | dash-leaflet with CartoDB Positron tiles |
| **Data** | OpenStreetMap, UBOS Uganda census, WorldPop |
| **Analysis** | Custom CBA engine with 2024 UNRA HDM-4 calibration |
| **Charts** | Plotly |
| **Reports** | FPDF2 |
```

### Project Structure
Generate this from the actual directory listing:
```markdown
## Project Structure
```
Run `find . -type f -name "*.py" | head -30` and organise into a tree.

### Footer
```markdown
## Author

**Kyeyune Kazibwe** — Transport Engineer, Kampala, Uganda

- Built solo in 6 days during the Anthropic Claude Code Hackathon (Feb 10-16, 2026)
- Winner of the "Keep Thinking" Prize

## License

MIT — see [LICENSE](LICENSE)
```

## Task 2: Clean up .DS_Store

```bash
git rm --cached .DS_Store
echo ".DS_Store" >> .gitignore
```

## Task 3: Update repo "About" description

This must be done manually on GitHub (Settings gear icon on the right sidebar). But remind the user to change it to:

> 🏆 AI-powered road appraisal from dashcam footage. Winner, Anthropic Claude Code Hackathon 2026.

And add these topics: `ai`, `claude`, `transport`, `road-assessment`, `dashcam`, `infrastructure`, `uganda`, `hackathon`, `computer-vision`, `open-source`

## IMPORTANT
- Do NOT change any application code — only README.md, .gitignore, and docs/ folder
- Do NOT remove any existing files
- Commit with message: "Professional README with badges, demo video, and screenshots"
- Verify the YouTube thumbnail URL works: https://img.youtube.com/vi/GFCrXehS1DE/maxresdefault.jpg
