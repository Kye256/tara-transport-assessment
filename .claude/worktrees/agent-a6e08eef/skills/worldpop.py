"""
TARA WorldPop Population Skill
Fetches corridor population data from WorldPop (REST API first, local GeoTIFF fallback).
Used for equity analysis and corridor context in road appraisals.
"""

import json
import math
import os
import time
import logging
from pathlib import Path
from typing import Optional

import requests

from config.parameters import (
    WORLDPOP_API_URL,
    WORLDPOP_DATASET,
    WORLDPOP_YEAR,
    WORLDPOP_RASTER_URL,
    WORLDPOP_RASTER_DIR,
    POPULATION_BUFFERS_KM,
    UGANDA_POPULATION_GROWTH_RATE,
    DENSITY_THRESHOLDS,
    POVERTY_HEADCOUNT_RATIO,
    BASE_YEAR,
)

logger = logging.getLogger(__name__)


def get_population(
    bbox: dict,
    road_coords: Optional[list[list[float]]] = None,
    buffer_km: float = 5.0,
    year: int = WORLDPOP_YEAR,
    country: str = "UGA",
) -> dict:
    """
    Get population data for a road corridor from WorldPop.

    Tries REST API first, falls back to local GeoTIFF raster.
    Returns population within multiple buffer zones, density, and poverty estimates.

    Args:
        bbox: Bounding box dict with south, north, west, east keys.
        road_coords: List of [lat, lon] coordinate pairs along the road.
        buffer_km: Default buffer distance in km (used if road_coords not provided).
        year: WorldPop data year (default: 2020).
        country: ISO3 country code (default: UGA for Uganda).

    Returns:
        Dict with population counts, densities, poverty estimates, and classification.
    """
    warnings: list[str] = []
    buffers_result = {}
    source = None

    for buf_km in POPULATION_BUFFERS_KM:
        if road_coords and len(road_coords) >= 2:
            polygon = _build_corridor_polygon(road_coords, buf_km)
        else:
            polygon = _build_bbox_polygon(bbox, buf_km)

        population = None

        # Try REST API first
        api_pop = _query_worldpop_api(polygon, year, WORLDPOP_DATASET)
        if api_pop is not None:
            population = api_pop
            if source is None:
                source = "api"
        else:
            # Fallback to local raster
            if source is None:
                warnings.append("WorldPop API unavailable; attempting local raster fallback.")
            raster_path = _download_raster(country, year)
            if raster_path:
                raster_pop = _query_local_raster(raster_path, polygon)
                if raster_pop is not None:
                    population = raster_pop
                    if source is None:
                        source = "raster"
                else:
                    if source is None:
                        warnings.append("Local raster query failed.")
            else:
                if source is None:
                    warnings.append("Could not download raster file.")

        if population is not None:
            area_km2 = _estimate_area_km2(polygon)
            density = population / area_km2 if area_km2 > 0 else 0
            buffers_result[f"{buf_km}km"] = {
                "population": round(population),
                "area_km2": round(area_km2, 1),
                "density_per_km2": round(density, 1),
            }
        else:
            buffers_result[f"{buf_km}km"] = {
                "population": None,
                "area_km2": None,
                "density_per_km2": None,
            }

    if not source:
        warnings.append("Population data unavailable from both API and raster sources.")
        return _empty_result(warnings)

    # Use the middle buffer (5km) for classification and poverty
    ref_buffer = buffers_result.get("5.0km", buffers_result.get("5km"))
    if ref_buffer is None:
        # Fallback: use whatever buffer we have
        ref_buffer = next(
            (v for v in buffers_result.values() if v["population"] is not None), None
        )

    if ref_buffer and ref_buffer["density_per_km2"] is not None:
        density = ref_buffer["density_per_km2"]
        classification = _classify_density(density)
        poverty_ratio = POVERTY_HEADCOUNT_RATIO.get(
            classification, POVERTY_HEADCOUNT_RATIO["national"]
        )
        ref_pop = ref_buffer["population"]
        poverty_pop = round(ref_pop * poverty_ratio) if ref_pop else 0
    else:
        classification = "unknown"
        poverty_ratio = POVERTY_HEADCOUNT_RATIO["national"]
        poverty_pop = 0

    # Extrapolate to current year if data year differs
    extrapolated_to = None
    if year < BASE_YEAR:
        years_diff = BASE_YEAR - year
        growth_factor = (1 + UGANDA_POPULATION_GROWTH_RATE) ** years_diff
        extrapolated_to = BASE_YEAR
        for key in buffers_result:
            buf = buffers_result[key]
            if buf["population"] is not None:
                buf["population_base_year"] = buf["population"]
                buf["population"] = round(buf["population"] * growth_factor)
                buf["density_per_km2"] = round(
                    buf["population"] / buf["area_km2"], 1
                ) if buf["area_km2"] else buf["density_per_km2"]
        # Recalculate poverty with extrapolated population
        if ref_buffer and ref_buffer.get("population") is not None:
            poverty_pop = round(ref_buffer["population"] * poverty_ratio)
        # Update classification with extrapolated density
        if ref_buffer and ref_buffer.get("density_per_km2") is not None:
            classification = _classify_density(ref_buffer["density_per_km2"])

    return {
        "found": True,
        "source": source,
        "year": year,
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

    lines = ["**Corridor Population** (WorldPop)"]
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


# --- Private Helpers ---


def _build_corridor_polygon(
    road_coords: list[list[float]], buffer_km: float
) -> dict:
    """
    Build a GeoJSON polygon by buffering a road polyline.

    Creates a simplified corridor polygon by offsetting each road segment
    perpendicular to its direction. Simplifies to ~50 vertices max for API compatibility.

    Args:
        road_coords: List of [lat, lon] pairs forming the road centerline.
        buffer_km: Buffer distance in km on each side of the road.

    Returns:
        GeoJSON Polygon dict (coordinates in [lon, lat] order per GeoJSON spec).
    """
    if len(road_coords) < 2:
        # Single point — build a circle-like bbox
        lat, lon = road_coords[0]
        return _build_bbox_polygon(
            {"south": lat, "north": lat, "west": lon, "east": lon}, buffer_km
        )

    # Convert buffer to approximate degrees
    buffer_lat = buffer_km / 111.0
    avg_lat = sum(c[0] for c in road_coords) / len(road_coords)
    buffer_lon = buffer_km / (111.0 * math.cos(math.radians(avg_lat)))

    # Build left and right offset lines
    left_side = []
    right_side = []

    for i in range(len(road_coords) - 1):
        lat1, lon1 = road_coords[i]
        lat2, lon2 = road_coords[i + 1]

        # Direction vector
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        length = math.sqrt(dlat ** 2 + dlon ** 2)
        if length == 0:
            continue

        # Perpendicular unit vector (normalized in degree space)
        perp_lat = -dlon / length * buffer_lat
        perp_lon = dlat / length * buffer_lon

        left_side.append([lon1 + perp_lon, lat1 + perp_lat])
        right_side.append([lon1 - perp_lon, lat1 - perp_lat])

        if i == len(road_coords) - 2:
            left_side.append([lon2 + perp_lon, lat2 + perp_lat])
            right_side.append([lon2 - perp_lon, lat2 - perp_lat])

    # Build polygon: left side forward + right side reversed
    right_side.reverse()
    ring = left_side + right_side
    if ring:
        ring.append(ring[0])  # Close the ring

    # Simplify to max ~50 vertices
    ring = _simplify_ring(ring, max_vertices=50)

    return {
        "type": "Polygon",
        "coordinates": [ring],
    }


def _build_bbox_polygon(bbox: dict, buffer_km: float) -> dict:
    """
    Build a GeoJSON polygon from a bounding box, expanded by buffer_km.

    Args:
        bbox: Dict with south, north, west, east keys.
        buffer_km: Buffer distance to expand the bbox.

    Returns:
        GeoJSON Polygon dict.
    """
    buffer_lat = buffer_km / 111.0
    avg_lat = (bbox["south"] + bbox["north"]) / 2
    buffer_lon = buffer_km / (111.0 * math.cos(math.radians(avg_lat)))

    south = bbox["south"] - buffer_lat
    north = bbox["north"] + buffer_lat
    west = bbox["west"] - buffer_lon
    east = bbox["east"] + buffer_lon

    ring = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    return {
        "type": "Polygon",
        "coordinates": [ring],
    }


def _simplify_ring(ring: list[list[float]], max_vertices: int = 50) -> list[list[float]]:
    """Downsample a polygon ring to at most max_vertices points."""
    if len(ring) <= max_vertices:
        return ring
    step = max(1, len(ring) // max_vertices)
    simplified = ring[::step]
    # Ensure the ring is closed
    if simplified[-1] != simplified[0]:
        simplified.append(simplified[0])
    return simplified


def _query_worldpop_api(
    geojson_polygon: dict, year: int, dataset: str, timeout: int = 60
) -> Optional[float]:
    """
    Query the WorldPop REST API for population within a polygon.

    Handles both immediate responses and async task polling.

    Args:
        geojson_polygon: GeoJSON Polygon dict.
        year: Data year (2000-2020).
        dataset: WorldPop dataset ID (e.g., 'wpgppop').
        timeout: Max wait time in seconds.

    Returns:
        Total population as float, or None on failure.
    """
    try:
        geojson_str = json.dumps(geojson_polygon)
        params = {
            "dataset": dataset,
            "year": year,
            "geojson": geojson_str,
        }

        resp = requests.get(WORLDPOP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Check for immediate result
        if "data" in data and "total_population" in data["data"]:
            pop = data["data"]["total_population"]
            if pop is not None and pop > 0:
                return float(pop)

        # Check for async task
        task_id = data.get("taskid")
        if task_id:
            return _poll_worldpop_task(task_id, timeout)

        logger.warning("WorldPop API returned unexpected format: %s", data)
        return None

    except requests.RequestException as e:
        logger.warning("WorldPop API request failed: %s", e)
        return None
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        logger.warning("WorldPop API parse error: %s", e)
        return None


def _poll_worldpop_task(task_id: str, timeout: int = 60) -> Optional[float]:
    """
    Poll a WorldPop async task until completion or timeout.

    Args:
        task_id: Task ID from initial API response.
        timeout: Max seconds to wait.

    Returns:
        Total population or None.
    """
    task_url = f"https://api.worldpop.org/v1/tasks/{task_id}"
    start = time.time()
    poll_interval = 3

    while time.time() - start < timeout:
        try:
            resp = requests.get(task_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("status", "").lower()
            if status == "finished":
                result = data.get("data", {})
                pop = result.get("total_population")
                if pop is not None:
                    return float(pop)
                return None
            elif status in ("failed", "error"):
                logger.warning("WorldPop task %s failed: %s", task_id, data)
                return None

            time.sleep(poll_interval)
        except requests.RequestException:
            time.sleep(poll_interval)

    logger.warning("WorldPop task %s timed out after %ds", task_id, timeout)
    return None


def _download_raster(country: str, year: int) -> Optional[Path]:
    """
    Download a WorldPop GeoTIFF raster file if not already cached.

    Args:
        country: ISO3 country code (e.g., 'UGA').
        year: Data year.

    Returns:
        Path to local raster file, or None on failure.
    """
    raster_dir = Path(WORLDPOP_RASTER_DIR)
    raster_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{country.lower()}_ppp_{year}.tif"
    local_path = raster_dir / filename

    if local_path.exists():
        return local_path

    url = WORLDPOP_RASTER_URL.format(year=year)
    logger.info("Downloading WorldPop raster from %s ...", url)

    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("Downloaded raster to %s (%.1f MB)", local_path, local_path.stat().st_size / 1e6)
        return local_path

    except requests.RequestException as e:
        logger.warning("Failed to download raster: %s", e)
        if local_path.exists():
            local_path.unlink()
        return None


def _query_local_raster(raster_path: Path, polygon: dict) -> Optional[float]:
    """
    Query a local GeoTIFF raster for population within a polygon.

    Uses rasterio to mask the raster with the polygon and sum pixel values.

    Args:
        raster_path: Path to the GeoTIFF file.
        polygon: GeoJSON Polygon dict.

    Returns:
        Total population as float, or None on failure.
    """
    try:
        import rasterio
        from rasterio.mask import mask as rasterio_mask
        import numpy as np

        with rasterio.open(raster_path) as src:
            out_image, _ = rasterio_mask(src, [polygon], crop=True, nodata=0)
            # WorldPop rasters: pixel value = estimated population count
            # NoData is typically -99999 or very negative
            data = out_image[0]
            data = data[data > 0]  # Exclude nodata and zero
            total = float(np.sum(data))
            return total if total > 0 else None

    except ImportError:
        logger.warning("rasterio not installed — cannot query local raster.")
        return None
    except Exception as e:
        logger.warning("Raster query failed: %s", e)
        return None


def _estimate_area_km2(polygon: dict) -> float:
    """
    Estimate the area of a GeoJSON polygon in km².

    Uses the Shoelace formula on lat/lon coordinates with a cos(lat) correction.
    This is approximate but sufficient for corridor-scale calculations.

    Args:
        polygon: GeoJSON Polygon dict.

    Returns:
        Approximate area in km².
    """
    ring = polygon["coordinates"][0]
    if len(ring) < 3:
        return 0.0

    # Shoelace formula in degree space
    n = len(ring)
    area_deg2 = 0.0
    for i in range(n - 1):
        lon1, lat1 = ring[i]
        lon2, lat2 = ring[i + 1]
        area_deg2 += lon1 * lat2 - lon2 * lat1

    area_deg2 = abs(area_deg2) / 2.0

    # Convert to km² using average latitude
    avg_lat = sum(pt[1] for pt in ring) / len(ring)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))

    area_km2 = area_deg2 * km_per_deg_lat * km_per_deg_lon
    return area_km2


def _classify_density(density_per_km2: float) -> str:
    """
    Classify an area by population density.

    Args:
        density_per_km2: People per km².

    Returns:
        Classification string: 'rural', 'peri-urban', or 'urban'.
    """
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
        "year": WORLDPOP_YEAR,
        "extrapolated_to": None,
        "buffers": {},
        "poverty_estimate": {
            "headcount_ratio": POVERTY_HEADCOUNT_RATIO["national"],
            "population_in_poverty": 0,
        },
        "classification": "unknown",
        "warnings": warnings or ["Population data unavailable."],
    }
