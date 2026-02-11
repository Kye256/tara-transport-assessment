"""
TARA Kontur Population Skill
Local population lookup using Kontur H3 hexagon data.
Falls back to WorldPop API if Kontur file is not present.

Replaces the slower WorldPop API with instant local spatial joins.
"""

import math
import os
import logging
from typing import Optional

from config.parameters import (
    POPULATION_BUFFERS_KM,
    UGANDA_POPULATION_GROWTH_RATE,
    DENSITY_THRESHOLDS,
    POVERTY_HEADCOUNT_RATIO,
    BASE_YEAR,
)

logger = logging.getLogger(__name__)

# Module-level cache for the Kontur dataset
_kontur_gdf = None
_kontur_pop_col: Optional[str] = None

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_KONTUR_PATH = os.path.join(_DATA_DIR, "kontur_uganda_population.gpkg")

# Kontur data year (most recent dataset is 2022)
_KONTUR_YEAR = 2022


def _load_kontur():
    """Load and cache the Kontur GeoPackage."""
    global _kontur_gdf, _kontur_pop_col

    if _kontur_gdf is not None:
        return True

    if not os.path.exists(_KONTUR_PATH):
        logger.info("Kontur file not found at %s — will fall back to WorldPop", _KONTUR_PATH)
        return False

    try:
        import geopandas as gpd
    except ImportError:
        logger.warning("geopandas not installed — cannot use Kontur data")
        return False

    logger.info("Loading Kontur population data from %s ...", _KONTUR_PATH)
    _kontur_gdf = gpd.read_file(_KONTUR_PATH)

    if _kontur_gdf.crs and _kontur_gdf.crs.to_epsg() != 4326:
        _kontur_gdf = _kontur_gdf.to_crs(epsg=4326)

    # Find the population column
    for candidate in ["population", "pop", "population_2020", "population_2022", "pop_count"]:
        if candidate in _kontur_gdf.columns:
            _kontur_pop_col = candidate
            break

    if _kontur_pop_col is None:
        logger.warning("Could not find population column in Kontur data: %s", list(_kontur_gdf.columns))
        _kontur_gdf = None
        return False

    logger.info("Loaded %d Kontur hexagons (pop column: %s)", len(_kontur_gdf), _kontur_pop_col)
    return True


def get_population(
    bbox: dict,
    road_coords: Optional[list] = None,
    buffer_km: float = 5.0,
) -> dict:
    """
    Get population data for a road corridor using Kontur H3 hexagons.

    Falls back to WorldPop API if Kontur data is not available.

    Args:
        bbox: Bounding box dict with south, north, west, east keys.
        road_coords: List of [lat, lon] coordinate pairs along the road.
        buffer_km: Default buffer distance in km.

    Returns:
        Dict matching the WorldPop get_population() return format:
        {found, source, year, buffers, poverty_estimate, classification, warnings}
    """
    if not _load_kontur():
        # Fall back to WorldPop
        try:
            from skills.worldpop import get_population as wp_get_population
            logger.info("Falling back to WorldPop API for population data")
            return wp_get_population(bbox, road_coords, buffer_km)
        except Exception as e:
            logger.warning("WorldPop fallback failed: %s", e)
            return _empty_result(["Kontur file not found and WorldPop fallback failed."])

    from shapely.geometry import LineString, box

    warnings: list[str] = []
    buffers_result = {}

    for buf_km in POPULATION_BUFFERS_KM:
        buffer_deg = buf_km / 111.0

        # Build the query geometry
        if road_coords and len(road_coords) >= 2:
            # Build corridor buffer around road
            line_coords = [(lon, lat) for lat, lon in road_coords[:500]]  # limit for perf
            geom = LineString(line_coords).buffer(buffer_deg)
        else:
            # Expand bbox
            geom = box(
                bbox["west"] - buffer_deg,
                bbox["south"] - buffer_deg,
                bbox["east"] + buffer_deg,
                bbox["north"] + buffer_deg,
            )

        # Spatial query
        try:
            candidates_idx = list(_kontur_gdf.sindex.intersection(geom.bounds))
            if candidates_idx:
                candidates = _kontur_gdf.iloc[candidates_idx]
                intersecting = candidates[candidates.geometry.intersects(geom)]
                population = int(intersecting[_kontur_pop_col].sum())
            else:
                population = 0

            area_km2 = _estimate_area_km2(geom)
            density = population / area_km2 if area_km2 > 0 else 0

            buffers_result[f"{buf_km}km"] = {
                "population": population,
                "area_km2": round(area_km2, 1),
                "density_per_km2": round(density, 1),
            }
        except Exception as e:
            logger.warning("Kontur spatial query failed for %skm buffer: %s", buf_km, e)
            buffers_result[f"{buf_km}km"] = {
                "population": None,
                "area_km2": None,
                "density_per_km2": None,
            }

    # Use 5km buffer for classification
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
        # Recalculate poverty with extrapolated population
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


def _estimate_area_km2(geom) -> float:
    """Estimate the area of a Shapely geometry in km2."""
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    avg_lat = (bounds[1] + bounds[3]) / 2
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))
    # Use the area in degrees squared, scaled
    area_deg2 = geom.area
    return area_deg2 * km_per_deg_lat * km_per_deg_lon


def _classify_density(density_per_km2: float) -> str:
    """Classify area by population density."""
    if density_per_km2 < DENSITY_THRESHOLDS["rural"]:
        return "rural"
    elif density_per_km2 < DENSITY_THRESHOLDS["peri-urban"]:
        return "peri-urban"
    else:
        return "urban"


def _empty_result(warnings: Optional[list[str]] = None) -> dict:
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
