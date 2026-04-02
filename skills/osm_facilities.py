"""
TARA Facility Data
Finds health facilities, schools, markets, and water points near a road corridor.

Facilities loaded from local GeoJSON files at startup.
Overpass API removed — see TARA Data Pipeline Plan.
Sources:
  Health:  gis_osm_pois_free_1.shp (Geofabrik OSM Uganda, 2026-03-31)
  Schools: gis_osm_pois_free_1.shp (Geofabrik OSM Uganda, 2026-03-31)
  Markets: Trading_Centres_UBOS.shp (UBOS, 2018)
  Water:   gis_osm_pois_free_1.shp (Geofabrik OSM Uganda, 2026-03-31)
"""

import json
import math
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Facility categories and their display config (imported by output/maps.py)
FACILITY_CATEGORIES = {
    "health": {
        "tags": [],  # retained for compatibility
        "icon": "🏥",
        "color": "red",
    },
    "education": {
        "tags": [],
        "icon": "🏫",
        "color": "blue",
    },
    "market": {
        "tags": [],
        "icon": "🏪",
        "color": "green",
    },
    "water": {
        "tags": [],
        "icon": "💧",
        "color": "cyan",
    },
    "transport": {
        "tags": [],
        "icon": "🚌",
        "color": "orange",
    },
    "worship": {
        "tags": [],
        "icon": "⛪",
        "color": "purple",
    },
}

# ---------------------------------------------------------------------------
# Load local facility data at module import time
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

_FACILITY_FILES = {
    "health": os.path.join(_DATA_DIR, "uganda_health_facilities.geojson"),
    "education": os.path.join(_DATA_DIR, "uganda_schools.geojson"),
    "market": os.path.join(_DATA_DIR, "uganda_markets.geojson"),
    "water": os.path.join(_DATA_DIR, "uganda_water_points.geojson"),
}

# In-memory cache: category -> list of {"lat": ..., "lon": ..., "name": ..., ...}
_FACILITIES: dict[str, list[dict]] = {}


def _load_facilities() -> None:
    """Load all facility GeoJSON files into memory at startup."""
    for category, path in _FACILITY_FILES.items():
        if not os.path.exists(path):
            logger.warning(f"Facility file missing: {path} — {category} will be empty")
            _FACILITIES[category] = []
            continue

        try:
            with open(path) as f:
                geojson = json.load(f)

            facilities = []
            for feat in geojson.get("features", []):
                props = feat.get("properties", {})
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [])
                if not coords or len(coords) < 2:
                    continue

                lon, lat = coords[0], coords[1]

                name = props.get("name") or "Unnamed"
                fclass = props.get("fclass", "")

                # Build subcategory label
                if category == "market":
                    subcategory = "Trading Centre"
                else:
                    subcategory = _fclass_to_subcategory(fclass)

                facilities.append({
                    "osm_id": props.get("osm_id", ""),
                    "name": name,
                    "category": category,
                    "subcategory": subcategory,
                    "lat": lat,
                    "lon": lon,
                    "tags": {k: v for k, v in props.items()
                             if k in ("name", "fclass", "district", "population", "source")},
                })

            _FACILITIES[category] = facilities
            logger.info(f"Loaded {len(facilities)} {category} facilities from {os.path.basename(path)}")

        except Exception as e:
            logger.warning(f"Failed to load {path}: {e} — {category} will be empty")
            _FACILITIES[category] = []


def _fclass_to_subcategory(fclass: str) -> str:
    """Convert OSM fclass to a readable subcategory label."""
    mapping = {
        "hospital": "Hospital",
        "clinic": "Health Clinic",
        "doctors": "Doctor",
        "pharmacy": "Pharmacy",
        "school": "School",
        "university": "University",
        "college": "College",
        "kindergarten": "Kindergarten",
        "drinking_water": "Water Point",
        "water_well": "Water Well",
        "water_tower": "Water Tower",
    }
    return mapping.get(fclass, fclass.replace("_", " ").title())


# Load on import
_load_facilities()


def find_facilities(
    bbox: dict,
    buffer_km: float = 5.0,
    categories: Optional[list[str]] = None,
    timeout: int = 30,
) -> dict:
    """
    Find facilities near a road corridor using local data.

    Args:
        bbox: Bounding box dict with south, north, west, east
        buffer_km: Buffer distance around corridor in km (default 5km)
        categories: List of categories to search (default: all)
        timeout: Ignored (kept for API compatibility)

    Returns:
        dict with facilities grouped by category
    """
    if not bbox:
        return {"facilities": {}, "total_count": 0}

    # Expand bbox by buffer
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * math.cos(math.radians((bbox["south"] + bbox["north"]) / 2)))

    south = bbox["south"] - lat_buffer
    west = bbox["west"] - lon_buffer
    north = bbox["north"] + lat_buffer
    east = bbox["east"] + lon_buffer

    # Select categories
    if categories is None:
        categories = list(FACILITY_CATEGORIES.keys())

    facilities = {}
    for cat in categories:
        if cat not in _FACILITIES:
            facilities[cat] = []
            continue

        # Filter by expanded bbox
        filtered = []
        for f in _FACILITIES.get(cat, []):
            if south <= f["lat"] <= north and west <= f["lon"] <= east:
                filtered.append(f)
        facilities[cat] = filtered

    total = sum(len(v) for v in facilities.values())

    return {
        "facilities": facilities,
        "total_count": total,
        "bbox_searched": {
            "south": south,
            "west": west,
            "north": north,
            "east": east,
        },
        "buffer_km": buffer_km,
        "categories_searched": categories,
    }


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
    test_bbox = {
        "south": 0.38,
        "north": 0.46,
        "west": 32.52,
        "east": 32.62,
    }

    print("Searching for facilities near Matugga-Kasangati corridor...")
    result = find_facilities(test_bbox, buffer_km=3.0)
    print(get_facilities_summary(result))

    print(f"\nBreakdown:")
    for cat, items in result["facilities"].items():
        print(f"  {cat}: {len(items)}")
