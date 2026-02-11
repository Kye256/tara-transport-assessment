"""
TARA Local Road Database
Loads the pre-processed UNRA/HOT Export road network GeoJSON and provides
search, lookup, and listing functions for the Dash UI.

Road segments sharing the same name and highway class are merged into
single logical roads so the dropdown shows ~300-500 unique roads rather
than thousands of tiny segments.
"""

import json
import math
import os
from typing import Optional

# Module-level cache
_road_network: Optional[dict] = None

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_ENRICHED_PATH = os.path.join(_DATA_DIR, "uganda_main_roads_enriched.geojson")
_BASE_PATH = os.path.join(_DATA_DIR, "uganda_main_roads.geojson")
# Prefer enriched file if it exists
_GEOJSON_PATH = _ENRICHED_PATH if os.path.exists(_ENRICHED_PATH) else _BASE_PATH


def load_road_network() -> dict:
    """
    Load the processed GeoJSON, merge segments by name + highway class,
    and return parsed data. Caches in memory after first load.

    Returns:
        dict with keys: roads (list of merged road dicts),
                        by_id (dict mapping id -> road)
    """
    global _road_network
    if _road_network is not None:
        return _road_network

    with open(_GEOJSON_PATH) as f:
        geojson = json.load(f)

    # Group raw segments by (name, highway_class)
    groups: dict[tuple[str, str], list[dict]] = {}

    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        name = props.get("name") or "Unnamed"
        highway = props.get("highway", "unknown")
        key = (name, highway)

        coords = _extract_coords(geom)
        if not coords:
            continue

        groups.setdefault(key, []).append({
            "osm_id": str(props.get("osm_id", "")),
            "coords": coords,
            "length_km": _polyline_length_km(coords),
            "surface": props.get("surface"),
            "width": props.get("width"),
            "lanes": props.get("lanes"),
            "smoothness": props.get("smoothness"),
            "bridge": props.get("bridge"),
            "geometry": geom,
            # Enriched properties (may be None if not enriched)
            "pop_5km": props.get("pop_5km"),
            "surface_predicted": props.get("surface_predicted"),
            "pct_paved": props.get("pct_paved"),
            "urban_pct": props.get("urban_pct"),
        })

    # Merge each group into a single logical road
    roads = []
    by_id = {}

    for (name, highway), segments in groups.items():
        # Use first segment's osm_id as the road ID
        road_id = segments[0]["osm_id"]

        all_coords = []
        all_geometries = []
        total_length = 0.0
        surfaces = set()
        widths = set()
        lanes_set = set()
        osm_ids = []

        # Enriched property accumulators
        pop_5km_total = 0
        pop_5km_any = False
        surface_preds = set()
        pct_paved_vals = []
        urban_pct_vals = []

        for seg in segments:
            all_coords.extend(seg["coords"])
            all_geometries.append(seg["geometry"])
            total_length += seg["length_km"]
            osm_ids.append(seg["osm_id"])
            if seg["surface"]:
                surfaces.add(seg["surface"])
            if seg["width"]:
                widths.add(seg["width"])
            if seg["lanes"]:
                lanes_set.add(seg["lanes"])
            # Aggregate enriched properties
            if seg.get("pop_5km") is not None:
                pop_5km_total += seg["pop_5km"]
                pop_5km_any = True
            if seg.get("surface_predicted"):
                surface_preds.add(seg["surface_predicted"])
            if seg.get("pct_paved") is not None:
                pct_paved_vals.append(seg["pct_paved"])
            if seg.get("urban_pct") is not None:
                urban_pct_vals.append(seg["urban_pct"])

        lats = [c[0] for c in all_coords]
        lons = [c[1] for c in all_coords]

        road = {
            "id": road_id,
            "name": name,
            "highway_class": highway,
            "surface": ", ".join(sorted(surfaces)) if surfaces else None,
            "width": ", ".join(sorted(widths)) if widths else None,
            "lanes": ", ".join(sorted(lanes_set)) if lanes_set else None,
            "length_km": round(total_length, 2),
            "segment_count": len(segments),
            "osm_ids": osm_ids,
            "coordinates": all_coords,
            "geometries": all_geometries,
            "center": {
                "lat": sum(lats) / len(lats),
                "lon": sum(lons) / len(lons),
            },
            "bbox": {
                "south": min(lats), "north": max(lats),
                "west": min(lons), "east": max(lons),
            },
            # Enriched properties (None if not available)
            "pop_5km": pop_5km_total if pop_5km_any else None,
            "surface_predicted": ", ".join(sorted(surface_preds)) if surface_preds else None,
            "pct_paved": round(sum(pct_paved_vals) / len(pct_paved_vals), 1) if pct_paved_vals else None,
            "urban_pct": round(sum(urban_pct_vals) / len(urban_pct_vals), 1) if urban_pct_vals else None,
        }

        roads.append(road)
        by_id[road_id] = road

    # Sort by length descending so longer (more important) roads appear first
    roads.sort(key=lambda r: -r["length_km"])

    _road_network = {"roads": roads, "by_id": by_id}
    return _road_network


def search_roads(query: str, limit: int = 50) -> list[dict]:
    """
    Search roads by name. Case-insensitive matching.

    Sorts by relevance: exact match first, then starts-with, then contains.
    Within each tier, longer roads appear first.

    Args:
        query: Search string (e.g. "Gayaza" or "Jinja - Mbale")
        limit: Max results to return

    Returns:
        List of matching road summary dicts (without geometry)
    """
    network = load_road_network()
    query_lower = query.lower().strip()
    if not query_lower:
        return []

    exact = []
    starts = []
    contains = []

    for road in network["roads"]:
        name_lower = road["name"].lower()
        if name_lower == query_lower:
            exact.append(road)
        elif name_lower.startswith(query_lower):
            starts.append(road)
        elif query_lower in name_lower:
            contains.append(road)

    # Multi-word: check if all words appear in the name
    words = [w for w in query_lower.replace("-", " ").split() if len(w) > 2]
    if len(words) > 1:
        seen_ids = {r["id"] for r in exact + starts + contains}
        for road in network["roads"]:
            if road["id"] in seen_ids:
                continue
            name_lower = road["name"].lower()
            if all(w in name_lower for w in words):
                contains.append(road)

    results = exact + starts + contains
    return [_lightweight(r) for r in results[:limit]]


def get_road_by_id(road_id: str) -> Optional[dict]:
    """
    Get a single road's full data including geometry.

    Args:
        road_id: The road's ID (first osm_id of the merged group)

    Returns:
        Complete road record with coordinates and geometries, or None
    """
    network = load_road_network()
    return network["by_id"].get(road_id)


def list_all_roads() -> list[dict]:
    """
    Return summary of all roads for dropdown population.

    Returns lightweight records sorted alphabetically, each with a
    pre-formatted label: "Road Name (Highway Class, X.Xkm)"
    """
    network = load_road_network()
    roads = []
    for road in network["roads"]:
        r = _lightweight(road)
        roads.append(r)

    roads.sort(key=lambda r: r["name"].lower())
    return roads


def _lightweight(road: dict) -> dict:
    """Return a road record without geometry/coordinates (for UI)."""
    hw = road["highway_class"].replace("_", " ").title()
    result = {
        "id": road["id"],
        "name": road["name"],
        "highway_class": road["highway_class"],
        "surface": road["surface"],
        "width": road["width"],
        "lanes": road["lanes"],
        "length_km": road["length_km"],
        "segment_count": road["segment_count"],
        "label": f"{road['name']} ({hw}, {road['length_km']}km)",
    }
    # Include enriched properties if available
    if road.get("pop_5km") is not None:
        result["pop_5km"] = road["pop_5km"]
    if road.get("surface_predicted") is not None:
        result["surface_predicted"] = road["surface_predicted"]
    if road.get("pct_paved") is not None:
        result["pct_paved"] = road["pct_paved"]
    if road.get("urban_pct") is not None:
        result["urban_pct"] = road["urban_pct"]
    return result


def _extract_coords(geom: dict) -> list[tuple[float, float]]:
    """Extract (lat, lon) coordinates from GeoJSON geometry."""
    coords = []
    geom_type = geom.get("type", "")

    if geom_type == "LineString":
        for lon, lat, *_ in geom.get("coordinates", []):
            coords.append((lat, lon))
    elif geom_type == "MultiLineString":
        for line in geom.get("coordinates", []):
            for lon, lat, *_ in line:
                coords.append((lat, lon))

    return coords


def _polyline_length_km(coords: list[tuple[float, float]]) -> float:
    """Calculate polyline length in km using Haversine formula."""
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine(coords[i][0], coords[i][1],
                            coords[i + 1][0], coords[i + 1][1])
    return total


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


if __name__ == "__main__":
    print("Loading road network...")
    net = load_road_network()
    print(f"Unique merged roads: {len(net['roads'])}")

    print("\nTop 10 longest roads:")
    for r in net["roads"][:10]:
        print(f"  {r['name']} ({r['highway_class']}) — {r['length_km']}km, {r['segment_count']} segments")

    print("\nSearching for 'Gayaza':")
    for r in search_roads("Gayaza")[:5]:
        print(f"  {r['name']} ({r['highway_class']}, {r['length_km']}km, {r['segment_count']} segs)")

    print("\nSearching for 'Jinja':")
    for r in search_roads("Jinja")[:5]:
        print(f"  {r['name']} ({r['highway_class']}, {r['length_km']}km, {r['segment_count']} segs)")

    print(f"\nAll roads for dropdown: {len(list_all_roads())} entries")
