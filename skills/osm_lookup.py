"""
TARA OSM Road Lookup Skill
Finds roads on OpenStreetMap and extracts geometry, attributes, and metadata.
Uses the Overpass API (free, no key required).
"""

import requests
import json
import math
from typing import Optional


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def search_road(road_name: str, country: str = "Uganda", timeout: int = 30) -> dict:
    """
    Search for a road by name on OpenStreetMap.
    
    Args:
        road_name: Name of the road (e.g., "Kasangati-Matugga road")
        country: Country to search in (default: Uganda)
        timeout: API timeout in seconds
        
    Returns:
        dict with road data: geometry, attributes, length, etc.
    """
    # Clean up road name for search
    search_terms = _build_search_terms(road_name)
    
    # Try multiple search strategies
    for query in _build_queries(search_terms, country):
        try:
            result = _execute_overpass_query(query, timeout)
            if result and result.get("elements"):
                road_data = _process_road_results(result["elements"], road_name)
                if road_data and road_data["segments"]:
                    return road_data
        except Exception as e:
            continue
    
    # Fallback: try Nominatim geocoding first, then Overpass in that area
    return _search_with_nominatim_fallback(road_name, country, timeout)


def _build_search_terms(road_name: str) -> list[str]:
    """Generate multiple search terms from the road name."""
    terms = [road_name]
    
    # Try variations
    # "Kasangati-Matugga road" → "Kasangati - Matugga", "Kasangati Matugga"
    cleaned = road_name.lower().replace(" road", "").replace(" highway", "").replace(" street", "")
    terms.append(cleaned)
    
    # Split on hyphens and dashes for endpoint search
    for sep in ["-", "–", "—", " to ", " - "]:
        if sep in cleaned:
            parts = cleaned.split(sep)
            terms.extend([p.strip() for p in parts])
            break
    
    return list(set(terms))


def _build_queries(search_terms: list[str], country: str) -> list[str]:
    """Build Overpass queries to find the road."""
    queries = []
    
    # Strategy 1: Search by road name in country
    for term in search_terms[:2]:  # Limit to avoid too many queries
        query = f"""
        [out:json][timeout:30];
        area["name"="{country}"]["admin_level"="2"]->.searchArea;
        (
          way["highway"]["name"~"{term}",i](area.searchArea);
        );
        out body geom;
        """
        queries.append(query)
    
    # Strategy 2: Search by ref (road number) if it looks like one
    for term in search_terms:
        if any(c.isdigit() for c in term):
            query = f"""
            [out:json][timeout:30];
            area["name"="{country}"]["admin_level"="2"]->.searchArea;
            (
              way["highway"]["ref"~"{term}",i](area.searchArea);
            );
            out body geom;
            """
            queries.append(query)
    
    # Strategy 3: If we have two place names, find roads connecting them
    for term in search_terms:
        for sep in ["-", "–", "—", " to ", " - "]:
            if sep in term:
                parts = [p.strip() for p in term.split(sep)]
                if len(parts) == 2:
                    query = f"""
                    [out:json][timeout:30];
                    area["name"="{country}"]["admin_level"="2"]->.searchArea;
                    (
                      way["highway"]["name"~"{parts[0]}",i](area.searchArea);
                      way["highway"]["name"~"{parts[1]}",i](area.searchArea);
                    );
                    out body geom;
                    """
                    queries.append(query)
                    break
    
    return queries


def _execute_overpass_query(query: str, timeout: int = 30) -> Optional[dict]:
    """Execute an Overpass API query and return the response."""
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=timeout,
            headers={"User-Agent": "TARA Transport Assessment Agent/1.0"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Overpass API error: {e}")
        return None


def _search_with_nominatim_fallback(road_name: str, country: str, timeout: int) -> dict:
    """Use Nominatim to find the road's approximate location, then query Overpass."""
    try:
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{road_name}, {country}",
            "format": "json",
            "limit": 5,
            "addressdetails": 1,
        }
        response = requests.get(
            nominatim_url, 
            params=params, 
            timeout=10,
            headers={"User-Agent": "TARA Transport Assessment Agent/1.0"}
        )
        response.raise_for_status()
        results = response.json()
        
        if not results:
            return _empty_result(road_name)
        
        # Use the bounding box of the first result to search Overpass
        result = results[0]
        bbox = result.get("boundingbox", [])
        
        if len(bbox) == 4:
            south, north, west, east = [float(b) for b in bbox]
            # Expand bbox slightly
            pad = 0.02
            query = f"""
            [out:json][timeout:30];
            (
              way["highway"~"primary|secondary|tertiary|trunk|motorway"]
                ({south-pad},{west-pad},{north+pad},{east+pad});
            );
            out body geom;
            """
            overpass_result = _execute_overpass_query(query, timeout)
            if overpass_result and overpass_result.get("elements"):
                return _process_road_results(overpass_result["elements"], road_name)
        
        # If Overpass still fails, return what Nominatim found
        return {
            "road_name": road_name,
            "found": True,
            "source": "nominatim",
            "latitude": float(result["lat"]),
            "longitude": float(result["lon"]),
            "display_name": result.get("display_name", ""),
            "segments": [],
            "total_length_km": 0,
            "attributes": {},
        }
        
    except Exception as e:
        print(f"Nominatim fallback error: {e}")
        return _empty_result(road_name)


def _process_road_results(elements: list, road_name: str) -> dict:
    """Process Overpass API results into structured road data."""
    
    segments = []
    all_coords = []
    surface_types = set()
    highway_types = set()
    widths = []
    lanes_set = set()
    names_found = set()
    
    for element in elements:
        if element["type"] != "way":
            continue
        
        tags = element.get("tags", {})
        geometry = element.get("geometry", [])
        
        if not geometry:
            continue
        
        # Extract coordinates
        coords = [(point["lat"], point["lon"]) for point in geometry]
        
        # Calculate segment length
        length_km = _calculate_length(coords)
        
        segment = {
            "osm_id": element["id"],
            "name": tags.get("name", "Unnamed"),
            "highway_type": tags.get("highway", "unknown"),
            "surface": tags.get("surface", "unknown"),
            "width": tags.get("width", "unknown"),
            "lanes": tags.get("lanes", "unknown"),
            "maxspeed": tags.get("maxspeed", "unknown"),
            "oneway": tags.get("oneway", "no"),
            "bridge": "yes" if tags.get("bridge") else "no",
            "tunnel": "yes" if tags.get("tunnel") else "no",
            "lit": tags.get("lit", "unknown"),
            "length_km": round(length_km, 3),
            "coordinates": coords,
        }
        
        segments.append(segment)
        all_coords.extend(coords)
        names_found.add(tags.get("name", ""))
        
        if tags.get("surface"):
            surface_types.add(tags["surface"])
        if tags.get("highway"):
            highway_types.add(tags["highway"])
        if tags.get("width"):
            try:
                widths.append(float(tags["width"].replace("m", "").strip()))
            except ValueError:
                pass
        if tags.get("lanes"):
            lanes_set.add(tags["lanes"])
    
    if not segments:
        return _empty_result(road_name)
    
    # Calculate total length
    total_length = sum(s["length_km"] for s in segments)
    
    # Calculate bounding box
    if all_coords:
        lats = [c[0] for c in all_coords]
        lons = [c[1] for c in all_coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        bbox = {
            "south": min(lats),
            "north": max(lats),
            "west": min(lons),
            "east": max(lons),
        }
    else:
        center_lat, center_lon = 0, 0
        bbox = {}
    
    return {
        "road_name": road_name,
        "found": True,
        "source": "overpass",
        "total_length_km": round(total_length, 2),
        "segment_count": len(segments),
        "center": {"lat": center_lat, "lon": center_lon},
        "bbox": bbox,
        "attributes": {
            "surface_types": list(surface_types),
            "highway_types": list(highway_types),
            "avg_width_m": round(sum(widths) / len(widths), 1) if widths else None,
            "lanes": list(lanes_set),
            "names_found": [n for n in names_found if n],
        },
        "segments": segments,
        "coordinates_all": all_coords,
    }


def _calculate_length(coords: list[tuple]) -> float:
    """Calculate the length of a polyline in km using the Haversine formula."""
    total = 0.0
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        total += _haversine(lat1, lon1, lat2, lon2)
    return total


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _empty_result(road_name: str) -> dict:
    """Return an empty result when road is not found."""
    return {
        "road_name": road_name,
        "found": False,
        "source": None,
        "total_length_km": 0,
        "segment_count": 0,
        "center": None,
        "bbox": None,
        "attributes": {},
        "segments": [],
        "coordinates_all": [],
    }


def get_road_summary(road_data: dict) -> str:
    """Generate a human-readable summary of the road data."""
    if not road_data["found"]:
        return f"Could not find '{road_data['road_name']}' on OpenStreetMap."
    
    attrs = road_data["attributes"]
    
    summary_parts = [
        f"**{road_data['road_name']}**",
        f"- Total length: {road_data['total_length_km']} km ({road_data['segment_count']} segments)",
    ]
    
    if attrs.get("surface_types"):
        summary_parts.append(f"- Surface: {', '.join(attrs['surface_types'])}")
    if attrs.get("highway_types"):
        summary_parts.append(f"- Road class: {', '.join(attrs['highway_types'])}")
    if attrs.get("avg_width_m"):
        summary_parts.append(f"- Average width: {attrs['avg_width_m']}m")
    if attrs.get("lanes"):
        summary_parts.append(f"- Lanes: {', '.join(attrs['lanes'])}")
    if attrs.get("names_found"):
        summary_parts.append(f"- Names on OSM: {', '.join(attrs['names_found'])}")
    
    # Count special features
    bridges = sum(1 for s in road_data["segments"] if s.get("bridge") == "yes")
    if bridges:
        summary_parts.append(f"- Bridges: {bridges}")
    
    return "\n".join(summary_parts)


# Quick test function
if __name__ == "__main__":
    print("Searching for Kasangati-Matugga road...")
    result = search_road("Kasangati-Matugga road", "Uganda")
    print(json.dumps({k: v for k, v in result.items() if k != "coordinates_all" and k != "segments"}, indent=2))
    print(f"\nSegments found: {len(result.get('segments', []))}")
    if result.get("segments"):
        for s in result["segments"][:5]:
            print(f"  - {s['name']}: {s['length_km']}km, surface={s['surface']}, highway={s['highway_type']}")
    print("\n" + get_road_summary(result))
