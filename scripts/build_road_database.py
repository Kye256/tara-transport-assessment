"""
One-time script to convert the HOT Export Uganda roads shapefile
into a filtered GeoJSON containing only named main roads.

Input:  data/hotosm_uga_roads.zip  (157MB shapefile, ~313k km of all roads)
Output: data/uganda_main_roads.geojson (named trunk/primary/secondary/tertiary only)

Usage: venv/bin/python scripts/build_road_database.py
"""

import geopandas as gpd
import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_PATH = os.path.join(BASE_DIR, "data", "hotosm_uga_roads.zip")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "uganda_main_roads.geojson")

MAIN_ROAD_CLASSES = {"trunk", "primary", "secondary", "tertiary",
                     "trunk_link", "primary_link", "secondary_link", "tertiary_link"}

KEEP_COLUMNS = ["osm_id", "name", "name_en", "highway", "surface",
                "width", "lanes", "smoothness", "bridge", "geometry"]


def main():
    if not os.path.exists(ZIP_PATH):
        print(f"ERROR: {ZIP_PATH} not found. Download it first.")
        sys.exit(1)

    print(f"Reading shapefile from {ZIP_PATH}...")
    gdf = gpd.read_file(f"zip://{ZIP_PATH}")
    print(f"  Total features: {len(gdf):,}")
    print(f"  Highway classes: {gdf['highway'].value_counts().to_dict()}")

    # Filter to main road classes
    gdf_main = gdf[gdf["highway"].isin(MAIN_ROAD_CLASSES)].copy()
    print(f"\n  After filtering to main classes: {len(gdf_main):,}")

    # Filter to named roads only
    gdf_named = gdf_main[gdf_main["name"].notna() & (gdf_main["name"] != "")].copy()
    print(f"  After filtering to named roads: {len(gdf_named):,}")

    # Keep only needed columns
    cols_present = [c for c in KEEP_COLUMNS if c in gdf_named.columns]
    gdf_out = gdf_named[cols_present].copy()

    # Ensure CRS is WGS84
    if gdf_out.crs and gdf_out.crs.to_epsg() != 4326:
        gdf_out = gdf_out.to_crs(epsg=4326)

    # Summary by class
    print("\n  Breakdown by highway class:")
    for cls, count in gdf_out["highway"].value_counts().items():
        print(f"    {cls}: {count:,}")

    # Save
    print(f"\n  Saving to {OUTPUT_PATH}...")
    gdf_out.to_file(OUTPUT_PATH, driver="GeoJSON")

    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"  Output size: {size_mb:.1f} MB")
    print(f"  Total roads: {len(gdf_out):,}")
    print("\nDone.")


if __name__ == "__main__":
    main()
