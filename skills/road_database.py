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
_UNRA_PATH = os.path.join(_DATA_DIR, "uganda_roads_unra.geojson")
_ENRICHED_PATH = os.path.join(_DATA_DIR, "uganda_main_roads_enriched.geojson")
_BASE_PATH = os.path.join(_DATA_DIR, "uganda_main_roads.geojson")

# Prefer UNRA official data > enriched OSM > base OSM
if os.path.exists(_UNRA_PATH):
    _GEOJSON_PATH = _UNRA_PATH
    _DATA_FORMAT = "unra"
elif os.path.exists(_ENRICHED_PATH):
    _GEOJSON_PATH = _ENRICHED_PATH
    _DATA_FORMAT = "osm"
else:
    _GEOJSON_PATH = _BASE_PATH
    _DATA_FORMAT = "osm"


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

    roads = []
    by_id = {}

    if _DATA_FORMAT == "unra":
        # UNRA data: each feature is already a logical road link — no merging
        for feat in geojson.get("features", []):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = _extract_coords(geom)
            if not coords:
                continue

            road_id = props.get("road_id", "")
            name = props.get("name") or "Unnamed"
            length_km = props.get("length_km") or round(_polyline_length_km(coords), 2)

            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]

            road = {
                "id": road_id,
                "name": name,
                "highway_class": props.get("unra_class_raw", "unknown"),
                "surface": props.get("surface"),
                "width": None,
                "lanes": None,
                "length_km": round(length_km, 2),
                "segment_count": 1,
                "osm_ids": [road_id],
                "coordinates": coords,
                "geometries": [geom],
                "center": {
                    "lat": sum(lats) / len(lats),
                    "lon": sum(lons) / len(lons),
                },
                "bbox": {
                    "south": min(lats), "north": max(lats),
                    "west": min(lons), "east": max(lons),
                },
                # UNRA-specific fields
                "road_ref": props.get("road_ref"),
                "unra_class": props.get("unra_class"),
                "unra_class_raw": props.get("unra_class_raw"),
                "unra_station": props.get("unra_station"),
                "source": props.get("source"),
                # Enriched fields (not available for UNRA data)
                "pop_5km": None,
                "surface_predicted": None,
                "pct_paved": None,
                "urban_pct": None,
                "feeder_road_km": None,
            }
            roads.append(road)
            by_id[road_id] = road

    else:
        # OSM data: group raw segments by (name, highway_class) and merge
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
                "pop_5km": props.get("pop_5km"),
                "surface_predicted": props.get("surface_predicted"),
                "pct_paved": props.get("pct_paved"),
                "urban_pct": props.get("urban_pct"),
                "feeder_road_km": props.get("feeder_road_km"),
            })

        for (name, highway), segments in groups.items():
            road_id = segments[0]["osm_id"]

            all_coords = []
            all_geometries = []
            total_length = 0.0
            surfaces = set()
            widths = set()
            lanes_set = set()
            osm_ids = []

            pop_5km_total = 0
            pop_5km_any = False
            surface_preds = set()
            pct_paved_vals = []
            urban_pct_vals = []
            feeder_km_total = 0.0
            feeder_km_any = False

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
                if seg.get("pop_5km") is not None:
                    pop_5km_total += seg["pop_5km"]
                    pop_5km_any = True
                if seg.get("surface_predicted"):
                    surface_preds.add(seg["surface_predicted"])
                if seg.get("pct_paved") is not None:
                    pct_paved_vals.append(seg["pct_paved"])
                if seg.get("urban_pct") is not None:
                    urban_pct_vals.append(seg["urban_pct"])
                if seg.get("feeder_road_km") is not None:
                    feeder_km_total += seg["feeder_road_km"]
                    feeder_km_any = True

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
                "pop_5km": pop_5km_total if pop_5km_any else None,
                "surface_predicted": ", ".join(sorted(surface_preds)) if surface_preds else None,
                "pct_paved": round(sum(pct_paved_vals) / len(pct_paved_vals), 1) if pct_paved_vals else None,
                "urban_pct": round(sum(urban_pct_vals) / len(urban_pct_vals), 1) if urban_pct_vals else None,
                "feeder_road_km": round(feeder_km_total, 1) if feeder_km_any else None,
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
    _NOISE = {"road", "highway", "street", "route", "the"}
    words = [w for w in query_lower.replace("-", " ").split() if len(w) > 2 and w not in _NOISE]
    if len(words) > 1:
        seen_ids = {r["id"] for r in exact + starts + contains}
        for road in network["roads"]:
            if road["id"] in seen_ids:
                continue
            name_lower = road["name"].lower()
            if all(w in name_lower for w in words):
                contains.append(road)

    # Also match against road_ref (e.g. "A005", "C797")
    if len(query_lower) >= 2:
        seen_ids = {r["id"] for r in exact + starts + contains}
        for road in network["roads"]:
            if road["id"] in seen_ids:
                continue
            ref = (road.get("road_ref") or "").lower()
            if ref and (ref == query_lower or ref.startswith(query_lower)):
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
    # Build label based on data source
    if road.get("road_ref"):
        label = f"{road['name']} ({road['road_ref']}, {road['length_km']}km)"
    else:
        hw = road["highway_class"].replace("_", " ").title()
        label = f"{road['name']} ({hw}, {road['length_km']}km)"

    result = {
        "id": road["id"],
        "name": road["name"],
        "highway_class": road["highway_class"],
        "surface": road["surface"],
        "width": road["width"],
        "lanes": road["lanes"],
        "length_km": road["length_km"],
        "segment_count": road["segment_count"],
        "label": label,
    }
    # UNRA-specific fields
    for key in ("road_ref", "unra_class", "unra_class_raw", "unra_station", "source"):
        if road.get(key) is not None:
            result[key] = road[key]
    # Enriched properties (if available)
    for key in ("pop_5km", "surface_predicted", "pct_paved", "urban_pct", "feeder_road_km"):
        if road.get(key) is not None:
            result[key] = road[key]
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
    print(f"Loading road network ({_DATA_FORMAT} format)...")
    net = load_road_network()
    print(f"Roads loaded: {len(net['roads'])}")

    print("\nTop 10 longest roads:")
    for r in net["roads"][:10]:
        ref = r.get("road_ref", r["highway_class"])
        cls = r.get("unra_class", "")
        print(f"  {r['name']} ({ref}) — {r['length_km']}km, {cls}")

    print("\nSearching for 'Kampala':")
    for r in search_roads("Kampala")[:5]:
        print(f"  {r['label']}")

    print("\nSearching for 'A109':")
    for r in search_roads("A109")[:5]:
        print(f"  {r['label']}")

    print(f"\nAll roads for dropdown: {len(list_all_roads())} entries")
