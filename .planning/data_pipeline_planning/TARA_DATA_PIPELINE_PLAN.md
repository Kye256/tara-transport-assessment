# TARA Data Pipeline Plan

**Created:** April 2, 2026  
**Purpose:** Phased data source acquisition and validation. Each phase gates the next. No phase starts until the previous gate is fully passed.

---

## Dead Sources (Confirmed 404 — Do Not Use)

- ~~`data.humdata.org/dataset/1958a079...`~~ — UNRA GeoJSON: gone
- ~~`data.humdata.org/dataset/uganda-road-network`~~ — WFP Uganda roads: gone

---

## Phase 1 — Roads

**Source:** Geofabrik Uganda shapefile  
**URL:** `https://download.geofabrik.de/africa/uganda-latest-free.shp.zip`  
**Status:** ✅ Confirmed live. Updated daily. ~1.1GB zip. Free. ODbL licensed.  
**Target layer:** `gis_osm_roads_free_1.shp` inside the zip.

### Fields available from Geofabrik roads layer

| Field needed    | Geofabrik provides                            | Gap                              |
| --------------- | --------------------------------------------- | -------------------------------- |
| Line geometry   | ✅ LineString in `gis_osm_roads_free_1.shp`    | None                             |
| Road name       | ✅ `name` field                                | Some roads unnamed in OSM        |
| Road class      | ✅ `fclass` (trunk/primary/secondary/tertiary) | Not UNRA A/B/C — needs mapping   |
| Surface type    | ✅ `surface` (asphalt/gravel/unpaved/etc.)     | Incomplete — many roads blank    |
| Length          | 🔧 Computed from geometry via GeoPandas       | Not stored — calculate at import |
| Width / lanes   | ❌ Not in free shapefile                       | Known gap                        |
| Condition / IRI | ❌ Not in base data                            | Comes from dashcam (TARA's job)  |

### UNRA classification mapping

```
trunk        → National Road (UNRA)
primary      → National Road (UNRA)
secondary    → District Road
tertiary     → District / Community Road
unclassified → Community Access Road
```

### Processing steps (one-time offline script)

- [x] Download zip (~1.1GB) from Geofabrik

- [x] Extract `gis_osm_roads_free_1.shp` from zip
- [x] Filter to: `fclass IN (trunk, primary, secondary, tertiary, unclassified)`
- [x] Filter to: roads WITH a name (`name IS NOT NULL AND name != ''`)
- [x] Calculate `length_km` from geometry using GeoPandas (project to UTM first)
- [x] Map `fclass` → `unra_class` using lookup table above
- [x] Save to `data/uganda_roads.geojson`

### Phase 1 gate — ALL must pass before starting Phase 2

- [ ] GeoJSON loads in Dash/Leaflet and roads render as **lines** (not points)
- [ ] Road name search returns real results (not "5th Street", "Access Road")
- [ ] Selecting a road returns: name, class, surface, length_km
- [ ] Main corridors visible and correct: Kampala–Jinja, Kampala–Gulu, Malaba–Kampala

---

## Phase 2 — Population

*(Do not start until Phase 1 gate is fully passed)*

**Source:** WorldPop 2020 Uganda, constrained, UN-adjusted  
**URL:** `https://data.humdata.org/dataset/worldpop-population-counts-for-uganda`  
**File to download:** `uga_ppp_2020_UNadj.tif`  
**Status:** ✅ Confirmed accessible on HDX, no login required, ~60MB GeoTiff.

**Key principle:** Do NOT query the raster at runtime. Pre-compute everything offline.

### Processing steps (one-time offline script)

- [ ] Download `uga_ppp_2020_UNadj.tif` from HDX
- [ ] Load UBOS subcounty polygons (already local)
- [ ] For each subcounty: sum WorldPop pixel values within polygon → population estimate
- [ ] Save as `data/subcounty_population.json` (lookup by subcounty name/ID)
- [ ] Write `get_population_in_buffer(geometry, radius_km)` — queries local GeoTiff, not live API

### Phase 2 gate — ALL must pass before starting Phase 3

- [ ] Given a road geometry + 5km buffer, returns a population figure
- [ ] Figure cross-checks reasonably against known benchmarks:
  - Wakiso District corridor: ~2 million
  - Gulu District corridor: ~500k
- [ ] No runtime latency — lookup from pre-computed file

---

## Phase 3 — Facilities

*(Do not start until Phase 2 gate is fully passed)*

**Sources:**

- Health facilities: HOT OSM Uganda — `https://data.humdata.org/dataset/hotosm_uga_health_facilities`
- Schools + markets: Geofabrik POI layer — `gis_osm_pois_free_1.shp` (already in the Phase 1 download)

**This replaces the Overpass API entirely. No 504 timeouts. No live dependency.**

### Processing steps (one-time offline script)

- [ ] Download HOT Uganda health facilities GeoJSON → `data/uganda_health_facilities.geojson`
- [ ] Extract schools from Geofabrik POI layer (`fclass = 'school'`) → `data/uganda_schools.geojson`
- [ ] Extract markets from Geofabrik POI layer (`fclass IN ('marketplace', 'supermarket')`) → `data/uganda_markets.geojson`
- [ ] Write `get_facilities_near_road(geometry, radius_km, types)` — spatial query from local files

### Phase 3 gate

- [ ] Given a road geometry + buffer, returns counts of health facilities, schools, markets
- [ ] Results are plausible for known corridors (e.g., Kampala–Jinja should show many facilities)
- [ ] No live API calls anywhere in the facility pipeline

---

## Overall gate summary

```
Phase 1: Roads        → lines on map, named search, length/class/surface
         ↓ (gate passed)
Phase 2: Population   → buffer population, cross-checked against district totals
         ↓ (gate passed)  
Phase 3: Facilities   → health/school/market counts from local cache, no Overpass
         ↓ (gate passed)
→ Integrate into TARA Milestone 1
```

---

## Notes

- All sources must be stored locally. No live API calls for base data in Milestone 1.
- Length is always calculated from geometry, never trusted from a source field.
- Surface type from OSM will be incomplete — that is expected and acceptable. TARA's dashcam fills this gap.
- WorldPop data is 2020. This is the most current gridded dataset available for Uganda. UBOS 2024 census projections provide the national total check.
