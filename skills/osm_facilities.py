"""
TARA OSM Facilities Skill
Finds health facilities, schools, markets, and other amenities near a road corridor.
Uses the Overpass API.
"""

import requests
import math
from typing import Optional


OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Facility categories and their OSM tags
FACILITY_CATEGORIES = {
    "health": {
        "tags": [
            '["amenity"="hospital"]',
            '["amenity"="clinic"]',
            '["amenity"="doctors"]',
            '["amenity"="health_post"]',
            '["healthcare"]',
        ],
        "icon": "🏥",
        "color": "red",
    },
    "education": {
        "tags": [
            '["amenity"="school"]',
            '["amenity"="university"]',
            '["amenity"="college"]',
            '["amenity"="kindergarten"]',
        ],
        "icon": "🏫",
        "color": "blue",
    },
    "market": {
        "tags": [
            '["amenity"="marketplace"]',
            '["shop"="supermarket"]',
            '["amenity"="market"]',
        ],
        "icon": "🏪",
        "color": "green",
    },
    "water": {
        "tags": [
            '["amenity"="drinking_water"]',
            '["man_made"="water_well"]',
            '["amenity"="water_point"]',
        ],
        "icon": "💧",
        "color": "cyan",
    },
    "transport": {
        "tags": [
            '["amenity"="bus_station"]',
            '["highway"="bus_stop"]',
            '["amenity"="fuel"]',
        ],
        "icon": "🚌",
        "color": "orange",
    },
    "worship": {
        "tags": [
            '["amenity"="place_of_worship"]',
        ],
        "icon": "⛪",
        "color": "purple",
    },
}


def find_facilities(
    bbox: dict,
    buffer_km: float = 5.0,
    categories: Optional[list[str]] = None,
    timeout: int = 30,
) -> dict:
    """
    Find facilities near a road corridor.
    
    Args:
        bbox: Bounding box dict with south, north, west, east
        buffer_km: Buffer distance around corridor in km (default 5km)
        categories: List of categories to search (default: all)
        timeout: API timeout in seconds
        
    Returns:
        dict with facilities grouped by category
    """
    if not bbox:
        return {"facilities": {}, "total_count": 0}
    
    # Expand bbox by buffer
    lat_buffer = buffer_km / 111.0  # ~111km per degree latitude
    lon_buffer = buffer_km / (111.0 * math.cos(math.radians((bbox["south"] + bbox["north"]) / 2)))
    
    expanded_bbox = (
        bbox["south"] - lat_buffer,
        bbox["west"] - lon_buffer,
        bbox["north"] + lat_buffer,
        bbox["east"] + lon_buffer,
    )
    bbox_str = f"{expanded_bbox[0]},{expanded_bbox[1]},{expanded_bbox[2]},{expanded_bbox[3]}"
    
    # Select categories
    if categories is None:
        categories = list(FACILITY_CATEGORIES.keys())
    
    # Build single query for all facility types
    tag_queries = []
    for cat in categories:
        if cat in FACILITY_CATEGORIES:
            for tag in FACILITY_CATEGORIES[cat]["tags"]:
                tag_queries.append(f'  node{tag}({bbox_str});')
                tag_queries.append(f'  way{tag}({bbox_str});')
    
    query = f"""
    [out:json][timeout:{timeout}];
    (
    {chr(10).join(tag_queries)}
    );
    out center;
    """
    
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=timeout,
            headers={"User-Agent": "TARA Transport Assessment Agent/1.0"}
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Overpass API error: {e}")
        return {"facilities": {cat: [] for cat in categories}, "total_count": 0}
    
    # Process results
    facilities = {cat: [] for cat in categories}
    seen_ids = set()
    
    for element in data.get("elements", []):
        element_id = element["id"]
        if element_id in seen_ids:
            continue
        seen_ids.add(element_id)
        
        tags = element.get("tags", {})
        
        # Get coordinates (node has lat/lon directly, way has center)
        if element["type"] == "node":
            lat = element.get("lat")
            lon = element.get("lon")
        else:
            center = element.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")
        
        if not lat or not lon:
            continue
        
        # Categorize the facility
        category = _categorize_facility(tags)
        if category and category in facilities:
            facility = {
                "osm_id": element_id,
                "name": tags.get("name", "Unnamed"),
                "category": category,
                "subcategory": _get_subcategory(tags),
                "lat": lat,
                "lon": lon,
                "tags": {k: v for k, v in tags.items() if k in [
                    "name", "amenity", "healthcare", "shop", "highway",
                    "operator", "addr:city", "phone", "opening_hours"
                ]},
            }
            facilities[category].append(facility)
    
    total = sum(len(v) for v in facilities.values())
    
    return {
        "facilities": facilities,
        "total_count": total,
        "bbox_searched": {
            "south": expanded_bbox[0],
            "west": expanded_bbox[1],
            "north": expanded_bbox[2],
            "east": expanded_bbox[3],
        },
        "buffer_km": buffer_km,
        "categories_searched": categories,
    }


def _categorize_facility(tags: dict) -> Optional[str]:
    """Determine which category a facility belongs to."""
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")
    shop = tags.get("shop", "")
    highway = tags.get("highway", "")
    man_made = tags.get("man_made", "")
    
    if amenity in ["hospital", "clinic", "doctors", "health_post"] or healthcare:
        return "health"
    elif amenity in ["school", "university", "college", "kindergarten"]:
        return "education"
    elif amenity in ["marketplace", "market"] or shop == "supermarket":
        return "market"
    elif amenity in ["drinking_water", "water_point"] or man_made == "water_well":
        return "water"
    elif amenity in ["bus_station", "fuel"] or highway == "bus_stop":
        return "transport"
    elif amenity == "place_of_worship":
        return "worship"
    
    return None


def _get_subcategory(tags: dict) -> str:
    """Get a more specific subcategory label."""
    amenity = tags.get("amenity", "")
    healthcare = tags.get("healthcare", "")
    
    subcategory_map = {
        "hospital": "Hospital",
        "clinic": "Health Clinic",
        "doctors": "Doctor",
        "health_post": "Health Post",
        "school": "School",
        "university": "University",
        "college": "College",
        "kindergarten": "Kindergarten",
        "marketplace": "Market",
        "market": "Market",
        "bus_station": "Bus Station",
        "fuel": "Fuel Station",
        "bus_stop": "Bus Stop",
        "place_of_worship": "Place of Worship",
        "drinking_water": "Water Point",
        "water_point": "Water Point",
    }
    
    if healthcare:
        return healthcare.replace("_", " ").title()
    
    return subcategory_map.get(amenity, amenity.replace("_", " ").title())


def get_facilities_summary(facilities_data: dict) -> str:
    """Generate a human-readable summary of facilities found."""
    if facilities_data["total_count"] == 0:
        return "No facilities found in the search area."
    
    parts = [
        f"**Facilities within {facilities_data['buffer_km']}km of corridor** "
        f"({facilities_data['total_count']} total):",
    ]
    
    for category, items in facilities_data["facilities"].items():
        if items:
            cat_info = FACILITY_CATEGORIES.get(category, {})
            icon = cat_info.get("icon", "📍")
            named = [f["name"] for f in items if f["name"] != "Unnamed"]
            
            line = f"- {icon} **{category.title()}:** {len(items)}"
            if named and len(named) <= 5:
                line += f" ({', '.join(named)})"
            elif named:
                line += f" (including {', '.join(named[:3])} and {len(named)-3} more)"
            
            parts.append(line)
    
    return "\n".join(parts)


def calculate_distances_to_road(facilities: list[dict], road_coords: list[tuple]) -> list[dict]:
    """Calculate the minimum distance from each facility to the road."""
    for facility in facilities:
        min_dist = float("inf")
        for lat, lon in road_coords:
            dist = _haversine(facility["lat"], facility["lon"], lat, lon)
            if dist < min_dist:
                min_dist = dist
        facility["distance_to_road_km"] = round(min_dist, 2)
    
    return sorted(facilities, key=lambda f: f["distance_to_road_km"])


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# Quick test
if __name__ == "__main__":
    # Test with Kasangati-Matugga approximate bbox
    test_bbox = {
        "south": 0.38,
        "north": 0.42,
        "west": 32.55,
        "east": 32.62,
    }
    
    print("Searching for facilities near Kasangati-Matugga corridor...")
    result = find_facilities(test_bbox, buffer_km=3.0)
    print(get_facilities_summary(result))
