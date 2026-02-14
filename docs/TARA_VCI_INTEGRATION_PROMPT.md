# TARA: TMH12 Visual Condition Index — Video Pipeline Integration

## YOUR TASK

Upgrade TARA's dashcam vision assessment from direct IRI guessing to a rigorous
TMH12/ASTM D6433 Visual Condition Index (VCI) methodology.

**Before writing any code, you MUST audit the existing video pipeline.**

---

## STEP 1: AUDIT (do this first, report findings before proceeding)

Read every file related to dashcam/video analysis. At minimum check:

```
video/vision_assess.py
video/video_frames.py
video/gps_utils.py
video/video_map.py
video/video_pipeline.py
video/__init__.py
dashcam.py (root level — may be a duplicate)
```

Also check which files the Dash app actually imports from:
```
app.py
callbacks/ (all files)
```

Answer these questions:

1. **Which module does the Dash app actually call** when the user uploads
   video or triggers analysis? Is it `dashcam.py` or `video/video_pipeline.py`
   or something else?

2. **Is there duplication?** Does `dashcam.py` duplicate functionality in
   `video/vision_assess.py`? If so, which is the active one and which is dead code?

3. **Is tool use already implemented?** Does the current vision API call use
   `tools` + `tool_choice` for structured extraction, or does it use raw JSON
   parsing from text output?

4. **What does the current tool schema look like?** What fields does it extract
   per frame? List them.

5. **What model is being used?** Opus 4.6 or Sonnet? (Should be Opus 4.6 for
   the hackathon — judges score on Opus 4.6 usage.)

6. **How does the system prompt currently instruct Claude?** Does it ask Claude
   to guess IRI directly, or does it score components?

7. **How are results aggregated?** Per-frame → per-section → overall. What's
   the current aggregation logic?

8. **How do results feed into the CBA?** Trace the data flow from vision output
   → condition store → CBA engine. What keys does the CBA expect?

9. **What's the frame extraction strategy?** Time-based (every N seconds) or
   distance-based (every N metres using GPS)?

10. **Are there any other redundancies** you notice in the video pipeline?

**Report your audit findings before writing any code.** I need to see the
answers to decide whether to proceed.

---

## STEP 2: IMPLEMENT VCI ASSESSMENT

Based on your audit findings, implement the following changes in whichever
file(s) are actually active. Remove or consolidate dead code if you find
duplication.

### 2.1 System Prompt — TMH12/ASTM D6433 Protocol

Replace the current system prompt with this. It goes in the `system` parameter
of the API call (enable prompt caching if not already enabled):

```
You are an experienced road engineer conducting a windshield survey in Uganda.
You assess road condition using the TMH12 visual assessment protocol (Jones &
Paige-Green, 2000, CSIR South Africa) for unsealed roads, and ASTM D6433 for
paved roads. You have 15 years of field experience in East Africa.

ASSESSMENT PROTOCOL

For each dashcam frame, you will score the road on specific distress components
using published severity scales. Score ONLY what you can observe in the image.
If a component cannot be assessed from this frame, score it -1.

For each component: first DESCRIBE what you observe in concrete terms, then
assign the degree score based on the criteria below.

═══════════════════════════════════════════════════════════════
UNSEALED ROAD DISTRESS SCALES (TMH12, 5-point degree)
═══════════════════════════════════════════════════════════════

POTHOLES (weight: 0.20)
  0: No potholes visible
  1: Depressions just visible. Shallow, would not be felt in vehicle.
  2: Potholes <20mm deep
  3: Potholes 20-50mm deep, large enough to affect safety
  4: Potholes 50-75mm deep
  5: Large dangerous potholes >75mm deep, vehicles take evasive action

CORRUGATION (weight: 0.15)
  0: No corrugation visible
  1: Faint ripple pattern, would not be felt or heard in a light vehicle
  2: Visible ripple pattern, can be felt/heard but no speed reduction needed
  3: Obvious corrugation, speed reduction necessary
  4: Significant corrugation, significant speed reduction necessary
  5: Severe — vehicles select different path and drive very slowly

EROSION (weight: 0.15)
  Score the worse of transverse or longitudinal erosion:
  0: No erosion visible
  1: Minor evidence of water damage
  2: Erosion channels visible but shallow (<20mm)
  3: Channels 20-40mm deep, speed reduction necessary
  4: Channels 40-60mm deep, significant speed reduction
  5: Deep channels >60mm, vehicles drive very slowly and avoid them

LOOSE MATERIAL (weight: 0.10)
  0: No loose material visible
  1: Just visible — thin dusting of loose material
  2: Loose material <20mm thick
  3: Loose material 20-40mm thick, windrows forming
  4: Loose material 40-60mm thick
  5: Loose material >60mm thick, significant safety hazard

DRAINAGE (weight: 0.15)
  0: Road well above ground level (>300mm), effective side drains visible
  1: Road above ground level, side drains present, functioning
  2: Road slightly above ground (50-300mm), drains present but marginal
  3: Road level with surrounding ground, drains ineffective or absent
  4: Road slightly below ground level, no drains, localised ponding
  5: Road is the lowest point (canal) — serves as drainage for the area

GRAVEL CONDITION (weight: 0.10)
  Combines gravel quantity and quality:
  0: Plenty of gravel, good shape, no stone protrusion, >125mm thick
  1: Sufficient gravel, no subgrade exposure, minor stone protrusion
  2: Good gravel layer but some quality issues (cracking, minor ravelling)
  3: Isolated subgrade exposures (<25%), or gravel quality clearly poor
  4: Extensive subgrade exposures (25-75%), or very poor material quality
  5: No gravel remaining (75-100% subgrade exposed)

ROAD PROFILE (weight: 0.05)
  0: Well-formed camber (~3-4%), road sheds water easily
  1: Good camber (~2%), adequate drainage shape
  2: Camber mostly <2%, minor unevenness
  3: Flat — some ponding likely
  4: Uneven — obvious irregularities impeding drainage
  5: Very uneven — severe irregularities, water flows to centre of road

RIDING QUALITY (weight: 0.10)
  Overall ride assessment:
  0: Very good — comfortable speed >100 km/h
  1: Good — comfortable speed 80-100 km/h
  2: Average-good — comfortable speed ~80 km/h
  3: Average — comfortable speed 60-80 km/h
  4: Poor — comfortable speed 40-60 km/h
  5: Very poor — comfortable speed <40 km/h

═══════════════════════════════════════════════════════════════
PAVED ROAD DISTRESS SCALES (ASTM D6433 adapted, 5-point degree)
═══════════════════════════════════════════════════════════════

When the road surface is paved (asphalt or concrete), use these instead:

SURFACE DISTRESS (weight: 0.30)
  0: Intact surface, no visible defects
  1: Minor hairline cracking, no spalling, surface intact
  2: Moderate cracking pattern visible, isolated patching, edges intact
  3: Interconnected cracking (alligator pattern), potholes present,
     patching >10% of surface, base becoming exposed
  4: Severe cracking, multiple potholes, extensive patching failures
  5: Surface disintegrating, base fully exposed

DEFORMATION (weight: 0.20)
  0: Smooth, no rutting or undulation visible
  1: Minor rutting (<10mm) or slight undulation
  2: Moderate rutting (10-20mm), visible wheel path depressions
  3: Significant rutting (20-40mm), or heaving/shoving visible
  4: Deep rutting (40-60mm), water ponds in wheel paths
  5: Severe deformation (>60mm), vehicles weave to avoid

DRAINAGE (weight: 0.15)
  Same scale as unsealed roads above

EDGE CONDITION (weight: 0.15)
  0: Defined edges, shoulders intact, clear delineation
  1: Minor edge cracking, shoulders mostly intact
  2: Moderate edge break, some shoulder erosion
  3: Significant edge deterioration, shoulder eroded, carriageway narrowing
  4: Severe edge break, no defined shoulder
  5: Complete edge loss, effective road width severely reduced

PATCHING & REPAIRS (weight: 0.10)
  0: No patching visible, or well-executed patches flush with surface
  1: Minor patching visible, patches in good condition
  2: Multiple patches, mostly sound but some deterioration
  3: Extensive patching, some patch failures
  4: Patch-on-patch visible, indicating repeated failure
  5: Patches have mostly failed

RIDING QUALITY (weight: 0.10)
  Same scale as unsealed roads above

═══════════════════════════════════════════════════════════════
SCAN PROTOCOL
═══════════════════════════════════════════════════════════════

Scan the frame systematically:
1. ROAD SURFACE: carriageway — surface type, distresses, width
2. EDGES & SHOULDERS: left and right edges, shoulder condition
3. DRAINAGE: side drains, culverts, water evidence, road elevation vs ground
4. ROADSIDE LEFT: facilities, activity, land use
5. ROADSIDE RIGHT: facilities, activity, land use

═══════════════════════════════════════════════════════════════
SURFACE TYPE IDENTIFICATION
═══════════════════════════════════════════════════════════════

- PAVED ASPHALT: Black/dark grey smooth surface, may show markings
- PAVED CONCRETE: Light grey, may have joints visible
- SURFACE TREATMENT: Thin bituminous layer on gravel base (chip seal)
- GRAVEL: Compacted earth/stone mix, brown/red/grey, no bitumen
- EARTH: Natural ground, no imported material, dirt track
- UNDER CONSTRUCTION: Active construction visible

═══════════════════════════════════════════════════════════════
ACTIVITY & EQUITY OBSERVATIONS
═══════════════════════════════════════════════════════════════

Also observe and report:
- Pedestrian activity: count visible, are they ON the road?
- Cyclists/motorcycles: count visible
- Vehicle types visible (boda-boda, matatu, truck, car, etc.)
- Roadside facilities: health centres, schools, markets, water points
- NMT infrastructure: separated footpath, usable shoulder, or no provision
```

### 2.2 Tool Schema

Replace the current tool definition with this. Keep the same tool use API call
pattern (tools + tool_choice forcing the tool call).

```python
ROAD_VCI_TOOL = {
    "name": "assess_road_condition",
    "description": (
        "Record the visual condition assessment for this dashcam frame "
        "using TMH12 (unsealed) or ASTM D6433 (paved) severity scales."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # ── Surface identification ──
            "surface_type": {
                "type": "string",
                "enum": [
                    "paved_asphalt", "paved_concrete", "surface_treatment",
                    "gravel", "earth", "under_construction",
                ],
                "description": "Dominant surface type of the trafficked carriageway",
            },

            # ── UNSEALED distress scores (TMH12) ──
            "unpaved_potholes_obs": {
                "type": "string",
                "description": "Describe potholes/depressions: approximate size, count, depth",
            },
            "unpaved_potholes": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "TMH12 pothole degree. -1 if cannot assess.",
            },
            "unpaved_corrugation_obs": {
                "type": "string",
                "description": "Describe ripple/corrugation pattern, regularity, apparent depth",
            },
            "unpaved_corrugation": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "TMH12 corrugation degree. -1 if cannot assess.",
            },
            "unpaved_erosion_obs": {
                "type": "string",
                "description": "Describe water channels, runnels, scour marks",
            },
            "unpaved_erosion": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "TMH12 erosion degree. -1 if cannot assess.",
            },
            "unpaved_loose_material_obs": {
                "type": "string",
                "description": "Describe loose stones, sand, windrows, dust evidence",
            },
            "unpaved_loose_material": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "TMH12 loose material degree. -1 if cannot assess.",
            },
            "unpaved_gravel_condition_obs": {
                "type": "string",
                "description": "Describe gravel coverage, subgrade exposure, material quality",
            },
            "unpaved_gravel_condition": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Gravel quantity+quality degree. -1 if cannot assess.",
            },

            # ── PAVED distress scores (ASTM D6433 adapted) ──
            "paved_surface_distress_obs": {
                "type": "string",
                "description": "Describe cracking, potholes, raveling, base exposure",
            },
            "paved_surface_distress": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Surface distress degree. -1 if cannot assess.",
            },
            "paved_deformation_obs": {
                "type": "string",
                "description": "Describe rutting, shoving, heaving, undulation",
            },
            "paved_deformation": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Deformation degree. -1 if cannot assess.",
            },
            "paved_edge_condition_obs": {
                "type": "string",
                "description": "Describe edge break, shoulder condition",
            },
            "paved_edge_condition": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Edge condition degree. -1 if cannot assess.",
            },
            "paved_patching_obs": {
                "type": "string",
                "description": "Describe patched areas, patch condition",
            },
            "paved_patching": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Patching degree. -1 if cannot assess.",
            },

            # ── SHARED components (both surface types) ──
            "drainage_obs": {
                "type": "string",
                "description": "Describe side drains, road elevation vs ground, water evidence",
            },
            "drainage": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "TMH12 drainage degree. -1 if cannot assess.",
            },
            "road_profile_obs": {
                "type": "string",
                "description": "Describe camber/crown, cross-slope",
            },
            "road_profile": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Road profile degree. -1 if cannot assess.",
            },
            "riding_quality": {
                "type": "integer", "minimum": -1, "maximum": 5,
                "description": "Overall riding quality degree. -1 if cannot assess.",
            },

            # ── Road geometry ──
            "road_width_estimate_m": {
                "type": ["number", "null"],
                "description": "Estimated carriageway width in metres",
            },
            "has_markings": {
                "type": "boolean",
                "description": "Are road markings visible?",
            },

            # ── Equity / activity observations ──
            "pedestrian_count": {
                "type": "integer", "minimum": 0,
                "description": "Number of pedestrians visible",
            },
            "pedestrians_on_road": {
                "type": "boolean",
                "description": "Are pedestrians walking ON the carriageway?",
            },
            "cyclist_motorcycle_count": {
                "type": "integer", "minimum": 0,
                "description": "Number of cyclists and boda-bodas visible",
            },
            "vehicle_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "car", "suv_pickup", "minibus_matatu", "bus",
                        "light_truck", "heavy_truck", "semi_trailer",
                        "boda_boda", "bicycle", "handcart", "tractor", "none",
                    ],
                },
                "description": "Vehicle types visible in frame",
            },
            "facilities_visible": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "health_centre", "school", "market", "water_point",
                        "place_of_worship", "commercial", "fuel_station", "none",
                    ],
                },
                "description": "Roadside facilities visible",
            },
            "nmt_infrastructure": {
                "type": "string",
                "enum": [
                    "separated_footpath", "usable_shoulder",
                    "no_provision", "not_visible",
                ],
                "description": "NMT infrastructure provision",
            },
            "notes": {
                "type": "string",
                "description": "Other observations: construction, hazards, landmarks",
            },
        },
        "required": [
            "surface_type",
            "drainage", "drainage_obs",
            "road_profile", "road_profile_obs",
            "riding_quality",
            "road_width_estimate_m", "has_markings",
            "pedestrian_count", "pedestrians_on_road",
            "cyclist_motorcycle_count", "vehicle_types",
            "facilities_visible", "nmt_infrastructure",
            "notes",
        ],
    },
}
```

**Note:** The surface-specific distress fields (unpaved_* or paved_*) are
intentionally NOT in the required list. Claude fills the appropriate set based
on surface_type. This prevents errors on under_construction or mixed surfaces.

### 2.3 VCI Computation Functions

Add these functions to the appropriate module (wherever the aggregation logic
lives). These replace any existing condition_score or IRI guessing logic.

```python
import math

UNPAVED_WEIGHTS = {
    "unpaved_potholes": 0.20,
    "unpaved_corrugation": 0.15,
    "unpaved_erosion": 0.15,
    "unpaved_loose_material": 0.10,
    "unpaved_gravel_condition": 0.10,
    "drainage": 0.15,
    "road_profile": 0.05,
    "riding_quality": 0.10,
}

PAVED_WEIGHTS = {
    "paved_surface_distress": 0.30,
    "paved_deformation": 0.20,
    "paved_edge_condition": 0.15,
    "paved_patching": 0.10,
    "drainage": 0.15,
    "riding_quality": 0.10,
}


def compute_vci(assessment: dict) -> float:
    """
    Compute Visual Condition Index (0-100) from TMH12 distress scores.
    0 = perfect condition, 100 = worst possible.
    Only components scored >= 0 are included (handles partial visibility).
    """
    surface = assessment.get("surface_type", "gravel")

    if surface in ("paved_asphalt", "paved_concrete"):
        weights = PAVED_WEIGHTS
    else:
        weights = UNPAVED_WEIGHTS

    weighted_sum = 0.0
    total_weight = 0.0

    for component, weight in weights.items():
        score = assessment.get(component, -1)
        if isinstance(score, (int, float)) and score >= 0:
            weighted_sum += score * weight
            total_weight += weight

    if total_weight == 0:
        return 50.0  # fallback if nothing scored

    vci = (weighted_sum / (5.0 * total_weight)) * 100.0
    return round(vci, 1)


def vci_to_iri(vci_score: float, surface_type: str) -> tuple:
    """
    Convert VCI to IRI estimate using published PCI-IRI relationships.
    Returns (iri_low, iri_mid, iri_high).

    Sources:
        Paved: Egypt/Iran PCI-IRI exponential (R² 0.75-0.82)
        Gravel: HDM-4 gravel deterioration ranges
        Earth: World Bank TP46 reference scale
    """
    if surface_type in ("paved_asphalt", "paved_concrete"):
        pci_equiv = 100.0 - vci_score
        iri_mid = 16.07 * math.exp(-0.026 * pci_equiv)
        uncertainty = 0.25

    elif surface_type == "surface_treatment":
        pci_equiv = 100.0 - vci_score
        iri_mid = 18.0 * math.exp(-0.024 * pci_equiv)
        uncertainty = 0.30

    elif surface_type == "gravel":
        iri_mid = 6.0 + (vci_score / 100.0) * 14.0
        uncertainty = 0.35

    elif surface_type == "earth":
        iri_mid = 8.0 + (vci_score / 100.0) * 16.0
        uncertainty = 0.40

    else:
        iri_mid = 12.0
        uncertainty = 0.50

    iri_low = max(1.0, round(iri_mid * (1.0 - uncertainty), 1))
    iri_mid = round(iri_mid, 1)
    iri_high = min(24.0, round(iri_mid * (1.0 + uncertainty), 1))

    return (iri_low, iri_mid, iri_high)


def classify_condition(iri_mid: float) -> str:
    """IRI to condition class."""
    if iri_mid <= 3.0:
        return "very_good"
    elif iri_mid <= 5.0:
        return "good"
    elif iri_mid <= 8.0:
        return "fair"
    elif iri_mid <= 12.0:
        return "poor"
    elif iri_mid <= 16.0:
        return "very_poor"
    else:
        return "impassable"
```

### 2.4 Section Aggregation

Update the section aggregation to use median VCI:

```python
def aggregate_section(frame_assessments: list) -> dict:
    """
    Aggregate per-frame assessments into section-level summary.
    Uses median VCI (robust to outlier frames).
    """
    if not frame_assessments:
        return None

    vcis = [compute_vci(a) for a in frame_assessments]
    vci_median = sorted(vcis)[len(vcis) // 2]

    # Dominant surface type (mode)
    surfaces = [a.get("surface_type", "gravel") for a in frame_assessments]
    surface_mode = max(set(surfaces), key=surfaces.count)

    iri_low, iri_mid, iri_high = vci_to_iri(vci_median, surface_mode)
    condition = classify_condition(iri_mid)

    # Per-component averages for the report
    if surface_mode in ("paved_asphalt", "paved_concrete"):
        components = list(PAVED_WEIGHTS.keys())
    else:
        components = list(UNPAVED_WEIGHTS.keys())

    distress_summary = {}
    for comp in components:
        scores = [a.get(comp, -1) for a in frame_assessments]
        valid = [s for s in scores if s >= 0]
        distress_summary[comp] = round(sum(valid) / len(valid), 1) if valid else None

    # Equity aggregation
    total_peds = sum(a.get("pedestrian_count", 0) for a in frame_assessments)
    peds_on_road = sum(1 for a in frame_assessments if a.get("pedestrians_on_road"))
    total_cyclists = sum(a.get("cyclist_motorcycle_count", 0) for a in frame_assessments)

    all_facilities = []
    for a in frame_assessments:
        fac = a.get("facilities_visible", [])
        all_facilities.extend([f for f in fac if f != "none"])

    all_vehicles = []
    for a in frame_assessments:
        vt = a.get("vehicle_types", [])
        all_vehicles.extend([v for v in vt if v != "none"])

    nmt_provisions = [a.get("nmt_infrastructure", "not_visible") for a in frame_assessments]
    nmt_worst = "no_provision" if "no_provision" in nmt_provisions else (
        "usable_shoulder" if "usable_shoulder" in nmt_provisions else "separated_footpath"
    )

    return {
        "vci": vci_median,
        "iri_low": iri_low,
        "iri_mid": iri_mid,
        "iri_high": iri_high,
        "condition_class": condition,
        "surface_type": surface_mode,
        "n_frames": len(frame_assessments),
        "distress_summary": distress_summary,
        "equity_summary": {
            "total_pedestrians": total_peds,
            "frames_with_pedestrians_on_road": peds_on_road,
            "total_cyclists_motorcycles": total_cyclists,
            "facilities_observed": list(set(all_facilities)),
            "vehicle_types_observed": list(set(all_vehicles)),
            "nmt_provision": nmt_worst,
        },
    }
```

### 2.5 Model Selection

The API call MUST use `claude-opus-4-6-20250514`. If it currently uses Sonnet,
change it. The hackathon judges score on Opus 4.6 usage (25% of total score).

### 2.6 Downstream Compatibility

After implementing VCI, make sure:

- The condition store (dcc.Store or equivalent) receives `iri_mid` where it
  previously received the IRI estimate
- The CBA engine receives the IRI value it expects
- The map coloring still works (uses condition_class)
- The sensitivity analysis still works if it varies condition
- The AI analysis panel text still renders

Trace the data flow and fix any broken references.

---

## STEP 3: CLEAN UP DUPLICATION

If you find that `dashcam.py` and `video/vision_assess.py` duplicate
functionality:

- Keep the one that's actually used by the Dash app
- Delete or deprecate the other
- If the app imports from both, consolidate into one path

Do NOT leave dead code that confuses future maintenance.

---

## CONSTRAINTS

**Hard constraints — do not violate:**
- Do NOT break the existing app. It must still run after your changes.
- Do NOT change the Dash UI layout or step navigation.
- Do NOT remove equity observation fields (pedestrians, facilities, vehicles, NMT).
- The VCI computation MUST happen in Python, not in the Claude prompt.
  Claude scores components; Python computes VCI and converts to IRI.
- Use tool_choice to FORCE the tool call (no optional tool use).

**Soft constraints:**
- You can rename tool fields
- You can add new keys to stores
- You can refactor aggregation logic
- You can add the VCI functions to an existing module or create a new one

---

## VERIFICATION

After implementation, verify:

1. [ ] `compute_vci()` returns 0 for all-zero scores and 100 for all-five scores
2. [ ] `vci_to_iri(0, "gravel")` returns approximately (3.9, 6.0, 8.1)
3. [ ] `vci_to_iri(100, "gravel")` returns approximately (13.0, 20.0, 24.0)
4. [ ] `vci_to_iri(0, "paved_asphalt")` returns approximately (1.1, 1.2, 1.5)
5. [ ] Vision API call uses model `claude-opus-4-6-20250514`
6. [ ] Vision API call uses tool_choice forcing `assess_road_condition`
7. [ ] No JSON parsing of text responses (tool use handles structure)
8. [ ] Section aggregation uses median VCI, not mean
9. [ ] CBA engine receives a valid IRI number
10. [ ] Map coloring works with the new condition_class values
11. [ ] No duplicate dashcam analysis code remains
