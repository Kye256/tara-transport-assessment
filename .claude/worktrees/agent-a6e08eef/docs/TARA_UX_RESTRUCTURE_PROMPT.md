# TARA UX Restructuring — Autonomous Agent Prompt
# Paste into Claude Code on the `ux-customisation` branch.
# Read UX_AUDIT.md and CLAUDE.md first before doing anything.

---

## ORCHESTRATOR INSTRUCTIONS

You are the orchestrator agent for restructuring TARA's user experience. You will:
1. Read and understand the entire codebase
2. Dispatch sub-agents for parallel work on separate files
3. Validate the result by running the app and checking every step
4. Iterate until all acceptance criteria pass

**Read these files first (in order):**
- `CLAUDE.md`
- `UX_AUDIT.md` (the full UX audit — this is your map)
- `app.py` (entire file — all callbacks and layouts)
- `assets/style.css`
- `assets/typing.js` (if exists)
- `video/video_pipeline.py`

**Branch:** You are on `ux-customisation`. Commit after each major change with descriptive messages.

---

## THE GOAL

Transform TARA from an 8-step form wizard into a guided, intelligent flow that tells a story: "pick a road → watch AI analyse it → review the economics → understand the risks → get a report." The experience should feel like an AI agent doing work for you, not a form you fill out.

---

## CHANGE 1: Reduce to 7 Steps — Merge Equity into Results

### What to do
- Remove Step 7 "Equity" as a standalone step
- Merge equity display INTO Step 5 "Results" — below the CBA charts
- Renumber: old Step 8 (Report) becomes Step 7
- Update `current-step-store` to use 1-7 range
- Update `navigate_steps` callback bounds
- Update `update_step_display` to handle 7 panels
- Update step indicator bar to show 7 segments

### New step labels (short, fits in nav bar)
1. `ROAD` 
2. `ANALYSE`
3. `TRAFFIC`
4. `COSTS`
5. `RESULTS`
6. `SENSITIVITY`
7. `REPORT`

### Step indicator styling
- Labels: 9px uppercase DM Mono
- Active: green bg (#2d5f4a) + white text
- Completed (past): light green bg (#eaf2ee) + green text
- Future: grey bg (#e8e5de) + muted text (#8a8578)
- Mark steps as "completed" when they have data in their output store

### Equity in Results (Step 5)
- After the charts (waterfall, cashflow, traffic growth), add a horizontal divider
- Below divider: "EQUITY & SOCIAL IMPACT" section header (same style as other section headers: 15px Libre Franklin + 12px muted description)
- Show the equity summary box, per-section equity table, and equity narrative
- If no equity data (video pipeline didn't run), show a single muted line: "Run video analysis in Step 2 to see equity observations." — not a big blue alert
- The equity content is the SAME components currently in Step 7, just relocated

### Callback changes
- `show_equity_step` callback: change trigger from `current-step-store == 7` to `current-step-store == 5`
- OR better: merge equity display into `run_cba_callback` output so it all appears together when CBA runs
- The `run_cba_callback` already computes `equity-store` — just render it in the same results area

---

## CHANGE 2: Landing State — Welcome Before Step Bar

### What to do
When the app first loads (Step 1), the left panel should show:

```
[TARA logo or "T" mark — if available in assets/]

TARA
Transport Appraisal & Risk Analysis

AI-powered road appraisal from dashcam footage.
Select a road to begin.

[Road search dropdown]
```

- The step indicator bar should be HIDDEN on Step 1
- Steps 2-7 bar appears only after a road is selected (i.e., when `road-data-store` has data)
- On Step 1, the left panel has no Back/Next buttons — just the dropdown
- When user selects a road, the road info appears and a "Begin Analysis →" button appears below it
- Clicking "Begin Analysis" advances to Step 2 AND makes the step bar visible

### Implementation
- In `update_step_display`, if `current-step == 1`: hide step indicator bar, hide Back button, hide Next button
- Add a separate "Begin Analysis" button (`begin-analysis-btn`) in Step 1 panel, below road info
- This button is hidden until road-data-store has data (use a callback: road-data-store → begin-analysis-btn.style)
- Wire `begin-analysis-btn` click to set `current-step-store = 2`
- From Step 2 onward, step bar is visible and Back/Next work normally

### Map on first load
- Map shows Uganda road network faintly (if GeoJSON is loaded) or just the blank Positron tiles
- Zoom level 10 centered on Kampala area is fine
- After road selected: zoom to road bounds, show green polyline + facility markers (already works)

---

## CHANGE 3: Step 2 — Simplify Condition Panel

### What to do
Remove the single dashcam image upload entirely. The step should have two clear paths:

**Primary: Video Analysis (the star feature)**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DASHCAM ANALYSIS
Analyse road condition from video footage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dataset    [dropdown: auto-scanned presets]
Interval   [dropdown: frame extraction interval]

[▶ Run Analysis]  (~5 min · uses AI vision)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Secondary: Manual Entry (collapsed by default)**
```
▶ Or enter condition manually
  [collapsed — click to expand]
  
  Surface type  [dropdown]
  Condition     [dropdown] 
  IRI estimate  [number input]
```

### Components to remove
- `dashcam-upload` (dcc.Upload for single image)
- `dashcam-result` div
- `handle_dashcam_upload` callback
- Any layout code for the single-image upload section

### Components to keep
- Video preset dropdown, frame interval dropdown
- Run Video Analysis button
- Video/GPX path inputs (hidden, populated by preset selection)
- Cache status display
- Re-analyse button and confirmation
- Manual condition inputs (surface, condition, IRI) — but inside a collapsible

### Collapsible manual entry
Use `dbc.Collapse` with a toggle:
```python
html.Div([
    html.A("Or enter condition manually ▶", id="toggle-manual-condition", 
           style={"cursor": "pointer", "fontSize": "13px", "color": "#5c5950"}),
    dbc.Collapse(
        id="manual-condition-collapse",
        is_open=False,
        children=[
            # surface-type-select, condition-rating-select, iri-input
        ]
    )
])
```
Add a clientside callback or simple callback to toggle `is_open`.

### Run Analysis button
- Label: "▶ Run Analysis"
- Below the label, in 11px muted text: "~5 min · analyses frames with Claude Vision"
- Use the amber color (#d4920b) — this is the primary CTA of the whole app
- Keep it disabled until a valid dataset is selected

---

## CHANGE 4: Video Pipeline Progress Feedback

### What to do
Replace the loading spinner with real-time stage-by-stage progress.

### Implementation approach
The video pipeline callback (`run_video_pipeline`) currently returns all-at-once after the pipeline finishes. We need incremental progress. 

**Option A (simpler, recommended):** Use a progress div that the pipeline updates via a `dcc.Interval` — NO WAIT. We don't use dcc.Interval. 

**Option B (correct approach):** Use a `dcc.Store` for progress state + a long_callback or background callback pattern. BUT this adds complexity.

**Option C (simplest, do this):** The pipeline already prints progress to console. Instead of a spinner, show a static staged progress indicator that updates via the pipeline callback's partial outputs. Since Dash callbacks are atomic (can't send partial updates), do this:

Break the pipeline into stages with separate callbacks chained together:
1. Callback 1: Extract frames → write to `pipeline-stage-store = "frames_done"`
2. Callback 2: Triggered by stage-store, GPS match → write `"gps_done"`
3. Callback 3: Triggered by stage-store, Vision analysis → write `"vision_done"` 
4. Callback 4: Triggered by stage-store, Sectioning + GeoJSON → write `"complete"`

Each stage callback updates a progress display div.

**HOWEVER** — if this is too complex to refactor safely, do the MINIMUM viable version:

Before the pipeline runs, show a static message:
```
Analysing road condition...

This typically takes 5-7 minutes for a full dataset.
TARA is extracting frames, matching GPS coordinates,
and analysing each frame with Claude Vision.
```

And after it completes, show the success summary (which already exists).

**Choose whichever approach you can implement WITHOUT breaking the existing pipeline.** The chained callback approach is better but riskier. The static message is safe.

---

## CHANGE 5: Auto-Advance After Video Pipeline

### What to do
When the video pipeline completes successfully, automatically advance to Step 3 (Traffic).

### Why
The pipeline has already populated condition data, intervention recommendations, costs, and equity observations. Steps 3 and 4 have sensible defaults. The user's next meaningful input is traffic data, which the camera can't provide.

### Implementation
In `run_video_pipeline` callback, add `current-step-store` as an additional Output:
```python
Output('current-step-store', 'data', allow_duplicate=True)
```
When pipeline succeeds, return `3` for the step store.
When pipeline fails, return `dash.no_update` (stay on Step 2).

**IMPORTANT:** Use `allow_duplicate=True` since `current-step-store` is already written by `navigate_steps`.

### UX on auto-advance
When the user lands on Step 3 after auto-advance, show a green success banner at the top:
```
✓ Video analysis complete — 12.4 km · 6 sections · 47 frames analysed
  Condition, costs, and equity data have been pre-populated.
```
This banner should be visible on Steps 3 and 4 (since both were auto-populated) and disappear on Step 5+.

---

## CHANGE 6: Disable Next Until Step Has Data

### What to do
Prevent the user from advancing past steps that don't have required data.

### Rules
| Step | Next enabled when... |
|------|---------------------|
| 1 (Road) | `road-data-store` has data (but user uses "Begin Analysis" button, not Next) |
| 2 (Analyse) | `condition-store` OR `video-condition-store` has data |
| 3 (Traffic) | `total-adt-input` > 0 (always true with default 3000) |
| 4 (Costs) | `total-cost-input` > 0 |
| 5 (Results) | `results-store` has data (CBA has been run) |
| 6 (Sensitivity) | Always enabled (sensitivity is optional) |
| 7 (Report) | N/A (last step, no Next button) |

### Implementation
Modify `update_step_display` callback to read the relevant stores as State and set `next-btn.disabled` accordingly. The callback already receives `current-step-store` as Input — add the stores as State inputs.

---

## CHANGE 7: Expand Acronyms and Add Context

### What to do
First occurrence of every technical term should be spelled out.

### Specific changes

**Step 3:**
- "Total ADT" → "Average Daily Traffic (ADT)"
- Add helper text below: "Total vehicles per day in both directions"

**Step 4:**
- "Discount Rate" → "Discount Rate (%)" with helper: "Uganda EOCK default: 12%"
- "Analysis Period" → "Analysis Period (years)"

**Step 5 metric cards:**
- "NPV" → "Net Present Value (NPV)"
- "BCR" → "Benefit–Cost Ratio (BCR)"
- "EIRR" → "Economic Internal Rate of Return (EIRR)"
- "FYRR" → "First Year Rate of Return (FYRR)"

**Step 6:**
- "Switching Values" table: add a one-line explanation above: "The % change in each variable that would make the project unviable (NPV = 0)"

### Style for helper text
- 11px Source Sans 3, color #8a8578, margin-top: 2px
- Don't over-explain — one line max per field

---

## CHANGE 8: Step 5 "Run Appraisal" → "Run Economic Analysis"

### What to do
- Rename the button from "Run Appraisal" to "Run Economic Analysis"
- Keep it amber (#d4920b)
- Add helper text below: "Calculates costs, benefits, and returns over the analysis period"

---

## CHANGE 9: Fix Base Year Default

### What to do
- Change `base-year-input` default from 2025 to 2026

---

## CHANGE 10: Update Header Subtitle

### What to do
- Change subtitle from "Transport Assessment & Road Appraisal" to "Transport Appraisal & Risk Analysis" (the new name)
- If the header badge says "Uganda" keep it. If not, add a small "Uganda" badge.

---

## VALIDATION CHECKLIST

After all changes, run the app and verify:

- [ ] App loads with clean landing state — no step bar, just road dropdown
- [ ] Step bar appears after road selection + "Begin Analysis" click
- [ ] Step bar shows 7 steps with correct labels (ROAD through REPORT)
- [ ] Completed steps show light green background
- [ ] Step 2 shows video pipeline as primary, manual as collapsed secondary
- [ ] Single dashcam upload is gone (no `dashcam-upload` component)
- [ ] Run Analysis button shows cost/time hint
- [ ] Video pipeline runs successfully (test with cached data if available)
- [ ] After pipeline completes, auto-advances to Step 3
- [ ] Steps 3-4 show green success banner about pre-populated data
- [ ] Next button disabled when step lacks required data
- [ ] Step 5 shows CBA results + equity section below
- [ ] No separate Step 7 for equity (old step 7 is now Report)
- [ ] Step 7 (Report) generates PDF successfully
- [ ] All acronyms spelled out on first appearance
- [ ] Header says "Transport Appraisal & Risk Analysis"
- [ ] Base year defaults to 2026
- [ ] Back navigation preserves all data
- [ ] No console errors
- [ ] Map displays correctly at every step
- [ ] Typing animation still works on AI interpretation

---

## SUB-AGENT DISPATCH PLAN

If using sub-agents, assign work by file to prevent conflicts:

**Agent 1 — Layout & Structure (app.py layout sections):**
- Changes 1 (step merge), 2 (landing state), 3 (condition simplify), 7 (acronyms), 8 (button rename), 9 (base year), 10 (header)
- Touches: layout definitions in app.py, step panel HTML

**Agent 2 — Callbacks (app.py callback sections):**
- Changes 1 (equity callback merge), 2 (begin-analysis button wiring), 4 (progress feedback), 5 (auto-advance), 6 (next-button gating)
- Touches: callback functions in app.py

**Agent 3 — Styles (assets/):**
- Step bar completed-state styling
- Collapsible manual entry styling
- Success banner styling
- Helper text styling
- Progress indicator styling
- Touches: assets/style.css only

**IMPORTANT:** If agents work in sequence (not parallel), a single agent can do all changes. Work through them in order (1→10), testing after each major change.

---

## WHAT NOT TO CHANGE

- Do NOT touch `video/` directory files — the pipeline works, don't break it
- Do NOT change `dcc.Store` IDs — downstream code depends on them
- Do NOT change the CBA engine or sensitivity analysis logic
- Do NOT remove any store components — only add new ones if needed
- Do NOT change pattern-matching callback IDs (traffic inputs)
- Do NOT add `dcc.Interval` components — use clientside callbacks for any timing needs
- Keep all existing map functionality intact
- Keep the typing animation clientside callback intact
