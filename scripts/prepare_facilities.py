"""
Prepare local facility GeoJSON files from source shapefiles.
One-time preprocessing — run this before starting the app.

Sources:
  Health, Schools, Water: gis_osm_pois_free_1.shp (Geofabrik OSM Uganda, 2026-03-31)
  Markets: Trading_Centres_UBOS.shp (UBOS, 2018) — official government data
"""

import os
import geopandas as gpd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
POIS_SHP = os.path.join(DATA_DIR, "uganda-260331-free.shp", "gis_osm_pois_free_1.shp")
TRADING_CENTRES_SHP = os.path.join(
    DATA_DIR, "GoU_Data", "ShapeFiles", "2018", "Settlements", "Trading_Centres_UBOS.shp"
)


def extract_pois(gdf: gpd.GeoDataFrame, fclass_list: list[str], category: str,
                 output_name: str) -> None:
    """Extract POIs by fclass, add category field, save as GeoJSON."""
    subset = gdf[gdf["fclass"].isin(fclass_list)].copy()
    subset = subset[["osm_id", "name", "fclass", "geometry"]].copy()
    subset["category"] = category
    subset = subset.dropna(subset=["geometry"])

    out_path = os.path.join(DATA_DIR, output_name)
    subset.to_file(out_path, driver="GeoJSON")

    print(f"\n=== {output_name} ===")
    print(f"Features: {len(subset)}")
    print(f"Bounding box: {subset.total_bounds}")
    print(f"fclass breakdown: {subset['fclass'].value_counts().to_dict()}")
    print(subset[["osm_id", "name", "fclass", "category"]].head(3).to_string())


def extract_markets() -> None:
    """Extract UBOS Trading Centres, reproject to WGS84, save as GeoJSON."""
    gdf = gpd.read_file(TRADING_CENTRES_SHP)

    # Reproject from EPSG:21096 (Arc 1960 / UTM zone 36N) to WGS84
    gdf = gdf.to_crs(epsg=4326)

    # Keep and rename fields
    out = gdf[["NAME", "DISTRICT", "POPULATION", "geometry"]].copy()
    out = out.rename(columns={"NAME": "name", "DISTRICT": "district", "POPULATION": "population"})
    out["category"] = "market"
    out["source"] = "UBOS Trading Centres 2018"
    out = out.dropna(subset=["geometry"])

    out_path = os.path.join(DATA_DIR, "uganda_markets.geojson")
    out.to_file(out_path, driver="GeoJSON")

    print(f"\n=== uganda_markets.geojson ===")
    print(f"Features: {len(out)}")
    print(f"Bounding box: {out.total_bounds}")
    print(out[["name", "district", "population", "category"]].head(3).to_string())


def main() -> None:
    print("Loading POIs shapefile...")
    pois = gpd.read_file(POIS_SHP)
    print(f"Loaded {len(pois)} POIs")

    # Health facilities
    extract_pois(pois, ["hospital", "clinic", "doctors", "pharmacy"],
                 "health", "uganda_health_facilities.geojson")

    # Schools / education
    extract_pois(pois, ["school", "college", "university", "kindergarten"],
                 "education", "uganda_schools.geojson")

    # Water points
    extract_pois(pois, ["drinking_water", "water_well", "water_tower"],
                 "water", "uganda_water_points.geojson")

    # Markets — from UBOS Trading Centres
    print("\nLoading Trading Centres shapefile...")
    extract_markets()

    print("\n\nDone. All facility GeoJSONs saved to data/")


if __name__ == "__main__":
    main()
