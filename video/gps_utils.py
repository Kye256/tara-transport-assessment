"""GPX parsing and GPS-to-frame matching utilities."""

import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


GPX_NS = "{http://www.topografix.com/GPX/1/1}"


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000  # Earth radius in metres
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_gpx(gpx_path: str) -> list[dict]:
    """Parse GPX file, extract trackpoints with lat, lon, elevation, time."""
    tree = ET.parse(gpx_path)
    root = tree.getroot()

    trackpoints = []
    for trkpt in root.iter(f"{GPX_NS}trkpt"):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])

        ele_el = trkpt.find(f"{GPX_NS}ele")
        elevation = float(ele_el.text) if ele_el is not None else None

        time_el = trkpt.find(f"{GPX_NS}time")
        time_obj = None
        if time_el is not None:
            ts = time_el.text.replace("Z", "+00:00")
            time_obj = datetime.fromisoformat(ts)

        trackpoints.append({
            "lat": lat,
            "lon": lon,
            "elevation": elevation,
            "time": time_obj,
        })

    return trackpoints


def parse_gpx_folder(gpx_path: str) -> list[dict]:
    """Parse all GPX files in a directory, combine trackpoints chronologically.

    Args:
        gpx_path: path to a single .gpx file or a directory containing .gpx files.

    Returns: combined list of trackpoints sorted by time.
    """
    if os.path.isfile(gpx_path):
        return parse_gpx(gpx_path)

    if not os.path.isdir(gpx_path):
        raise FileNotFoundError(f"GPX path not found: {gpx_path}")

    gpx_files = sorted(
        f for f in os.listdir(gpx_path)
        if f.lower().endswith(".gpx")
    )

    if not gpx_files:
        raise FileNotFoundError(f"No GPX files found in: {gpx_path}")

    print(f"  Found {len(gpx_files)} GPX files in {gpx_path}")

    all_trackpoints = []
    for gpx_file in gpx_files:
        full_path = os.path.join(gpx_path, gpx_file)
        tps = parse_gpx(full_path)
        all_trackpoints.extend(tps)
        print(f"    {gpx_file}: {len(tps)} trackpoints")

    # Sort by time (None times go to end)
    all_trackpoints.sort(key=lambda tp: tp["time"].timestamp() if tp["time"] else float("inf"))
    return all_trackpoints


def match_frames_to_gps(
    frames: list[dict],
    trackpoints: list[dict],
    video_start_time: str = None,
    utc_offset_hours: int = 3,
) -> list[dict]:
    """Match each frame to a GPS coordinate by timestamp interpolation.

    Args:
        frames: output from extract_frames()
        trackpoints: output from parse_gpx()
        video_start_time: local time string "2026-02-12 14:18:00" (optional)
        utc_offset_hours: local timezone offset from UTC (Uganda = 3)

    Returns: frames list with added lat, lon, elevation keys.
    """
    if not trackpoints:
        return frames

    tz_local = timezone(timedelta(hours=utc_offset_hours))

    # Determine video start in UTC
    if video_start_time:
        local_dt = datetime.strptime(video_start_time, "%Y-%m-%d %H:%M:%S")
        local_dt = local_dt.replace(tzinfo=tz_local)
        start_utc = local_dt.astimezone(timezone.utc)
    else:
        # Use first trackpoint time (already UTC) + offset as approximate start
        start_utc = trackpoints[0]["time"]

    # Pre-compute trackpoint UTC timestamps in seconds since epoch
    tp_times = []
    for tp in trackpoints:
        if tp["time"] is not None:
            tp_times.append(tp["time"].timestamp())
        else:
            tp_times.append(None)

    start_epoch = start_utc.timestamp()

    for frame in frames:
        frame_epoch = start_epoch + frame["timestamp_sec"]
        lat, lon, ele = _interpolate_gps(frame_epoch, trackpoints, tp_times)
        frame["lat"] = lat
        frame["lon"] = lon
        frame["elevation"] = ele

    return frames


def _interpolate_gps(
    target_epoch: float,
    trackpoints: list[dict],
    tp_times: list[float],
) -> tuple[float, float, float | None]:
    """Find the two nearest trackpoints and linearly interpolate."""
    best_idx = 0
    best_diff = abs(tp_times[0] - target_epoch) if tp_times[0] else float("inf")

    for i, t in enumerate(tp_times):
        if t is None:
            continue
        diff = abs(t - target_epoch)
        if diff < best_diff:
            best_diff = diff
            best_idx = i

    # Find neighbor for interpolation
    if best_idx == 0:
        neighbor = 1
    elif best_idx == len(trackpoints) - 1:
        neighbor = best_idx - 1
    else:
        # Pick the neighbor on the side closer to the target
        diff_prev = abs(tp_times[best_idx - 1] - target_epoch) if tp_times[best_idx - 1] else float("inf")
        diff_next = abs(tp_times[best_idx + 1] - target_epoch) if tp_times[best_idx + 1] else float("inf")
        neighbor = best_idx - 1 if diff_prev < diff_next else best_idx + 1

    t1 = tp_times[best_idx]
    t2 = tp_times[neighbor]
    if t1 is None or t2 is None or t1 == t2:
        tp = trackpoints[best_idx]
        return tp["lat"], tp["lon"], tp["elevation"]

    # Interpolation factor
    frac = (target_epoch - t1) / (t2 - t1)
    frac = max(0.0, min(1.0, frac))  # clamp

    tp1 = trackpoints[best_idx]
    tp2 = trackpoints[neighbor]
    lat = tp1["lat"] + frac * (tp2["lat"] - tp1["lat"])
    lon = tp1["lon"] + frac * (tp2["lon"] - tp1["lon"])

    ele = None
    if tp1["elevation"] is not None and tp2["elevation"] is not None:
        ele = tp1["elevation"] + frac * (tp2["elevation"] - tp1["elevation"])

    return lat, lon, ele
