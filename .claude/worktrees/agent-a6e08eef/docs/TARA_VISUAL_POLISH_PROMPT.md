# TARA Visual Polish — Comprehensive UX Upgrade
# Paste into Claude Code on the `ux-customisation` branch.
# This prompt focuses on VISUAL IMPROVEMENTS ONLY — do not change any business logic, CBA calculations, pipeline processing, or data flows.

---

## ORCHESTRATOR INSTRUCTIONS

Read these files first:
- `CLAUDE.md`
- `app.py` (entire file)
- `assets/style.css`
- `output/report_gen.py` (or wherever PDF generation lives)
- `output/charts.py` (or wherever chart generation lives)

**Golden rule: Do not break anything that currently works.** Run the app after each change. Commit after each major section.

---

## CHANGE 1: Step Bar — Icons with Tooltips

### Problem
Step labels are truncated ("ANA...", "TRA...", "COS...") because 7 labels don't fit in 380px. Looks broken.

### Solution
Replace text labels with SVG icons + step numbers. Show full name as tooltip on hover.

### Implementation

Add Lucide Icons via CDN in the app's external_scripts or in assets/:
```
https://unpkg.com/lucide@latest
```

Or simpler: use inline SVG or Unicode symbols. Here are the 7 steps with clean minimal icons (use inline SVG for reliability — no external dependency):

| Step | Icon concept | SVG/Unicode | Tooltip |
|------|-------------|-------------|---------|
| 1. Road | Map pin | 📍 or `<svg>` pin icon | "Select Road" |
| 2. Analyse | Camera/lens | 🔬 or `<svg>` scan icon | "Video Analysis" |
| 3. Traffic | Vehicle | 🚗 or `<svg>` car icon | "Traffic Data" |
| 4. Costs | Currency | 💲 or `<svg>` dollar icon | "Project Costs" |
| 5. Results | Chart | 📊 or `<svg>` bar-chart icon | "Economic Results" |
| 6. Sensitivity | Sliders | ⚖️ or `<svg>` sliders icon | "Risk Analysis" |
| 7. Report | Document | 📄 or `<svg>` file-text icon | "Final Report" |

**Best approach for Dash:** Create small inline SVG strings for each icon (16x16 or 20x20). Use `html.Div` with `dangerouslySetInnerHTML` or embed SVGs as data URIs in `html.Img` tags.

**Simpler alternative that works well:** Use step NUMBER + short label that fits:
```
① ROAD  ② VIDEO  ③ TRAFFIC  ④ COSTS  ⑤ RESULTS  ⑥ RISK  ⑦ REPORT
```
With circled numbers as the "icon". Style them as 24px circles with the number inside, green when active/complete, grey when future. The label below in 7px uppercase. This fits in 380px because labels are max 7 characters.

### Styling
```css
.step-icon {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: bold;
    margin: 0 auto 2px;
}
.step-icon.active { background: #2d5f4a; color: white; }
.step-icon.completed { background: #eaf2ee; color: #2d5f4a; }
.step-icon.future { background: #e8e5de; color: #8a8578; }

.step-label {
    font-family: 'DM Mono', monospace;
    font-size: 7px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #5c5950;
    text-align: center;
}

.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    flex: 1;
    position: relative;
}

/* Connector line between steps */
.step-item:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 14px;
    left: calc(50% + 16px);
    width: calc(100% - 32px);
    height: 2px;
    background: #e8e5de;
}
.step-item.completed:not(:last-child)::after {
    background: #2d5f4a;
}
```

### Tooltip
Wrap each step item in `html.Div` with `title="Select Road"` etc. Native browser tooltip — no JS library needed.

---

## CHANGE 2: Landing Page — First Impression

### Problem
Landing page is empty white space below a single dropdown. No personality, no promise, no visual impact.

### Solution
Transform the landing page into a statement about what TARA does.

### Left Panel Layout (Step 1)

```
[TARA wordmark — already in header, don't duplicate]

─────────────────────────────────

Drive any road.
Get a complete investment appraisal.

    🎥              📊              👥
  Video         Economic        Equity
  Analysis      Returns         Impact

─────────────────────────────────

SELECT A ROAD

[Searchable dropdown]

─────────────────────────────────

Or select a video dataset to begin
analysis directly.

[Dataset dropdown - scanned from data/videos/]
```

### Implementation Details

**Tagline:** Use Libre Franklin, 22px, bold, color #2c2a26. Line height 1.3.

**Three feature icons:** Use a horizontal flexbox with three items. Each has:
- A 36px circle with icon (green bg #eaf2ee, green icon #2d5f4a)
- Label below in 11px DM Mono uppercase
- Short description in 10px Source Sans 3, muted color

```python
html.Div([
    html.Div([
        html.Div("🎥", className="feature-circle"),
        html.Div("Video Analysis", className="feature-label"),
        html.Div("AI assesses every frame", className="feature-desc"),
    ], className="feature-item"),
    html.Div([
        html.Div("📊", className="feature-circle"),
        html.Div("Economic Returns", className="feature-label"),
        html.Div("NPV, BCR, EIRR, FYRR", className="feature-desc"),
    ], className="feature-item"),
    html.Div([
        html.Div("👥", className="feature-circle"),
        html.Div("Equity Impact", className="feature-label"),
        html.Div("People-centred appraisal", className="feature-desc"),
    ], className="feature-item"),
], className="feature-row")
```

```css
.feature-row {
    display: flex;
    justify-content: space-around;
    margin: 24px 0;
    padding: 16px 0;
    border-top: 1px solid #e8e5de;
    border-bottom: 1px solid #e8e5de;
}
.feature-item { text-align: center; flex: 1; }
.feature-circle {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: #eaf2ee;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 6px;
    font-size: 18px;
}
.feature-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    color: #2c2a26;
    letter-spacing: 0.5px;
}
.feature-desc {
    font-size: 10px;
    color: #8a8578;
    margin-top: 2px;
}
```

### Map on Landing

**Replace the plain CartoDB Positron with a more vivid base:**

Option A (preferred): Keep CartoDB Positron BUT overlay the Uganda road network GeoJSON faintly. Load `data/uganda_main_roads.geojson` as a `dl.GeoJSON` layer with thin lines (#2d5f4a at 30% opacity, weight 1). This shows the road network without being overwhelming. When a road is selected, it highlights bold.

Option B: Use CartoDB Voyager tiles instead of Positron — same clean look but with more colour in the terrain and labels:
```
https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png
```

**Go with Option B (Voyager) — it's a one-line change and immediately makes the map feel more alive.**

### Dataset Dropdown on Landing

Add a second dropdown below the road selector, separated by an "or" divider:

```python
html.Div("— or —", style={"textAlign": "center", "color": "#8a8578", 
    "fontSize": "12px", "margin": "16px 0"}),
html.Div("Start from dashcam footage", style={"fontSize": "13px", 
    "color": "#5c5950", "marginBottom": "8px"}),
dcc.Dropdown(id='landing-dataset-dropdown', 
    placeholder="Select a video dataset...",
    options=[...])  # Same options as video-preset-dropdown
```

When a dataset is selected here, auto-advance to Step 2 with that dataset pre-selected. This gives users a SECOND entry point — they can start from a road OR from footage.

---

## CHANGE 3: Hide Raw File Paths

### Problem
Users see `data/videos/matugg...` filesystem paths. Looks like a developer tool.

### Solution

1. **Hide** the `video-path-input` and `gpx-path-input` text inputs entirely (`display: none`). They still exist for the callback to read, but the user never sees them.

2. **Improve the dataset dropdown labels.** Instead of showing folder names, show human-readable labels. When scanning datasets, generate a label like:
   ```
   "Matugga – Kiteezi  ·  30 clips  ·  7.6 km"
   ```
   Read the clip count from the clips folder and distance from the GPX if possible. If not, just show the folder name cleaned up (replace underscores with spaces, title case).

3. **Cache status:** Keep the caching system (it saves $10-15 per re-run). But simplify the display:
   - If cached: Show a green checkmark and "Previous results available · Analysed [date]" below the dropdown
   - If not cached: Show nothing (the "No cached results" message is unnecessary — just let them click Run)
   - Move the re-analyse button inline: "Previous results available · [Use cached] [Re-analyse]"

---

## CHANGE 4: Charts — Clean, Professional, No Overlaps

### Problem
Chart titles overlap legends. Colours are default Plotly. Layout assumes vertical monitor.

### Solution

Apply these rules to ALL Plotly charts in the app:

### Global Chart Style
```python
TARA_CHART_LAYOUT = dict(
    font=dict(family="Source Sans 3, sans-serif", size=12, color="#2c2a26"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=20, t=50, b=60),
    title=dict(font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="left",
        x=0,
        font=dict(size=11),
    ),
    xaxis=dict(gridcolor="#f0eeea", linecolor="#ddd9d1", linewidth=1),
    yaxis=dict(gridcolor="#f0eeea", linecolor="#ddd9d1", linewidth=1),
)
```

### TARA Colour Sequence (replace default Plotly colours)
```python
TARA_COLORS = [
    "#2d5f4a",  # primary green
    "#3d8b6e",  # light green
    "#9a6b2f",  # amber
    "#3a5a80",  # blue
    "#a83a2f",  # red
    "#6b8f71",  # sage
    "#c4956a",  # tan
]

TARA_COST_COLOR = "#a83a2f"     # red for costs
TARA_BENEFIT_COLOR = "#2d5f4a"  # green for benefits
TARA_NPV_COLOR = "#9a6b2f"     # amber for NPV line
```

### Waterfall Chart Fixes
- Title: "Benefit & Cost Breakdown (Present Value)" — left-aligned, 15px
- Legend below chart, not overlapping
- Use TARA_COST_COLOR for construction and maintenance, TARA_BENEFIT_COLOR for savings
- NPV bar in TARA_NPV_COLOR (amber)
- Add `hovertemplate` for clean hover text: "$%{y:,.0f}"

### Cashflow Chart Fixes
- Title: "Annual Cashflows & Cumulative NPV" — left-aligned
- **Move legend BELOW the chart** (orientation="h", y=-0.15)
- Use TARA colour sequence for the stacked bars
- Cumulative NPV line in amber (#9a6b2f), thicker (width=3)
- Ensure y-axis labels don't overlap with dual axis

### Traffic Forecast Chart Fixes
- Title: "Traffic Forecast" — left-aligned
- Total ADT line in primary green, weight 3
- Normal traffic (dashed) in muted grey
- Capacity line in red (dashed)
- Construction period shading in light amber (#f8f1e5)

### Chart Container Sizing
Design for 16:9 horizontal monitor (the normal orientation judges will use):
```python
# Each chart in the right panel
dcc.Graph(
    figure=fig,
    config={"displayModeBar": False},
    style={"height": "350px", "width": "100%"},
)
```

**CRITICAL: Set `config={"displayModeBar": False}` on ALL charts.** The Plotly toolbar looks unprofessional in a demo.

### Right Panel Chart Layout
Charts should stack vertically in the right panel below the map, each with clear spacing:
```css
.chart-container {
    background: white;
    border: 1px solid #e8e5de;
    border-radius: 3px;
    padding: 16px;
    margin-bottom: 16px;
}
```

---

## CHANGE 5: Equity Presentation — People-Centred Design

### Problem
Equity summary is monospace preformatted text that looks like terminal output. This is TARA's biggest differentiator and it looks like an afterthought.

### Solution
Redesign the equity section in Step 5 (Results) as a warm, human, data-driven story.

### Structure

**Section header:**
```python
html.H3("Who Benefits From This Road", 
    style={"fontFamily": "Libre Franklin", "fontSize": "18px", 
           "color": "#2c2a26", "marginBottom": "4px"}),
html.P("Camera-observed equity indicators along the corridor", 
    style={"fontSize": "12px", "color": "#8a8578", "marginBottom": "16px"}),
```

**Highlight cards** — 2x2 grid of key findings:
```css
.equity-highlights {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 20px;
}
.equity-card {
    background: #f7f6f3;
    border: 1px solid #e8e5de;
    border-radius: 3px;
    padding: 14px;
    border-left: 3px solid #2d5f4a;
}
.equity-card.concern {
    border-left-color: #a83a2f;
}
.equity-card-icon {
    font-size: 20px;
    margin-bottom: 6px;
}
.equity-card-stat {
    font-family: 'DM Mono', monospace;
    font-size: 22px;
    font-weight: bold;
    color: #2c2a26;
    margin-bottom: 4px;
}
.equity-card-label {
    font-size: 12px;
    color: #5c5950;
    line-height: 1.4;
}
```

**Build the cards dynamically from video-condition-store equity data:**

Card 1: Facilities observed
```python
html.Div([
    html.Div("🏥", className="equity-card-icon"),
    html.Div(f"{facility_count}", className="equity-card-stat"),
    html.Div("Facilities observed: health centres, schools, markets, pharmacies", 
        className="equity-card-label"),
], className="equity-card")
```

Card 2: NMT infrastructure (this is the concern card)
```python
html.Div([
    html.Div("🚶", className="equity-card-icon"),
    html.Div(f"{no_footpath_count} of {total_sections}", className="equity-card-stat"),
    html.Div("Sections with no footpath — pedestrians share the carriageway", 
        className="equity-card-label"),
], className="equity-card concern")
```

Card 3: Trading centres / commercial activity
```python
html.Div([
    html.Div("🏪", className="equity-card-icon"),
    html.Div(f"{trading_centre_count} sections", className="equity-card-stat"),
    html.Div("Active trading centres — this road is a commercial lifeline",
        className="equity-card-label"),
], className="equity-card")
```

Card 4: High equity concern sections
```python
html.Div([
    html.Div("⚠️", className="equity-card-icon"),
    html.Div(f"{high_concern_count} sections", className="equity-card-stat"),
    html.Div("Flagged as high equity concern — vulnerable road users at risk",
        className="equity-card-label"),
], className="equity-card concern")
```

**Per-section table:** Keep the existing table but ensure:
- Highlighted rows (salmon/pink) for high-concern sections — KEEP THIS, it's effective
- Add a small legend above: "Highlighted sections have high equity concern"
- Column headers should be full words, not truncated

**Equity narrative (AI-generated):** This is the long text from the equity analysis. Display it in the AI analysis panel style:
```css
.equity-narrative {
    background: #f0eeea;
    border: 1px solid #ddd9d1;
    border-left: 3px solid #2d5f4a;
    padding: 16px;
    margin-top: 16px;
    font-size: 13px;
    line-height: 1.7;
    color: #2c2a26;
    white-space: pre-wrap;
}
.equity-narrative-label {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #2d5f4a;
    margin-bottom: 8px;
}
```

**Equity score reframing:** Change "Low positive equity impact" to a needs-based framing:
- Score 0-25: "Critical — this corridor urgently needs investment for its users"
- Score 26-50: "High need — significant infrastructure gaps affect vulnerable users"
- Score 51-75: "Moderate — some infrastructure serves users but gaps remain"
- Score 76-100: "Well-served — existing infrastructure meets most user needs"

This flips the narrative: a LOW score becomes the ARGUMENT for investment, not a negative judgement.

---

## CHANGE 6: PDF Report — Professional Output

### Problem
Report says wrong name, shows "N/A km", missing narrative and images, sensitivity says "not available".

### Solution

**Fix the title page:**
- "TARA" heading
- "Transport Appraisal & Risk Analysis" (new name)
- Road name from road-data-store
- Date
- "Powered by Claude Opus 4.6"

**Fix road length:** Ensure road length flows from `road-data-store` into the report. Debug why it shows "N/A km".

**Add sections to the report:**

1. **Executive Summary** (exists — fix N/A)
2. **Road Description** (exists — fix data flow)
3. **Corridor Context** (exists — population, facilities)
4. **Condition Assessment** — NEW: Include:
   - Per-section condition table (surface, condition, IRI, intervention)
   - 3-4 representative dashcam images (pick the first frame from each section, or worst/best sections)
   - The AI condition narrative if available
5. **Traffic Analysis** (exists)
6. **Economic Analysis** (exists — charts)
7. **Equity Assessment** — EXPAND:
   - The equity highlight cards data (facilities, NMT, trading centres, concerns)
   - Per-section equity table
   - The AI equity narrative (this is the most compelling text in the whole report)
8. **Sensitivity Analysis** — FIX: Include switching values table and risk assessment if `sensitivity-store` has data
9. **Risk Assessment & Recommendation** (exists)

**Including dashcam images in PDF:**
The video pipeline saves frames. Find the representative frame for each section (or at minimum the first and last frame). Include them in the report at a reasonable size (width ~400px).

To include images in reportlab:
```python
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage

# Get frame path from pipeline cache
frame_path = "data/videos/dataset_name/cache/frames/frame_001.jpg"
img = RLImage(frame_path, width=400, height=225)  # 16:9 aspect
story.append(img)
```

**Report styling:**
- Use Libre Franklin for headings (register the font if available, otherwise Helvetica-Bold)
- Use Source Sans 3 for body (or Helvetica)
- DM Mono for data tables
- Primary green (#2d5f4a) for heading underlines and accent bars
- Page numbers in footer
- TARA logo on title page if `assets/tara-logo.png` exists

---

## CHANGE 7: Progress Feedback with Rotating Quotes

### Problem
User sees "Analysing road condition... This may take a few minutes" for 5-10 minutes with no progress indication.

### Solution
Write pipeline progress to a JSON file. A clientside callback polls it and updates the UI.

### Pipeline Side (video/video_pipeline.py or wherever the pipeline runs)

Add a progress writer:
```python
import json, os

PROGRESS_FILE = "data/.pipeline_progress.json"

def write_progress(stage, current=0, total=0, message=""):
    """Write progress to file for UI polling."""
    progress = {
        "stage": stage,
        "current": current,
        "total": total, 
        "message": message,
        "timestamp": time.time()
    }
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except:
        pass  # Never let progress writing break the pipeline

def clear_progress():
    """Remove progress file."""
    try:
        os.remove(PROGRESS_FILE)
    except:
        pass
```

Call `write_progress` at key points:
```python
# Before frame extraction
write_progress("extracting", 0, clip_count, "Extracting frames from video clips...")

# During extraction, per clip
write_progress("extracting", clip_idx + 1, clip_count, f"Extracting clip {clip_idx+1}/{clip_count}")

# Before GPS matching
write_progress("gps", 0, 0, "Matching frames to GPS coordinates...")

# Before vision analysis
write_progress("vision", 0, frame_count, "Preparing AI analysis...")

# During vision, per frame
write_progress("vision", frame_idx + 1, frame_count, f"Analysing frame {frame_idx+1}/{frame_count}")

# Before sectioning
write_progress("sectioning", 0, 0, "Building road sections...")

# Done
write_progress("complete", 0, 0, "Analysis complete!")
```

At pipeline START: `clear_progress()` (delete stale file)
At pipeline END: leave the "complete" state for 2 seconds, then `clear_progress()`

### UI Side — Progress Display

Replace the static "Analysing road condition..." with a progress container:

```python
html.Div(id="pipeline-progress-container", children=[
    # Progress bar
    html.Div([
        html.Div(id="pipeline-progress-bar", style={
            "width": "0%", "height": "4px", "background": "#2d5f4a",
            "borderRadius": "2px", "transition": "width 0.5s ease",
        })
    ], style={
        "width": "100%", "height": "4px", "background": "#e8e5de",
        "borderRadius": "2px", "marginBottom": "12px",
    }),
    
    # Stage message
    html.Div(id="pipeline-progress-message", children="Starting analysis...", style={
        "fontFamily": "'DM Mono', monospace", "fontSize": "12px", 
        "color": "#2c2a26", "marginBottom": "12px",
    }),
    
    # Rotating quote
    html.Div(id="pipeline-progress-quote", style={
        "fontSize": "12px", "color": "#8a8578", "fontStyle": "italic",
        "lineHeight": "1.5", "borderTop": "1px solid #e8e5de",
        "paddingTop": "12px", "minHeight": "40px",
    }),
], style={"display": "none"})  # Hidden until pipeline starts
```

### Clientside Callback — Poll Progress File

```javascript
// In assets/progress.js

const TARA_QUOTES = [
    "Roads are the arteries of economic development. Their condition determines the cost of everything.",
    "In rural Africa, a road improvement can cut travel time to the nearest hospital by 60%.",
    "Every frame tells a story about the people who depend on this road.",
    "Transport infrastructure is the largest determinant of access to opportunity in rural communities.",
    "Good roads don't just move vehicles — they connect communities to healthcare, education, and markets.",
    "78% of Uganda's freight moves by road. Road condition directly impacts the cost of food and goods.",
    "TARA combines AI vision with engineering methodology to see what traditional surveys miss.",
    "A single road improvement can transform economic access for an entire district.",
    "Road investment decisions affect millions of lives. They deserve rigorous, people-centred analysis.",
    "Traditional road appraisal takes months. TARA aims to make it accessible in minutes.",
];

let progressInterval = null;
let quoteIndex = 0;
let quoteInterval = null;

function startProgressPolling() {
    const container = document.getElementById('pipeline-progress-container');
    const bar = document.getElementById('pipeline-progress-bar');
    const message = document.getElementById('pipeline-progress-message');
    const quote = document.getElementById('pipeline-progress-quote');
    
    if (!container) return;
    container.style.display = 'block';
    
    // Show first quote
    quote.textContent = TARA_QUOTES[0];
    
    // Rotate quotes every 8 seconds
    quoteInterval = setInterval(() => {
        quoteIndex = (quoteIndex + 1) % TARA_QUOTES.length;
        quote.style.opacity = '0';
        setTimeout(() => {
            quote.textContent = TARA_QUOTES[quoteIndex];
            quote.style.opacity = '1';
        }, 300);
    }, 8000);
    
    // Poll progress file every 2 seconds
    progressInterval = setInterval(async () => {
        try {
            const resp = await fetch('/assets/.pipeline_progress.json?' + Date.now());
            if (resp.ok) {
                const data = await resp.json();
                message.textContent = data.message || 'Processing...';
                
                if (data.total > 0) {
                    const pct = Math.round((data.current / data.total) * 100);
                    bar.style.width = pct + '%';
                } else if (data.stage === 'gps') {
                    bar.style.width = '15%';
                } else if (data.stage === 'sectioning') {
                    bar.style.width = '95%';
                } else if (data.stage === 'complete') {
                    bar.style.width = '100%';
                    stopProgressPolling();
                }
            }
        } catch (e) {
            // File doesn't exist yet, that's fine
        }
    }, 2000);
}

function stopProgressPolling() {
    if (progressInterval) clearInterval(progressInterval);
    if (quoteInterval) clearInterval(quoteInterval);
    progressInterval = null;
    quoteInterval = null;
}

// Expose to Dash
window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.tara = window.dash_clientside.tara || {};
window.dash_clientside.tara.startProgress = function() { startProgressPolling(); return ''; };
window.dash_clientside.tara.stopProgress = function() { stopProgressPolling(); return ''; };
```

**IMPORTANT:** The progress JSON file needs to be written to the `assets/` directory (or served via a Dash route) for the browser to fetch it. If writing to `data/.pipeline_progress.json`, you'll need a simple Dash route to serve it:

```python
@app.server.route('/progress')
def serve_progress():
    try:
        with open('data/.pipeline_progress.json') as f:
            return f.read(), 200, {'Content-Type': 'application/json'}
    except:
        return '{}', 200, {'Content-Type': 'application/json'}
```

Then the JS polls `/progress?t=` instead of a static file.

### Triggering the Progress Display

When the "Run Analysis" button is clicked (before the pipeline callback starts processing):
1. Show the progress container (set display: block)
2. Start the JS polling via clientside callback
3. Hide the Run button

When the pipeline callback returns:
1. Hide the progress container
2. Show the success summary
3. Clear the progress file

The simplest way: In the `run_video_pipeline` callback, BEFORE calling the pipeline, write initial progress. The callback Output already includes the pipeline-result div — also output to the progress container's style to toggle visibility.

**If the polling approach is too complex, do the MINIMUM version:** Just show the progress container with a CSS animation (pulsing green bar) and the rotating quotes via a clientside callback triggered on button click. The progress message stays generic: "Analysing road condition..." but the quotes keep the user engaged. No file polling, no real progress numbers. This is MUCH simpler and still dramatically better than a spinner.

---

## CHANGE 8: Quote Fade Animation CSS

```css
#pipeline-progress-quote {
    transition: opacity 0.3s ease;
}

/* Pulsing progress bar animation (for the minimum version) */
@keyframes pulse-bar {
    0% { width: 5%; }
    50% { width: 60%; }
    100% { width: 5%; }
}
.progress-bar-pulsing {
    animation: pulse-bar 3s ease-in-out infinite;
    height: 4px;
    background: #2d5f4a;
    border-radius: 2px;
}
```

---

## CHANGE 9: Right Panel Results Layout

### Problem
On horizontal monitors (which judges will use), the metric cards, verdict, equity bar, and charts below the map can be cramped or poorly arranged.

### Solution

The right panel below the map should use a structured grid:

```
[     Map (50vh height)      ]
[NPV] [EIRR] [BCR] [FYRR]    ← 4 metric cards in a row
[   ECONOMICALLY VIABLE    ]  ← verdict banner
[   Equity Assessment      ]  ← score bar
[   Waterfall Chart        ]  ← benefit breakdown
[   Cashflow Chart         ]  ← annual cashflows  
[   Traffic Chart          ]  ← forecast
```

### Metric Cards Styling
```css
.metric-cards-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0;
}
.metric-card {
    background: white;
    border: 1px solid #e8e5de;
    border-radius: 3px;
    padding: 16px;
    text-align: center;
}
.metric-card-label {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8a8578;
    margin-bottom: 6px;
}
.metric-card-value {
    font-family: 'DM Mono', monospace;
    font-size: 24px;
    font-weight: bold;
    color: #2c2a26;
}
```

### Map Height
Change from 45vh to 50vh for horizontal monitors. Add a min-height of 300px.

---

## VALIDATION CHECKLIST

After all changes, run the app on a HORIZONTAL monitor and verify:

- [ ] Step bar shows numbered circles with short labels, no truncation
- [ ] Completed steps have green circles, connector lines turn green
- [ ] Landing page shows tagline, feature icons, road dropdown
- [ ] Map uses CartoDB Voyager tiles (more colour)
- [ ] File paths are hidden — only dataset dropdown visible
- [ ] Cache status shows clean "Previous results available" or nothing
- [ ] All charts use TARA colour palette, no default Plotly colours
- [ ] Chart legends below charts, no overlaps with titles
- [ ] Plotly toolbar hidden on all charts
- [ ] Equity section shows highlight cards (2x2 grid) with icons
- [ ] NMT/concern cards have red left border
- [ ] Equity narrative in AI analysis panel style
- [ ] Equity score label uses needs-based framing
- [ ] PDF title page says "Transport Appraisal & Risk Analysis"
- [ ] PDF includes condition table and dashcam images
- [ ] PDF includes equity narrative
- [ ] PDF includes sensitivity data if available
- [ ] Progress container shows when pipeline runs
- [ ] Rotating quotes appear during pipeline processing
- [ ] Right panel metric cards in 4-column grid on horizontal monitor
- [ ] No console errors
- [ ] All existing functionality still works

---

## WHAT NOT TO CHANGE

- Do NOT touch `video/` pipeline logic — only add `write_progress` calls
- Do NOT change CBA calculations or sensitivity analysis logic
- Do NOT change `dcc.Store` IDs
- Do NOT change pattern-matching callback IDs
- Do NOT add `dcc.Interval` components
- Do NOT change the equity scoring algorithm — only the PRESENTATION
- Do NOT change the map overlay logic (condition colours, facility markers)
- Keep all existing callbacks functional — only modify their OUTPUT formatting
