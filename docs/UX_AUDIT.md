# TARA UX Audit Report

Generated: 2026-02-13

---

## 1. Step List

### Step 1: Select Road
| Aspect | Detail |
|--------|--------|
| **Label** | "1. Select Road" |
| **UI Components** | Searchable dropdown (`road-select-dropdown`), road info table, loading spinner |
| **Data In** | None (first step) |
| **Data Out** | `road-data-store` (road metadata, geometry, attributes), `facilities-data-store` (OSM facilities), `map-bounds-store` |
| **API/Compute** | OSM Overpass API for facilities lookup (non-critical, try/except) |
| **What user sees** | "Select Road" heading, descriptive text, searchable dropdown with placeholder "Type to search roads...", empty result div below |

### Step 2: Condition
| Aspect | Detail |
|--------|--------|
| **Label** | "2. Condition" |
| **UI Components** | Surface type select (`surface-type-select`), condition rating select (`condition-rating-select`), IRI input (`iri-input`), dashcam upload (`dashcam-upload`), video preset dropdown (`video-preset-dropdown`), frame interval dropdown (`frame-interval-dropdown`), Run Video Analysis button (`run-video-btn`), video/GPX path inputs, cache status display (`video-cache-status`), re-analyse button (`reanalyse-video-btn`), confirmation dialog (`reanalyse-confirm`) |
| **Data In** | `road-data-store` (for surface type prefill) |
| **Data Out** | `condition-store`, `video-condition-store`, `force-reanalyse-store`, map children updated |
| **API/Compute** | Claude Vision API for video pipeline (~$10-15, 5-10 minutes); dashcam single-image analysis |
| **What user sees** | Three condition entry methods: manual selects, dashcam upload, or full video+GPS pipeline with preset datasets |

### Step 3: Traffic
| Aspect | Detail |
|--------|--------|
| **Label** | "3. Traffic" |
| **UI Components** | Total ADT input (`total-adt-input`), growth rate input (`growth-rate-input`), per-vehicle-class table with pattern-matched inputs (`{"type": "traffic-adt", "vc": "Cars"}` etc.), warnings div (`traffic-warnings`) |
| **Data In** | None directly (standalone inputs) |
| **Data Out** | Values read as State by CBA callback |
| **API/Compute** | None |
| **What user sees** | Traffic volume input, growth rate, vehicle class breakdown table (Cars, Buses/LGV, HGV, Semi-Trailers) with ADT and % columns |

### Step 4: Costs
| Aspect | Detail |
|--------|--------|
| **Label** | "4. Costs" |
| **UI Components** | Total cost input (`total-cost-input`), cost/km display (`cost-per-km-display`), construction years input (`construction-years-input`), discount rate input (`discount-rate-input`), analysis period input (`analysis-period-input`), base year input (`base-year-input`), warnings div (`cost-warnings`), video cost breakdown div (`video-cost-breakdown`) |
| **Data In** | `road-data-store` (for cost/km calc), `video-condition-store` (for auto-populating total cost and breakdown table) |
| **Data Out** | Values read as State by CBA callback |
| **API/Compute** | None |
| **What user sees** | Cost parameters, auto-calculated cost/km, validation warnings, per-section cost breakdown table (if video pipeline ran) |

### Step 5: Results
| Aspect | Detail |
|--------|--------|
| **Label** | "5. Results" |
| **UI Components** | Run Appraisal button (`run-cba-btn`, amber), results area (`cba-results-area`) with verdict badge, metric cards (NPV, BCR, EIRR, FYRR), waterfall chart, cashflow chart, traffic growth chart |
| **Data In** | `road-data-store`, `facilities-data-store`, `condition-store`, all traffic/cost inputs, `video-condition-store` |
| **Data Out** | `results-store`, `cba-inputs-store`, `population-store`, `equity-store`, `right-panel-results` |
| **API/Compute** | CBA engine (local, <1s), Kontur/WorldPop population lookup, equity scoring |
| **What user sees** | "Run Appraisal" button, then verdict badge (VIABLE/NOT VIABLE), 4 metric cards, 3 charts |

### Step 6: Sensitivity
| Aspect | Detail |
|--------|--------|
| **Label** | "6. Sensitivity" |
| **UI Components** | Cost slider (`sens-cost-slider`), traffic slider (`sens-traffic-slider`), growth slider (`sens-growth-slider`), Run Full Sensitivity button (`run-sensitivity-btn`), AI Interpretation button (`ai-interpret-btn`), results area (`sensitivity-results-area`), AI narrative div (`ai-narrative`) |
| **Data In** | `results-store`, `cba-inputs-store` |
| **Data Out** | `sensitivity-store`, `ai-narrative-store` |
| **API/Compute** | Multiple CBA re-runs (local, fast); Claude Opus 4.6 for AI interpretation (~$2-3) |
| **What user sees** | Three sliders for live sensitivity, full analysis button for tornado/scenario charts, AI interpretation button |

### Step 7: Equity
| Aspect | Detail |
|--------|--------|
| **Label** | "7. Equity" |
| **UI Components** | Summary box (`equity-summary-box`), section table (`equity-section-table`), narrative panel (`equity-narrative-panel`) |
| **Data In** | `video-condition-store`, `condition-store` |
| **Data Out** | Display only (no stores written) |
| **API/Compute** | None (reads pre-computed data) |
| **What user sees** | Key findings summary, per-section equity observations table (land use, activity, facilities, pedestrians, NMT, vehicles, concern level), AI equity narrative |

### Step 8: Report
| Aspect | Detail |
|--------|--------|
| **Label** | "8. Report" |
| **UI Components** | Generate PDF button (`gen-pdf-btn`), Export CSV button (`gen-csv-btn`), download components (`download-pdf`, `download-csv`), report preview (`report-summary`) |
| **Data In** | `road-data-store`, `facilities-data-store`, `population-store`, `results-store`, `sensitivity-store`, `equity-store`, `condition-store` |
| **Data Out** | File downloads (PDF, CSV) |
| **API/Compute** | PDF generation (local, reportlab) |
| **What user sees** | Two export buttons, markdown preview of report (truncated to 2000 chars) |

---

## 2. First Load Experience

**What is visible on localhost:8050:**

- **Header bar**: "TARA" wordmark (Libre Franklin bold), subtitle "Transport Assessment & Road Appraisal", badge "Built with Claude Opus 4.6" — dark green background (#1a3a2a)

- **Left panel (380px fixed):**
  - Step indicator bar showing 8 segments, Step 1 highlighted green, others grey
  - Step 1 content: "Select Road" heading, text "Choose a road from the Uganda UNRA network.", searchable dropdown with placeholder "Type to search roads..."
  - Back button (disabled) and Next button at bottom

- **Right panel (flex):**
  - Leaflet map centered on Uganda [0.35, 32.58] at zoom 10
  - CartoDB Positron (light grey) base tiles
  - No markers, layers, or overlays yet
  - Empty results div below map

- **Footer**: "TARA — Built for the Anthropic Claude Code Hackathon | Feb 2026"

**Can the user immediately understand what to do?**
Yes — the dropdown is the only interactive element, with a clear placeholder. However, there is no welcome message, onboarding tooltip, or brief explanation of what TARA does or what the 8-step journey involves. A first-time user sees 8 cryptic step labels ("Sensitivity", "Equity") without context for what comes next.

---

## 3. User Flow Map (Happy Path)

| Step | User Action | Duration | Feedback | Breakpoints |
|------|------------|----------|----------|-------------|
| **1. Select Road** | Type road name in dropdown, select from list | Instant (local DB) | Road info table appears, map zooms to road with polyline + facility markers | Empty if no match found |
| **2. Condition** | Select video preset from dropdown, click "Run Video Analysis" | 5-10 minutes (Vision API) OR instant (cached) | Loading spinner → success alert with distance/time/sections, map updates with condition overlay | Pipeline can fail (no video files, bad GPX, API error); manual entry is instant fallback |
| **3. Traffic** | Enter total ADT (default 3000), adjust growth rate (default 3.5%), optionally adjust vehicle split | Instant | Validation warnings for unusual values | No blocking errors possible |
| **4. Costs** | Review auto-populated total cost (from video pipeline), adjust if needed, set discount rate/period | Instant | Cost/km auto-calculated, per-section breakdown shown | Total cost may not auto-populate if video didn't run |
| **5. Results** | Click "Run Appraisal" | <1 second | Verdict badge (VIABLE/NOT VIABLE), 4 metric cards, 3 charts | Requires ADT and cost to be entered; shows warning if missing |
| **6. Sensitivity** | Drag sliders for live preview, click "Run Full Sensitivity Analysis", optionally click "AI Interpretation" | Sliders: instant. Full analysis: 1-2s. AI: 5-15s | Live metric updates, tornado chart, scenario table, AI narrative with typing animation | Requires Step 5 to have run |
| **7. Equity** | View equity data (no input needed) | Instant | Summary box, section table, narrative panel | Shows "not available" message if video pipeline didn't capture equity data (old cache) |
| **8. Report** | Click "Generate PDF Report" or "Export CSV Data" | 1-3 seconds | Download triggers, report preview shown | Requires CBA to have run for meaningful report |

**Total happy path time**: ~6-12 minutes (dominated by video pipeline wait)

---

## 4. Step Transitions

| Transition | Trigger | Auto-populate? | Back preserves data? | Skippable? |
|-----------|---------|----------------|---------------------|------------|
| 1 → 2 | Next button | Surface type prefilled from road OSM data | Yes (road-data-store persists) | No (need a road) |
| 2 → 3 | Next button | No | Yes (condition-store persists) | Yes (can use defaults) |
| 3 → 4 | Next button | Total cost auto-populated from video pipeline interventions | Yes (inputs persist) | Yes (can use defaults) |
| 4 → 5 | Next button | No | Yes (inputs persist) | No (need costs for CBA) |
| 5 → 6 | Next button | Sensitivity controls built from CBA results | Yes (results-store persists) | Yes (sensitivity optional) |
| 6 → 7 | Next button | Equity data read from video-condition-store | Yes (sensitivity-store persists) | Yes (equity is display-only) |
| 7 → 8 | Next button | Report preview built from all stores | Yes (all stores persist) | No (final step) |

**Navigation mechanics:**
- Back/Next buttons in `navigate_steps()` callback
- Back disabled on Step 1, Next disabled on Step 8
- `current-step-store` holds integer 1-8
- `update_step_display()` toggles panel visibility (display:none/block)
- All 8 step panels pre-rendered on page load; only one visible at a time
- Going back preserves all data — stores are not cleared on navigation
- No step is formally "locked" — user can Next through without entering data (will get empty/default results)

---

## 5. Data Dependencies

```
Step 1 (Road)
  └─→ road-data-store ──→ Step 2 (surface prefill)
  │                    ──→ Step 4 (cost/km calculation)
  │                    ──→ Step 5 (CBA input)
  │                    ──→ Step 8 (report)
  └─→ facilities-data-store ──→ Step 5 (equity scoring)
  │                          ──→ Step 8 (report)
  └─→ map-bounds-store ──→ Map fitBounds

Step 2 (Condition)
  └─→ condition-store ──→ Step 5 (CBA input)
  │                   ──→ Step 7 (equity fallback)
  │                   ──→ Step 8 (report)
  └─→ video-condition-store ──→ Step 4 (cost auto-populate + breakdown)
                             ──→ Step 5 (IRI-based VOC scaling)
                             ──→ Step 7 (equity display)

Step 3 (Traffic)
  └─→ [direct State reads] ──→ Step 5 (CBA input)

Step 4 (Costs)
  └─→ [direct State reads] ──→ Step 5 (CBA input)

Step 5 (Results)
  └─→ results-store ──→ Step 6 (sensitivity baseline)
  │                  ──→ Step 8 (report)
  └─→ cba-inputs-store ──→ Step 6 (sensitivity re-runs)
  └─→ population-store ──→ Step 8 (report)
  └─→ equity-store ──→ Step 8 (report)

Step 6 (Sensitivity)
  └─→ sensitivity-store ──→ Step 8 (report)
  └─→ ai-narrative-store ──→ AI typing display

Step 7 (Equity)
  └─→ [display only, no output stores]

Step 8 (Report)
  └─→ [file downloads only]
```

**Hard dependencies** (step won't function without prior data):
- Step 5 requires Step 3 (ADT) + Step 4 (cost) — shows warning if missing
- Step 6 requires Step 5 — shows "Run the appraisal in Step 5 first"
- Step 7 requires Step 2 video pipeline — shows "not available" if no equity data
- Step 8 requires Step 5 — report is empty without CBA results

**Soft dependencies** (step works but is less useful):
- Step 2 surface prefill from Step 1 (defaults to gravel if no road)
- Step 4 cost auto-populate from Step 2 video pipeline (user can enter manually)
- Step 5 IRI-based VOC scaling from Step 2 (uses default VOC if no video)

**Independent steps:**
- Step 3 (Traffic) — standalone inputs with defaults
- Step 4 (Costs) — standalone inputs (auto-populate is bonus)

---

## 6. Current Pain Points

### Empty States with No Guidance
- **Step 1**: No explanation of what TARA does or what the 8-step journey involves. A first-time user sees step labels like "Sensitivity" and "Equity" with no context.
- **Step 5**: Before clicking "Run Appraisal", the results area is completely empty — no preview of what will appear or what inputs are required.
- **Step 7**: If video pipeline didn't run (or used old cache without equity), shows a blue info alert but no guidance on what to do about it.
- **Step 8**: Before generating report, the preview area is empty.

### Technical Jargon Without Explanation
- **IRI** (International Roughness Index) — no tooltip or explanation. Range 1-30 means nothing to a non-specialist.
- **EIRR**, **FYRR**, **BCR**, **NPV** — acronyms shown in metric cards without expansion or context.
- **VOC** (Vehicle Operating Cost) — referenced in cost breakdown but never explained.
- **EOCK** (Economic Opportunity Cost of Capital) — used as discount rate default but not labeled.
- **ADT** (Average Daily Traffic) — label says "Total ADT" but many users won't know the acronym.
- **Sensitivity switching values** — table shows when NPV=0 but doesn't explain significance.

### Steps That Feel Redundant or Confusing
- **Step 2 has three condition entry methods** (manual, dashcam, video pipeline) stacked vertically. It's unclear whether they're alternatives or sequential. The relationship between manual entry and video pipeline output is confusing — does video override manual? (Yes, it does.)
- **Step 4 base year** defaults to 2025 but the current year is 2026. User may not notice.
- **Step 3 vehicle split table** shows both ADT and % columns that update each other — the bidirectional update can be confusing.

### Long Waits with No Progress Feedback
- **Video pipeline (5-10 min)**: Only shows a loading spinner. No progress bar, no "Analysing frame 15/40...", no estimated time remaining. User has no idea if it's working or frozen.
- **AI Interpretation (5-15s)**: Shows typing dots animation, which is better, but no indication of what's happening.

### Buttons That Don't Clearly Indicate What They Do
- **"Run Video Analysis"** — doesn't indicate the $10-15 API cost or 5-10 minute wait time (cost only shown on "Re-analyse" confirmation).
- **"Run Appraisal"** — could mean anything. "Calculate Economic Analysis" would be clearer.
- **"AI Interpretation"** — vague. "Get AI Summary of Results" would be clearer.
- **Next button** — always enabled even when current step has no data. User can click through 8 empty steps.

### Dead Ends and Error States
- **No video data + Step 7**: Shows "Equity data not available" but the only action is to go back to Step 2 and run the pipeline. No button to do this.
- **CBA fails (missing inputs)**: Shows warning "Please enter traffic (ADT) and construction cost" but doesn't indicate which step to go back to.
- **Sensitivity without CBA**: Shows "Run the appraisal in Step 5 first" — references step by number, which is fragile and not user-friendly.

### Other Issues
- **No save/resume**: If the user closes the browser, all progress is lost. No session persistence.
- **No undo**: Clicking "Re-analyse" deletes the cache permanently. No way to recover old results.
- **Map height fixed at 45vh**: On smaller screens, map and wizard panel compete for space. No responsive breakpoints.
- **Left panel 380px fixed**: No responsive behavior — will break on tablets.
- **Step indicator labels truncate**: 8 labels in 380px is tight. "Sensitivity" and "Equity" may overlap on smaller panels.
- **No keyboard navigation**: Tab order and Enter-to-submit not tested. Sliders require mouse.
- **PDF report**: Preview shows first 2000 chars of markdown — not a visual preview of the actual PDF.
- **Base year default 2025**: Should be 2026 (current year).

---

## 7. Component Inventory

### dcc.Store Components (14 total)

| Store ID | Contents | Written By |
|----------|----------|-----------|
| `current-step-store` | Integer 1-8 (active step) | `navigate_steps` |
| `road-data-store` | Road metadata: name, length_km, segments, bbox, coordinates, attributes, source | `select_road` |
| `facilities-data-store` | OSM facilities: {facilities: {category: [items]}, total_count} | `select_road` |
| `condition-store` | Surface/condition: source, surface_type, condition_rating, iri, overall_condition, sections | `store_manual_condition`, `handle_dashcam_upload`, `run_video_pipeline` |
| `traffic-store` | Reserved (not actively used) | — |
| `cost-store` | Reserved (not actively used) | — |
| `results-store` | CBA results: npv, bcr, summary{economically_viable, eirr_pct, fyrr_pct}, yearly_cashflows | `run_cba_callback` |
| `sensitivity-store` | Sensitivity: switching_values{}, summary{risk_assessment, most_sensitive_variable} | `update_sensitivity` |
| `population-store` | Population metrics from Kontur/WorldPop | `run_cba_callback` |
| `equity-store` | Equity scores: overall_score, classification | `run_cba_callback` |
| `cba-inputs-store` | CBA input snapshot: base_adt, growth_rate, road_length_km, construction_cost_total, etc. | `run_cba_callback` |
| `ai-narrative-store` | AI text: {text: string, targetId: "ai-narrative"} | `ai_interpretation` |
| `map-bounds-store` | Map viewport: [[minLat, minLon], [maxLat, maxLon]] | `select_road`, `run_video_pipeline` |
| `video-condition-store` | Full pipeline output: summary, geojson, panel_data, interventions, equity_narrative | `run_video_pipeline` |
| `force-reanalyse-store` | Boolean flag to trigger cache deletion and re-run | `confirm_reanalyse` |

### Major Callbacks (25 total)

| Callback | Input(s) → Output(s) | Description |
|----------|----------------------|-------------|
| `navigate_steps` | back-btn, next-btn → current-step-store | Step navigation (increment/decrement) |
| `update_step_display` | current-step-store → step-indicator, back-btn, next-btn, 8x step-panel | Show/hide step panels, update nav bar |
| `select_road` | road-select-dropdown → road-search-result, road-data-store, facilities-data-store, map | Load road, facilities, update map |
| `prefill_surface` | road-data-store → surface-type-select | Auto-fill surface type from OSM |
| `store_manual_condition` | surface/condition/iri inputs → condition-store | Store manual condition entry |
| `handle_dashcam_upload` | dashcam-upload → dashcam-result, condition-store | Analyse uploaded dashcam image |
| `populate_preset_paths` | video-preset-dropdown → video-path-input, gpx-path-input | Fill paths from preset dataset |
| `update_video_upload_status` | video/gpx paths → video-upload-status, run-video-btn.disabled | Validate paths, enable Run button |
| `show_cache_status` | video/gpx paths → video-cache-status, reanalyse-video-btn.style | Show cached result info |
| `trigger_reanalyse_confirm` | reanalyse-video-btn → reanalyse-confirm.displayed | Show confirmation dialog |
| `confirm_reanalyse` | reanalyse-confirm.submit → force-reanalyse-store | Set re-analyse flag |
| `run_video_pipeline` | run-video-btn, force-reanalyse → pipeline-result, stores, map | Execute video+GPS pipeline |
| `update_cost_per_km` | total-cost-input, road-data → cost-per-km-display | Calculate and display cost/km |
| `auto_populate_costs` | video-condition-store → total-cost-input | Auto-fill cost from pipeline |
| `show_video_cost_breakdown` | video-condition-store, step → video-cost-breakdown | Per-section cost table (Step 4 only) |
| `validate_traffic` | total-adt-input → traffic-warnings | Warn on unusual ADT values |
| `validate_costs` | cost inputs, road-data → cost-warnings | Warn on unusual cost parameters |
| `run_cba_callback` | run-cba-btn + all inputs → results, charts, equity | Run full CBA with IRI-based VOC scaling |
| `build_sensitivity_controls` | current-step-store, results → sensitivity-controls | Build sliders (Step 6 only) |
| `update_sensitivity` | sliders, run-btn, inputs → sensitivity-results-area | Live slider updates + full tornado analysis |
| `ai_interpretation` | ai-interpret-btn, stores → ai-narrative-store | Claude Opus 4.6 text generation |
| `show_equity_step` | current-step-store, stores → equity panels | Populate equity step (Step 7 only) |
| `generate_pdf_report` | gen-pdf-btn + all stores → download-pdf | Generate and trigger PDF download |
| `export_csv` | gen-csv-btn + stores → download-csv | Export yearly cashflows as CSV |
| `show_report_summary` | results-store, step → report-summary | Markdown preview (Step 8 only) |

### Clientside Callbacks (2)

| Name | Input → Output | Description |
|------|---------------|-------------|
| `typeText` | ai-narrative-store → ai-narrative.children | Typing animation for AI text |
| `fitBounds` | map-bounds-store → main-map.bounds | JavaScript Leaflet fitBounds() |

---

## Design System Summary

| Element | Value |
|---------|-------|
| **Primary palette** | World Bank-inspired greens: #1a3a2a (header), #2d5f4a (actions), #3d8b6e (accents) |
| **Neutrals** | Slate: #1e2a32 (text), #607d8b (muted), #eceff1 (panels) |
| **Semantic** | Amber #d4920b (CTA), Red #a83a2f (danger), Blue #2a6496 (info) |
| **Body font** | Source Sans 3 (14px base) |
| **Heading font** | Libre Franklin (humanist, authoritative) |
| **Mono font** | DM Mono (technical data, metrics) |
| **Border radius** | 3px throughout (sharp, professional) |
| **Left panel** | 380px fixed, white background, scrollable |
| **Right panel** | Flex, slate-100 background |
| **Map** | 45vh height, CartoDB Positron tiles |
| **Buttons** | Green primary, amber CTA, outlined secondary |
| **Alerts** | Color-coded with 3px left border |

---

*End of UX Audit Report*
