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
            "children": [dl.TileLayer()],
            "center": UGANDA_CENTER,
            "zoom": DEFAULT_ZOOM,
            "bounds": None,
        }

    center = road_data["center"]
    map_center = [center["lat"], center["lon"]]

    children = [dl.TileLayer()]

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
    """Build dash-leaflet Marker components for facilities."""
    layers = []

    # Color mapping for marker icons
    color_map = {
        "red": "#e74c3c",
        "blue": "#3498db",
        "green": "#2ecc71",
        "cyan": "#1abc9c",
        "orange": "#e67e22",
        "purple": "#9b59b6",
    }

    for category, items in facilities_data.get("facilities", {}).items():
        if not items:
            continue

        cat_info = FACILITY_CATEGORIES.get(category, {})
        icon_char = cat_info.get("icon", "")
        color = cat_info.get("color", "gray")
        marker_color = color_map.get(color, "#95a5a6")

        for facility in items:
            popup_html = (
                f"<b>{facility.get('name', 'Unnamed')}</b><br>"
                f"Type: {facility.get('subcategory', category)}"
            )
            if facility.get("distance_to_road_km"):
                popup_html += f"<br>Distance to road: {facility['distance_to_road_km']} km"

            tooltip_text = facility.get("name", category.title())

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
            fillColor="#27ae60",
            fillOpacity=1,
            children=[dl.Tooltip("Start of road (A)")],
        ),
        dl.CircleMarker(
            center=[end[0], end[1]],
            radius=10,
            color="white",
            weight=3,
            fillColor="#e74c3c",
            fillOpacity=1,
            children=[dl.Tooltip("End of road (B)")],
        ),
    ]


def _surface_color(surface: str) -> str:
    """Color-code road segments by surface type."""
    surface_colors = {
        "asphalt": "#2196F3",
        "paved": "#2196F3",
        "concrete": "#1565C0",
        "gravel": "#FF9800",
        "unpaved": "#FF9800",
        "compacted": "#FFC107",
        "dirt": "#795548",
        "earth": "#795548",
        "sand": "#FFEB3B",
        "ground": "#8D6E63",
    }
    return surface_colors.get(surface.lower(), "#9E9E9E")


def _condition_color(condition_score: float) -> str:
    """Color-code by condition score (0-100, higher = better)."""
    if condition_score >= 80:
        return "#4CAF50"
    elif condition_score >= 60:
        return "#8BC34A"
    elif condition_score >= 40:
        return "#FFC107"
    elif condition_score >= 20:
        return "#FF9800"
    else:
        return "#F44336"
