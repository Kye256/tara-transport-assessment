# TARA — Deterioration Modeling Integration
# Paste into Claude Code. Uses sub-agents for parallel work on separate files.
# Do NOT commit anything. Do NOT run git commands. I will test and commit manually.

---

## OVERVIEW

Add deterioration-driven economic analysis to TARA. Instead of using fixed "before/after" VOC rates for the CBA, the deterioration model generates **year-by-year IRI curves** for both do-nothing and with-project scenarios, computes **VOC/VoT as a function of IRI each year**, and schedules **maintenance costs at the years they actually occur**. This makes the economic analysis internally consistent with the deterioration chart.

**What we're adding:**
1. A new Python module `analysis/deterioration.py` (provided — copy it in)
2. A deterioration chart in the Step 5 (Results) right panel
3. **Optionally: use `generate_cashflows()` to drive the CBA** instead of fixed VOC rates — this is the Level 2 integration described below
4. A deterioration narrative paragraph in the AI analysis block
5. Deterioration summary data fed into the PDF report

**Level 2 CBA integration (the key upgrade):**
The module includes `generate_cashflows()` which takes the same inputs the CBA engine already has (IRI, ADT, road length, construction cost) and returns a complete year-by-year cashflow with NPV, EIRR, BCR. The benefit stream grows over time because the do-nothing road gets worse while the improved road stays good. Maintenance events (reseals, regravels) appear as costs in the years they occur.

**Integration approach — choose ONE:**
- **Option A (clean):** Replace the existing CBA engine's benefit calculation with `generate_cashflows()`. The cashflow function returns NPV/EIRR/BCR directly, so the existing metric cards and charts can read from the same output dict. This is the cleanest but touches the CBA engine.
- **Option B (safe):** Keep the existing CBA engine unchanged. Add the deterioration chart and narrative alongside it. The two calculations may produce slightly different NPV/EIRR numbers (because the existing engine uses fixed VOC rates while deterioration uses time-varying rates), but they'll be directionally consistent. Use this if modifying the CBA engine feels risky.
- **Option C (hybrid):** Use `generate_cashflows()` to generate the deterioration chart and narrative, but feed its year-by-year RUC savings back into the existing CBA engine as the benefit stream. This gives you time-varying benefits without rewriting the CBA.

**Read the existing CBA engine first, then decide which option fits best.**

**What we are NOT changing:**
- Step navigation, step count, step labels — leave as-is
- Sensitivity analysis — no changes (it re-runs CBA with adjusted inputs, so it'll pick up the new benefit calculation automatically if using Option A)
- Video pipeline — no changes
- Map display — no changes

---

## STEP 0: AUDIT (do this first, report findings before proceeding)

Read the codebase and answer these questions. This determines how we wire things up.

1. **Where is the Step 5 (Results) callback defined?** Find the callback that fires when "Run Analysis" is clicked. What file is it in? What are its Outputs? List all Output component IDs.

2. **What does the Step 5 callback return for the right panel?** Find where the CBA charts (waterfall, cashflow, traffic forecast) are created and returned. Are they in a list of `dcc.Graph` components? A div with children? What's the container ID?

3. **What stores contain the data we need?**
   - `condition-store`: What structure? Does it have per-section IRI values? What key?
   - `traffic-store`: What structure? Where is total ADT? Is ADT broken down by vehicle class (Cars, Buses_LGV, HGV, Semi_Trailers)? What keys?
   - `road-data-store`: What structure? Does it have road name, surface type?
   - `results-store`: What does the CBA engine return? What keys?
   - `cost-store`: What structure? Where is construction cost? Road length?

4. **How does the CBA engine compute benefits?** Read `engine/cba.py` (or wherever the CBA calculation lives) and answer:
   - Does it use fixed "without_project" / "with_project" VOC rates from `config/parameters.py`?
   - Or does it compute VOC from IRI using a function?
   - How are annual benefits computed? Is it `(voc_without - voc_with) × ADT × 365 × length` constant every year, or does it vary by year?
   - How are maintenance costs handled? Fixed annual amount, or scheduled?
   - What does the CBA engine's main function signature look like? What does it accept, what does it return?
   - How does the sensitivity analysis callback call the CBA engine? (This matters — if we change the CBA inputs, sensitivity must still work)

4. **Where are charts created?** Is there a `charts.py` or `output/charts.py` module? Or are Plotly figures built inline in the callback?

5. **What is the current right-panel chart layout for Step 5?** List in order: metric cards, verdict, equity bar, then which charts in what order?

6. **Where is the AI analysis narrative generated?** The typing animation block in Step 5 — what callback generates the text? What store holds it?

7. **Does `analysis/` directory exist?** If not, where should the deterioration module go? Check existing module locations (engine/, video/, skills/).

8. **What surface type values does the pipeline use?** Search for surface type strings in condition-store data and the vision pipeline. Are they: "gravel", "earth", "paved"? Or different strings like "unpaved", "asphalt", "murram"?

**Report all findings. Do not proceed until you've answered every question.**

---

## STEP 1: Install the Deterioration Module

### Sub-agent task (if analysis/ directory exists):
```
Copy the deterioration module into the project.
```

### If `analysis/` directory does NOT exist:
Create it, or place the module where other analysis code lives (likely `engine/`). Follow whatever pattern the codebase uses.

The module file is provided below. Copy it EXACTLY — do not modify the math, coefficients, or chart styling. The only thing you may need to adjust is the import path.

<deterioration_module>
**File: `analysis/deterioration.py`**

Copy the complete file from: [the deterioration.py that was just created]

If you cannot find the file, create it with these key functions:

```python
# Core functions the integration needs:

def compute_k(surface_type, adt, rainfall_zone='tropical_wet', material_quality='medium') -> float:
    """Compute deterioration rate coefficient k."""

def predict_iri(iri_initial, years, k, cap=22.0) -> np.ndarray:
    """Predict IRI over time (do-nothing scenario)."""

def predict_with_maintenance(iri_initial, years, k, ...) -> dict:
    """Predict IRI with intervention and periodic maintenance.
    Returns: {'years': array, 'iri': array, 'events': [(year, type, iri_before, iri_after), ...]}"""

def create_deterioration_chart(iri_current, surface_type, adt, ...) -> go.Figure:
    """Create Plotly figure with do-nothing vs with-intervention curves."""

def get_deterioration_summary(iri_current, surface_type, adt, ...) -> dict:
    """Summary stats for narrative generation."""

def generate_narrative(summary) -> str:
    """Plain-language deterioration paragraph."""

# Level 2 CBA functions:

def voc_from_iri(iri, vehicle_class) -> float:
    """VOC (USD/veh-km) from IRI. Calibrated to Highway-1 rates at IRI 2.5 and 12."""

def vot_from_iri(iri, vehicle_class) -> float:
    """Value of time cost from IRI."""

def generate_cashflows(iri_current, surface_type, adt_by_class, road_length_km,
                       construction_cost_total, ...) -> dict:
    """Full year-by-year CBA driven by deterioration model.
    Returns dict with: npv, eirr, bcr, fyrr, ruc_savings[], construction_costs[],
    maintenance_donothing[], maintenance_withproject[], net_benefits[], events, summary"""
```

The module uses these parameters:
- `surface_type`: one of 'paved_good', 'paved_fair', 'paved_poor', 'gravel', 'earth'
- `adt`: float, vehicles/day
- `rainfall_zone`: default 'tropical_wet' for Uganda
- `material_quality`: 'good', 'medium', 'poor', 'very_poor'
- `intervention_type`: 'reconstruct', 'regravel', 'reseal', 'overlay'
- `post_intervention_surface`: surface type after intervention

**CRITICAL:** The module imports `numpy` and `plotly.graph_objects`. Both are already in TARA's dependencies. Do NOT install anything new.
</deterioration_module>

After copying the file, verify it imports cleanly:
```bash
cd <project_root>
python -c "from analysis.deterioration import create_deterioration_chart, get_deterioration_summary, generate_narrative; print('OK')"
```

If the import path doesn't work (e.g. the module is in `engine/` instead), adjust accordingly. The import must work before proceeding.

---

## STEP 2: Wire Deterioration Chart into Step 5 Results

This is the main integration. **Read the audit findings from Step 0 carefully before writing code.**

### 2.1 Locate the Step 5 callback

Find the callback that builds the right-panel content for Step 5 (Results). This is where metric cards, verdict banner, equity bar, and CBA charts are assembled.

### 2.2 Extract inputs for deterioration

From the stores already available in the callback (condition-store, traffic-store, road-data-store), extract:

```python
# You need these values — find them in whatever key structure the stores use:
iri_current = <from condition-store — average IRI across sections, or weighted average>
surface_type = <from condition-store or road-data-store — map to deterioration module's expected values>
adt = <from traffic-store — total ADT>
road_name = <from road-data-store — display name>
```

**Surface type mapping:** The vision pipeline may use different strings than the deterioration module expects. Create a mapping:
```python
SURFACE_TYPE_MAP = {
    # Vision pipeline values → deterioration module values
    'asphalt': 'paved_fair',
    'paved': 'paved_fair',
    'gravel': 'gravel',
    'murram': 'gravel',
    'laterite': 'gravel',
    'earth': 'earth',
    'dirt': 'earth',
    'unpaved': 'gravel',  # default for generic unpaved
}
```
Check what values the pipeline actually produces and adjust this mapping.

**IRI extraction:** The condition-store likely has per-section data. Compute a weighted average IRI (weighted by section length) for the deterioration chart. If sections don't have length, use simple average.

### 2.3 Determine intervention type from costs

Check the cost-store or the CBA inputs to determine what intervention is planned:
- If upgrading gravel/earth to paved → `intervention_type='reconstruct'`, `post_intervention_surface='paved_good'`
- If regravelling → `intervention_type='regravel'`, `post_intervention_surface='gravel'`
- If resealing paved → `intervention_type='reseal'`, `post_intervention_surface='paved_fair'`

If you can't determine this from the stores, default to `'reconstruct'` with `'paved_good'` — this is the most common UNRA project type.

### 2.4 Extract ADT by vehicle class

The `generate_cashflows()` function accepts ADT broken down by vehicle class:
```python
adt_by_class = {
    'Cars': <from traffic-store>,
    'Buses_LGV': <from traffic-store>,
    'HGV': <from traffic-store>,
    'Semi_Trailers': <from traffic-store>,
}
```

If the traffic store only has total ADT, apply Uganda default fleet composition:
```python
# Uganda typical fleet split (from UNRA traffic counts)
total_adt = <from traffic-store>
adt_by_class = {
    'Cars': total_adt * 0.57,        # 57% cars/light vehicles
    'Buses_LGV': total_adt * 0.23,   # 23% buses and light goods
    'HGV': total_adt * 0.14,         # 14% heavy goods
    'Semi_Trailers': total_adt * 0.06,  # 6% semi-trailers
}
```

### 2.5 CBA Integration (Level 2) — CHOOSE ONE OPTION

**Read the audit findings for question 4 (CBA engine internals) before deciding.**

#### Option A: Replace CBA benefit calculation with generate_cashflows()

If the existing CBA engine uses fixed VOC rates and the code is clean enough to modify:

```python
from analysis.deterioration import generate_cashflows

cashflow_result = generate_cashflows(
    iri_current=avg_iri,
    surface_type=mapped_surface,
    adt_by_class=adt_by_class,
    road_length_km=road_length,
    construction_cost_total=total_construction_cost,
    analysis_years=analysis_period,
    construction_years=construction_years,
    traffic_growth_rate=growth_rate,
    discount_rate=discount_rate,
    intervention_type=intervention_type,
    post_intervention_surface=post_surface,
)

# Use cashflow_result directly for metrics and charts:
npv = cashflow_result['npv']
eirr = cashflow_result['eirr']
bcr = cashflow_result['bcr']
fyrr = cashflow_result['fyrr']
# Year-by-year data for cashflow chart:
# cashflow_result['ruc_savings'], cashflow_result['construction_costs'], etc.
```

**Advantage:** Single source of truth — deterioration chart and CBA numbers are perfectly consistent.
**Risk:** Must ensure the sensitivity analysis still works. Check how sensitivity re-runs the CBA — if it calls the CBA function with adjusted inputs, you'll need to make `generate_cashflows()` accept the same adjustments (cost ±%, traffic ±%, growth rate ±%, discount rate ±%).

**The `generate_cashflows()` function already accepts all these as parameters**, so sensitivity just needs to call it with adjusted values:
```python
# Sensitivity: e.g. construction cost +30%
result_high_cost = generate_cashflows(..., construction_cost_total=cost * 1.30, ...)
```

#### Option B: Keep existing CBA, add deterioration chart alongside

If the CBA engine is complex or the sensitivity analysis depends on its specific internals:

```python
# Existing CBA runs as before
cba_results = existing_cba_function(...)

# Deterioration chart is ADDITIONAL — visual + narrative only
from analysis.deterioration import create_deterioration_chart, get_deterioration_summary, generate_narrative

det_fig = create_deterioration_chart(...)
det_summary = get_deterioration_summary(...)
det_narrative = generate_narrative(det_summary)
```

**Advantage:** Zero risk to existing CBA.
**Drawback:** Chart and CBA numbers may differ slightly (chart shows time-varying benefits, CBA uses fixed rates).

#### Option C: Hybrid — deterioration feeds into existing CBA

Extract the year-by-year RUC savings from `generate_cashflows()` and pass them into the existing CBA engine as the benefit stream, replacing the fixed annual benefit:

```python
cashflow = generate_cashflows(...)

# Feed time-varying benefits into existing engine
annual_benefits = cashflow['ruc_savings'] + cashflow['maintenance_savings']
# Pass annual_benefits array into existing CBA instead of fixed annual amount
```

**This only works if the existing CBA engine can accept an array of annual benefits instead of computing its own.**

### 2.6 Generate the deterioration chart

Regardless of which CBA option you chose:

```python
from analysis.deterioration import create_deterioration_chart

try:
    det_fig = create_deterioration_chart(
        iri_current=avg_iri,
        surface_type=mapped_surface,
        adt=total_adt,
        analysis_years=analysis_period,
        intervention_type=intervention_type,
        intervention_year=1,
        post_intervention_surface=post_surface,
        construction_years=construction_years,
        road_name=road_name,
    )
    det_chart = dcc.Graph(
        figure=det_fig,
        config={"displayModeBar": False},
        style={"height": "380px", "width": "100%"},
    )
except Exception as e:
    print(f"Deterioration chart error: {e}")
    det_chart = None
```

### 2.7 Add chart to the right panel

Find where the existing charts are assembled (waterfall, cashflow, traffic forecast). Add the deterioration chart AFTER the existing charts. It should be the last chart in the stack.

**Follow the existing pattern exactly.** If charts are wrapped in a div with a CSS class, wrap this one the same way. If they're in a list, append to the list. Example:

```python
# If existing code looks like:
charts_children = [
    waterfall_chart,
    cashflow_chart,
    traffic_chart,
]

# Add:
if det_chart is not None:
    charts_children.append(det_chart)
```

**Do NOT restructure the existing chart layout.** Just append.

### 2.6 Add a section header above the chart

Match the existing section header pattern in the results panel. Something like:
```python
html.Div([
    html.Div("DETERIORATION PREDICTION", style={...}),  # match existing label style
    html.Div("Road condition forecast with and without intervention", style={...}),
], ...)
```
Look at how other chart sections are labeled and copy that pattern exactly.

---

## STEP 3: Add Deterioration Narrative to AI Analysis Block

### Sub-agent task (touches different callback than Step 2):

Find the callback that generates the AI analysis narrative text (the typing animation block). This is likely a separate callback from the chart-building one, or it might be part of the same callback but stored in a different output.

**Option A — If narrative is built by Claude API call:**
Add deterioration context to the prompt. Append to whatever data is sent to the API:
```python
# Add to the context dict/string sent to Claude:
det_summary = get_deterioration_summary(avg_iri, mapped_surface, total_adt)
det_narrative = generate_narrative(det_summary)
# Include det_narrative in the API prompt so Claude can reference it
```

**Option B — If narrative is built by Python string formatting:**
Append the deterioration paragraph:
```python
from analysis.deterioration import get_deterioration_summary, generate_narrative

det_summary = get_deterioration_summary(avg_iri, mapped_surface, total_adt)
det_narrative = generate_narrative(det_summary)
# Append to existing narrative text
narrative_text += f"\n\n{det_narrative}"
```

**Option C — If there's no narrative system yet:**
Skip this step. The chart alone is sufficient.

Wrap in try/except — narrative is a bonus, never crash the app:
```python
try:
    det_summary = get_deterioration_summary(...)
    det_narrative = generate_narrative(det_summary)
except Exception:
    det_narrative = ""
```

---

## STEP 4: Feed Deterioration Data to Report Generator

### Sub-agent task (separate file from Steps 2-3):

Find the report generation module (likely `output/report.py` or similar). The PDF report callback is triggered from the Report step (Step 8).

**If the report module accepts a data dict:** Add deterioration data to it:
```python
# In the report callback, add to the data dict:
report_data['deterioration'] = {
    'summary': det_summary,  # from get_deterioration_summary()
    'narrative': det_narrative,  # from generate_narrative()
    'chart_fig': det_fig,  # the Plotly figure (report can render as image)
}
```

**If the report reads directly from stores:** Add a `deterioration-store` or include deterioration data in the `results-store`:
```python
# In the Step 5 callback, include deterioration in results:
results_data['deterioration_summary'] = det_summary
results_data['deterioration_narrative'] = det_narrative
```

**If report integration is too complex:** Skip it. The chart in Step 5 is the priority. Report is a stretch goal within this stretch goal.

---

## VERIFICATION CHECKLIST

After all changes, test:

1. [ ] `python -c "from analysis.deterioration import create_deterioration_chart, generate_cashflows"` — imports OK?
2. [ ] Start the app — no import errors?
3. [ ] Select a road, run pipeline, enter traffic/costs — all still work?
4. [ ] Click "Run Analysis" (Step 5) — CBA results appear?
5. [ ] **NPV, EIRR, BCR numbers are reasonable?** (EIRR 10-35% for typical Uganda road upgrade. Negative NPV may be correct if ADT is low — see note below.)
6. [ ] **Deterioration chart appears in the right panel?**
7. [ ] **Chart shows: red dashed do-nothing curve rising, green solid with-intervention with maintenance drops, IRI condition bands, event markers?**
8. [ ] Step 6 (Sensitivity) — **still works?** Move the cost slider — NPV should change.
9. [ ] Steps 7-8 (Equity, Report) — still work?

**If NPV is negative:** This may be correct. The deterioration-driven CBA is more realistic than fixed rates. At $800k/km with ADT 350, gravel-to-paved genuinely may not be viable — you'd need ADT ~1000+. At ADT 1500, NPV should be strongly positive. This honest economics is a feature: TARA doesn't lie about project viability.

**If sensitivity breaks after Option A:** Update the sensitivity callback to call `generate_cashflows()` with adjusted parameters.

---

## CONSTRAINTS

### Hard constraints (never violate):
- Do not modify the video/vision pipeline or condition scoring
- Do not modify step navigation or step count
- Do not change any existing callback's Output signature (number and IDs of Outputs) unless necessary for Option A integration
- Do not change the data structure of existing `dcc.Store` components in ways that break downstream consumers — you CAN add new keys, but existing keys must remain
- Do not add new pip dependencies
- Do not add `dcc.Interval`
- Do not change the math or chart styling in `create_deterioration_chart()` — it already matches TARA's palette
- If using Option A (replace CBA), the sensitivity analysis MUST still work — test it

### Soft constraints (use judgment):
- You CAN refactor the Step 5 callback internals to integrate cleanly — e.g. extracting chart creation into helper functions, reorganising how chart children are assembled, adding new keys to results-store (as long as existing keys are preserved)
- You CAN modify the right-panel layout structure if it makes the integration cleaner — e.g. if charts are in a hardcoded list, it's better to make that list dynamic than to hack around it
- You CAN add new `dcc.Store` components if needed (e.g. `deterioration-store`)
- You CAN add the deterioration chart between existing charts if it makes more visual sense (e.g. after the cashflow chart but before the traffic forecast) — it doesn't have to be last
- If the existing code has a chart-building pattern (e.g. a `build_charts()` function), follow that pattern rather than creating a parallel one
- If you see a clearly better way to structure the integration than what this prompt describes, do it — just don't break existing functionality

## SUB-AGENT DISPATCH PLAN

You can parallelise:
- **Agent A:** Step 1 (copy module) + Step 2 (wire into Step 5 callback) — these are sequential and touch the results callback
- **Agent B:** Step 4 (report integration) — touches `output/report.py`, completely independent

Step 3 (narrative) depends on whether the narrative system is in the same callback as Step 2 or separate. If separate, it can also be a sub-agent task. If it's in the same callback, do it sequentially with Step 2.

**File touch map:**
- `analysis/deterioration.py` (NEW — copy in) or `engine/deterioration.py`
- `analysis/__init__.py` (NEW if creating analysis/) or existing `engine/__init__.py`
- The file containing the Step 5 Results callback (likely `callbacks/step5.py` or `app.py`)
- `engine/cba.py` or equivalent (ONLY if using Option A — replace benefit calculation)
- The sensitivity callback file (ONLY if using Option A — must call generate_cashflows with adjusted params)
- The file containing the AI narrative callback (may be same as results callback)
- `output/report.py` (only if doing Step 4)

No other files should be modified.
