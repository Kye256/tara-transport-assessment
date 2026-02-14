"""UBOS subcounty population data — corridor enrichment layer.

Loads Uganda Bureau of Statistics 2014 census subcounty boundaries and
provides corridor-level population summaries for road appraisal.
"""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from shapely.geometry import shape, LineString, MultiPoint
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

# Module-level cache: district name → list of (properties, shapely_geom, geojson_geom)
_district_cache: dict[str, list[tuple[dict, Any, dict]]] = {}

# Path to UBOS GeoJSON
_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "ubos", "subcounty_boundaries.geojson",
)

# Growth rate for 2014→2026 projection (3.2% p.a., 12 years)
_GROWTH_FACTOR = (1.032) ** 12  # ≈1.459


def _load_district(district: str) -> list[tuple[dict, Any, dict]]:
    """Load and cache subcounty features for a given district.

    Args:
        district: District name (uppercase, e.g. "WAKISO").

    Returns:
        List of (properties, shapely_geometry, geojson_geometry) tuples.
    """
    district_upper = district.upper()
    if district_upper in _district_cache:
        return _district_cache[district_upper]

    if not os.path.exists(_DATA_PATH):
        print(f"  UBOS GeoJSON not found at {_DATA_PATH}")
        _district_cache[district_upper] = []
        return []

    try:
        with open(_DATA_PATH) as f:
            gj = json.load(f)
    except Exception as e:
        print(f"  Failed to load UBOS GeoJSON: {e}")
        _district_cache[district_upper] = []
        return []

    features = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        dname = (props.get("DNAME2014") or "").upper()
        if dname != district_upper:
            continue
        try:
            geom = shape(feat["geometry"])
            if geom.is_valid:
                features.append((props, geom, feat["geometry"]))
        except Exception:
            continue

    _district_cache[district_upper] = features
    print(f"  UBOS: loaded {len(features)} subcounties for {district_upper}")
    return features


def get_corridor_subcounties(
    road_data: dict,
    buffer_km: float = 2.0,
) -> list[dict]:
    """Find subcounties within a buffer of the road corridor.

    Args:
        road_data: Road data dict with ``coordinates_all`` as (lat, lon) tuples.
        buffer_km: Buffer distance in km (converted to degrees at equator).

    Returns:
        List of subcounty dicts sorted by projected population descending.
        Empty list if data unavailable or on error.
    """
    if not HAS_SHAPELY:
        print("  UBOS: shapely not installed, skipping subcounty lookup")
        return []

    try:
        coords_all = road_data.get("coordinates_all", [])
        if not coords_all or len(coords_all) < 2:
            return []

        # Flip (lat, lon) → (lon, lat) for Shapely
        line_coords = [(lon, lat) for lat, lon in coords_all]
        road_line = LineString(line_coords)

        # Buffer in degrees (1° ≈ 111km at equator; Uganda is near equator)
        buffer_deg = buffer_km * 0.009
        road_buffer = road_line.buffer(buffer_deg)

        # Determine district from road center
        center = road_data.get("center", {})
        district = _guess_district(center)

        district_features = _load_district(district)
        if not district_features:
            return []

        results = []
        for props, geom, geojson_geom in district_features:
            try:
                if not road_buffer.intersects(geom):
                    continue
            except Exception:
                continue

            pop_2014 = props.get("POP2014", 0) or 0
            hh = props.get("HH2014", 0) or 0
            pop_projected = int(pop_2014 * _GROWTH_FACTOR)
            hh_projected = int(hh * _GROWTH_FACTOR)

            # Area in km² (approximate: degrees² → km² at equator)
            try:
                area_deg2 = geom.area
                # 1° lat ≈ 111km, 1° lon ≈ 111km at equator
                area_sq_km = area_deg2 * (111 ** 2)
            except Exception:
                area_sq_km = 0

            density = pop_projected / area_sq_km if area_sq_km > 0 else 0

            results.append({
                "name": (props.get("SNAME2014") or "Unknown").title(),
                "district": (props.get("DNAME2014") or "Unknown").title(),
                "pop_2014": pop_2014,
                "pop_projected": pop_projected,
                "households": hh_projected,
                "area_sq_km": round(area_sq_km, 2),
                "density_per_sq_km": round(density, 0),
                "geometry": geojson_geom,
            })

        results.sort(key=lambda x: x["pop_projected"], reverse=True)
        return results

    except Exception as e:
        print(f"  UBOS corridor lookup failed: {e}")
        return []


def _guess_district(center: dict) -> str:
    """Guess the district from road center coordinates.

    For now, defaults to WAKISO (our demo district). Could be extended
    to do a point-in-polygon lookup across all districts.
    """
    return "WAKISO"


def get_subcounty_geojson(corridor_subcounties: list[dict]) -> dict:
    """Build a GeoJSON FeatureCollection for map rendering.

    Args:
        corridor_subcounties: Output of get_corridor_subcounties().

    Returns:
        GeoJSON FeatureCollection with density_category in properties.
    """
    features = []
    for sc in corridor_subcounties:
        density = sc.get("density_per_sq_km", 0)
        if density > 5000:
            density_cat = "very_high"
        elif density > 2000:
            density_cat = "high"
        elif density > 500:
            density_cat = "moderate"
        else:
            density_cat = "low"

        features.append({
            "type": "Feature",
            "properties": {
                "name": sc["name"],
                "pop_projected": sc["pop_projected"],
                "households": sc["households"],
                "density_per_sq_km": sc["density_per_sq_km"],
                "density_category": density_cat,
            },
            "geometry": sc["geometry"],
        })

    return {"type": "FeatureCollection", "features": features}


def get_population_summary(corridor_subcounties: list[dict]) -> dict:
    """Compute aggregate population statistics for the corridor.

    Args:
        corridor_subcounties: Output of get_corridor_subcounties().

    Returns:
        Summary dict with totals and per-subcounty breakdown.
    """
    if not corridor_subcounties:
        return {}

    total_pop = sum(sc["pop_projected"] for sc in corridor_subcounties)
    total_hh = sum(sc["households"] for sc in corridor_subcounties)

    by_density = sorted(corridor_subcounties, key=lambda x: x["density_per_sq_km"], reverse=True)
    highest = by_density[0] if by_density else None
    lowest = by_density[-1] if by_density else None

    return {
        "total_population": total_pop,
        "total_households": total_hh,
        "num_subcounties": len(corridor_subcounties),
        "highest_density": {
            "name": highest["name"],
            "density": highest["density_per_sq_km"],
        } if highest else None,
        "lowest_density": {
            "name": lowest["name"],
            "density": lowest["density_per_sq_km"],
        } if lowest else None,
        "subcounties": corridor_subcounties,
        "projection_year": 2026,
        "census_year": 2014,
        "_geojson": get_subcounty_geojson(corridor_subcounties),
    }
