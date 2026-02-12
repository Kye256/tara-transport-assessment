"""
TARA Map Generation
Creates interactive map components for road alignments, facilities, and analysis results.
Uses dash-leaflet (Leaflet.js via Dash).
"""

import dash_leaflet as dl
from typing import Optional

from skills.osm_facilities import FACILITY_CATEGORIES


# Default map center (Uganda)
UGANDA_CENTER = [0.35, 32.58]
DEFAULT_ZOOM = 10

# CartoDB Positron — clean, muted basemap for analytical overlays
TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
TILE_ATTR = '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'


def create_road_map(
    road_data: dict,
    facilities_data: Optional[dict] = None,
    condition_data: Optional[list] = None,
) -> dict:
    """
    Create map component data for a road and its context.

    Args:
        road_data: Output from osm_lookup.search_road()
        facilities_data: Output from osm_facilities.find_facilities()
        condition_data: Optional list of condition scores by segment

    Returns:
        Dict with 'children' (list of dl components), 'center', 'zoom', 'bounds'
    """
    if not road_data.get("found") or not road_data.get("center"):
        return {
            "children": [dl.TileLayer(url=TILE_URL, attribution=TILE_ATTR)],
            "center": UGANDA_CENTER,
            "zoom": DEFAULT_ZOOM,
            "bounds": None,
        }

    center = road_data["center"]
    map_center = [center["lat"], center["lon"]]

    children = [dl.TileLayer(url=TILE_URL, attribution=TILE_ATTR)]

    # Add road segments
    road_layers = _build_road_segments(road_data, condition_data)
    children.extend(road_layers)

    # Add facilities
    if facilities_data and facilities_data.get("total_count", 0) > 0:
        facility_layers = _build_facilities(facilities_data)
        children.extend(facility_layers)

    # Add start/end markers
    endpoint_markers = _build_endpoint_markers(road_data)
    children.extend(endpoint_markers)

    # Calculate bounds
    bounds = None
    if road_data.get("bbox"):
        bbox = road_data["bbox"]
        bounds = [
            [bbox["south"] - 0.01, bbox["west"] - 0.01],
            [bbox["north"] + 0.01, bbox["east"] + 0.01],
        ]

    return {
        "children": children,
        "center": map_center,
        "zoom": 13,
        "bounds": bounds,
    }


def _build_road_segments(
    road_data: dict, condition_data: Optional[list] = None
) -> list:
    """Build dash-leaflet Polyline components for road segments."""
    layers = []

    for i, segment in enumerate(road_data.get("segments", [])):
        coords = segment.get("coordinates", [])
        if not coords:
            continue

        # Determine color based on condition or surface type
        if condition_data and i < len(condition_data):
            color = _condition_color(condition_data[i])
        else:
            color = _surface_color(segment.get("surface", "unknown"))

        # Convert coords to [lat, lng] format for dash-leaflet
        positions = [[c[0], c[1]] for c in coords]

        tooltip_text = f"{segment.get('name', 'Road')} ({segment.get('length_km', 0)} km)"

        popup_html = (
            f"<b>{segment.get('name', 'Unnamed')}</b><br>"
            f"Length: {segment.get('length_km', 0)} km<br>"
            f"Surface: {segment.get('surface', 'unknown')}<br>"
            f"Type: {segment.get('highway_type', 'unknown')}<br>"
            f"Width: {segment.get('width', 'unknown')}<br>"
            f"Lanes: {segment.get('lanes', 'unknown')}"
        )

        if segment.get("bridge") == "yes":
            popup_html += "<br><b>Bridge</b>"

        layers.append(
            dl.Polyline(
                positions=positions,
                color=color,
                weight=5,
                opacity=0.8,
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(popup_html),
                ],
            )
        )

    return layers


def _build_facilities(facilities_data: dict) -> list:
    """Build dash-leaflet CircleMarker components for facilities."""
    layers = []

    # TARA palette for facility categories
    color_map = {
        "red": "#a83a2f",
        "blue": "#2a6496",
        "green": "#2d5f4a",
        "cyan": "#3d8b6e",
        "orange": "#d4920b",
        "purple": "#6b3f7a",
    }

    for category, items in facilities_data.get("facilities", {}).items():
        if not items:
            continue

        cat_info = FACILITY_CATEGORIES.get(category, {})
        icon_char = cat_info.get("icon", "")
        color = cat_info.get("color", "gray")
        marker_color = color_map.get(color, "#607d8b")
        letter = category[0].upper() if category else "?"

        for facility in items:
            popup_html = (
                f"<b>{facility.get('name', 'Unnamed')}</b><br>"
                f"Type: {facility.get('subcategory', category)}"
            )
            if facility.get("distance_to_road_km"):
                popup_html += f"<br>Distance to road: {facility['distance_to_road_km']} km"

            tooltip_text = f"[{letter}] {facility.get('name', category.title())}"

            layers.append(
                dl.CircleMarker(
                    center=[facility["lat"], facility["lon"]],
                    radius=7,
                    color="white",
                    weight=2,
                    fillColor=marker_color,
                    fillOpacity=0.9,
                    children=[
                        dl.Tooltip(tooltip_text),
                        dl.Popup(popup_html),
                    ],
                )
            )

    return layers


def _build_endpoint_markers(road_data: dict) -> list:
    """Build start and end point markers."""
    segments = road_data.get("segments", [])
    if not segments:
        return []

    all_coords = []
    for s in segments:
        all_coords.extend(s.get("coordinates", []))

    if len(all_coords) < 2:
        return []

    start = all_coords[0]
    end = all_coords[-1]

    return [
        dl.CircleMarker(
            center=[start[0], start[1]],
            radius=10,
            color="white",
            weight=3,
            fillColor="#2d5f4a",
            fillOpacity=1,
            children=[dl.Tooltip("Start of road (A)")],
        ),
        dl.CircleMarker(
            center=[end[0], end[1]],
            radius=10,
            color="white",
            weight=3,
            fillColor="#a83a2f",
            fillOpacity=1,
            children=[dl.Tooltip("End of road (B)")],
        ),
    ]


def build_condition_layer(geojson: dict) -> list:
    """Build dash-leaflet CircleMarker components from video pipeline GeoJSON.

    Args:
        geojson: GeoJSON FeatureCollection from video pipeline (frames_to_geojson).

    Returns:
        List of dl.CircleMarker components, color-coded by condition class.
    """
    condition_colors = {
        "good": "#2d5f4a",
        "fair": "#9a6b2f",
        "poor": "#c4652a",
        "bad": "#a83a2f",
    }

    markers = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]
        condition = props.get("condition_class", "fair")
        color = condition_colors.get(condition, "#9a6b2f")
        iri = props.get("iri_estimate", "?")
        surface = props.get("surface_type", "?")
        notes = props.get("notes", "")
        distress = props.get("distress_types", [])
        severity = props.get("distress_severity", "?")

        tooltip_text = f"{condition.title()} | IRI ~{iri} | {surface}"

        distress_str = ", ".join(distress) if distress else "none"
        popup_html = (
            f"<b>Condition: {condition.title()}</b><br>"
            f"IRI: {iri} m/km<br>"
            f"Surface: {surface}<br>"
            f"Distress: {distress_str}<br>"
            f"Severity: {severity}<br>"
            f"<i>{notes}</i>"
        )

        markers.append(
            dl.CircleMarker(
                center=[lat, lon],
                radius=8,
                color="white",
                weight=2,
                fillColor=color,
                fillOpacity=0.9,
                children=[
                    dl.Tooltip(tooltip_text),
                    dl.Popup(popup_html),
                ],
            )
        )

    return markers


def _surface_color(surface: str) -> str:
    """Color-code road segments by surface type."""
    surface_colors = {
        "asphalt": "#2d5f4a",
        "paved": "#2d5f4a",
        "concrete": "#1a3a2a",
        "gravel": "#9a6b2f",
        "unpaved": "#9a6b2f",
        "compacted": "#d4920b",
        "dirt": "#a83a2f",
        "earth": "#a83a2f",
        "sand": "#d4920b",
        "ground": "#9a6b2f",
    }
    return surface_colors.get(surface.lower(), "#607d8b")


def _condition_color(condition_score: float) -> str:
    """Color-code by condition score (0-100, higher = better)."""
    if condition_score >= 80:
        return "#2d5f4a"
    elif condition_score >= 60:
        return "#3d8b6e"
    elif condition_score >= 40:
        return "#d4920b"
    elif condition_score >= 20:
        return "#9a6b2f"
    else:
        return "#a83a2f"
