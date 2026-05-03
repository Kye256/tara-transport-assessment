# TARA UI Redesign — Claude Code Orchestrator Prompt

## OBJECTIVE

Redesign the TARA Dash app's visual appearance and UX to look like a professional institutional engineering tool — not a video game or generic SaaS app. The tone should be: **World Bank report meets modern analytics dashboard**. Sober, credible, data-dense, but with an AI feel (typing animation on agent analysis blocks).

**Performance is the #1 constraint.** Nothing in this redesign should add server round-trips, slow down callbacks, or increase load time. All visual changes are CSS/layout only. The typing animation MUST use clientside callbacks (JavaScript in the browser), never server-side callbacks with `dcc.Interval`.

## CURRENT STATE

- 7-step Dash wizard with dash-leaflet map
- ~7,000 lines across 16 Python files
- App runs on port 8050 via `venv/bin/python app.py`
- Steps: Road Search → Condition → Traffic → Costs → CBA → Sensitivity → Report
- Road data: local GeoJSON at `data/uganda_main_roads.geojson`
- Map: dash-leaflet with `dl.Map`, `dl.TileLayer`, `dl.GeoJSON`/`dl.Polyline`

## DESIGN SPECIFICATION

### Color Palette
```
Background:        #f7f6f3  (warm off-white)
Cards/Panels:      #ffffff
Panel background:  #f0eeea
Borders:           #ddd9d1
Border light:      #e8e5de
Text primary:      #2c2a26
Text secondary:    #5c5950
Text muted:        #8a8578
Text dim:          #aaa59c
Primary (green):   #2d5f4a
Primary light:     #eaf2ee
Amber:             #9a6b2f
Amber light:       #f8f1e5
Red:               #a83a2f
Blue:              #3a5a80
Green light:       #ecf4ef
```

### Typography
- **Body text:** Source Sans 3 (Google Fonts) — or system serif fallback
- **Monospace (data/numbers):** DM Mono (Google Fonts) — or system mono fallback
- **Headings:** Libre Franklin (Google Fonts) — or system sans fallback
- Load fonts via `assets/` CSS file, not inline in Python
- Font sizes: headings 15px, body 12-13px, labels 9-11px, data values in mono

### Layout
- **Header bar:** White background, 1px bottom border. Left: "TARA" in bold tracked letters + divider + "Transport Assessment & Road Appraisal" in body font. Right: "Claude Opus 4.6" + "Uganda" badge (subtle, muted).
- **Two-column layout:** Left panel (380px fixed width) with step content. Right: dash-leaflet map fills remaining space.
- **Step navigation:** Horizontal segmented bar at top of left panel. 7 steps. Active step = primary green background + white text. Past steps = light green background. Future steps = panel grey. Monospace labels, 8-9px, uppercase.

### Component Styling
- **Border radius:** 3-4px maximum. No rounded pills. No 8px+ curves.
- **Shadows:** Minimal. Only on dropdowns (4px blur, 6% opacity). No card shadows.
- **Tables over cards:** Use HTML tables for data display (traffic breakdown, costs, condition values, report downloads). Not card grids. Engineers expect tables.
- **Table style:** Thin bottom borders (#e8e5de), no cell backgrounds, left-aligned labels, right-aligned values in mono font.
- **Buttons:** Full-width, 3px border radius, 9px vertical padding. Primary = green bg + white text. Secondary = white bg + green text + border. "Run analysis" button = amber.
- **Section headers:** 15px Libre Franklin semibold + 12px muted description below. No giant text.
- **Data source attribution:** Small mono text (8-9px) below data tables, e.g. "Source: UNRA traffic count station KJ-07, 2024"

### Map Styling
- **Selected road:** Highlighted as a bold polyline in primary green (#2d5f4a), stroke-width 4-5px. Use `dl.Polyline` with the road's GeoJSON coordinates.
- **Map should zoom/fit to the selected road's bounding box** when a road is selected.
- **Facilities layer (Step 2+):** Small square markers (not circles) with letter labels (H, S, M, W) for health, education, market, water. Show in a legend overlay (top-right, white bg, subtle border).
- **Population density overlay (Step 3+):** If WorldPop data is available, show as a subtle amber-tinted heatmap or choropleth. If not available, skip — don't fake it.
- **Bottom attribution bar:** 8px mono text, source info on left, selected road name on right.
- **Tile layer:** Use a muted/desaturated tile — CartoDB Positron (`https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`) instead of the default bright OSM tiles.

### AI Agent Analysis Block (CRITICAL — typing animation)
This is the one animated element. It appears on Step 2 (condition) and Step 6 (sensitivity).

**Visual design:**
- Panel background (#f0eeea), 1px border, 3px LEFT border in primary green
- Top: label in 9px uppercase mono, e.g. "CONDITION ANALYSIS" in primary green
- Body: 13px Source Sans 3, line-height 1.7, secondary text color, `white-space: pre-wrap`
- Small pulsing dot (4px, green) next to label while typing is in progress
- Blinking cursor character (▍) at end of text while typing

**Implementation — MUST use clientside callback:**
```python
# In the layout, the AI block is a simple html.Div with an id
html.Div(id='ai-analysis-text', children='', style={...})

# Store the full analysis text in a dcc.Store
dcc.Store(id='ai-analysis-full-text', data='')

# When analysis is computed (server-side callback), write full text to the Store
@app.callback(
    Output('ai-analysis-full-text', 'data'),
    Input('some-trigger', 'n_clicks'),
)
def compute_analysis(n):
    # ... run analysis ...
    return full_analysis_text

# CLIENTSIDE callback does the typing animation — NO server round-trips
app.clientside_callback(
    """
    function(fullText) {
        if (!fullText) return '';
        
        const targetId = 'ai-analysis-text';
        const el = document.getElementById(targetId);
        if (!el) return '';
        
        let i = 0;
        const cursor = '▍';
        
        if (window._typingInterval) clearInterval(window._typingInterval);
        
        window._typingInterval = setInterval(function() {
            if (i < fullText.length) {
                el.textContent = fullText.slice(0, i + 1) + cursor;
                i++;
            } else {
                el.textContent = fullText;
                clearInterval(window._typingInterval);
            }
        }, 10);
        
        return '';
    }
    """,
    Output('ai-typing-dummy', 'data'),  # dummy output
    Input('ai-analysis-full-text', 'data'),
)
```

**Key rules:**
- The analysis text is computed ONCE by a regular server callback and stored in `dcc.Store`
- The typing animation is PURELY clientside JavaScript — zero server calls
- When typing finishes, the cursor disappears and the dot stops pulsing
- The pulsing dot can be pure CSS: `@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`

### What NOT to Do
- No dark mode / mission control theme
- No neon colors, glows, or gradients
- No card-heavy layouts with big rounded corners
- No emoji in the UI
- No `dcc.Interval` for animations
- No extra API calls or network requests for styling
- No heavy JS libraries (no React, no D3 — just vanilla JS in clientside callbacks)
- Do not break any existing callback chains or data flows
- Do not change the CBA engine, sensitivity analysis, or report generation logic
- Do not modify any analysis/computation code — this is a visual-only redesign

## TASK BREAKDOWN FOR SUB-AGENTS

### Sub-Agent 1: CSS & Assets
**Files:** `assets/style.css`, `assets/fonts.css` (create if needed)
**Task:**
1. Create `assets/style.css` with the complete color palette as CSS custom properties
2. Add Google Fonts import for Source Sans 3, DM Mono, Libre Franklin
3. Define all component styles: tables, buttons, step nav, section headers, AI block, header bar
4. Add the `@keyframes pulse` and `@keyframes blink` animations
5. Override any existing Dash default styles that conflict
6. Ensure all font sizes, colors, spacing match the spec above

### Sub-Agent 2: Layout & Header
**Files:** `app.py` (layout section only), relevant layout files
**Task:**
1. Restructure the main layout: header bar + two-column (left panel 380px + map)
2. Build the header: "TARA" wordmark + divider + subtitle + right-side model/country badges
3. Implement the 7-step horizontal segmented navigation bar
4. Ensure the left panel scrolls independently from the map
5. Apply CSS classes from the stylesheet (don't inline styles in Python)

### Sub-Agent 3: Step Panels (Steps 1-4)
**Files:** Step 1-4 layout/callback files
**Task:**
1. Step 1 (Road): Searchable `dcc.Dropdown` → selected road info in a table (not cards) → "Continue" button
2. Step 2 (Condition): Table with surface/PCI/IRI values → AI analysis block (with typing) → "Continue" button
3. Step 3 (Traffic): Table with vehicle class breakdown (columns: class, ADT, share %) → total row → data source attribution → "Continue" button
4. Step 4 (Costs): Table with cost parameters (label, value, note columns) → "Run economic analysis" amber button
5. Use `html.Table`/`html.Tr`/`html.Td` with CSS classes, not `dash_table.DataTable` for these simple display tables

### Sub-Agent 4: Step Panels (Steps 5-7) + AI Typing
**Files:** Step 5-7 layout/callback files
**Task:**
1. Step 5 (CBA): Green "Economically viable" verdict banner → 2×2 grid of metric cards (NPV, BCR, EIRR, FYRR) → tornado sensitivity chart → "Continue" button
2. Step 6 (Sensitivity): AI analysis block with typing animation → "Generate report" button
3. Step 7 (Report): Green completion banner → download table (PDF, CSV, Markdown rows)
4. **Implement the clientside callback for typing animation** (see spec above)
5. Wire up `dcc.Store` components for the full analysis text
6. Ensure typing works for BOTH Step 2 and Step 6 (two separate blocks, same pattern)

### Sub-Agent 5: Map Styling
**Files:** Map-related layout/callback files
**Task:**
1. Switch tile layer to CartoDB Positron: `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`
2. When road is selected: draw highlighted `dl.Polyline` in primary green, weight=5
3. Fit map bounds to selected road's bounding box (use `dl.Map` `bounds` prop or a callback)
4. Add facility markers as square-ish markers with letter labels (Step 2+)
5. Add a legend overlay (top-right corner) for facility types when visible
6. Add bottom attribution bar with data source + selected road name
7. Keep map performant — don't re-render the entire GeoJSON on every callback

## PERFORMANCE RULES (NON-NEGOTIABLE)

1. **Zero new server round-trips for visual changes.** All animations are clientside.
2. **No dcc.Interval components.** Ever.
3. **CSS in stylesheet files**, not inline Python dicts (reduces callback payload size).
4. **Map GeoJSON is loaded once** and filtered client-side or via minimal callbacks.
5. **Font loading is non-blocking** (use `font-display: swap` in CSS).
6. **Test the app after changes** — run `venv/bin/python app.py` and verify it loads and all 7 steps work.
7. **If something breaks, fix it before moving on.** A working ugly app beats a broken pretty one.

## VERIFICATION CHECKLIST

After all changes, verify:
- [ ] App starts without errors on port 8050
- [ ] Step 1: Dropdown populates with roads from local GeoJSON
- [ ] Step 1: Selecting a road highlights it on the map in green
- [ ] Step 2: Condition table displays, AI typing animation plays
- [ ] Step 3: Traffic table displays with proper formatting
- [ ] Step 4: Cost parameters display, amber "Run analysis" button works
- [ ] Step 5: CBA results display (NPV, BCR, EIRR, FYRR)
- [ ] Step 6: Sensitivity AI typing animation plays
- [ ] Step 7: Report downloads work (PDF, CSV, Markdown)
- [ ] Map tile layer is CartoDB Positron (muted/light)
- [ ] Map zooms to selected road
- [ ] No console errors in browser
- [ ] Typing animation is smooth (no jank, no server calls)
- [ ] All existing analysis logic still works correctly
