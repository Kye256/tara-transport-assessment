# TARA Data Pipeline Plan
**Created:** April 2, 2026
**Last updated:** April 2, 2026 — post full repo audit
**Purpose:** Phased data source acquisition and validation. Each phase gates the next.

---

## Critical Finding: Almost Everything Is Already Local

A full repo audit confirmed that TARA has sufficient data for Phases 1–3 entirely
from local files. No new downloads required before integration work begins.
The live Overpass API call is completely redundant and must be removed.

---

## Dead Sources — Do Not Use
- ~~`data.humdata.org/dataset/1958a079...`~~ — UNRA GeoJSON on HDX: 404 gone
- ~~`data.humdata.org/dataset/uganda-road-network`~~ — WFP Uganda roads: 404 gone
- ~~`unra_road_network.geojson`~~ — failed download, file is HTML not GeoJSON, delete it
- ~~Live Overpass API (`overpass-api.de`)~~ — replaced entirely by local Geofabrik POI files

---

## Data Source Architecture

```
Uganda roads:        UNRA official GIS files (local)              → PRIMARY
Uganda health:       Geofabrik POI layer — hospital/clinic (local) → PRIMARY (replaces Overpass)
Uganda schools:      OSM POI layer — school (local, 24,163)        → PRIMARY (more coverage than GoU 6,371)
Uganda markets:      UBOS Trading Centres (local, 2,866)           → PRIMARY (5x OSM coverage, official)
Uganda water:        Geofabrik POI layer — water points (local)    → PRIMARY
Uganda population:   Kontur H3 grid (local) + WorldPop raster      → PRIMARY
Uganda poverty:      Ug_Rural-Poverty2005.shp (local)              → PRIMARY for equity scoring
Other countries:     Geofabrik OSM extract                         → FALLBACK only
NHFR API:           nhfr.health.go.ug/api/orgunits                → UPGRADE path for health (needs credentials)
GoU School_Geo.shp: SPATIAL_DATA_FRAMEWORK/SocioEnvironmental/    → REFERENCE only (sparse attributes)
```

---

## Complete Local Data Inventory

### Roads

| File | Features | Key fields | Use |
|---|---|---|---|
| `uganda_roads.geojson` (from Links_Jun13.shp) | 883 | road_id, name, road_ref, unra_class, surface, length_km | ✅ Primary road network — in use |
| `SPATIAL_DATA_FRAMEWORK/RoadNetwork/SECTIONS.shp` | 1,190 | SECTION_ID, ROAD_CLASS, ROAD_NAME, LENGTH, DIRECTION | 🔍 Finer granularity — evaluate for upgrade |
| `UNRA_Mapping/Network/ROADS.shp` | 597 | ROAD_NAME, LENGTH, ROAD_CLASS, **AADT**, Ave_Elevat | ⭐ Has traffic counts — join to road network |
| `gis_osm_roads_free_1.shp` (Geofabrik) | 672,347 | fclass, name, ref, bridge, tunnel | Fallback for non-Uganda countries |
| `uganda_main_roads_enriched.geojson` | 2,396 | name, highway, pop_5km, surface_predicted, pct_paved | Hackathon artefact — superseded |
| `heigit_uga_roadsurface_lines.gpkg` | 803,716 | pred_class, pred_label, surface | ML surface predictions — Milestone 2 enrichment |

### Facilities

| File | Features | Key fields | Use |
|---|---|---|---|
| `gis_osm_pois_free_1.shp` (fclass=school) | 24,163 | name | ✅ Schools — replaces Overpass |
| `gis_osm_pois_free_1.shp` (hospital+clinic+doctors) | 6,389 | name, fclass | ✅ Health — replaces Overpass |
| `gis_osm_pois_free_1.shp` (fclass=market_place) | 574 | name | ✅ Markets — replaces Overpass |
| `gis_osm_pois_free_1.shp` (drinking_water+water_well) | 3,974 | name | ✅ Water points — replaces Overpass |
| `SPATIAL_DATA_FRAMEWORK/SocioEnvironmental/School_Geo.shp` | 6,371 | NAME1_, NAME2_ | ⭐ Official GoU schools — inspect for upgrade |
| `2018/Settlements/Trading_Centres_UBOS.shp` | 2,866 | NAME, DISTRICT, POPULATION, POWER_SUPP | ⭐ Better market proxy than OSM 574 points |
| `UNRA_Mapping/Bridges/Brigdes_UTM.shp` | 217 | BRIDGE_NAM, ROAD, CHAINAGE | Corridor analysis, cost estimation |
| `gis_osm_transport_free_1.shp` | 496 | fclass, name | Transport hubs |
| `gis_osm_traffic_free_1.shp` (fclass=fuel) | 1,169 | name | VOC analysis |

### Traffic

| File | Features | Key fields | Use |
|---|---|---|---|
| `UNRA_Mapping/Network/ROADS.shp` | 597 | ROAD_NAME, AADT | ⭐ Baseline AADT — join to road network |
| `UNRA_Mapping/Traffic/Traffic.shp` | 155 | ROAD_NO, ADT_MOTORI, STATION | Traffic count stations |
| `Roads/KampalaJinja.csv` | 32 rows | road_name, adt, start/end lat/lon | A001 corridor ADT per section |

### Population

| File | Features | Key fields | Use |
|---|---|---|---|
| `worldpop/uga_ppp_2020.tif` | Raster 6515×6856 ~100m | population per pixel | ✅ Phase 2 primary — corridor buffer analysis |
| `kontur_uganda_population.gpkg` | 182,094 H3 hexagons | h3, population | ✅ Pre-gridded alternative to WorldPop raster |
| `2018/Admin/Subcounties_2014_v3_UBOS.shp` | 1,378 | SNAME2014, Population, Households, Urban_Stat | ✅ Phase 2 admin zones |
| `2018/Admin/Districts_2016_UBOS.shp` | 116 | DNAME2016, Population, Households | Reference/validation |
| `SocioEnvironmental/Population_LC3.shp` | 808 | LC3_NAME, TOTPOP91 | Too old (1991) — do not use |

### Equity & Poverty

| File | Features | Key fields | Use |
|---|---|---|---|
| `Ug_Rural-Poverty2005.shp` | 958 | FGT0, FGT1, FGT2, GINI | ⭐ Equity scoring — poverty headcount/gap/severity |
| `Ug_Safe-water-coverage2008.shp` | 958 | Cvrg2008 | Equity scoring — water access |

### Administrative Boundaries

| File | Features | Key fields | Use |
|---|---|---|---|
| `2018/Admin/Districts_2016_UBOS.shp` | 116 | DNAME2016, REGION, SUBREGION | Reference |
| `2018/Admin/Subcounties_2014_v3_UBOS.shp` | 1,378 | SNAME2014, DNAME2014, Urban_Stat | Phase 2 zones |
| `2018/Settlements/Towns_2016_UBOS.shp` | 197 | Town_Name, Population | Reference |
| `2018/Settlements/Trading_Centres_UBOS.shp` | 2,866 | NAME, DISTRICT, POPULATION | Markets proxy |

### Other

| File | Features | Key fields | Use |
|---|---|---|---|
| `2018/Energy_Utilities/Distribution_Lines*.shp` | 144,642 | Voltage, Status, Operator | Grid proximity — Milestone 2+ |
| `SocioEnvironmental/Land_Cover.shp` | 49,874 | COVER_TYPE, WETNESS | Milestone 2+ |

---

## Known Data Issues

- **CRS chaos:** Files use EPSG:32636, EPSG:21096, EPSG:4326, EPSG:3857, and many have no CRS. Every processing script must explicitly set/reproject CRS — never assume.
- **22 of 26 root-level 2017 shapefiles have empty .dbf files** — geometry only, no attributes. The same data with attributes lives in `SPATIAL_DATA_FRAMEWORK/` or `UNRA_Mapping/` subdirectories. Always use those.
- **UNRA data is 2013.** Network has changed. Flag to users.
- **Poverty data is 2005, water coverage is 2008.** Old but best available spatial poverty data for Uganda. Use with disclosure.
- **School_Geo.shp has only NAME1_, NAME2_** — no school type or level. OSM has 4x more coverage (24,163 vs 6,371). Decision needed on which to use.

---

## Phase 1 — Roads ✅ COMPLETE

**Output:** `data/uganda_roads.geojson` — 883 UNRA links, processed from Links_Jun13.shp

### Phase 1 gate
- [ ] Renders as lines in Dash/Leaflet (not points) — **confirmed working**
- [ ] Road name search returns UNRA segment names — **confirmed working**
- [ ] Selecting a road returns name, road_ref, unra_class, surface, length_km — **confirmed working**
- [ ] C-roads visible (district coverage) — **confirmed, 724 C-road links**

### Phase 1 follow-on work (not blocking Phase 2)
- [ ] Evaluate `SECTIONS.shp` (1,190 features) vs `Links_Jun13` (883) — is finer granularity worth migrating?
- [ ] Join `UNRA_Mapping/Network/ROADS.shp` AADT to road network — surface baseline traffic counts in UI
- [ ] Fix tooltip HTML rendering (raw `<b>`, `<br>` tags showing as text)
- [ ] Delete `unra_road_network.geojson` (corrupt HTML file)

---

## Phase 2 — Population
*(Do not start until Phase 1 gate is fully passed)*

**Two options — both local, no download needed:**

**Option A: WorldPop raster** (`worldpop/uga_ppp_2020.tif`)
- 100m resolution, 2020, UN-adjusted
- Best for corridor buffer analysis (sum pixels within buffer)
- Requires rasterio processing

**Option B: Kontur H3 grid** (`kontur_uganda_population.gpkg`)
- 182,094 pre-gridded H3 hexagons with population
- Faster spatial queries — no raster processing needed
- Resolution roughly equivalent to WorldPop

**Recommendation:** Use Kontur for runtime queries (fast), WorldPop as validation reference.

### Processing steps
- [ ] Load Kontur H3 GeoPackage — confirm it loads and covers Uganda
- [ ] Write `get_population_in_buffer(geometry, radius_km)` using Kontur H3 spatial filter
- [ ] Validate output against UBOS district totals (Districts_2016_UBOS.shp has Population field)
- [ ] Pre-compute subcounty population from WorldPop raster as a secondary check

### Phase 2 gate — ALL must pass before starting Phase 3
- [ ] Given a road geometry + 5km buffer, returns a population figure
- [ ] Cross-checks against known benchmarks:
  - Wakiso District: ~2 million
  - Gulu District: ~500k
- [ ] No runtime latency — all from local files

---

## Phase 3 — Facilities
*(Do not start until Phase 2 gate is fully passed)*

**All facility data is already local in Geofabrik POI files. No downloads needed.**
**Primary task: replace live Overpass API call with local file queries.**

### The change
- **Remove:** `skills/osm_facilities.py` live Overpass call at lines 138-145
- **Replace with:** spatial filter on pre-loaded local GeoJSON files
- **App behaviour:** identical — same output structure, same map rendering

### Source decisions (final)

| Facility type | Source | File | Features | Rationale |
|---|---|---|---|---|
| Health | OSM Geofabrik POI | `gis_osm_pois_free_1.shp` (hospital+clinic+doctors) | 6,389 | Best available until NHFR credentials obtained |
| Schools | OSM Geofabrik POI | `gis_osm_pois_free_1.shp` (fclass=school) | 24,163 | 4x more coverage than GoU School_Geo.shp (6,371) |
| Markets | UBOS Trading Centres | `2018/Settlements/Trading_Centres_UBOS.shp` | 2,866 | 5x OSM coverage (574), official source, has population |
| Water points | OSM Geofabrik POI | `gis_osm_pois_free_1.shp` (drinking_water+water_well) | 3,974 | Best available |

### Processing steps
- [ ] Extract health from `gis_osm_pois_free_1.shp` → `data/uganda_health_facilities.geojson`
- [ ] Extract schools from `gis_osm_pois_free_1.shp` → `data/uganda_schools.geojson`
- [ ] Process `Trading_Centres_UBOS.shp` → `data/uganda_markets.geojson` (reproject to WGS84, standardise fields)
- [ ] Extract water points from `gis_osm_pois_free_1.shp` → `data/uganda_water_points.geojson`
- [ ] Rewrite `find_facilities()` in `skills/osm_facilities.py`:
  - Load all four GeoJSONs at app startup into memory (not per query)
  - Replace Overpass HTTP call with in-memory bbox spatial filter
  - Return same data structure — `_build_facilities()` in `output/maps.py` must need no changes
  - Add `source` field to each facility for data attribution

### Phase 3 gate
- [ ] Road selection returns facility counts with no Overpass call
- [ ] Works offline — no internet required for facility data
- [ ] Health, schools, markets, water all showing correctly
- [ ] No regression in map rendering

---

## Upgrade Path (Post Milestone 1)

### NHFR API — health facility upgrade
- **URL:** `https://nhfr.health.go.ug/api/orgunits?level=6&status=Functional`
- **Auth:** HTTP Basic Authentication required — request credentials from MoH
- **Value:** HC I–IV level classification per facility — critical for accessibility scoring
- **Action:** Request API credentials. When obtained, replace OSM health layer with NHFR data.
- **Key fields:** name, latitude, longitude, facility_level (HC II/III/IV/Hospital), status, district, subcounty

### UNRA AADT join — traffic data upgrade
- Join `UNRA_Mapping/Network/ROADS.shp` AADT to `uganda_roads.geojson` by road reference
- Surface baseline traffic in Step 1 UI — engineers see existing ADT when selecting a road
- Reduces manual data entry for well-monitored corridors

### HeiGIT surface predictions — surface type upgrade
- `heigit_uga_roadsurface_lines.gpkg` has ML surface predictions for 803,716 road segments
- Join to UNRA network to fill blank surface fields
- Milestone 2 task

### Poverty/equity integration
- `Ug_Rural-Poverty2005.shp` — FGT0/FGT1/FGT2/Gini at subcounty level
- `Ug_Safe-water-coverage2008.shp` — water access rates
- Feed into equity-weighted NPV calculation
- Milestone 2 task

---

## Overall Gate Summary

```
Phase 1: Roads        → ✅ COMPLETE
         ↓
Phase 2: Population   → Kontur H3 buffer query, validated against UBOS  [ ]
         ↓
Phase 3: Facilities   → Overpass replaced, all local, no regression      [ ]
         ↓
→ Integrate into TARA Milestone 1
```
