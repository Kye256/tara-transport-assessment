# TARA Repository Cleanup — Submission Prep

## Context
TARA is being submitted to the Anthropic Claude Code Hackathon. Deadline is Monday Feb 16, 3:00 PM EST. The demo video is done. We need the repo clean, public-ready, and professionally presented.

## Tasks (in order)

### 1. LICENSE file
Create an MIT LICENSE file in the repo root if one doesn't exist. Use:
- Year: 2026
- Author: Check git log for the author name

### 2. Secrets check
Search the entire codebase for hardcoded API keys, tokens, or secrets:
```bash
grep -r "sk-ant-" . --include="*.py" --include="*.json" --include="*.env"
grep -r "ANTHROPIC_API_KEY.*=" . --include="*.py" | grep -v "os.environ\|os.getenv\|\.env"
```
Any hardcoded keys must be replaced with `os.environ.get("ANTHROPIC_API_KEY")` or similar. Check for any other sensitive strings.

### 3. requirements.txt
Generate or update `requirements.txt` with all Python dependencies. If a virtual environment exists, use `pip freeze`. Otherwise, scan imports across all .py files and create a minimal requirements list. Pin versions.

### 4. .gitignore and large file cleanup
Ensure .gitignore includes at minimum:
```
.env
__pycache__/
*.pyc
*.pyo
*.mov
*.mp4
*.zip
.DS_Store
*.egg-info/
dist/
build/
venv/
.venv/
cache/
*.log
```

**Specific cleanup:** Check `docs/Submission/` for any `.mov` or `.mp4` video files. Use `git rm --cached` to remove them from git tracking while keeping them on the local filesystem. Keep the HTML slide files — those are small and fine to keep. The judges already have the video from the submission platform.

Also check that no other large files (raw shapefiles, zip files, video files) are tracked anywhere in the repo. If they are, `git rm --cached` them and add their patterns to .gitignore. Don't rewrite git history — just untrack and commit.

### 5. README.md
Create a professional README.md. Structure:

```markdown
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
- Anthropic API key

### Installation
```bash
git clone https://github.com/[YOUR_USERNAME]/tara.git
cd tara
pip install -r requirements.txt
```

### Run
```bash
export ANTHROPIC_API_KEY=your_key_here
python app.py
```
Open http://localhost:8050 in your browser.

### Demo Data
The `data/` directory includes pre-cached assessment results from roads near Kampala, Uganda. Select a dataset from the dropdown to explore the full workflow without needing your own dashcam footage or API calls.

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
[Let Claude Code fill this in based on actual file structure]

## License
MIT
```

Adapt the GitHub URL and fill in the project structure section by listing the actual directories and key files.

### 6. Clean up dead code
- Use `git rm --cached` on any files that are clearly debug/test artifacts (e.g., `test_*.py` files that aren't real tests, scratch files, backup copies like `app_old.py`). This untracks them from git but keeps them on the local filesystem.
- Remove excessive `print()` debug statements from production code paths (keep logging if it exists)
- Do NOT refactor working code — only remove obvious junk
- Add untracked artifact filenames to .gitignore so they don't get re-added

### 7. System dependencies check
Scan the codebase for any imports or subprocess calls that require system-level packages beyond pip. Common ones to check for:
- `ffmpeg` / `ffprobe` (video processing)
- `gdal` / `ogr2ogr` (geospatial)
- `cairo` (PDF/SVG rendering)
- Any other non-Python binaries called via `subprocess` or `os.system`

List all system dependencies found. These must be documented in the README installation section.

Also verify that all local data files the app needs to run are committed to the repo (not gitignored). Check:
- `data/uganda_main_roads.geojson` 
- UBOS population/boundary data files
- Any other files loaded at startup or during the cached demo flow

Run the app fresh and note any FileNotFoundError or ImportError — those indicate missing dependencies or data.

### 8. Final check
Run the app once to make sure nothing is broken:
```bash
python app.py
```
Confirm it starts without errors on port 8050.

## IMPORTANT
- Do NOT change any working functionality
- Do NOT refactor or restructure the codebase
- Do NOT touch the data/ directory or cached results
- PRESERVE all cached assessment results (these let judges demo the app without an API key or dashcam footage). Make sure cached results for at least the Matugga-Kiteezi dataset are committed to the repo. Check where cached results are stored (likely in `data/` or `cache/` or similar) and ensure they are NOT in .gitignore.
- Keep changes minimal and safe — the demo video is already recorded
- If unsure about removing something, leave it
