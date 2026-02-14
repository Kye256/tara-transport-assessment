"""Claude Vision road condition assessment using TMH12/ASTM D6433 VCI methodology.

Uses tool_use for structured distress scoring. Python computes VCI, IRI, and condition class.
"""

import time

from video.vci import (
    compute_vci,
    vci_to_iri,
    classify_condition,
    condition_to_ui_class,
    UNPAVED_WEIGHTS,
    PAVED_WEIGHTS,
)


VCI_SYSTEM_PROMPT = """You are an experienced road engineer conducting a windshield survey in Uganda.
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
- NMT infrastructure: separated footpath, usable shoulder, or no provision"""


ROAD_VCI_TOOL = {
    "name": "assess_road_condition",
    "description": (
        "Record the visual condition assessment for this dashcam frame "
        "using TMH12 (unsealed) or ASTM D6433 (paved) severity scales."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # -- Surface identification --
            "surface_type": {
                "type": "string",
                "enum": [
                    "paved_asphalt", "paved_concrete", "surface_treatment",
                    "gravel", "earth", "under_construction",
                ],
                "description": "Dominant surface type of the trafficked carriageway",
            },

            # -- UNSEALED distress scores (TMH12) --
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

            # -- PAVED distress scores (ASTM D6433 adapted) --
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

            # -- SHARED components (both surface types) --
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

            # -- Road geometry --
            "road_width_estimate_m": {
                "type": ["number", "null"],
                "description": "Estimated carriageway width in metres",
            },
            "has_markings": {
                "type": "boolean",
                "description": "Are road markings visible?",
            },

            # -- Equity / activity observations --
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


def _build_backward_compat(assessment: dict) -> dict:
    """Add backward-compatible keys to a VCI assessment dict.

    Adds: iri_estimate, condition_class, distress_types, distress_severity,
    roadside_environment, activity_profile, vci, iri_low, iri_mid, iri_high.
    """
    vci = compute_vci(assessment)
    surface = assessment.get("surface_type", "gravel")
    iri_low, iri_mid, iri_high = vci_to_iri(vci, surface)
    condition_6 = classify_condition(iri_mid)
    condition_4 = condition_to_ui_class(condition_6)

    # Distress types: component names where score >= 3
    all_weights = {**UNPAVED_WEIGHTS, **PAVED_WEIGHTS}
    distress_types = [
        comp for comp in all_weights
        if isinstance(assessment.get(comp, -1), (int, float)) and assessment.get(comp, -1) >= 3
    ] or ["none"]

    # Distress severity from VCI
    if vci < 10:
        distress_severity = "none"
    elif vci < 30:
        distress_severity = "low"
    elif vci < 50:
        distress_severity = "moderate"
    elif vci < 70:
        distress_severity = "high"
    else:
        distress_severity = "severe"

    # Build nested activity_profile for equity aggregation compatibility
    ped_count = assessment.get("pedestrian_count", 0)
    if ped_count >= 5:
        ped_level = "many"
    elif ped_count >= 2:
        ped_level = "some"
    elif ped_count >= 1:
        ped_level = "few"
    else:
        ped_level = "none"

    cyclist_count = assessment.get("cyclist_motorcycle_count", 0)
    if cyclist_count >= 3:
        boda_level = "many"
    elif cyclist_count >= 1:
        boda_level = "some"
    else:
        boda_level = "none"

    nmt = assessment.get("nmt_infrastructure", "not_visible")
    footpath_map = {
        "separated_footpath": "good",
        "usable_shoulder": "poor",
        "no_provision": "none",
        "not_visible": "none",
    }

    facilities = assessment.get("facilities_visible", ["none"])
    # Map new facility names to old-format names
    facility_map = {
        "health_centre": "health_facility",
        "school": "school",
        "market": "market_stalls",
        "water_point": "water_point",
        "place_of_worship": "church",
        "commercial": "shops",
        "fuel_station": "fuel_station",
        "none": "none",
    }
    mapped_facilities = [facility_map.get(f, f) for f in facilities]

    vehicle_types = assessment.get("vehicle_types", ["none"])
    vt_has = lambda t: t in vehicle_types  # noqa: E731

    activity_profile = {
        "land_use": "mixed",  # not directly assessed in VCI tool
        "activity_level": "moderate" if ped_count > 0 or cyclist_count > 0 else "low",
        "people_observed": {
            "pedestrians": ped_level,
            "school_children": False,  # not separately tracked in VCI
            "vendors_roadside": "market" in facilities or "commercial" in facilities,
            "people_carrying_loads": False,
        },
        "vehicles_observed": {
            "boda_bodas": boda_level,
            "bicycles": "some" if "bicycle" in vehicle_types else "none",
            "minibus_taxi": "some" if "minibus_matatu" in vehicle_types else "none",
            "cars": "some" if vt_has("car") or vt_has("suv_pickup") else "none",
            "trucks": "some" if vt_has("light_truck") or vt_has("heavy_truck") or vt_has("semi_trailer") else "none",
        },
        "facilities_visible": mapped_facilities,
        "nmt_infrastructure": {
            "footpath": footpath_map.get(nmt, "none"),
            "shoulder_usable": nmt == "usable_shoulder",
            "pedestrians_on_carriageway": assessment.get("pedestrians_on_road", False),
        },
    }

    result = dict(assessment)
    result.update({
        "vci": vci,
        "iri_low": iri_low,
        "iri_mid": iri_mid,
        "iri_high": iri_high,
        "iri_estimate": iri_mid,  # backward compat
        "condition_class": condition_4,  # 4-class for section breaking
        "condition_class_6": condition_6,  # 6-class for enhanced display
        "distress_types": distress_types,
        "distress_severity": distress_severity,
        "roadside_environment": "peri_urban",  # default, not in VCI tool
        "activity_profile": activity_profile,
    })
    return result


DEFAULT_ASSESSMENT = {
    "surface_type": "unknown",
    "condition_class": "fair",
    "iri_estimate": 8.0,
    "vci": 50.0,
    "iri_low": 4.0,
    "iri_mid": 8.0,
    "iri_high": 12.0,
    "condition_class_6": "fair",
    "distress_types": ["unknown"],
    "distress_severity": "moderate",
    "roadside_environment": "peri_urban",
    "notes": "Assessment could not be completed",
    "activity_profile": {
        "land_use": "unknown",
        "activity_level": "unknown",
        "people_observed": {"pedestrians": "none", "school_children": False, "vendors_roadside": False, "people_carrying_loads": False},
        "vehicles_observed": {"boda_bodas": "none", "bicycles": "none", "minibus_taxi": "none", "cars": "none", "trucks": "none"},
        "facilities_visible": ["none"],
        "nmt_infrastructure": {"footpath": "none", "shoulder_usable": False, "pedestrians_on_carriageway": False},
    },
}


def assess_frame(image_base64: str, anthropic_client, model: str = "claude-opus-4-6") -> dict:
    """Send one frame to Claude Vision with TMH12/ASTM D6433 tool_use.

    Uses forced tool_choice to get structured distress scores.
    Python computes VCI, IRI, and condition class from the scores.

    Args:
        image_base64: JPEG image as base64 string.
        anthropic_client: Anthropic client instance.
        model: model ID to use.

    Returns:
        Assessment dict with VCI data and backward-compat keys.
    """
    for attempt in range(2):
        try:
            response = anthropic_client.messages.create(
                model=model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": VCI_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                tools=[ROAD_VCI_TOOL],
                tool_choice={"type": "tool", "name": "assess_road_condition"},
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": "Assess this road frame."},
                    ],
                }],
            )

            # Extract structured tool input — no JSON parsing needed
            tool_input = response.content[0].input

            # Build full assessment with VCI computation and backward compat
            return _build_backward_compat(tool_input)

        except Exception as e:
            if attempt == 0:
                continue
            print(f"  Vision API error: {e}")
            return dict(DEFAULT_ASSESSMENT)


_MOCK_COUNTER = 0

# Deterministic cycling sequences for reproducible testing
_MOCK_SURFACES = ["paved_asphalt", "paved_asphalt", "gravel", "earth"]
_MOCK_NOTES = [
    "Tarmac in fair condition with edge erosion",
    "Paved surface with patching and minor cracks",
    "Gravel road with corrugation visible",
    "Laterite surface with moderate potholing",
    "Road under active construction with earthworks",
    "Earth road with deep ruts after rain",
]

# Distress score profiles: (potholes, corrugation, erosion, loose, gravel, drainage, profile, riding)
_MOCK_UNPAVED_SCORES = [
    (1, 1, 0, 1, 1, 1, 1, 1),  # good
    (0, 0, 1, 0, 1, 1, 0, 1),  # good
    (2, 2, 2, 1, 2, 2, 2, 2),  # fair
    (2, 2, 1, 2, 2, 2, 1, 2),  # fair
    (3, 3, 3, 3, 3, 3, 3, 3),  # poor
    (1, 0, 1, 0, 1, 1, 1, 1),  # good
    (0, 1, 0, 1, 0, 1, 0, 1),  # good
    (2, 1, 2, 1, 2, 2, 2, 2),  # fair
    (3, 3, 2, 3, 3, 3, 3, 4),  # poor
    (4, 4, 4, 4, 4, 4, 4, 5),  # bad
]
# Paved scores: (surface_distress, deformation, edge, patching, drainage, riding)
_MOCK_PAVED_SCORES = [
    (1, 0, 1, 0, 1, 1),  # good
    (0, 1, 0, 1, 1, 1),  # good
    (2, 1, 2, 1, 2, 2),  # fair
    (2, 2, 2, 2, 2, 2),  # fair
    (3, 3, 3, 3, 3, 3),  # poor
    (1, 0, 0, 1, 1, 1),  # good
    (0, 0, 1, 0, 1, 0),  # good
    (2, 2, 1, 2, 2, 2),  # fair
    (3, 3, 3, 2, 3, 4),  # poor
    (4, 4, 4, 4, 4, 5),  # bad
]


def assess_frame_mock(image_base64: str) -> dict:
    """Return deterministic VCI-format assessment for testing without API.

    Cycles through surface types and distress score profiles to produce
    realistic VCI assessments with all backward-compat keys.
    """
    global _MOCK_COUNTER
    idx = _MOCK_COUNTER
    _MOCK_COUNTER += 1

    surface = _MOCK_SURFACES[idx % len(_MOCK_SURFACES)]

    # Build raw assessment (simulating tool_use output)
    assessment: dict = {
        "surface_type": surface,
        "drainage_obs": "Side drains visible, marginal condition",
        "road_profile_obs": "Moderate camber observed",
        "road_width_estimate_m": 6.0 + (idx % 3),
        "has_markings": surface in ("paved_asphalt", "paved_concrete"),
        "pedestrian_count": idx % 4,
        "pedestrians_on_road": idx % 3 == 0,
        "cyclist_motorcycle_count": idx % 3,
        "vehicle_types": ["boda_boda", "car"] if idx % 2 == 0 else ["bicycle", "none"],
        "facilities_visible": [["commercial", "market"], ["none"], ["school"], ["health_centre"]][idx % 4],
        "nmt_infrastructure": ["no_provision", "usable_shoulder", "separated_footpath", "no_provision"][idx % 4],
        "notes": _MOCK_NOTES[idx % len(_MOCK_NOTES)],
    }

    if surface in ("paved_asphalt", "paved_concrete"):
        scores = _MOCK_PAVED_SCORES[idx % len(_MOCK_PAVED_SCORES)]
        assessment.update({
            "paved_surface_distress_obs": "Surface assessed",
            "paved_surface_distress": scores[0],
            "paved_deformation_obs": "Deformation assessed",
            "paved_deformation": scores[1],
            "paved_edge_condition_obs": "Edges assessed",
            "paved_edge_condition": scores[2],
            "paved_patching_obs": "Patching assessed",
            "paved_patching": scores[3],
            "drainage": scores[4],
            "road_profile": scores[4],  # use drainage as proxy
            "riding_quality": scores[5],
        })
    else:
        scores = _MOCK_UNPAVED_SCORES[idx % len(_MOCK_UNPAVED_SCORES)]
        assessment.update({
            "unpaved_potholes_obs": "Potholes assessed",
            "unpaved_potholes": scores[0],
            "unpaved_corrugation_obs": "Corrugation assessed",
            "unpaved_corrugation": scores[1],
            "unpaved_erosion_obs": "Erosion assessed",
            "unpaved_erosion": scores[2],
            "unpaved_loose_material_obs": "Loose material assessed",
            "unpaved_loose_material": scores[3],
            "unpaved_gravel_condition_obs": "Gravel condition assessed",
            "unpaved_gravel_condition": scores[4],
            "drainage": scores[5],
            "road_profile": scores[6],
            "riding_quality": scores[7],
        })

    # Compute VCI/IRI and add backward-compat keys
    return _build_backward_compat(assessment)


def assess_road(
    frames_with_gps: list[dict],
    anthropic_client=None,
    max_frames: int = None,
    delay: float = 1.0,
    use_mock: bool = False,
    model: str = "claude-opus-4-6",
) -> dict:
    """Assess all (or sampled) frames. Returns results dict with frames and summary."""
    frames = list(frames_with_gps)

    # Sample evenly if max_frames is set
    if max_frames and len(frames) > max_frames:
        step = len(frames) / max_frames
        indices = [int(i * step) for i in range(max_frames)]
        frames = [frames[i] for i in indices]

    total = len(frames)
    for i, frame in enumerate(frames):
        if use_mock:
            assessment = assess_frame_mock(frame["image_base64"])
        else:
            assessment = assess_frame(frame["image_base64"], anthropic_client, model=model)
            if i < total - 1:
                time.sleep(delay)

        frame["assessment"] = assessment
        cond = assessment["condition_class"]
        iri = assessment["iri_estimate"]
        vci = assessment.get("vci", "?")
        print(f"    Assessing frame {i + 1}/{total}... [{cond}, IRI ~{iri}, VCI {vci}]")

    # Build summary
    conditions = [f["assessment"]["condition_class"] for f in frames]
    iris = [f["assessment"]["iri_estimate"] for f in frames]
    surfaces = [f["assessment"]["surface_type"] for f in frames]
    all_distress = set()
    for f in frames:
        for d in f["assessment"]["distress_types"]:
            if d != "none":
                all_distress.add(d)

    from collections import Counter
    condition_counts = dict(Counter(conditions))
    surface_counts = Counter(surfaces)

    # VCI stats
    vcis = [f["assessment"].get("vci") for f in frames if f["assessment"].get("vci") is not None]
    avg_vci = round(sum(vcis) / len(vcis), 1) if vcis else None

    summary = {
        "total_frames_assessed": total,
        "condition_distribution": condition_counts,
        "average_iri": round(sum(iris) / len(iris), 1) if iris else 0,
        "dominant_surface": surface_counts.most_common(1)[0][0] if surface_counts else "unknown",
        "dominant_condition": Counter(conditions).most_common(1)[0][0] if conditions else "unknown",
        "distress_types_found": sorted(all_distress),
        "average_vci": avg_vci,
        "vci_methodology": "TMH12/ASTM_D6433",
    }

    return {"frames": frames, "summary": summary}
