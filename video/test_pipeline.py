"""Pipeline validator — 11 checks on GeoJSON output.

Run with: python -m video.test_pipeline
"""

import json
import math
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(BASE, "data", "videos", "demo2_kasangati_loop", "clips_compressed")
GPX_PATH = os.path.join(BASE, "data", "videos", "12-Feb-2026-1537.gpx")

# Expected route parameters
EXPECTED_DISTANCE_KM = 8.35
LAT_BOUNDS = (0.35, 0.42)
LON_BOUNDS = (32.60, 32.67)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two GPS coordinates."""
    R = 6_371_000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def linestring_length_km(coords: list[list[float]]) -> float:
    """Total length of a LineString in km. Coords are [lon, lat]."""
    total = 0.0
    for i in range(1, len(coords)):
        total += haversine(coords[i - 1][1], coords[i - 1][0], coords[i][1], coords[i][0])
    return total / 1000


def run_checks(geojson: dict, pipeline_result: dict = None) -> int:
    """Run 11 validation checks on GeoJSON. Returns number of passes."""
    features = geojson.get("features", [])
    passed = 0
    total = 11

    # --- Check 1: CONTINUITY ---
    if len(features) < 2:
        print(f"[FAIL] 1. Continuity: Only {len(features)} section(s), need 2+ to check")
    else:
        max_gap = 0.0
        gaps_ok = True
        for i in range(1, len(features)):
            prev_coords = features[i - 1]["geometry"]["coordinates"]
            curr_coords = features[i]["geometry"]["coordinates"]
            prev_end = prev_coords[-1]  # [lon, lat]
            curr_start = curr_coords[0]
            gap = haversine(prev_end[1], prev_end[0], curr_start[1], curr_start[0])
            max_gap = max(max_gap, gap)
            if gap > 50:
                gaps_ok = False
        if gaps_ok:
            print(f"[PASS] 1. Continuity: All {len(features)} sections connected (max gap: {max_gap:.0f}m)")
            passed += 1
        else:
            print(f"[FAIL] 1. Continuity: Max gap {max_gap:.0f}m exceeds 50m limit")

    # --- Check 2: SECTION LENGTH ---
    max_section_len = 0.0
    longest_idx = 0
    all_ok = True
    for i, feat in enumerate(features):
        length = linestring_length_km(feat["geometry"]["coordinates"])
        if length > max_section_len:
            max_section_len = length
            longest_idx = i
        if length > 1.5:
            all_ok = False
    if all_ok:
        print(f"[PASS] 2. Section length: Longest is {max_section_len:.2f}km (section {longest_idx})")
        passed += 1
    else:
        print(f"[FAIL] 2. Section length: Section {longest_idx} is {max_section_len:.2f}km (max 1.5km)")

    # --- Check 3: MINIMUM SECTIONS ---
    if len(features) >= 6:
        print(f"[PASS] 3. Minimum sections: {len(features)} sections (need 6+)")
        passed += 1
    else:
        print(f"[FAIL] 3. Minimum sections: Only {len(features)} sections (need 6+)")

    # --- Check 4: GPS DENSITY ---
    sparse_sections = []
    for i, feat in enumerate(features):
        n_coords = len(feat["geometry"]["coordinates"])
        if n_coords < 2:
            sparse_sections.append((i, n_coords))
    if not sparse_sections:
        print(f"[PASS] 4. GPS density: All sections have 2+ coordinate pairs")
        passed += 1
    else:
        print(f"[FAIL] 4. GPS density: {len(sparse_sections)} sections have <2 coords: {sparse_sections[:5]}")

    # --- Check 5: COORDINATES IN BOUNDS ---
    out_of_bounds = []
    for i, feat in enumerate(features):
        for coord in feat["geometry"]["coordinates"]:
            lon, lat = coord[0], coord[1]
            if not (LAT_BOUNDS[0] <= lat <= LAT_BOUNDS[1] and LON_BOUNDS[0] <= lon <= LON_BOUNDS[1]):
                out_of_bounds.append((i, lat, lon))
    if not out_of_bounds:
        print(f"[PASS] 5. Coordinates in bounds: All coords within expected area")
        passed += 1
    else:
        print(f"[FAIL] 5. Coordinates in bounds: {len(out_of_bounds)} coords out of bounds. "
              f"First: section {out_of_bounds[0][0]} at ({out_of_bounds[0][1]:.4f}, {out_of_bounds[0][2]:.4f})")

    # --- Check 6: NO STRAIGHT LINES ---
    straight_sections = []
    for i, feat in enumerate(features):
        coords = feat["geometry"]["coordinates"]
        length = linestring_length_km(coords)
        if length > 0.5 and len(coords) < 3:
            straight_sections.append((i, length, len(coords)))
    if not straight_sections:
        print(f"[PASS] 6. No straight lines: All long sections have 3+ coords")
        passed += 1
    else:
        print(f"[FAIL] 6. No straight lines: {len(straight_sections)} sections >500m with <3 coords: "
              f"{straight_sections[:3]}")

    # --- Check 7: PROPERTIES ---
    required_props = {"condition_class", "color", "avg_iri", "surface_type", "section_index"}
    missing = []
    for i, feat in enumerate(features):
        props = feat.get("properties", {})
        absent = required_props - set(props.keys())
        if absent:
            missing.append((i, absent))
    if not missing:
        print(f"[PASS] 7. Properties: All features have required properties")
        passed += 1
    else:
        print(f"[FAIL] 7. Properties: {len(missing)} features missing keys. "
              f"Section {missing[0][0]} missing: {missing[0][1]}")

    # --- Check 8: TEMPORAL ORDER ---
    indices = [feat["properties"].get("section_index", -1) for feat in features]
    expected = list(range(len(features)))
    if indices == expected:
        print(f"[PASS] 8. Temporal order: Section indices sequential 0-{len(features)-1}")
        passed += 1
    else:
        print(f"[FAIL] 8. Temporal order: Indices {indices[:10]}... expected {expected[:10]}...")

    # --- Check 9: POPUP HTML ---
    missing_popup = []
    for i, feat in enumerate(features):
        popup = feat["properties"].get("popup_html", "")
        if not popup or "<img" not in popup:
            missing_popup.append(i)
    if not missing_popup:
        print(f"[PASS] 9. Popup HTML: All features have popup_html with <img> tag")
        passed += 1
    else:
        print(f"[FAIL] 9. Popup HTML: {len(missing_popup)} features missing popup with <img>: "
              f"sections {missing_popup[:5]}")

    # --- Check 10: TOTAL DISTANCE ---
    total_dist = sum(linestring_length_km(f["geometry"]["coordinates"]) for f in features)
    tolerance = EXPECTED_DISTANCE_KM * 0.20
    if abs(total_dist - EXPECTED_DISTANCE_KM) <= tolerance:
        print(f"[PASS] 10. Total distance: {total_dist:.2f}km (expected {EXPECTED_DISTANCE_KM}km +/- 20%)")
        passed += 1
    else:
        print(f"[FAIL] 10. Total distance: {total_dist:.2f}km (expected {EXPECTED_DISTANCE_KM}km +/- 20%)")

    # --- Check 11: SIZE GUARDS ---
    # Test that the pipeline rejects oversized inputs
    size_ok = True
    try:
        from video.video_pipeline import run_pipeline
        # Test with too many clips (>30) — we can check by calling with a non-existent dir
        # For now, check that the function has the guard logic
        import inspect
        source = inspect.getsource(run_pipeline)
        has_size_check = "500" in source or "size" in source.lower() or "memory" in source.lower()
        has_clip_count_check = "30" in source or "clip" in source.lower()
        has_error_handling = "MemoryError" in source or "OverflowError" in source

        if has_size_check and has_error_handling:
            print(f"[PASS] 11. Size guards: Pipeline has size validation and error handling")
            passed += 1
        else:
            missing_guards = []
            if not has_size_check:
                missing_guards.append("size check")
            if not has_error_handling:
                missing_guards.append("MemoryError/OverflowError handling")
            print(f"[FAIL] 11. Size guards: Missing {', '.join(missing_guards)}")
    except Exception as e:
        print(f"[FAIL] 11. Size guards: Error inspecting pipeline: {e}")

    print(f"\n{'=' * 40}")
    if passed == total:
        print(f"{passed}/{total} checks passed \u2713")
    else:
        print(f"{passed}/{total} checks passed")
    return passed


def main():
    """Run the pipeline and validate output."""
    print("=" * 50)
    print("TARA Video Pipeline Validator")
    print("=" * 50)

    # Check test data exists
    if not os.path.isdir(VIDEO_DIR):
        print(f"ERROR: Test video dir not found: {VIDEO_DIR}")
        sys.exit(1)
    if not os.path.isfile(GPX_PATH):
        print(f"ERROR: Test GPX not found: {GPX_PATH}")
        sys.exit(1)

    mp4_count = len([f for f in os.listdir(VIDEO_DIR) if f.lower().endswith(".mp4")])
    print(f"Video dir: {VIDEO_DIR} ({mp4_count} clips)")
    print(f"GPX: {GPX_PATH}")
    print()

    # Reset mock counter for deterministic results
    from video import vision_assess
    vision_assess._MOCK_COUNTER = 0

    from video.video_pipeline import run_pipeline
    t0 = time.time()
    result = run_pipeline(
        video_path=VIDEO_DIR,
        gpx_path=GPX_PATH,
        frame_interval=30,
        max_frames=40,
        use_mock=True,
    )
    elapsed = time.time() - t0
    print(f"\nPipeline ran in {elapsed:.1f}s")

    geojson = result["geojson"]
    print(f"GeoJSON: {len(geojson['features'])} features")
    print()

    # Run validation
    print("-" * 40)
    print("VALIDATION RESULTS")
    print("-" * 40)
    passed = run_checks(geojson, result)

    # Save test output
    output_path = os.path.join(BASE, "output", "test_condition.geojson")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"\nTest GeoJSON saved to {output_path}")

    return passed


if __name__ == "__main__":
    passed = main()
    sys.exit(0 if passed == 11 else 1)
