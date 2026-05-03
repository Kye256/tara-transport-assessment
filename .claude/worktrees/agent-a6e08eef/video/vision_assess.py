"""Claude Vision road condition assessment."""

import base64
import json
import random
import re
import time


VISION_PROMPT = """You are a road condition assessment expert analysing dashcam footage from Uganda.

Look at this road image and assess the visible road condition AND the activity/people visible. Respond ONLY with valid JSON, no markdown, no backticks, no explanation:

{"surface_type":"paved or gravel or earth or mixed or under_construction","condition_class":"good or fair or poor or bad","iri_estimate":8.5,"distress_types":["list","of","visible","issues"],"distress_severity":"none or low or moderate or high or severe","roadside_environment":"urban or peri_urban or rural","notes":"One sentence observation max 20 words","activity_profile":{"land_use":"trading_centre or residential or agricultural or institutional or mixed or open","activity_level":"high or moderate or low or none","people_observed":{"pedestrians":"many or some or few or none","school_children":false,"vendors_roadside":false,"people_carrying_loads":false},"vehicles_observed":{"boda_bodas":"many or some or few or none","bicycles":"many or some or few or none","minibus_taxi":"many or some or few or none","cars":"many or some or few or none","trucks":"many or some or few or none"},"facilities_visible":["shops","market_stalls","none"],"nmt_infrastructure":{"footpath":"good or poor or none","shoulder_usable":false,"pedestrians_on_carriageway":false}}}

Valid distress_types: pothole, cracking, rutting, edge_break, patching, raveling, corrugation, erosion, none
IRI ranges: good paved 2-4, fair paved 4-6, poor paved 6-10, good gravel 6-8, fair gravel 8-12, poor gravel 12-16, bad any 16+

Activity profile guidance:
- land_use: What is the dominant land use VISIBLE from the road? trading_centre = shops/stalls/commercial, residential = houses/compounds, agricultural = farmland/open, institutional = school/hospital/government, mixed = combination, open = undeveloped
- activity_level: How much human activity is visible? high = many people, vehicles, commerce. moderate = some activity. low = few people. none = empty.
- people_observed: What kinds of people can you see? Look for pedestrians on or near the road, children in school uniforms, roadside vendors/sellers, people carrying goods/water/firewood on their heads or by bicycle.
- vehicles_observed: What vehicle types are visible? boda_bodas = motorcycle taxis (very common in Uganda). Look at the MIX — a road dominated by boda-bodas and pedestrians serves different users than one dominated by trucks and cars.
- facilities_visible: List ALL facility types you can see or identify from signs. Include shops, market_stalls, school, church, mosque, health_facility, fuel_station. Report "none" if no facilities visible.
- nmt_infrastructure: Is there a footpath/sidewalk alongside the road? Is the road shoulder wide and smooth enough for pedestrians to walk on safely? Are pedestrians walking ON the carriageway (the road surface where vehicles drive)?"""

DEFAULT_ASSESSMENT = {
    "surface_type": "unknown",
    "condition_class": "fair",
    "iri_estimate": 8.0,
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
    """Send one frame to Claude Vision, get condition assessment."""
    for attempt in range(2):
        try:
            response = anthropic_client.messages.create(
                model=model,
                max_tokens=600,
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
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }],
            )
            text = response.content[0].text.strip()
            # Strip markdown code blocks if present
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            result = json.loads(text)
            # Ensure activity_profile has safe defaults
            result.setdefault("activity_profile", DEFAULT_ASSESSMENT["activity_profile"])
            return result
        except json.JSONDecodeError:
            if attempt == 0:
                continue
            return dict(DEFAULT_ASSESSMENT)
        except Exception as e:
            if attempt == 0:
                continue
            print(f"  Vision API error: {e}")
            return dict(DEFAULT_ASSESSMENT)


_MOCK_COUNTER = 0

# Deterministic cycling sequences for reproducible testing
_MOCK_CONDITIONS = ["good", "good", "fair", "fair", "poor", "good", "good", "fair", "poor", "bad"]
_MOCK_IRI_RANGES = {"good": (3, 5), "fair": (6, 9), "poor": (10, 14), "bad": (15, 20)}
_MOCK_SURFACES = ["paved_asphalt", "paved_asphalt", "gravel", "earth"]
_MOCK_NOTES = [
    "Tarmac in fair condition with edge erosion",
    "Paved surface with patching and minor cracks",
    "Gravel road with corrugation visible",
    "Laterite surface with moderate potholing",
    "Road under active construction with earthworks",
    "Earth road with deep ruts after rain",
]


def assess_frame_mock(image_base64: str) -> dict:
    """Return deterministic cycling assessment for testing without API."""
    global _MOCK_COUNTER
    idx = _MOCK_COUNTER
    _MOCK_COUNTER += 1

    condition = _MOCK_CONDITIONS[idx % len(_MOCK_CONDITIONS)]
    surface = _MOCK_SURFACES[idx % len(_MOCK_SURFACES)]
    lo, hi = _MOCK_IRI_RANGES[condition]
    # Deterministic IRI within range
    iri = round(lo + (hi - lo) * ((idx % 7) / 6), 1)

    distress_pool = ["pothole", "cracking", "rutting", "edge_break", "patching", "raveling", "corrugation", "erosion"]
    n_distress = idx % 3
    distress = distress_pool[idx % len(distress_pool): idx % len(distress_pool) + n_distress] or ["none"]

    severity_cycle = ["none", "low", "moderate", "high", "severe"]
    env_cycle = ["urban", "peri_urban", "rural"]

    # Mock activity profile — cycling through realistic Uganda scenarios
    land_use_cycle = ["trading_centre", "residential", "agricultural", "mixed", "residential", "trading_centre"]
    activity_cycle = ["high", "moderate", "low", "moderate", "high", "low"]
    ped_cycle = ["many", "some", "few", "none", "some", "many"]
    boda_cycle = ["many", "some", "few", "many", "some", "few"]
    footpath_cycle = ["none", "poor", "none", "good", "poor", "none"]
    facilities_cycle = [
        ["shops", "market_stalls"],
        ["none"],
        ["none"],
        ["school", "church"],
        ["shops"],
        ["health_facility", "shops"],
    ]

    activity_profile = {
        "land_use": land_use_cycle[idx % len(land_use_cycle)],
        "activity_level": activity_cycle[idx % len(activity_cycle)],
        "people_observed": {
            "pedestrians": ped_cycle[idx % len(ped_cycle)],
            "school_children": idx % 5 == 3,
            "vendors_roadside": idx % 3 == 0,
            "people_carrying_loads": idx % 4 == 1,
        },
        "vehicles_observed": {
            "boda_bodas": boda_cycle[idx % len(boda_cycle)],
            "bicycles": ped_cycle[(idx + 2) % len(ped_cycle)],
            "minibus_taxi": "some" if idx % 3 == 0 else "few",
            "cars": "some" if idx % 2 == 0 else "few",
            "trucks": "few" if idx % 4 != 0 else "some",
        },
        "facilities_visible": facilities_cycle[idx % len(facilities_cycle)],
        "nmt_infrastructure": {
            "footpath": footpath_cycle[idx % len(footpath_cycle)],
            "shoulder_usable": idx % 3 == 2,
            "pedestrians_on_carriageway": footpath_cycle[idx % len(footpath_cycle)] == "none",
        },
    }

    return {
        "surface_type": surface,
        "condition_class": condition,
        "iri_estimate": iri,
        "distress_types": distress,
        "distress_severity": severity_cycle[idx % len(severity_cycle)],
        "roadside_environment": env_cycle[idx % len(env_cycle)],
        "notes": _MOCK_NOTES[idx % len(_MOCK_NOTES)],
        "activity_profile": activity_profile,
    }


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
        print(f"    Assessing frame {i + 1}/{total}... [{cond}, IRI ~{iri}]")

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

    summary = {
        "total_frames_assessed": total,
        "condition_distribution": condition_counts,
        "average_iri": round(sum(iris) / len(iris), 1) if iris else 0,
        "dominant_surface": surface_counts.most_common(1)[0][0] if surface_counts else "unknown",
        "dominant_condition": Counter(conditions).most_common(1)[0][0] if conditions else "unknown",
        "distress_types_found": sorted(all_distress),
    }

    return {"frames": frames, "summary": summary}
