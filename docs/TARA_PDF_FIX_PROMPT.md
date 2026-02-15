# TARA PDF Report Fix — Data Flow, Narratives, Images & Branding

## Priority: HIGH — The report is a demo deliverable

Read these files first:
- `output/report_gen.py` (the PDF generator)
- `app.py` — find the callback that triggers report generation and see what data it passes
- `assets/style.css` — for colour reference

---

## BUG 1: "Road Appraisal (N/A km)" — No road name or length

The PDF title page says "Road Appraisal" and the executive summary says "N/A km". The road name and length exist in the app — they come from the video pipeline or road selection.

**Debug steps:**
1. Find the report generation callback in `app.py`
2. Check what stores it reads: `road-data-store`, `video-condition-store`, `condition-store`
3. The video pipeline stores road info including the dataset name and total length. Trace where this data is supposed to flow into `report_gen.py`
4. The dataset name (e.g., "Kasangati - Matugga") should be the road name on the title page
5. The total road length is in the video condition store (sum of section lengths)

**Fix:** Ensure the report generator receives and uses:
- Road name (from dataset name or road-data-store)
- Road length (sum of section lengths from video-condition-store)
- Replace all instances of "Road Appraisal" with the actual road name
- Replace "N/A km" with actual length formatted to 1 decimal

---

## BUG 2: Per-section condition table shows all "?"

Page 10 shows 15 sections but every row has "?" for surface, condition, IRI, and intervention. The data IS in `video-condition-store` — the costs step (Step 4) displays it correctly in the UI with actual values (Earth, Poor, 9.1, etc).

**Fix:** The report generator is not reading the per-section data from the store. Find where it builds the condition table and ensure it reads from `video-condition-store['sections']` (or whatever key holds the section array). Each section should have: surface, condition, iri, intervention.

---

## BUG 3: No narratives in the report

The app generates two powerful AI narratives that are NOT in the PDF:

1. **Condition narrative** — The AI analysis of road condition (visible in Step 2 panel). This text describes distress types, IRI implications, and intervention needs. It's stored in `video-condition-store` (check for keys like `narrative`, `condition_narrative`, or `analysis_text`).

2. **Equity narrative** — The AI analysis of who benefits from the road (visible in Step 5 below the equity cards). This text describes pedestrian safety, NMT gaps, trading centres, and school children. Check `equity-store` or `video-condition-store` for keys like `equity_narrative`, `equity_analysis`, or similar.

**Fix:** Add both narratives to the PDF:
- Condition narrative → goes in Section 8 (Road Condition), after the condition table
- Equity narrative → goes in Section 7 (Equity Assessment), after the score breakdown

Use reportlab Paragraph with word wrapping. Style: 10pt, line spacing 1.4, left-aligned.

---

## BUG 4: "Road Description" and "Corridor Context" say "not available"

These sections show placeholder text because no road-data-store or population data flows in.

**Fix options (pick one):**
- If road-data-store has data: pipe it through
- If not (because we skipped road selection and went straight to video): Generate a brief description from the video pipeline data. Something like: "The assessed corridor is approximately 12.4 km of predominantly earth surface road. The assessment covered 15 sections based on dashcam analysis of 244 frames."
- For corridor context: Use equity data if available (facilities count, land use observations). If no population data: "Population data not available. Camera-based equity observations indicate 11 facilities along the corridor including health centres, trading centres, and fuel stations."

---

## IMPROVEMENT 1: Dashcam images in the report

The video pipeline caches extracted frames. Including 3-4 representative images makes the report dramatically more credible.

**Implementation:**
1. Find the cached frames directory. It's typically at `data/videos/[dataset_name]/cache/frames/` or similar. Check the video pipeline code for where frames are saved.
2. Pick representative frames — one from first section, one from worst condition section, one from best condition section, one showing a facility/trading centre if possible. If that's too complex, just pick frames at 25%, 50%, 75% of the total frame count.
3. Add images to the PDF using reportlab:

```python
from reportlab.platypus import Image as RLImage
from reportlab.lib.units import inch

def add_frame_image(story, frame_path, caption=""):
    """Add a dashcam frame to the report."""
    if os.path.exists(frame_path):
        img = RLImage(frame_path, width=5*inch, height=2.8*inch)  # 16:9 aspect
        story.append(img)
        if caption:
            story.append(Paragraph(caption, caption_style))
        story.append(Spacer(1, 12))
```

4. Place images in Section 8 (Road Condition) between the summary table and the per-section table. Add captions like: "Frame from Section 3 — Earth surface with corrugation and edge break (IRI 9.1 m/km)"

**If the frame paths are hard to find or this takes more than 20 minutes, skip it.** The narratives and data fixes are more important.

---

## IMPROVEMENT 2: Report preview in Step 7

The left panel preview currently shows the raw PDF title. Make it show a clean summary instead:

```python
html.Div([
    html.H3("TARA Road Appraisal Report", style={...}),
    html.P(road_name, style={"fontWeight": "bold"}),
    html.P(f"Generated: {date}", style={"fontStyle": "italic", "color": "#8a8578"}),
    html.Hr(),
    html.P(f"NPV: ${npv:,.0f}  |  EIRR: {eirr:.1f}%  |  BCR: {bcr:.2f}"),
    html.P(f"Verdict: ECONOMICALLY VIABLE" if viable else "NOT VIABLE"),
    html.P(f"Equity Score: {equity_score}/100"),
    html.P(f"Road Length: {length:.1f} km  |  Sections: {n_sections}"),
], className="report-preview")
```

This shows the user what's IN the report without rendering the actual PDF.

---

## BRANDING: Green accent bar on title page

If using reportlab, add a green bar across the top of the title page:

```python
from reportlab.lib.colors import HexColor

def draw_title_page(c, width, height):
    # Green header bar
    c.setFillColor(HexColor('#2d5f4a'))
    c.rect(0, height - 60, width, 60, fill=True, stroke=False)
    
    # TARA text in white on green bar
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 24)
    c.drawString(40, height - 42, 'TARA')
    
    # Subtitle
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica', 11)
    c.drawString(100, height - 42, 'Transport Appraisal & Risk Analysis')
```

Also add a thin green line (2pt, #2d5f4a) under each section heading throughout the report.

---

## VALIDATION CHECKLIST

After changes, generate a PDF and verify:
- [ ] Title page shows actual road name (e.g., "Kasangati - Matugga Road")
- [ ] Title page shows road length (e.g., "12.4 km")
- [ ] Executive summary has correct road name and length
- [ ] Per-section condition table has actual data (not "?")
- [ ] Condition narrative is present in Road Condition section
- [ ] Equity narrative is present in Equity Assessment section
- [ ] Road Description has at least basic info from pipeline
- [ ] Green header bar on title page
- [ ] All charts still render correctly in PDF
- [ ] Report preview in Step 7 shows road name and key metrics

## WHAT NOT TO CHANGE
- Do NOT rewrite the PDF generator from scratch
- Do NOT change the PDF library (stay with whatever is currently used — reportlab or fpdf)
- Do NOT change any dcc.Store IDs or callback signatures
- Do NOT spend more than 1.5 hours on this — fix bugs first, add images if time allows
