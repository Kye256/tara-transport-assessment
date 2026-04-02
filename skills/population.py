"""
TARA Population Skill
Local population lookup using Kontur H3 hexagons and UBOS subcounty data.
"""

import json
import logging
import os
from typing import Optional

import geopandas as gpd
from shapely.geometry import shape, LineString, box
from shapely.ops import transform
import pyproj

from config.parameters import (
    POPULATION_BUFFERS_KM,
    UGANDA_POPULATION_GROWTH_RATE,
    DENSITY_THRESHOLDS,
    POVERTY_HEADCOUNT_RATIO,
    BASE_YEAR,
)

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_KONTUR_PATH = os.path.join(_DATA_DIR, "kontur_uganda_population.gpkg")
_SUBCOUNTY_PATH = os.path.join(
    _DATA_DIR, "GoU_Data", "ShapeFiles", "2018", "Administrative", "Subcounties_2014_v3_UBOS.shp"
)
_SUBCOUNTY_JSON_PATH = os.path.join(_DATA_DIR, "subcounty_population.json")

# Module-level caches (loaded once on first call)
_kontur_gdf: Optional[gpd.GeoDataFrame] = None
_subcounty_gdf: Optional[gpd.GeoDataFrame] = None

# Projections
_TO_UTM = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32636", always_xy=True).transform
_TO_WGS = pyproj.Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True).transform


def _load_kontur() -> gpd.GeoDataFrame:
    """Load and cache Kontur hexagons in WGS84."""
    global _kontur_gdf
    if _kontur_gdf is None:
        logger.info("Loading Kontur population data...")
        _kontur_gdf = gpd.read_file(_KONTUR_PATH).to_crs(epsg=4326)
        logger.info("Loaded %d Kontur hexagons", len(_kontur_gdf))
    return _kontur_gdf


def _load_subcounties() -> gpd.GeoDataFrame:
    """Load and cache UBOS subcounties in WGS84."""
    global _subcounty_gdf
    if _subcounty_gdf is None:
        logger.info("Loading UBOS subcounty data...")
        _subcounty_gdf = gpd.read_file(_SUBCOUNTY_PATH).to_crs(epsg=4326)
        logger.info("Loaded %d subcounties", len(_subcounty_gdf))
    return _subcounty_gdf


def _to_shapely(geometry):
    """Convert GeoJSON dict or pass through shapely geometry."""
    if geometry is None:
        return None
    if isinstance(geometry, dict):
        return shape(geometry)
    return geometry


def get_population_in_buffer(
    geometry,
    radius_km: float = 5.0,
) -> dict:
    """
    Returns population within radius_km of a road geometry.

    Args:
        geometry: GeoJSON geometry dict or shapely geometry (LineString/MultiLineString)
        radius_km: buffer radius in km (default 5.0)

    Returns:
        dict with keys:
            total_population: int — total people within buffer
            area_km2: float — buffer area in km²
            density_per_km2: float — people per km²
            source: str — data source description
    """
    geom = _to_shapely(geometry)
    if geom is None or geom.is_empty:
        return {
            "total_population": 0,
            "area_km2": 0.0,
            "density_per_km2": 0.0,
            "source": "kontur (no geometry)",
        }

    try:
        # Project to UTM for accurate km buffer
        geom_utm = transform(_TO_UTM, geom)
        buffer_utm = geom_utm.buffer(radius_km * 1000)
        buffer_wgs = transform(_TO_WGS, buffer_utm)
        area_km2 = buffer_utm.area / 1e6
    except Exception as e:
        logger.warning("Projection error: %s", e)
        return {
            "total_population": 0,
            "area_km2": 0.0,
            "density_per_km2": 0.0,
            "source": f"kontur (projection error: {e})",
        }

    kontur = _load_kontur()

    # Spatial join to find intersecting hexagons
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_wgs], crs="EPSG:4326")
    candidates = gpd.sjoin(kontur, buffer_gdf, predicate="intersects")

    if candidates.empty:
        return {
            "total_population": 0,
            "area_km2": round(area_km2, 2),
            "density_per_km2": 0.0,
            "source": "kontur (no hexagons in buffer)",
        }

    # Weight population by proportion of hexagon area inside the buffer
    total_pop = 0.0
    for idx, row in candidates.iterrows():
        hex_geom = row.geometry
        intersection = hex_geom.intersection(buffer_wgs)
        if intersection.is_empty:
            continue
        fraction = intersection.area / hex_geom.area if hex_geom.area > 0 else 0.0
        total_pop += row["population"] * fraction

    total_population = int(round(total_pop))
    density = total_population / area_km2 if area_km2 > 0 else 0.0

    return {
        "total_population": total_population,
        "area_km2": round(area_km2, 2),
        "density_per_km2": round(density, 1),
        "source": "kontur_h3_hexagons_2022",
    }


def get_population_by_subcounty(
    road_geometry,
    radius_km: float = 5.0,
) -> list[dict]:
    """
    Returns list of subcounties within buffer with population figures.
    Used for equity reporting — shows which communities the road serves.

    Uses pre-computed subcounty_population.json (Kontur-enriched) if available,
    otherwise falls back to spatial join against UBOS shapefiles.

    Args:
        road_geometry: GeoJSON geometry dict or shapely geometry
        radius_km: buffer radius in km (default 5.0)

    Returns:
        list of dicts, each with:
            subcounty: str
            district: str
            population: int
            urban: bool
        Sorted by population descending.
    """
    geom = _to_shapely(road_geometry)
    if geom is None or geom.is_empty:
        return []

    try:
        geom_utm = transform(_TO_UTM, geom)
        buffer_utm = geom_utm.buffer(radius_km * 1000)
        buffer_wgs = transform(_TO_WGS, buffer_utm)
    except Exception as e:
        logger.warning("Projection error in subcounty lookup: %s", e)
        return []

    # Use pre-computed JSON if available (Kontur 2022 populations per subcounty)
    if os.path.exists(_SUBCOUNTY_JSON_PATH):
        return _subcounty_from_json(buffer_wgs)

    return _subcounty_from_shapefile(buffer_wgs)


def _subcounty_from_json(buffer_wgs) -> list[dict]:
    """Look up subcounties using pre-computed JSON + shapefile geometries for intersection."""
    with open(_SUBCOUNTY_JSON_PATH) as f:
        sc_lookup = json.load(f)

    subcounties = _load_subcounties()

    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_wgs], crs="EPSG:4326")
    hits = gpd.sjoin(subcounties, buffer_gdf, predicate="intersects")

    if hits.empty:
        return []

    results = []
    for _, row in hits.iterrows():
        sc_name = row.get("SNAME2014", "Unknown")
        district = row.get("DNAME2016", "Unknown")
        key = f"{sc_name}|{district}"

        # Weight by fraction of subcounty inside buffer
        sc_geom = row.geometry
        intersection = sc_geom.intersection(buffer_wgs)
        fraction = intersection.area / sc_geom.area if sc_geom.area > 0 else 0.0

        if key in sc_lookup:
            entry = sc_lookup[key]
            pop = int(round(entry["population"] * fraction))
            is_urban = entry["urban"]
        else:
            raw_pop = row.get("Population", 0) or 0
            pop = int(round(raw_pop * fraction))
            urban_val = str(row.get("Urban_Stat", "")).strip().lower()
            is_urban = urban_val in ("urban", "city", "municipality", "town council", "1")

        results.append({
            "subcounty": sc_name,
            "district": district,
            "population": pop,
            "urban": is_urban,
        })

    results.sort(key=lambda x: x["population"], reverse=True)
    return results


def _subcounty_from_shapefile(buffer_wgs) -> list[dict]:
    """Fallback: spatial join against UBOS shapefiles with UBOS 2014 populations."""
    subcounties = _load_subcounties()

    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_wgs], crs="EPSG:4326")
    hits = gpd.sjoin(subcounties, buffer_gdf, predicate="intersects")

    if hits.empty:
        return []

    results = []
    for _, row in hits.iterrows():
        sc_geom = row.geometry
        intersection = sc_geom.intersection(buffer_wgs)
        fraction = intersection.area / sc_geom.area if sc_geom.area > 0 else 0.0

        raw_pop = row.get("Population", 0) or 0
        weighted_pop = int(round(raw_pop * fraction))

        urban_val = str(row.get("Urban_Stat", "")).strip().lower()
        is_urban = urban_val in ("urban", "city", "municipality", "town council", "1")

        results.append({
            "subcounty": row.get("SNAME2014", "Unknown"),
            "district": row.get("DNAME2016", "Unknown"),
            "population": weighted_pop,
            "urban": is_urban,
        })

    results.sort(key=lambda x: x["population"], reverse=True)
    return results


# --- Legacy-compatible wrapper ---

_KONTUR_YEAR = 2022


def _classify_density(density_per_km2: float) -> str:
    """Classify area by population density."""
    if density_per_km2 < DENSITY_THRESHOLDS["rural"]:
        return "rural"
    elif density_per_km2 < DENSITY_THRESHOLDS["peri-urban"]:
        return "peri-urban"
    else:
        return "urban"


def get_population(
    bbox: dict,
    road_coords: Optional[list] = None,
    buffer_km: float = 5.0,
    **kwargs,
) -> dict:
    """
    Drop-in replacement for kontur_population.get_population().

    Calls get_population_in_buffer() for each configured buffer distance
    and returns the legacy dict format expected by equity, report, and agent code.

    Args:
        bbox: Bounding box dict with south, north, west, east keys.
        road_coords: List of [lat, lon] coordinate pairs along the road.
        buffer_km: Default buffer distance (unused — all POPULATION_BUFFERS_KM are queried).

    Returns:
        Dict with: found, source, year, extrapolated_to, buffers,
        poverty_estimate, classification, warnings.
    """
    # Build a shapely geometry from road_coords or bbox
    geom = None
    if road_coords and len(road_coords) >= 2:
        line_coords = [(lon, lat) for lat, lon in road_coords[:500]]
        geom = LineString(line_coords)
    elif bbox:
        geom = box(
            bbox.get("west", 0), bbox.get("south", 0),
            bbox.get("east", 0), bbox.get("north", 0),
        )

    if geom is None or geom.is_empty:
        return _empty_population_result(["No geometry provided."])

    warnings: list[str] = []
    buffers_result = {}

    for buf_km in POPULATION_BUFFERS_KM:
        result = get_population_in_buffer(geom, radius_km=buf_km)
        buffers_result[f"{buf_km}km"] = {
            "population": result["total_population"],
            "area_km2": result["area_km2"],
            "density_per_km2": result["density_per_km2"],
        }

    # Use 5km buffer for classification and poverty
    ref_buffer = buffers_result.get("5.0km", buffers_result.get("5km"))
    if ref_buffer is None:
        ref_buffer = next(
            (v for v in buffers_result.values() if v["population"] is not None), None
        )

    if ref_buffer and ref_buffer["density_per_km2"] is not None:
        density = ref_buffer["density_per_km2"]
        classification = _classify_density(density)
        poverty_ratio = POVERTY_HEADCOUNT_RATIO.get(
            classification, POVERTY_HEADCOUNT_RATIO["national"]
        )
        poverty_pop = round(ref_buffer["population"] * poverty_ratio) if ref_buffer["population"] else 0
    else:
        classification = "unknown"
        poverty_ratio = POVERTY_HEADCOUNT_RATIO["national"]
        poverty_pop = 0

    # Extrapolate to base year if Kontur data is older
    extrapolated_to = None
    if _KONTUR_YEAR < BASE_YEAR:
        years_diff = BASE_YEAR - _KONTUR_YEAR
        growth_factor = (1 + UGANDA_POPULATION_GROWTH_RATE) ** years_diff
        extrapolated_to = BASE_YEAR
        for key in buffers_result:
            buf = buffers_result[key]
            if buf["population"] is not None:
                buf["population_base_year"] = buf["population"]
                buf["population"] = round(buf["population"] * growth_factor)
                if buf["area_km2"]:
                    buf["density_per_km2"] = round(buf["population"] / buf["area_km2"], 1)
        if ref_buffer and ref_buffer.get("population") is not None:
            poverty_pop = round(ref_buffer["population"] * poverty_ratio)
        if ref_buffer and ref_buffer.get("density_per_km2") is not None:
            classification = _classify_density(ref_buffer["density_per_km2"])

    return {
        "found": True,
        "source": "kontur",
        "year": _KONTUR_YEAR,
        "extrapolated_to": extrapolated_to,
        "buffers": buffers_result,
        "poverty_estimate": {
            "headcount_ratio": poverty_ratio,
            "population_in_poverty": poverty_pop,
        },
        "classification": classification,
        "warnings": warnings,
    }


def get_population_summary(population_data: dict) -> str:
    """
    Generate a markdown summary of population data for display.

    Args:
        population_data: Result dict from get_population().

    Returns:
        Markdown-formatted summary string.
    """
    if not population_data.get("found"):
        return "**Population data:** Not available. " + "; ".join(
            population_data.get("warnings", [])
        )

    lines = ["**Corridor Population** (Kontur H3)"]
    lines.append(f"- Source: {population_data['source'].upper()}, Year: {population_data['year']}")
    if population_data.get("extrapolated_to"):
        lines.append(
            f"- Extrapolated to {population_data['extrapolated_to']} "
            f"(+{UGANDA_POPULATION_GROWTH_RATE:.0%}/yr growth)"
        )

    lines.append("")
    lines.append("| Buffer | Population | Area (km²) | Density (/km²) |")
    lines.append("|--------|-----------|------------|----------------|")
    for label, buf in population_data["buffers"].items():
        pop = f"{buf['population']:,}" if buf["population"] is not None else "N/A"
        area = f"{buf['area_km2']}" if buf["area_km2"] is not None else "N/A"
        dens = f"{buf['density_per_km2']:,.0f}" if buf["density_per_km2"] is not None else "N/A"
        lines.append(f"| {label} | {pop} | {area} | {dens} |")

    lines.append("")
    lines.append(f"- Classification: **{population_data['classification']}**")
    pov = population_data.get("poverty_estimate", {})
    if pov.get("population_in_poverty"):
        lines.append(
            f"- Estimated poverty: {pov['population_in_poverty']:,} people "
            f"({pov['headcount_ratio']:.0%} headcount ratio)"
        )

    if population_data.get("warnings"):
        lines.append("")
        for w in population_data["warnings"]:
            lines.append(f"- *Warning: {w}*")

    return "\n".join(lines)


def _empty_population_result(warnings: Optional[list[str]] = None) -> dict:
    """Return a standard empty/failure response dict."""
    return {
        "found": False,
        "source": None,
        "year": _KONTUR_YEAR,
        "extrapolated_to": None,
        "buffers": {},
        "poverty_estimate": {
            "headcount_ratio": POVERTY_HEADCOUNT_RATIO["national"],
            "population_in_poverty": 0,
        },
        "classification": "unknown",
        "warnings": warnings or ["Population data unavailable."],
    }
