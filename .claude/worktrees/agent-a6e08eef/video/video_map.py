"""Map output and condition narrative generation."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from video.gps_utils import haversine, get_trackpoints_between

CONDITION_COLORS = {
    "good": "#2d5f4a",
    "fair": "#9a6b2f",
    "poor": "#c4652a",
    "bad": "#a83a2f",
}


def aggregate_section_equity(section_frames: list[dict]) -> dict:
    """Aggregate activity profiles across frames in a section.

    Args:
        section_frames: list of frame dicts, each with optional activity_profile
            in their assessment.

    Returns:
        Dict with aggregated equity indicators for the section.
    """
    profiles = [
        f.get("assessment", {}).get("activity_profile", {})
        for f in section_frames
        if f.get("assessment", {}).get("activity_profile")
    ]

    if not profiles:
        return {
            "activity_level": "unknown",
            "dominant_land_use": "unknown",
            "pedestrian_presence": "unknown",
            "nmt_footpath": "unknown",
            "pedestrians_on_carriageway": False,
            "school_children_observed": False,
            "vendors_observed": False,
            "facilities_seen": [],
            "vehicle_mix_summary": {},
            "equity_concern": "unknown",
        }

    # Most common land_use across frames
    land_uses = [p.get("land_use", "unknown") for p in profiles]
    dominant_land_use = max(set(land_uses), key=land_uses.count)

    # Highest activity level observed
    level_order = {"high": 3, "moderate": 2, "low": 1, "none": 0, "unknown": -1}
    activity_levels = [p.get("activity_level", "unknown") for p in profiles]
    highest_activity = max(activity_levels, key=lambda x: level_order.get(x, -1))

    # Pedestrian presence — take the highest observed
    presence_order = {"many": 3, "some": 2, "few": 1, "none": 0}
    ped_levels = [p.get("people_observed", {}).get("pedestrians", "none") for p in profiles]
    pedestrian_presence = max(ped_levels, key=lambda x: presence_order.get(x, 0))

    # School children — true if seen in ANY frame
    school_children = any(
        p.get("people_observed", {}).get("school_children", False) for p in profiles
    )

    # Vendors — true if seen in ANY frame
    vendors = any(
        p.get("people_observed", {}).get("vendors_roadside", False) for p in profiles
    )

    # NMT — worst case across frames
    footpath_values = [p.get("nmt_infrastructure", {}).get("footpath", "none") for p in profiles]
    footpath_order = {"good": 2, "poor": 1, "none": 0}
    nmt_footpath = min(footpath_values, key=lambda x: footpath_order.get(x, 0))

    # Pedestrians on carriageway — true if seen in ANY frame
    peds_on_road = any(
        p.get("nmt_infrastructure", {}).get("pedestrians_on_carriageway", False) for p in profiles
    )

    # Collect all unique facilities seen across frames
    all_facilities: list[str] = []
    for p in profiles:
        facs = p.get("facilities_visible", [])
        if isinstance(facs, list):
            all_facilities.extend(facs)
    facilities_seen = sorted(set(f for f in all_facilities if f != "none"))

    # Vehicle mix — highest level per type across frames
    vehicle_types = ["boda_bodas", "bicycles", "minibus_taxi", "cars", "trucks"]
    vehicle_summary: dict[str, str] = {}
    for vtype in vehicle_types:
        levels = [p.get("vehicles_observed", {}).get(vtype, "none") for p in profiles]
        highest = max(levels, key=lambda x: presence_order.get(x, 0))
        if highest != "none":
            vehicle_summary[vtype] = highest

    # Equity concern flag
    equity_concern = "low"
    if pedestrian_presence in ("many", "some") and nmt_footpath == "none":
        equity_concern = "high"
    elif school_children or (pedestrian_presence == "some" and nmt_footpath == "poor"):
        equity_concern = "moderate"
    elif pedestrian_presence == "many":
        equity_concern = "moderate"

    return {
        "activity_level": highest_activity,
        "dominant_land_use": dominant_land_use,
        "pedestrian_presence": pedestrian_presence,
        "nmt_footpath": nmt_footpath,
        "pedestrians_on_carriageway": peds_on_road,
        "school_children_observed": school_children,
        "vendors_observed": vendors,
        "facilities_seen": facilities_seen,
        "vehicle_mix_summary": vehicle_summary,
        "equity_concern": equity_concern,
    }


def build_popup_html(frame: dict) -> str:
    """Build HTML string for a dash-leaflet popup with dashcam thumbnail and stats.

    Args:
        frame: assessed frame dict with assessment and image_base64 keys.

    Returns:
        HTML string for dl.Popup.
    """
    assessment = frame.get("assessment", {})
    condition = assessment.get("condition_class", "fair")
    color = CONDITION_COLORS.get(condition, "#9a6b2f")
    iri = assessment.get("iri_estimate", "?")
    surface = assessment.get("surface_type", "?")
    distress = assessment.get("distress_types", [])
    distress_str = ", ".join(d.replace("_", " ") for d in distress if d != "none") or "none"
    notes = assessment.get("notes", "")
    img_b64 = frame.get("image_base64", "")

    parts = [
        '<div style="font-family: \'Source Sans 3\', sans-serif; max-width: 320px;">',
    ]

    if img_b64:
        parts.append(
            f'<img src="data:image/jpeg;base64,{img_b64}" '
            f'style="width:300px; border-radius:3px;" />'
        )

    parts.append(
        f'<div style="margin-top:8px;">'
        f'<span style="background:{color}; color:white; padding:2px 8px; '
        f'border-radius:2px; font-size:11px; font-weight:600;">'
        f'{condition.upper()}</span>'
        f'<span style="color:#5c5950; font-size:12px; margin-left:8px;">'
        f'IRI ~{iri} m/km</span>'
        f'</div>'
    )

    parts.append(
        f'<div style="font-size:12px; color:#2c2a26; margin-top:6px;">'
        f'{surface.replace("_", " ").title()} surface &middot; {distress_str}'
        f'</div>'
    )

    if notes:
        parts.append(
            f'<div style="font-size:11px; color:#8a8578; margin-top:4px;">'
            f'{notes}</div>'
        )

    parts.append('</div>')
    return "\n".join(parts)


def frames_to_condition_geojson(
    assessed_frames: list[dict],
    trackpoints: list[dict] = None,
    video_start_time: str = None,
    all_frames: list[dict] = None,
) -> dict:
    """Convert assessed frames into color-coded LineString sections for the map.

    Groups consecutive frames into sections, breaking on condition_class change
    OR when cumulative section distance exceeds 1.0 km.  When GPX trackpoints
    are supplied, each section's LineString is densified with all intermediate
    trackpoints so the geometry follows the actual road.  When GPX has gaps,
    falls back to all_frames' interpolated GPS coordinates.

    Args:
        assessed_frames: list of frame dicts with assessment and GPS keys.
        trackpoints: optional GPX trackpoint list from parse_gpx / parse_gpx_folder.
            Each dict must have 'lat', 'lon', and 'time' (datetime) keys.
        video_start_time: optional local-time string "YYYY-MM-DD HH:MM:SS"
            (assumed UTC+3) used as the epoch base for computing frame times.
        all_frames: optional list of ALL extracted frames (including non-assessed)
            for GPS coordinate densification when GPX trackpoints are unavailable.

    Returns:
        GeoJSON FeatureCollection dict with LineString features.
    """
    # ------------------------------------------------------------------
    # 0.  Compute video start epoch (UTC) once, used for dense trackpoints
    # ------------------------------------------------------------------
    video_start_epoch: float | None = None
    if video_start_time is not None:
        tz_local = timezone(timedelta(hours=3))  # Uganda = UTC+3
        local_dt = datetime.strptime(video_start_time, "%Y-%m-%d %H:%M:%S")
        local_dt = local_dt.replace(tzinfo=tz_local)
        video_start_epoch = local_dt.astimezone(timezone.utc).timestamp()

    # ------------------------------------------------------------------
    # 1.  Filter to geo-tagged assessed frames
    # ------------------------------------------------------------------
    geo_frames = [
        f for f in assessed_frames
        if f.get("lat") is not None and f.get("lon") is not None
        and f.get("assessment")
    ]

    if not geo_frames:
        return {"type": "FeatureCollection", "features": []}

    # ------------------------------------------------------------------
    # Helper: epoch time for a frame
    # ------------------------------------------------------------------
    def _frame_epoch(frame: dict) -> float | None:
        """Return the UTC epoch seconds for *frame*, or None."""
        ts_sec = frame.get("timestamp_sec")
        if ts_sec is None:
            return None
        # Prefer the function-level video_start_time
        if video_start_epoch is not None:
            return video_start_epoch + ts_sec
        # Fall back to per-frame video_start_time field
        vst = frame.get("video_start_time")
        if vst:
            tz_local = timezone(timedelta(hours=3))
            local_dt = datetime.strptime(vst, "%Y-%m-%d %H:%M:%S")
            local_dt = local_dt.replace(tzinfo=tz_local)
            return local_dt.astimezone(timezone.utc).timestamp() + ts_sec
        return None

    # ------------------------------------------------------------------
    # 2.  Group frames into sections (smoothed)
    #     Rules:
    #     - Break on surface_type change (if section >= MIN_SECTION_KM)
    #     - Break on condition_class change only if SMOOTHING_WINDOW
    #       consecutive frames agree on the new condition
    #     - Enforce MIN_SECTION_KM (0.3 km) — no tiny sections
    #     - Enforce MAX_SECTION_KM (2.0 km) — force break
    #     - NEVER break on activity_profile changes
    # ------------------------------------------------------------------
    MIN_SECTION_KM = 0.5   # minimum section length
    MAX_SECTION_KM = 2.0   # maximum section length
    SMOOTHING_WINDOW = 3   # consecutive frames to confirm change

    sections: list[list[dict]] = []
    current_section = [geo_frames[0]]
    current_condition = geo_frames[0]["assessment"]["condition_class"]
    current_surface = geo_frames[0]["assessment"]["surface_type"]
    section_distance_m = 0.0  # running distance in metres

    for i, frame in enumerate(geo_frames[1:], 1):
        condition = frame["assessment"]["condition_class"]
        surface = frame["assessment"]["surface_type"]

        # Distance from previous frame to this frame
        prev = current_section[-1]
        dist_m = haversine(prev["lat"], prev["lon"], frame["lat"], frame["lon"])

        current_length_km = (section_distance_m + dist_m) / 1000
        should_break = False

        # Force break at max length
        if current_length_km >= MAX_SECTION_KM:
            should_break = True

        # Break on surface type change (if above min length AND sustained)
        elif current_length_km >= MIN_SECTION_KM and surface != current_surface:
            lookahead = geo_frames[i:i + SMOOTHING_WINDOW]
            if len(lookahead) >= SMOOTHING_WINDOW and all(
                f["assessment"]["surface_type"] == surface for f in lookahead
            ):
                should_break = True

        # Break on sustained condition change (if above min length)
        elif current_length_km >= MIN_SECTION_KM and condition != current_condition:
            # Look ahead: do the next SMOOTHING_WINDOW frames agree?
            lookahead = geo_frames[i:i + SMOOTHING_WINDOW]
            if len(lookahead) >= SMOOTHING_WINDOW and all(
                f["assessment"]["condition_class"] == condition for f in lookahead
            ):
                should_break = True

        if should_break:
            sections.append(current_section)
            current_section = [frame]
            current_condition = condition
            current_surface = surface
            section_distance_m = 0.0
        else:
            current_section.append(frame)
            section_distance_m += dist_m

    sections.append(current_section)

    # ------------------------------------------------------------------
    # 3.  Pre-compute epoch times for section boundary frames
    # ------------------------------------------------------------------
    section_epochs: list[tuple[float | None, float | None]] = []
    for sec_frames in sections:
        section_epochs.append((_frame_epoch(sec_frames[0]), _frame_epoch(sec_frames[-1])))

    # ------------------------------------------------------------------
    # 4.  Build GeoJSON features
    # ------------------------------------------------------------------
    features = []
    for idx, section_frames in enumerate(sections):
        condition = section_frames[0]["assessment"]["condition_class"]
        color = CONDITION_COLORS.get(condition, "#9a6b2f")

        # --- Dense LineString coordinates from trackpoints ---------------
        coords: list[list[float]] | None = None

        # Compute time window for this section (midpoints with neighbors)
        window_start: float | None = None
        window_end: float | None = None

        if section_epochs[idx][0] is not None:
            first_ep, last_ep = section_epochs[idx]

            if idx == 0:
                window_start = first_ep - 30.0
            else:
                prev_last = section_epochs[idx - 1][1]
                window_start = (prev_last + first_ep) / 2.0 if prev_last is not None else first_ep - 30.0

            if idx == len(sections) - 1:
                window_end = (last_ep or first_ep) + 30.0
            else:
                next_first = section_epochs[idx + 1][0]
                window_end = ((last_ep or first_ep) + next_first) / 2.0 if next_first is not None else (last_ep or first_ep) + 30.0

        # Try GPX trackpoints first (densest, follows actual road)
        if trackpoints and window_start is not None:
            dense = get_trackpoints_between(trackpoints, window_start, window_end)
            if dense:
                coords = dense

        # Fallback: use all_frames' GPS in the time window (for GPX gaps)
        if not coords and all_frames and window_start is not None:
            frame_coords = []
            for f in all_frames:
                if f.get("lat") is None or f.get("lon") is None:
                    continue
                ep = _frame_epoch(f)
                if ep is not None and window_start <= ep <= window_end:
                    frame_coords.append([f["lon"], f["lat"]])
            if len(frame_coords) >= 2:
                coords = frame_coords

        # Last fallback: section's own assessed frame GPS points
        if not coords:
            coords = [[f["lon"], f["lat"]] for f in section_frames]

        # Single-point section: duplicate with tiny offset for valid LineString
        if len(coords) == 1:
            lon, lat = coords[0]
            coords.append([lon + 0.00005, lat + 0.00005])

        # --- Section-level statistics ------------------------------------
        iris = [f["assessment"]["iri_estimate"] for f in section_frames]
        avg_iri = round(sum(iris) / len(iris), 1) if iris else 0

        surfaces = [f["assessment"]["surface_type"] for f in section_frames]
        surface_type = Counter(surfaces).most_common(1)[0][0] if surfaces else "unknown"

        all_distress: set[str] = set()
        for f in section_frames:
            for d in f["assessment"].get("distress_types", []):
                if d != "none":
                    all_distress.add(d)

        frame_indices = [f["frame_index"] for f in section_frames]
        rep_idx = len(section_frames) // 2
        rep_frame = section_frames[rep_idx]

        # --- Equity aggregation -----------------------------------------------
        equity = aggregate_section_equity(section_frames)

        popup_html = build_popup_html(rep_frame)

        # Add equity info to popup for high/moderate concern sections
        if equity["equity_concern"] in ("high", "moderate"):
            equity_color = "#a83a2f" if equity["equity_concern"] == "high" else "#9a6b2f"
            popup_html = popup_html.replace(
                '</div>\n</div>',  # before closing tags
                f'<div style="margin-top:6px;padding:4px 8px;background:{equity_color}15;'
                f'border-left:3px solid {equity_color};font-size:11px;">'
                f'<b style="color:{equity_color}">Equity: {equity["equity_concern"].upper()}</b><br>'
                f'{equity["dominant_land_use"].replace("_", " ").title()} area · '
                f'Pedestrians: {equity["pedestrian_presence"]}'
                f'{"  · School children observed" if equity["school_children_observed"] else ""}'
                f'{"  · No footpath" if equity["nmt_footpath"] == "none" else ""}'
                f'</div>\n</div>\n</div>',
                1,  # only first occurrence
            )

        # Notes from representative frame
        notes = rep_frame["assessment"].get("notes", "")

        # Store representative image for Dash component popups
        rep_image = rep_frame.get("image_base64", "")

        linestring_length_km_val = sum(
            haversine(coords[i-1][1], coords[i-1][0], coords[i][1], coords[i][0])
            for i in range(1, len(coords))
        ) / 1000

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "condition_class": condition,
                "color": color,
                "weight": 6,
                "avg_iri": avg_iri,
                "surface_type": surface_type,
                "distress_types": ", ".join(sorted(all_distress)) if all_distress else "none",
                "notes": notes,
                "length_km": round(linestring_length_km_val, 2),
                "section_index": idx,
                "frame_indices": frame_indices,
                "representative_frame_index": rep_frame["frame_index"],
                "representative_image": rep_image,
                "popup_html": popup_html,
                "equity": equity,
                "equity_concern": equity["equity_concern"],
            },
        }
        features.append(feature)

    # ------------------------------------------------------------------
    # 5.  Post-process: split sections exceeding MAX_SECTION_KM
    # ------------------------------------------------------------------
    split_limit = MAX_SECTION_KM * 1.5  # 1.5 km hard ceiling
    DENSIFY_RESOLUTION_KM = 0.25  # ensure enough points for any section >500m

    def _densify_coords(coords: list[list[float]]) -> list[list[float]]:
        """Insert intermediate points so no segment exceeds DENSIFY_RESOLUTION_KM."""
        dense = [coords[0]]
        for i in range(1, len(coords)):
            seg_km = haversine(coords[i - 1][1], coords[i - 1][0],
                               coords[i][1], coords[i][0]) / 1000
            if seg_km > DENSIFY_RESOLUTION_KM:
                n_parts = max(2, int(seg_km / DENSIFY_RESOLUTION_KM) + 1)
                for j in range(1, n_parts):
                    frac = j / n_parts
                    dense.append([
                        coords[i - 1][0] + frac * (coords[i][0] - coords[i - 1][0]),
                        coords[i - 1][1] + frac * (coords[i][1] - coords[i - 1][1]),
                    ])
            dense.append(coords[i])
        return dense

    final_features = []
    for feat in features:
        coords = _densify_coords(feat["geometry"]["coordinates"])
        feat["geometry"]["coordinates"] = coords

        total_km = 0.0
        for i in range(1, len(coords)):
            total_km += haversine(coords[i - 1][1], coords[i - 1][0],
                                  coords[i][1], coords[i][0]) / 1000

        if total_km <= split_limit:
            final_features.append(feat)
        else:

            # Split at MAX_SECTION_KM intervals
            sub_coords = [coords[0]]
            sub_dist = 0.0
            for i in range(1, len(coords)):
                seg_km = haversine(coords[i - 1][1], coords[i - 1][0],
                                   coords[i][1], coords[i][0]) / 1000
                if sub_dist + seg_km > MAX_SECTION_KM and len(sub_coords) >= 2:
                    sub_length_km = sum(
                        haversine(sub_coords[j-1][1], sub_coords[j-1][0],
                                  sub_coords[j][1], sub_coords[j][0])
                        for j in range(1, len(sub_coords))
                    ) / 1000
                    new_feat = {
                        "type": "Feature",
                        "geometry": {"type": "LineString", "coordinates": list(sub_coords)},
                        "properties": {**dict(feat["properties"]), "length_km": round(sub_length_km, 2)},
                    }
                    final_features.append(new_feat)
                    sub_coords = [coords[i - 1]]  # overlap at boundary
                    sub_dist = 0.0
                sub_coords.append(coords[i])
                sub_dist += seg_km
            if len(sub_coords) >= 2:
                sub_length_km = sum(
                    haversine(sub_coords[j-1][1], sub_coords[j-1][0],
                              sub_coords[j][1], sub_coords[j][0])
                    for j in range(1, len(sub_coords))
                ) / 1000
                new_feat = {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": list(sub_coords)},
                    "properties": {**dict(feat["properties"]), "length_km": round(sub_length_km, 2)},
                }
                final_features.append(new_feat)

    # Re-index section_index sequentially
    for i, feat in enumerate(final_features):
        feat["properties"]["section_index"] = i

    return {"type": "FeatureCollection", "features": final_features}


def frames_to_geojson(assessed_frames: list[dict]) -> dict:
    """Convert assessed frames to GeoJSON FeatureCollection (Point features).

    Kept for backward compatibility. Prefer frames_to_condition_geojson for map display.
    """
    features = []
    for frame in assessed_frames:
        assessment = frame.get("assessment", {})
        condition = assessment.get("condition_class", "fair")
        color = CONDITION_COLORS.get(condition, "#9a6b2f")

        lat = frame.get("lat")
        lon = frame.get("lon")
        if lat is None or lon is None:
            continue

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": {
                "condition_class": condition,
                "color": color,
                "iri_estimate": assessment.get("iri_estimate"),
                "surface_type": assessment.get("surface_type"),
                "distress_types": assessment.get("distress_types", []),
                "distress_severity": assessment.get("distress_severity"),
                "notes": assessment.get("notes", ""),
                "frame_index": frame.get("frame_index"),
                "timestamp_sec": frame.get("timestamp_sec"),
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def build_condition_summary_panel(summary: dict, total_distance_km: float = 0.0) -> dict:
    """Build data for the left panel condition display.

    Args:
        summary: pipeline summary dict from assess_road.
        total_distance_km: total GPS distance.

    Returns:
        Dict with panel display data.
    """
    condition_dist = summary.get("condition_distribution", {})
    total = summary.get("total_frames_assessed", 0) or 1

    condition_percentages = {
        cond: round(count / total * 100)
        for cond, count in condition_dist.items()
    }

    return {
        "total_distance_km": round(total_distance_km, 2),
        "average_iri": summary.get("average_iri", 0),
        "dominant_surface": summary.get("dominant_surface", "unknown"),
        "dominant_condition": summary.get("dominant_condition", "unknown"),
        "condition_percentages": condition_percentages,
        "key_issues": summary.get("distress_types_found", []),
    }


def generate_condition_narrative(summary: dict, anthropic_client, model: str = "claude-sonnet-4-5-20250929") -> str:
    """Send summary stats to Claude, get a 2-3 paragraph condition narrative."""
    prompt = f"""You are a road engineer writing a condition assessment for a road appraisal report.

Based on this dashcam analysis data, write a 2-3 paragraph professional road condition narrative suitable for inclusion in an investment appraisal report.

Data:
- Frames assessed: {summary.get('total_frames_assessed', 0)}
- Condition distribution: {summary.get('condition_distribution', {})}
- Average IRI: {summary.get('average_iri', 'N/A')}
- Dominant surface: {summary.get('dominant_surface', 'N/A')}
- Dominant condition: {summary.get('dominant_condition', 'N/A')}
- Distress types found: {', '.join(summary.get('distress_types_found', []))}

Write in third person, past tense. Be specific about the data. Do not use markdown headings."""

    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  Narrative generation error: {e}")
        return generate_condition_narrative_mock(summary)


def generate_condition_narrative_mock(summary: dict) -> str:
    """Return a mock narrative for testing without API."""
    avg_iri = summary.get("average_iri", 8.0)
    surface = summary.get("dominant_surface", "gravel")
    condition = summary.get("dominant_condition", "fair")
    n_frames = summary.get("total_frames_assessed", 0)
    distress = summary.get("distress_types_found", [])
    dist_str = ", ".join(distress) if distress else "no significant distress"

    return (
        f"A dashcam survey of the road corridor was conducted, with {n_frames} frames "
        f"analysed along the route. The road presented predominantly {surface} surfacing "
        f"in {condition} condition, with an estimated average International Roughness "
        f"Index (IRI) of {avg_iri} m/km.\n\n"
        f"The principal forms of distress observed were {dist_str}. "
        f"The condition distribution indicated variation along the corridor, "
        f"with sections ranging from good to poor condition. "
        f"The findings suggest that targeted maintenance interventions would be "
        f"appropriate to arrest further deterioration and preserve the existing asset."
    )
