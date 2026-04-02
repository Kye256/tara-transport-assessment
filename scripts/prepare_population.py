"""
Pre-compute subcounty population from Kontur H3 hexagons.

For each UBOS subcounty polygon, sums Kontur population within it
(area-weighted for partial overlaps) and saves as JSON for fast runtime lookup.

Usage:
    venv/bin/python scripts/prepare_population.py

Output:
    data/subcounty_population.json
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
KONTUR_PATH = os.path.join(DATA_DIR, "kontur_uganda_population.gpkg")
SUBCOUNTY_PATH = os.path.join(
    DATA_DIR, "GoU_Data", "ShapeFiles", "2018", "Administrative", "Subcounties_2014_v3_UBOS.shp"
)
OUTPUT_PATH = os.path.join(DATA_DIR, "subcounty_population.json")


def main():
    start = time.time()

    print("Loading Kontur hexagons...")
    kontur = gpd.read_file(KONTUR_PATH).to_crs(epsg=4326)
    print(f"  {len(kontur)} hexagons loaded")

    print("Loading UBOS subcounties...")
    subcounties = gpd.read_file(SUBCOUNTY_PATH).to_crs(epsg=4326)
    print(f"  {len(subcounties)} subcounties loaded")

    print("Computing spatial joins...")
    # sjoin to find which hexagons overlap which subcounties
    joined = gpd.sjoin(kontur, subcounties, predicate="intersects")
    print(f"  {len(joined)} hex-subcounty intersections found")

    print("Computing area-weighted populations per subcounty...")
    result = {}
    total_sc = len(subcounties)

    for i, (_, sc_row) in enumerate(subcounties.iterrows()):
        sc_name = sc_row.get("SNAME2014", "Unknown")
        district = sc_row.get("DNAME2016", "Unknown")
        urban_val = str(sc_row.get("Urban_Stat", "")).strip().lower()
        is_urban = urban_val in ("urban", "city", "municipality", "town council", "1")
        sc_geom = sc_row.geometry

        # Get hexagons that overlap this subcounty
        hex_in_sc = joined[joined["index_right"] == sc_row.name]

        pop = 0.0
        for _, hex_row in hex_in_sc.iterrows():
            hex_geom = hex_row.geometry
            intersection = hex_geom.intersection(sc_geom)
            if intersection.is_empty:
                continue
            fraction = intersection.area / hex_geom.area if hex_geom.area > 0 else 0.0
            pop += hex_row["population"] * fraction

        key = f"{sc_name}|{district}"
        result[key] = {
            "subcounty": sc_name,
            "district": district,
            "population": int(round(pop)),
            "urban": is_urban,
            "ubos_2014_population": int(sc_row.get("Population", 0) or 0),
        }

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{total_sc} subcounties processed...")

    # Save
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    elapsed = time.time() - start
    total_kontur_pop = sum(v["population"] for v in result.values())
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  {len(result)} subcounties written to {OUTPUT_PATH}")
    print(f"  Total Kontur population assigned: {total_kontur_pop:,}")


if __name__ == "__main__":
    main()
