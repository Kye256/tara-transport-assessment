"""
TARA Road Database Enrichment Pipeline

Enriches the base uganda_main_roads.geojson with:
  1. Kontur population data (H3 hexagons → pop within 5km buffer)
  2. HeiGIT road surface predictions (predicted surface, % paved, urban %)

Input files (download separately):
  - data/kontur_uganda_population.gpkg  — Kontur H3 hexagons with population
  - data/heigit_uganda_road_surface.gpkg — HeiGIT surface quality predictions

Output:
  - data/uganda_main_roads_enriched.geojson

Usage:
  venv/bin/python scripts/enrich_road_database.py
"""

import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BASE_GEOJSON = os.path.join(DATA_DIR, "uganda_main_roads.geojson")
ENRICHED_GEOJSON = os.path.join(DATA_DIR, "uganda_main_roads_enriched.geojson")
KONTUR_GPKG = os.path.join(DATA_DIR, "kontur_uganda_population.gpkg")
HEIGIT_GPKG = os.path.join(DATA_DIR, "heigit_uganda_road_surface.gpkg")

BUFFER_KM = 5.0


def check_dependencies():
    """Check that geopandas and shapely are available."""
    try:
        import geopandas  # noqa: F401
        import shapely  # noqa: F401
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: venv/bin/pip install geopandas shapely fiona pyproj")
        return False


def load_base_geojson() -> dict:
    """Load the base road network GeoJSON."""
    print(f"Loading base GeoJSON: {BASE_GEOJSON}")
    with open(BASE_GEOJSON) as f:
        data = json.load(f)
    print(f"  {len(data['features'])} features loaded")
    return data


def enrich_with_kontur(geojson: dict) -> dict:
    """Add pop_5km to each feature using Kontur H3 population hexagons."""
    if not os.path.exists(KONTUR_GPKG):
        print(f"\nKontur file not found: {KONTUR_GPKG}")
        print("  Download from: https://data.humdata.org/dataset/kontur-population-uganda")
        print("  Skipping Kontur enrichment.")
        return geojson

    import geopandas as gpd
    from shapely.geometry import shape
    from shapely.ops import unary_union

    print(f"\nLoading Kontur population: {KONTUR_GPKG}")
    kontur = gpd.read_file(KONTUR_GPKG)
    print(f"  {len(kontur)} hexagons loaded")

    # Ensure CRS is WGS84
    if kontur.crs and kontur.crs.to_epsg() != 4326:
        kontur = kontur.to_crs(epsg=4326)

    # Find the population column
    pop_col = None
    for candidate in ["population", "pop", "population_2020", "pop_count"]:
        if candidate in kontur.columns:
            pop_col = candidate
            break
    if pop_col is None:
        print(f"  Warning: Could not find population column in {list(kontur.columns)}")
        print("  Skipping Kontur enrichment.")
        return geojson

    print(f"  Using population column: {pop_col}")

    # Build spatial index
    kontur_sindex = kontur.sindex

    enriched_count = 0
    buffer_deg = BUFFER_KM / 111.0  # approximate degrees

    for feat in geojson["features"]:
        try:
            geom = shape(feat["geometry"])
            buffered = geom.buffer(buffer_deg)
            # Query spatial index
            candidates_idx = list(kontur_sindex.intersection(buffered.bounds))
            if not candidates_idx:
                feat["properties"]["pop_5km"] = 0
                continue
            candidates = kontur.iloc[candidates_idx]
            intersecting = candidates[candidates.geometry.intersects(buffered)]
            pop = int(intersecting[pop_col].sum())
            feat["properties"]["pop_5km"] = pop
            enriched_count += 1
        except Exception as e:
            feat["properties"]["pop_5km"] = None

    print(f"  Enriched {enriched_count}/{len(geojson['features'])} features with population data")
    return geojson


def enrich_with_heigit(geojson: dict) -> dict:
    """Add surface_predicted, pct_paved, urban_pct from HeiGIT surface data."""
    if not os.path.exists(HEIGIT_GPKG):
        print(f"\nHeiGIT file not found: {HEIGIT_GPKG}")
        print("  Download from: https://heigit.org/road-surface-prediction/")
        print("  Skipping HeiGIT enrichment.")
        return geojson

    import geopandas as gpd
    from shapely.geometry import shape

    print(f"\nLoading HeiGIT surface data: {HEIGIT_GPKG}")
    heigit = gpd.read_file(HEIGIT_GPKG)
    print(f"  {len(heigit)} road segments loaded")

    # Filter to relevant highway classes
    if "highway" in heigit.columns:
        highway_filter = heigit["highway"].isin(["trunk", "primary", "secondary", "tertiary"])
        heigit = heigit[highway_filter]
        print(f"  {len(heigit)} after filtering to trunk/primary/secondary/tertiary")

    if heigit.crs and heigit.crs.to_epsg() != 4326:
        heigit = heigit.to_crs(epsg=4326)

    # Find relevant columns
    surface_col = None
    for candidate in ["surface_predicted", "surface_pred", "predicted_surface", "surface"]:
        if candidate in heigit.columns:
            surface_col = candidate
            break

    paved_col = None
    for candidate in ["pct_paved", "paved_pct", "paved_fraction"]:
        if candidate in heigit.columns:
            paved_col = candidate
            break

    urban_col = None
    for candidate in ["urban_pct", "urban_fraction", "is_urban"]:
        if candidate in heigit.columns:
            urban_col = candidate
            break

    print(f"  Columns found: surface={surface_col}, paved={paved_col}, urban={urban_col}")

    heigit_sindex = heigit.sindex
    enriched_count = 0
    buffer_deg = 0.001  # ~100m match tolerance

    for feat in geojson["features"]:
        props = feat["properties"]
        osm_id = props.get("osm_id")

        # Try exact osm_id match first
        match = None
        if osm_id and "osm_id" in heigit.columns:
            matches = heigit[heigit["osm_id"] == osm_id]
            if len(matches) > 0:
                match = matches.iloc[0]

        # Fallback to spatial intersection
        if match is None:
            try:
                geom = shape(feat["geometry"])
                buffered = geom.buffer(buffer_deg)
                candidates_idx = list(heigit_sindex.intersection(buffered.bounds))
                if candidates_idx:
                    candidates = heigit.iloc[candidates_idx]
                    intersecting = candidates[candidates.geometry.intersects(buffered)]
                    if len(intersecting) > 0:
                        match = intersecting.iloc[0]
            except Exception:
                pass

        if match is not None:
            if surface_col:
                props["surface_predicted"] = str(match[surface_col]) if match[surface_col] else None
            if paved_col:
                props["pct_paved"] = float(match[paved_col]) if match[paved_col] else None
            if urban_col:
                val = match[urban_col]
                props["urban_pct"] = float(val) if val else None
            enriched_count += 1

    print(f"  Enriched {enriched_count}/{len(geojson['features'])} features with surface data")
    return geojson


def print_summary(geojson: dict):
    """Print enrichment summary statistics."""
    features = geojson["features"]
    total = len(features)

    pop_count = sum(1 for f in features if f["properties"].get("pop_5km") is not None)
    surface_count = sum(1 for f in features if f["properties"].get("surface_predicted") is not None)

    print(f"\n{'='*50}")
    print("Enrichment Summary")
    print(f"{'='*50}")
    print(f"Total features:     {total}")
    print(f"With population:    {pop_count} ({pop_count/total*100:.0f}%)")
    print(f"With surface pred:  {surface_count} ({surface_count/total*100:.0f}%)")

    if pop_count > 0:
        pops = [f["properties"]["pop_5km"] for f in features if f["properties"].get("pop_5km")]
        if pops:
            print(f"\nPopulation (5km buffer):")
            print(f"  Min:    {min(pops):,}")
            print(f"  Max:    {max(pops):,}")
            print(f"  Mean:   {sum(pops)/len(pops):,.0f}")
            print(f"  Median: {sorted(pops)[len(pops)//2]:,}")


def main():
    if not check_dependencies():
        sys.exit(1)

    geojson = load_base_geojson()
    geojson = enrich_with_kontur(geojson)
    geojson = enrich_with_heigit(geojson)

    print(f"\nWriting enriched GeoJSON: {ENRICHED_GEOJSON}")
    with open(ENRICHED_GEOJSON, "w") as f:
        json.dump(geojson, f)
    print(f"  Done ({os.path.getsize(ENRICHED_GEOJSON) / 1e6:.1f} MB)")

    print_summary(geojson)


if __name__ == "__main__":
    main()
