"""
TARA Road Database Enrichment Pipeline

Enriches the base uganda_main_roads.geojson with:
  1. Kontur population data (H3 hexagons → pop within 5km buffer)
  2. HeiGIT road surface predictions (predicted surface, % paved, urban %)

Input files (download separately):
  - data/kontur_uganda_population.gpkg  — Kontur H3 hexagons with population
  - data/heigit_uga_roadsurface_lines.gpkg — HeiGIT surface quality predictions

Output:
  - data/uganda_main_roads_enriched.geojson

Usage:
  venv/bin/python scripts/enrich_road_database.py
"""

import json
import os
import sys
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BASE_GEOJSON = os.path.join(DATA_DIR, "uganda_main_roads.geojson")
ENRICHED_GEOJSON = os.path.join(DATA_DIR, "uganda_main_roads_enriched.geojson")
KONTUR_GPKG = os.path.join(DATA_DIR, "kontur_uganda_population.gpkg")
HEIGIT_GPKG = os.path.join(DATA_DIR, "heigit_uga_roadsurface_lines.gpkg")
EDINBURGH_SHP = os.path.join(DATA_DIR, "travel_times", "AllRoads.shp")

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

    print(f"\nLoading Kontur population: {KONTUR_GPKG}")
    t0 = time.time()
    kontur = gpd.read_file(KONTUR_GPKG)
    print(f"  {len(kontur)} hexagons loaded in {time.time()-t0:.1f}s")
    print(f"  CRS: {kontur.crs}")
    print(f"  Columns: {list(kontur.columns)}")

    # Reproject to WGS84 (Kontur uses EPSG:3857)
    if kontur.crs and kontur.crs.to_epsg() != 4326:
        print(f"  Reprojecting from {kontur.crs} to EPSG:4326...")
        t0 = time.time()
        kontur = kontur.to_crs(epsg=4326)
        print(f"  Reprojected in {time.time()-t0:.1f}s")

    # The population column is "population"
    pop_col = "population"
    if pop_col not in kontur.columns:
        print(f"  Warning: '{pop_col}' column not found in {list(kontur.columns)}")
        print("  Skipping Kontur enrichment.")
        return geojson

    total_pop = kontur[pop_col].sum()
    print(f"  Total population in dataset: {total_pop:,.0f}")

    # Build spatial index
    print("  Building spatial index...")
    kontur_sindex = kontur.sindex

    enriched_count = 0
    total = len(geojson["features"])
    buffer_deg = BUFFER_KM / 111.0  # approximate degrees

    print(f"  Enriching {total} road segments (5km buffer)...")
    t0 = time.time()

    for i, feat in enumerate(geojson["features"]):
        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate
            print(f"    {i+1}/{total} ({rate:.0f}/s, ETA {eta:.0f}s)")

        try:
            geom = shape(feat["geometry"])
            buffered = geom.buffer(buffer_deg)
            # Query spatial index
            candidates_idx = list(kontur_sindex.intersection(buffered.bounds))
            if not candidates_idx:
                feat["properties"]["pop_5km"] = 0
                enriched_count += 1
                continue
            candidates = kontur.iloc[candidates_idx]
            intersecting = candidates[candidates.geometry.intersects(buffered)]
            pop = int(intersecting[pop_col].sum())
            feat["properties"]["pop_5km"] = pop
            enriched_count += 1
        except Exception as e:
            feat["properties"]["pop_5km"] = None

    elapsed = time.time() - t0
    print(f"  Enriched {enriched_count}/{total} features with population data in {elapsed:.1f}s")
    return geojson


def enrich_with_heigit(geojson: dict) -> dict:
    """Add surface_predicted, pct_paved, urban_pct from HeiGIT surface data.

    HeiGIT columns used:
      - combined_surface_osm_priority: surface type (paved/unpaved), OSM tag preferred
      - pred_label: 0 = paved, 1 = unpaved (AI prediction)
      - urban: float, 1.0 = urban, 0.0 = rural
      - osm_id: float, OSM way ID
    """
    if not os.path.exists(HEIGIT_GPKG):
        print(f"\nHeiGIT file not found: {HEIGIT_GPKG}")
        print("  Download from: https://data.humdata.org/dataset/uganda-road-surface-data")
        print("  Skipping HeiGIT enrichment.")
        return geojson

    import geopandas as gpd
    from shapely.geometry import shape
    import math

    print(f"\nLoading HeiGIT surface data: {HEIGIT_GPKG}")
    print("  (filtering to trunk/primary/secondary/tertiary — this may take a moment...)")
    t0 = time.time()
    # Use SQL filter on read for performance
    try:
        heigit = gpd.read_file(
            HEIGIT_GPKG,
            where="highway IN ('trunk', 'primary', 'secondary', 'tertiary', "
                  "'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link')",
        )
    except Exception:
        # Fallback: load all, then filter
        heigit = gpd.read_file(HEIGIT_GPKG)
        heigit = heigit[heigit["highway"].isin([
            "trunk", "primary", "secondary", "tertiary",
            "trunk_link", "primary_link", "secondary_link", "tertiary_link",
        ])]
    print(f"  {len(heigit)} road segments loaded in {time.time()-t0:.1f}s")

    if heigit.crs and heigit.crs.to_epsg() != 4326:
        heigit = heigit.to_crs(epsg=4326)

    # Build osm_id lookup (osm_id is float in HeiGIT)
    heigit_by_osmid = {}
    if "osm_id" in heigit.columns:
        for idx, row in heigit.iterrows():
            oid = row["osm_id"]
            if oid and not (isinstance(oid, float) and math.isnan(oid)):
                heigit_by_osmid[int(oid)] = idx
        print(f"  Built osm_id index: {len(heigit_by_osmid)} entries")

    heigit_sindex = heigit.sindex
    enriched_count = 0
    osm_match_count = 0
    spatial_match_count = 0
    total = len(geojson["features"])
    buffer_deg = 0.001  # ~100m match tolerance

    print(f"  Enriching {total} road segments...")
    t0 = time.time()

    for i, feat in enumerate(geojson["features"]):
        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate
            print(f"    {i+1}/{total} ({rate:.0f}/s, ETA {eta:.0f}s) "
                  f"[osm_id: {osm_match_count}, spatial: {spatial_match_count}]")

        props = feat["properties"]
        osm_id = props.get("osm_id")

        # Try exact osm_id match first
        match_rows = None
        if osm_id and int(osm_id) in heigit_by_osmid:
            match_idx = heigit_by_osmid[int(osm_id)]
            match_rows = heigit.loc[[match_idx]]
            osm_match_count += 1

        # Fallback to spatial intersection
        if match_rows is None or len(match_rows) == 0:
            try:
                geom = shape(feat["geometry"])
                buffered = geom.buffer(buffer_deg)
                candidates_idx = list(heigit_sindex.intersection(buffered.bounds))
                if candidates_idx:
                    candidates = heigit.iloc[candidates_idx]
                    intersecting = candidates[candidates.geometry.intersects(buffered)]
                    if len(intersecting) > 0:
                        match_rows = intersecting
                        spatial_match_count += 1
            except Exception:
                pass

        if match_rows is not None and len(match_rows) > 0:
            # Surface prediction — use combined_surface_osm_priority (most common across segments)
            surface_vals = match_rows["combined_surface_osm_priority"].dropna()
            if len(surface_vals) > 0:
                props["surface_predicted"] = surface_vals.mode().iloc[0]
            else:
                props["surface_predicted"] = None

            # Pct paved — from pred_label (0=paved, 1=unpaved)
            pred_vals = match_rows["pred_label"].dropna()
            if len(pred_vals) > 0:
                pct_paved = round((pred_vals == 0).mean() * 100, 1)
                props["pct_paved"] = pct_paved
            else:
                props["pct_paved"] = None

            # Urban percentage
            urban_vals = match_rows["urban"].dropna()
            if len(urban_vals) > 0:
                props["urban_pct"] = round(urban_vals.mean() * 100, 1)
            else:
                props["urban_pct"] = None

            enriched_count += 1

    elapsed = time.time() - t0
    print(f"  Enriched {enriched_count}/{total} features in {elapsed:.1f}s")
    print(f"    osm_id matches: {osm_match_count}")
    print(f"    spatial matches: {spatial_match_count}")
    return geojson


def enrich_with_edinburgh(geojson: dict) -> dict:
    """Add feeder_road_km from Edinburgh/UNICEF travel time roads.

    Counts total km of feeder/local roads within a 5km corridor of each
    main road segment. Higher density = better local connectivity.

    Edinburgh dataset has 931K road segments (OSM + MapWithAI), mostly
    residential/unclassified — exactly the feeder roads we want to measure.
    """
    if not os.path.exists(EDINBURGH_SHP):
        print(f"\nEdinburgh roads not found: {EDINBURGH_SHP}")
        print("  Extract UgandaTravelTimes.zip to data/travel_times/")
        print("  Skipping Edinburgh enrichment.")
        return geojson

    import geopandas as gpd
    from shapely.geometry import shape
    import math

    print(f"\nLoading Edinburgh/UNICEF roads: {EDINBURGH_SHP}")
    print("  (931K features — this will take a moment...)")
    t0 = time.time()
    edinburgh = gpd.read_file(EDINBURGH_SHP)
    print(f"  {len(edinburgh)} road segments loaded in {time.time()-t0:.1f}s")

    if edinburgh.crs and edinburgh.crs.to_epsg() != 4326:
        edinburgh = edinburgh.to_crs(epsg=4326)

    # Pre-compute segment lengths in km (geom_Lengt is in degrees)
    # At Uganda's latitude (~1°N), 1° lon ≈ 111 km, 1° lat ≈ 111 km
    print("  Building spatial index...")
    edin_sindex = edinburgh.sindex

    enriched_count = 0
    total = len(geojson["features"])
    buffer_deg = BUFFER_KM / 111.0

    print(f"  Enriching {total} road segments (5km feeder road density)...")
    t0 = time.time()

    for i, feat in enumerate(geojson["features"]):
        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (total - i - 1) / rate
            print(f"    {i+1}/{total} ({rate:.0f}/s, ETA {eta:.0f}s)")

        try:
            geom = shape(feat["geometry"])
            buffered = geom.buffer(buffer_deg)
            candidates_idx = list(edin_sindex.intersection(buffered.bounds))
            if not candidates_idx:
                feat["properties"]["feeder_road_km"] = 0.0
                enriched_count += 1
                continue

            candidates = edinburgh.iloc[candidates_idx]
            intersecting = candidates[candidates.geometry.intersects(buffered)]

            if len(intersecting) > 0:
                # Sum lengths: geom_Lengt is in degrees, convert to km
                # Approximate: 1 degree ≈ 111 km at equator, adjust for latitude
                avg_lat = (buffered.bounds[1] + buffered.bounds[3]) / 2
                deg_to_km = 111.0 * math.cos(math.radians(avg_lat))
                total_km = float(intersecting["geom_Lengt"].sum()) * deg_to_km
                feat["properties"]["feeder_road_km"] = round(total_km, 1)
            else:
                feat["properties"]["feeder_road_km"] = 0.0
            enriched_count += 1
        except Exception:
            feat["properties"]["feeder_road_km"] = None

    elapsed = time.time() - t0
    print(f"  Enriched {enriched_count}/{total} features in {elapsed:.1f}s")
    return geojson


def print_summary(geojson: dict):
    """Print enrichment summary statistics."""
    features = geojson["features"]
    total = len(features)

    pop_count = sum(1 for f in features if f["properties"].get("pop_5km") is not None)
    surface_count = sum(1 for f in features if f["properties"].get("surface_predicted") is not None)
    paved_count = sum(1 for f in features if f["properties"].get("pct_paved") is not None)
    urban_count = sum(1 for f in features if f["properties"].get("urban_pct") is not None)
    feeder_count = sum(1 for f in features if f["properties"].get("feeder_road_km") is not None)

    print(f"\n{'='*50}")
    print("Enrichment Summary")
    print(f"{'='*50}")
    print(f"Total features:     {total}")
    print(f"With population:    {pop_count} ({pop_count/total*100:.0f}%)")
    print(f"With surface pred:  {surface_count} ({surface_count/total*100:.0f}%)")
    print(f"With pct_paved:     {paved_count} ({paved_count/total*100:.0f}%)")
    print(f"With urban_pct:     {urban_count} ({urban_count/total*100:.0f}%)")
    print(f"With feeder roads:  {feeder_count} ({feeder_count/total*100:.0f}%)")

    if pop_count > 0:
        pops = [f["properties"]["pop_5km"] for f in features
                if f["properties"].get("pop_5km") and f["properties"]["pop_5km"] > 0]
        if pops:
            print(f"\nPopulation (5km buffer):")
            print(f"  Non-zero: {len(pops)}/{pop_count}")
            print(f"  Min:      {min(pops):,}")
            print(f"  Max:      {max(pops):,}")
            print(f"  Mean:     {sum(pops)/len(pops):,.0f}")
            print(f"  Median:   {sorted(pops)[len(pops)//2]:,}")

    if surface_count > 0:
        surfaces = [f["properties"]["surface_predicted"] for f in features
                    if f["properties"].get("surface_predicted")]
        from collections import Counter
        counts = Counter(surfaces)
        print(f"\nSurface predictions:")
        for surface, count in counts.most_common(10):
            print(f"  {surface}: {count} ({count/len(surfaces)*100:.0f}%)")

    if paved_count > 0:
        paved_vals = [f["properties"]["pct_paved"] for f in features
                      if f["properties"].get("pct_paved") is not None]
        avg_paved = sum(paved_vals) / len(paved_vals)
        print(f"\nPaved percentage: {avg_paved:.0f}% average across matched segments")

    if feeder_count > 0:
        feeder_vals = [f["properties"]["feeder_road_km"] for f in features
                       if f["properties"].get("feeder_road_km") and f["properties"]["feeder_road_km"] > 0]
        if feeder_vals:
            print(f"\nFeeder road density (5km corridor):")
            print(f"  Non-zero: {len(feeder_vals)}/{feeder_count}")
            print(f"  Min:      {min(feeder_vals):,.1f} km")
            print(f"  Max:      {max(feeder_vals):,.1f} km")
            print(f"  Mean:     {sum(feeder_vals)/len(feeder_vals):,.1f} km")
            print(f"  Median:   {sorted(feeder_vals)[len(feeder_vals)//2]:,.1f} km")


def main():
    if not check_dependencies():
        sys.exit(1)

    t_start = time.time()
    geojson = load_base_geojson()
    geojson = enrich_with_kontur(geojson)
    geojson = enrich_with_heigit(geojson)
    geojson = enrich_with_edinburgh(geojson)

    print(f"\nWriting enriched GeoJSON: {ENRICHED_GEOJSON}")
    with open(ENRICHED_GEOJSON, "w") as f:
        json.dump(geojson, f)
    size_mb = os.path.getsize(ENRICHED_GEOJSON) / 1e6
    print(f"  Done ({size_mb:.1f} MB)")

    print_summary(geojson)
    print(f"\nTotal time: {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
