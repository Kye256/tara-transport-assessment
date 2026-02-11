"""
TARA Map Generation
Creates interactive maps showing road alignments, facilities, and analysis results.
Uses Folium (Leaflet.js wrapper).
"""

import folium
from folium import plugins
from typing import Optional

from skills.osm_facilities import FACILITY_CATEGORIES


def create_road_map(
    road_data: dict,
    facilities_data: Optional[dict] = None,
    condition_data: Optional[list] = None,
    height: int = 500,
) -> folium.Map:
    """
    Create an interactive map showing the road and its context.
    
    Args:
        road_data: Output from osm_lookup.search_road()
        facilities_data: Output from osm_facilities.find_facilities()
        condition_data: Optional list of condition scores by segment
        height: Map height in pixels
        
    Returns:
        folium.Map object
    """
    if not road_data.get("found") or not road_data.get("center"):
        # Default to Uganda center
        m = folium.Map(location=[0.35, 32.58], zoom_start=10)
        return m
    
    center = road_data["center"]
    m = folium.Map(
        location=[center["lat"], center["lon"]],
        zoom_start=13,
        tiles="OpenStreetMap",
    )
    
    # Add road segments
    _add_road_segments(m, road_data, condition_data)
    
    # Add facilities
    if facilities_data and facilities_data.get("total_count", 0) > 0:
        _add_facilities(m, facilities_data)
    
    # Add start/end markers
    _add_endpoint_markers(m, road_data)
    
    # Fit bounds to road
    if road_data.get("bbox"):
        bbox = road_data["bbox"]
        m.fit_bounds([
            [bbox["south"] - 0.01, bbox["west"] - 0.01],
            [bbox["north"] + 0.01, bbox["east"] + 0.01],
        ])
    
    return m


def _add_road_segments(m: folium.Map, road_data: dict, condition_data: Optional[list] = None):
    """Add road segments to the map, optionally color-coded by condition."""
    
    road_group = folium.FeatureGroup(name="Road Alignment")
    
    for i, segment in enumerate(road_data.get("segments", [])):
        coords = segment.get("coordinates", [])
        if not coords:
            continue
        
        # Determine color based on condition or surface type
        if condition_data and i < len(condition_data):
            color = _condition_color(condition_data[i])
        else:
            color = _surface_color(segment.get("surface", "unknown"))
        
        # Build popup content
        popup_html = f"""
        <b>{segment.get('name', 'Unnamed')}</b><br>
        Length: {segment.get('length_km', 0)} km<br>
        Surface: {segment.get('surface', 'unknown')}<br>
        Type: {segment.get('highway_type', 'unknown')}<br>
        Width: {segment.get('width', 'unknown')}<br>
        Lanes: {segment.get('lanes', 'unknown')}<br>
        """
        
        if segment.get("bridge") == "yes":
            popup_html += "<b>🌉 Bridge</b><br>"
        
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=5,
            opacity=0.8,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{segment.get('name', 'Road')} ({segment.get('length_km', 0)} km)",
        ).add_to(road_group)
    
    road_group.add_to(m)


def _add_facilities(m: folium.Map, facilities_data: dict):
    """Add facility markers to the map."""
    
    for category, items in facilities_data.get("facilities", {}).items():
        if not items:
            continue
        
        cat_info = FACILITY_CATEGORIES.get(category, {})
        icon_char = cat_info.get("icon", "📍")
        color = cat_info.get("color", "gray")
        
        # Map colors to folium icon colors
        folium_color_map = {
            "red": "red",
            "blue": "blue",
            "green": "green",
            "cyan": "lightblue",
            "orange": "orange",
            "purple": "purple",
        }
        folium_color = folium_color_map.get(color, "gray")
        
        group = folium.FeatureGroup(name=f"{category.title()} Facilities")
        
        for facility in items:
            popup_html = f"""
            <b>{facility.get('name', 'Unnamed')}</b><br>
            Type: {facility.get('subcategory', category)}<br>
            """
            if facility.get("distance_to_road_km"):
                popup_html += f"Distance to road: {facility['distance_to_road_km']} km<br>"
            
            folium.Marker(
                location=[facility["lat"], facility["lon"]],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=facility.get("name", category.title()),
                icon=folium.Icon(color=folium_color, icon="info-sign"),
            ).add_to(group)
        
        group.add_to(m)


def _add_endpoint_markers(m: folium.Map, road_data: dict):
    """Add start and end point markers."""
    segments = road_data.get("segments", [])
    if not segments:
        return
    
    # Find start and end coordinates
    all_coords = []
    for s in segments:
        all_coords.extend(s.get("coordinates", []))
    
    if len(all_coords) >= 2:
        start = all_coords[0]
        end = all_coords[-1]
        
        folium.Marker(
            location=start,
            popup="Start",
            tooltip="Start of road",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(m)
        
        folium.Marker(
            location=end,
            popup="End",
            tooltip="End of road",
            icon=folium.Icon(color="red", icon="stop"),
        ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)


def _surface_color(surface: str) -> str:
    """Color-code road segments by surface type."""
    surface_colors = {
        "asphalt": "#2196F3",      # Blue
        "paved": "#2196F3",
        "concrete": "#1565C0",
        "gravel": "#FF9800",       # Orange
        "unpaved": "#FF9800",
        "compacted": "#FFC107",    # Amber
        "dirt": "#795548",         # Brown
        "earth": "#795548",
        "sand": "#FFEB3B",         # Yellow
        "ground": "#8D6E63",
    }
    return surface_colors.get(surface.lower(), "#9E9E9E")  # Grey for unknown


def _condition_color(condition_score: float) -> str:
    """Color-code by condition score (0-100, higher = better)."""
    if condition_score >= 80:
        return "#4CAF50"   # Green - Good
    elif condition_score >= 60:
        return "#8BC34A"   # Light green - Fair
    elif condition_score >= 40:
        return "#FFC107"   # Amber - Poor
    elif condition_score >= 20:
        return "#FF9800"   # Orange - Bad
    else:
        return "#F44336"   # Red - Very bad


def create_drive_plan_map(
    road_data: dict,
    waypoints: Optional[list[dict]] = None,
) -> folium.Map:
    """
    Create a drive plan map with waypoints and instructions.
    
    Args:
        road_data: Output from osm_lookup.search_road()
        waypoints: List of dicts with lat, lon, instruction, km
    """
    m = create_road_map(road_data)
    
    if waypoints:
        for wp in waypoints:
            folium.Marker(
                location=[wp["lat"], wp["lon"]],
                popup=folium.Popup(
                    f"<b>Km {wp.get('km', '?')}</b><br>{wp.get('instruction', '')}",
                    max_width=250,
                ),
                tooltip=f"Km {wp.get('km', '?')}",
                icon=folium.Icon(color="darkblue", icon="camera"),
            ).add_to(m)
    
    return m


def create_condition_map(
    road_data: dict,
    condition_scores: list[dict],
) -> folium.Map:
    """
    Create a map showing road condition from dashcam analysis.
    
    Args:
        road_data: Output from osm_lookup.search_road()
        condition_scores: List of dicts with lat, lon, score, description
    """
    center = road_data.get("center", {"lat": 0.4, "lon": 32.58})
    m = folium.Map(location=[center["lat"], center["lon"]], zoom_start=13)
    
    # Add condition points as colored circles
    for point in condition_scores:
        color = _condition_color(point.get("score", 50))
        
        folium.CircleMarker(
            location=[point["lat"], point["lon"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>Condition: {point.get('score', '?')}/100</b><br>"
                f"{point.get('description', '')}<br>"
                f"Surface: {point.get('surface', 'unknown')}",
                max_width=250,
            ),
            tooltip=f"Score: {point.get('score', '?')}/100",
        ).add_to(m)
    
    # Add legend
    _add_condition_legend(m)
    
    return m


def _add_condition_legend(m: folium.Map):
    """Add a condition color legend to the map."""
    legend_html = """
    <div style="position: fixed; bottom: 30px; right: 30px; z-index: 1000;
                background: white; padding: 10px; border-radius: 5px;
                border: 2px solid grey; font-size: 12px;">
        <b>Road Condition</b><br>
        <i style="background:#4CAF50;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Good (80-100)<br>
        <i style="background:#8BC34A;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Fair (60-79)<br>
        <i style="background:#FFC107;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Poor (40-59)<br>
        <i style="background:#FF9800;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Bad (20-39)<br>
        <i style="background:#F44336;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Very Bad (0-19)<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
