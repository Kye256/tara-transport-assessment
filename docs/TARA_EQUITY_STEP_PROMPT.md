# TARA — Equity Step & Display Prompt
# Sequential execution — touches app.py, layouts, callbacks

Do NOT commit anything. Do NOT run git commands. I will test and commit manually.

---

## CONTEXT

The equity integration just landed — the Vision prompt now captures activity_profile data (land use, pedestrians, facilities, vehicles, NMT) per frame, sections aggregate this into equity data, and an equity narrative is generated. 

BUT:
1. The equity data is only visible in section popups and a narrative panel — there's no structured display
2. Facilities observed by the camera are not showing prominently in the output
3. Equity findings deserve their own step in the wizard — they're a major feature, not a footnote

We are adding a NEW Step 7 (Equity & Social Impact) and pushing the current Step 7 (Report) to Step 8.

---

## STEP 0: AUDIT

Before changing anything, read and report:

1. How is step navigation implemented? (look for step count, step labels, step visibility logic)
2. Where are step labels defined? (the horizontal nav bar with "1. Road", "2. Condition", etc.)
3. How does the step nav bar render? (is it generated from a list? hardcoded?)
4. Where is the current Step 7 (Report) layout defined?
5. What `dcc.Store` IDs contain equity data from the pipeline? (search for "equity" in stores)
6. What does the pipeline result dict look like? (search for where pipeline result is unpacked into stores — what keys are extracted?)
7. Read the equity narrative panel that was just added — where is it, what store does it read from?
8. Read `video/video_map.py` — what does the `equity` key in section properties contain? List all fields.

Report all findings before proceeding.

---

## STEP 1: Expand Wizard from 7 to 8 Steps

Find where the step count and step labels are defined. Update:

- Total steps: 7 → 8
- Step labels should now be:
  1. Road
  2. Condition  
  3. Traffic
  4. Costs
  5. Results
  6. Sensitivity
  7. Equity (NEW)
  8. Report (was 7)

Update ALL places that reference step count or step 7:
- Step navigation bar (labels and count)
- Next/Back button logic
- Step visibility callbacks
- Any hardcoded references to "step 7" for the report

**Test mentally:** After this change, clicking "Next" from Step 6 (Sensitivity) should show Step 7 (Equity), and clicking "Next" from Step 7 should show Step 8 (Report). The Back button on Report should go to Equity.

---

## STEP 2: Create the Equity Step Layout

Create the layout for Step 7. It should have THREE sections stacked vertically in the left panel:

### Section A: Equity Summary Table

A per-section table showing what the camera observed. This is the structured data view.

Build the table from the equity data in the pipeline result sections. Each row is one section:

| Column | Data Source | Format |
|--------|-----------|--------|
| Section | section_index + 1 | "1", "2", "3" |
| Length | section length_km | "1.2 km" |
| Land Use | equity.dominant_land_use | Title case, replace underscores: "Trading Centre" |
| Activity | equity.activity_level | "High", "Moderate", "Low" |
| Facilities Observed | equity.facilities_seen | Comma-joined: "Shops, school, church" or "—" if empty |
| Pedestrians | equity.pedestrian_presence | "Many", "Some", "Few", "None" |
| NMT Provision | equity.nmt_footpath | "Good", "Poor", "None ⚠" |
| Vehicles | equity.vehicle_mix_summary | Top 2-3 types: "Boda-bodas (many), cars (some)" |
| Concern | equity.equity_concern | "HIGH", "MODERATE", "LOW" |

**Styling:**
- Use `html.Table` (not Dash DataTable — keep it simple, matches existing UI)
- Row background color by equity_concern:
  - HIGH: `#a83a2f15` (light red tint)
  - MODERATE: `#9a6b2f15` (light amber tint)  
  - LOW: no tint
- Concern cell text color:
  - HIGH: `#a83a2f` bold
  - MODERATE: `#9a6b2f` bold
  - LOW: `#5c5950`
- Table header: 9px uppercase mono, muted text color `#8a8578`
- Table cells: 12px Source Sans 3
- Cell padding: 6px 10px
- Borders: 1px solid `#e8e5de`
- Section header above table: "CAMERA OBSERVATIONS BY SECTION" in 9px uppercase mono

### Section B: Key Findings Summary

A brief stats box above or below the table:

```
EQUITY SUMMARY
─────────────────────────────
Sections surveyed:        5
High equity concern:      2 (Sections 2, 4)
Facilities observed:      Shops, school, church, mosque, health facility
Dominant road users:      Pedestrians, boda-bodas
NMT provision:           3 of 5 sections have no footpath
School children observed: Sections 2, 4
```

Build this from aggregating across all sections. Use the panel background style (`#f0eeea`, 1px border `#ddd9d1`).

### Section C: AI Equity Narrative

Move the equity narrative panel here (from wherever it currently is). This is the AI-generated prose assessment. Same styling as before — panel bg, 3px left border in blue (`#3a5a80`), label "EQUITY IMPACT ASSESSMENT" in 9px uppercase mono.

If the equity narrative panel was added to the condition/results step by the previous build, REMOVE it from there and place it here instead. It should only appear once, in Step 7.

---

## STEP 3: Wire the Data

The equity table and summary need data from the pipeline result. Find where the pipeline result is unpacked into `dcc.Store` components.

**Option A (preferred):** If there's already a store containing the full pipeline result or the sections data, read from that.

**Option B:** If equity data isn't in a store yet, add a new `dcc.Store(id='equity-data-store')` and populate it when the pipeline result arrives. Store the list of section equity dicts.

The callback for Step 7 should:
1. Read the equity data from the store
2. Build the table rows from section equity data
3. Build the key findings summary from aggregated data  
4. Return the equity narrative text

**CRITICAL:** If equity data is not available (e.g., old cached pipeline run without equity), show a message: "Equity data not available for this survey. Re-run video analysis with the latest version to generate equity observations."

---

## STEP 4: Update Map for Equity Step

When the user is on Step 7 (Equity), the map should ideally show sections colored by equity concern instead of condition. But this is OPTIONAL — only do it if it's straightforward with the existing map callback structure.

**If easy:** Add a toggle or automatically switch section colors when on Step 7:
- HIGH concern: `#a83a2f` (red)
- MODERATE concern: `#9a6b2f` (amber)
- LOW concern: `#2d5f4a` (green)

**If complex:** Skip this. The condition-colored map with equity popups is fine.

Do NOT break the existing map display for other steps.

---

## STEP 5: Check Facilities Data

Read the actual pipeline cache or result to check: are facilities being captured?

Look at the frames in the cached result:
- Do any frames have `activity_profile.facilities_visible` with actual values?
- Or are they all returning `["none"]` or empty arrays?

If facilities data IS present but not showing in the table, it's a display issue — fix the table rendering.

If facilities data is NOT present (all empty/none), the issue is in the Vision prompt or the model's response. Report this but do NOT change the Vision prompt — we'll address it separately.

---

## STEP 6: Verify

After all changes:

1. [ ] Step navigation shows 8 steps with correct labels?
2. [ ] Clicking through all 8 steps works (Next/Back)?
3. [ ] Step 7 shows the equity summary table?
4. [ ] Table rows are colored by equity concern?
5. [ ] Facilities column shows observed facilities (or "—" if none)?
6. [ ] Key findings summary shows aggregated stats?
7. [ ] Equity narrative panel appears in Step 7?
8. [ ] Equity narrative does NOT appear in any other step?
9. [ ] Step 8 (Report) still works correctly?
10. [ ] No existing functionality broken?

Report results.

---

## DO NOT

- Do not change the Vision prompt or video pipeline
- Do not change the CBA engine or sensitivity analysis  
- Do not delete or move existing steps (only insert new step 7 and renumber old step 7 to 8)
- Do not add new pip dependencies
- Do not add `dcc.Interval`
- Do not restructure the app layout pattern — follow existing conventions

## FILE TOUCH MAP

- Step navigation config (wherever step labels/count are defined)
- Layout file for new Step 7 (new file or added to existing layout module)
- Callback file for Step 7 data (new or added to existing)
- app.py (only if step registration happens there)
- Remove equity panel from wherever the previous build placed it (if not Step 7)
