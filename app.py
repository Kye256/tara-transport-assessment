"""
TARA: Transport Assessment & Road Appraisal
Main Dash Application — 7-step wizard with persistent map.

"From road data to investment decision — in minutes, not months."
"""

import json
import os
import base64
import copy
import tempfile
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ctx, ALL, ClientsideFunction
import dash_bootstrap_components as dbc
import dash_leaflet as dl

load_dotenv()

from config.parameters import (
    EOCK,
    ANALYSIS_PERIOD,
    BASE_YEAR,
    DEFAULT_TRAFFIC_GROWTH_RATE,
    DEFAULT_CONSTRUCTION_YEARS,
    VEHICLE_CLASSES,
    VEHICLE_CLASS_LABELS,
    CONSTRUCTION_COST_BENCHMARKS,
    MAINTENANCE_COSTS,
    SENSITIVITY_VARIABLES,
)

# ============================================================
# App Setup
# ============================================================

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Source+Sans+3:wght@400;600;700&"
    "family=DM+Mono:wght@400;500&"
    "family=Libre+Franklin:wght@600;700&"
    "display=swap"
)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, GOOGLE_FONTS_URL],
    suppress_callback_exceptions=True,
    title="TARA — Transport Assessment & Road Appraisal",
)
server = app.server
server.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024 * 1024  # 3 GB

STEP_LABELS = [
    "Select Road",
    "Condition",
    "Traffic",
    "Costs",
    "Results",
    "Sensitivity",
    "Report",
]

# Default Uganda traffic split
DEFAULT_SPLIT = {"Cars": 0.55, "Buses_LGV": 0.25, "HGV": 0.15, "Semi_Trailers": 0.05}
DEFAULT_ADT = 3000

# CartoDB Positron tile URL
TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
TILE_ATTR = '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'


# ============================================================
# Helpers
# ============================================================

def _metric_card(title: str, value: str, color: str = "primary") -> html.Div:
    """Build a small metric display using TARA CSS classes."""
    css_class = {
        "success": "positive",
        "danger": "negative",
        "warning": "warning",
        "info": "info",
        "primary": "",
    }.get(color, "")
    return html.Div([
        html.Div(title, className="tara-metric-label"),
        html.Div(value, className=f"tara-metric-value {css_class}"),
    ], className="tara-metric")


def _make_serializable(obj):
    """Make an object JSON-serializable for dcc.Store."""
    if obj is None:
        return None
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return json.loads(json.dumps(obj, default=str))


# ============================================================
# Step Indicator
# ============================================================

def make_step_indicator(active_step: int = 1) -> html.Div:
    """Build a segmented step bar (1-7)."""
    segments = []
    for i, label in enumerate(STEP_LABELS, 1):
        if i < active_step:
            cls = "tara-step-segment completed"
        elif i == active_step:
            cls = "tara-step-segment active"
        else:
            cls = "tara-step-segment"

        segments.append(
            html.Div(f"{i}. {label}", className=cls)
        )

    return html.Div(segments, className="tara-step-bar")


# ============================================================
# Step Content Builders
# ============================================================

def _build_road_dropdown_options() -> list[dict]:
    """Pre-load road dropdown options from local database."""
    from skills.road_database import list_all_roads
    return [{"label": r["label"], "value": r["id"]} for r in list_all_roads()]


def build_step1():
    return dbc.Card(dbc.CardBody([
        html.H5("Select Road", className="tara-heading"),
        html.P("Choose a road from the Uganda UNRA network.", className="text-muted"),
        dcc.Dropdown(
            id="road-select-dropdown",
            options=_build_road_dropdown_options(),
            placeholder="Type to search roads...",
            searchable=True,
            className="mb-3",
        ),
        dcc.Loading(type="circle", children=html.Div(id="road-search-result")),
    ]), className="mb-3")


def build_step2():
    return dbc.Card(dbc.CardBody([
        html.H5("Road Condition", className="tara-heading"),
        html.P("Describe the current road condition.", className="text-muted"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Surface Type"),
                dbc.Select(
                    id="surface-type-select",
                    options=[
                        {"label": "Asphalt", "value": "asphalt"},
                        {"label": "Gravel", "value": "gravel"},
                        {"label": "Earth/Dirt", "value": "earth"},
                        {"label": "Concrete", "value": "concrete"},
                        {"label": "Compacted", "value": "compacted"},
                    ],
                    value="gravel",
                ),
            ], md=6),
            dbc.Col([
                dbc.Label("Condition Rating"),
                dbc.Select(
                    id="condition-rating-select",
                    options=[
                        {"label": "Good (IRI 2-4)", "value": "good"},
                        {"label": "Fair (IRI 4-8)", "value": "fair"},
                        {"label": "Poor (IRI 8-14)", "value": "poor"},
                        {"label": "Very Poor (IRI 14+)", "value": "very_poor"},
                    ],
                    value="poor",
                ),
            ], md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("IRI (m/km) \u2014 optional override"),
                dbc.Input(id="iri-input", type="number", placeholder="e.g. 10",
                          min=1, max=30, step=0.5),
            ], md=6),
        ], className="mb-3"),
        html.Hr(),
        html.P("Or upload a dashcam image/video:", className="text-muted"),
        dcc.Upload(
            id="dashcam-upload",
            children=dbc.Button("Upload Dashcam File", color="outline-secondary", size="sm"),
            accept=".jpg,.jpeg,.png,.mp4,.avi,.mov",
            className="mb-2",
        ),
        html.Div(id="dashcam-result"),
        html.Hr(),
        html.P("Or run full video + GPS analysis:", className="text-muted fw-bold"),
        dbc.Row([
            dbc.Col([
                dcc.Dropdown(
                    id="video-preset-dropdown",
                    options=[
                        {"label": "Kasangati loop (42 clips, compressed)", "value": "demo2"},
                    ],
                    placeholder="Select a preset dataset...",
                    className="mb-2",
                ),
            ], md=8),
            dbc.Col([
                dbc.Button("Run Video Analysis", id="run-video-btn",
                           className="tara-btn-amber", size="sm", disabled=True),
            ], md=4),
        ], className="mb-2"),
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    id="video-path-input",
                    placeholder="Video folder or file path",
                    size="sm",
                    type="text",
                ),
            ], md=6),
            dbc.Col([
                dbc.Input(
                    id="gpx-path-input",
                    placeholder="GPX file or folder path",
                    size="sm",
                    type="text",
                ),
            ], md=6),
        ], className="mb-2"),
        # Hidden upload components (preserve IDs for other callbacks)
        dcc.Upload(id="dashcam-video-upload", style={"display": "none"}),
        dcc.Upload(id="gpx-upload", style={"display": "none"}),
        html.Div(id="video-upload-status", className="mb-2"),
        dcc.Loading(type="default", children=html.Div(id="video-pipeline-result")),
    ]), className="mb-3")


def build_step3():
    # Build vehicle class breakdown as an HTML table
    header = html.Thead(html.Tr([
        html.Th("Class"),
        html.Th("ADT"),
        html.Th("Share %"),
    ]))

    rows = []
    for vc in VEHICLE_CLASSES:
        label = VEHICLE_CLASS_LABELS[vc]
        pct = DEFAULT_SPLIT[vc]
        adt_val = int(DEFAULT_ADT * pct)
        rows.append(html.Tr([
            html.Td(label),
            html.Td(
                dbc.Input(id={"type": "traffic-adt", "vc": vc}, type="number",
                          value=adt_val, min=0, step=10, size="sm"),
            ),
            html.Td(
                dbc.Input(id={"type": "traffic-pct", "vc": vc}, type="number",
                          value=round(pct * 100, 1), min=0, max=100, step=0.1, size="sm"),
            ),
        ]))

    return dbc.Card(dbc.CardBody([
        html.H5("Traffic", className="tara-heading"),
        html.P("Enter average daily traffic by vehicle class.", className="text-muted"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Total ADT (vehicles/day)"),
                dbc.Input(id="total-adt-input", type="number",
                          value=DEFAULT_ADT, min=100, step=100),
            ], md=6),
            dbc.Col([
                dbc.Label("Growth Rate (% p.a.)"),
                dbc.Input(id="growth-rate-input", type="number",
                          value=round(DEFAULT_TRAFFIC_GROWTH_RATE * 100, 1),
                          min=0, max=15, step=0.1),
            ], md=6),
        ], className="mb-3"),
        html.Table([header, html.Tbody(rows)], className="tara-table"),
        html.Div(id="traffic-warnings"),
    ]), className="mb-3")


def build_step4():
    return dbc.Card(dbc.CardBody([
        html.H5("Costs", className="tara-heading"),
        html.P("Enter project costs and timing.", className="text-muted"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Total Construction Cost (USD)"),
                dbc.Input(id="total-cost-input", type="number",
                          value=5_000_000, min=100_000, step=100_000),
            ], md=6),
            dbc.Col([
                dbc.Label("Cost per km (auto-calculated)"),
                html.Div(id="cost-per-km-display", className="form-control-plaintext"),
            ], md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Construction Period (years)"),
                dbc.Input(id="construction-years-input", type="number",
                          value=DEFAULT_CONSTRUCTION_YEARS, min=1, max=10, step=1),
            ], md=6),
            dbc.Col([
                dbc.Label("Discount Rate (%)"),
                dbc.Input(id="discount-rate-input", type="number",
                          value=round(EOCK * 100, 1), min=1, max=25, step=0.5),
            ], md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Analysis Period (years)"),
                dbc.Input(id="analysis-period-input", type="number",
                          value=ANALYSIS_PERIOD, min=10, max=40, step=1),
            ], md=6),
            dbc.Col([
                dbc.Label("Base Year"),
                dbc.Input(id="base-year-input", type="number",
                          value=BASE_YEAR, min=2020, max=2035, step=1),
            ], md=6),
        ], className="mb-3"),
        html.Div(id="cost-warnings"),
    ]), className="mb-3")


def build_step5():
    return dbc.Card(dbc.CardBody([
        html.H5("Results", className="tara-heading"),
        html.P("Run the cost-benefit analysis.", className="text-muted"),
        dbc.Button("Run Appraisal", id="run-cba-btn", className="tara-btn-amber mb-3",
                    size="lg"),
        dcc.Loading(type="default", children=html.Div(id="cba-results-area")),
    ]), className="mb-3")


def build_step6():
    return dbc.Card(dbc.CardBody([
        html.H5("Sensitivity Analysis", className="tara-heading"),
        html.P("Adjust parameters and see how results change.", className="text-muted"),
        html.Div(id="sensitivity-controls"),
        dcc.Loading(type="default", children=html.Div(id="sensitivity-results-area")),
        html.Hr(),
        dbc.Button("AI Interpretation", id="ai-interpret-btn", color="outline-info",
                    size="sm", className="mb-2"),
        dcc.Loading(type="circle", children=html.Div(id="ai-narrative")),
    ]), className="mb-3")


def build_step7():
    return dbc.Card(dbc.CardBody([
        html.H5("Report", className="tara-heading"),
        html.P("Generate and download the appraisal report.", className="text-muted"),
        html.Div([
            dbc.Button("Generate PDF Report", id="gen-pdf-btn",
                        className="tara-btn-primary me-2"),
            dbc.Button("Export CSV Data", id="gen-csv-btn",
                        className="tara-btn-secondary"),
        ], className="mb-3"),
        dcc.Loading(type="circle", children=html.Div(id="report-result-area")),
        dcc.Download(id="download-pdf"),
        dcc.Download(id="download-csv"),
        html.Div(id="report-summary"),
    ]), className="mb-3")


# Pre-build all steps so component IDs exist in the layout
ALL_STEPS = {
    1: build_step1(),
    2: build_step2(),
    3: build_step3(),
    4: build_step4(),
    5: build_step5(),
    6: build_step6(),
    7: build_step7(),
}


# ============================================================
# Main Layout
# ============================================================

app.layout = html.Div([
    # Stores
    dcc.Store(id="current-step-store", data=1),
    dcc.Store(id="road-data-store", data=None),
    dcc.Store(id="facilities-data-store", data=None),
    dcc.Store(id="condition-store", data=None),
    dcc.Store(id="traffic-store", data=None),
    dcc.Store(id="cost-store", data=None),
    dcc.Store(id="results-store", data=None),
    dcc.Store(id="sensitivity-store", data=None),
    dcc.Store(id="population-store", data=None),
    dcc.Store(id="equity-store", data=None),
    dcc.Store(id="cba-inputs-store", data=None),
    dcc.Store(id="ai-narrative-store", data=None),
    dcc.Store(id="map-bounds-store", data=None),
    dcc.Store(id="video-condition-store", data=None),

    # Header
    html.Div([
        html.Div([
            html.Span("TARA", className="tara-wordmark"),
            html.Span("Transport Assessment & Road Appraisal", className="tara-subtitle d-none d-md-inline"),
        ]),
        html.Span("Built with Claude Opus 4.6", className="tara-badge d-none d-md-inline"),
    ], className="tara-header"),

    # Two-panel layout
    html.Div([
        # Left: Wizard
        html.Div([
            html.Div(id="step-indicator"),
            # All steps are rendered but hidden via display style
            *[
                html.Div(step, id=f"step-panel-{i}", style={"display": "block" if i == 1 else "none"})
                for i, step in ALL_STEPS.items()
            ],
            # Nav buttons
            html.Div([
                dbc.Button("\u2190 Back", id="back-btn", color="secondary",
                           outline=True, size="sm"),
                dbc.Button("Next \u2192", id="next-btn", color="primary",
                           size="sm"),
            ], className="tara-nav-buttons"),
        ], className="tara-left-panel"),

        # Right: Map + Results
        html.Div([
            html.Div(
                dl.Map(
                    id="main-map",
                    children=[dl.TileLayer(url=TILE_URL, attribution=TILE_ATTR)],
                    center=[0.35, 32.58],
                    zoom=10,
                    style={"height": "45vh", "width": "100%"},
                ),
                className="tara-map-container",
            ),
            html.Div(id="right-panel-results"),
        ], className="tara-right-panel"),
    ], className="tara-layout"),

    # Footer
    html.Div(
        "TARA \u2014 Built for the Anthropic Claude Code Hackathon | Feb 2026",
        className="tara-footer",
    ),
])


# ============================================================
# Clientside Callback: AI Typing Animation
# ============================================================

app.clientside_callback(
    ClientsideFunction(namespace="tara", function_name="typeText"),
    Output("ai-narrative", "children", allow_duplicate=True),
    Input("ai-narrative-store", "data"),
    prevent_initial_call=True,
)

# Clientside Callback: Map fitBounds
# dash-leaflet's `bounds` prop doesn't reliably trigger Leaflet's fitBounds().
# We use a store + clientside callback to invoke it via JS.
app.clientside_callback(
    ClientsideFunction(namespace="tara", function_name="fitBounds"),
    Output("main-map", "bounds"),
    Input("map-bounds-store", "data"),
    prevent_initial_call=True,
)


# ============================================================
# Callbacks
# ============================================================

# --- Step Navigation ---

@callback(
    Output("current-step-store", "data"),
    Input("back-btn", "n_clicks"),
    Input("next-btn", "n_clicks"),
    State("current-step-store", "data"),
    prevent_initial_call=True,
)
def navigate_steps(back_clicks, next_clicks, current_step):
    trigger = ctx.triggered_id
    if trigger == "back-btn" and current_step > 1:
        return current_step - 1
    elif trigger == "next-btn" and current_step < 7:
        return current_step + 1
    return no_update


@callback(
    Output("step-indicator", "children"),
    Output("back-btn", "disabled"),
    Output("next-btn", "disabled"),
    *[Output(f"step-panel-{i}", "style") for i in range(1, 8)],
    Input("current-step-store", "data"),
)
def update_step_display(current_step):
    indicator = make_step_indicator(current_step)
    back_disabled = current_step <= 1
    next_disabled = current_step >= 7
    styles = [
        {"display": "block"} if i == current_step else {"display": "none"}
        for i in range(1, 8)
    ]
    return indicator, back_disabled, next_disabled, *styles


# --- Step 1: Road Selection ---

@callback(
    Output("road-search-result", "children"),
    Output("road-data-store", "data"),
    Output("facilities-data-store", "data"),
    Output("main-map", "children"),
    Output("main-map", "center"),
    Output("main-map", "zoom"),
    Output("map-bounds-store", "data"),
    Input("road-select-dropdown", "value"),
    prevent_initial_call=True,
)
def select_road(road_id):
    if not road_id:
        return (no_update,) * 7

    from skills.road_database import get_road_by_id
    from output.maps import create_road_map

    road_record = get_road_by_id(road_id)
    if not road_record:
        return (
            dbc.Alert("Road not found in database.", color="danger"),
            None, None, no_update, no_update, no_update, no_update,
        )

    # Convert road_database format → road_data format expected by rest of app
    surface_types = [s.strip() for s in (road_record["surface"] or "unknown").split(",")]
    road_data = {
        "road_name": road_record["name"],
        "name": road_record["name"],
        "found": True,
        "source": "local_database",
        "total_length_km": road_record["length_km"],
        "segment_count": road_record["segment_count"],
        "center": road_record["center"],
        "bbox": road_record["bbox"],
        "attributes": {
            "surface_types": surface_types,
            "highway_types": [road_record["highway_class"]],
            "avg_width_m": None,
            "lanes": [road_record["lanes"]] if road_record["lanes"] else [],
            "names_found": [road_record["name"]],
        },
        "segments": _build_segments_from_geometries(road_record),
        "coordinates_all": road_record["coordinates"],
    }

    # Try to load facilities (uses Overpass — wrap in try/except)
    facilities_data = {"facilities": {}, "total_count": 0}
    try:
        from skills.osm_facilities import find_facilities, calculate_distances_to_road
        bbox = road_data["bbox"]
        facilities_data = find_facilities(bbox, buffer_km=3.0)
        for cat, items in facilities_data["facilities"].items():
            if items and road_data.get("coordinates_all"):
                facilities_data["facilities"][cat] = calculate_distances_to_road(
                    items, road_data["coordinates_all"]
                )
    except Exception as e:
        print(f"Facilities lookup failed (non-critical): {e}")

    map_result = create_road_map(road_data, facilities_data)

    # Road info as HTML table
    info_rows = [
        html.Tr([html.Td("Length"), html.Td(f"{road_data['total_length_km']} km")]),
        html.Tr([html.Td("Segments"), html.Td(f"{road_data['segment_count']}")]),
        html.Tr([html.Td("Surface"), html.Td(road_record["surface"] or "unknown")]),
        html.Tr([html.Td("Road Class"), html.Td(road_record["highway_class"].replace("_", " ").title())]),
    ]
    # Enriched data rows (shown when enrichment pipeline has been run)
    if road_record.get("surface_predicted"):
        info_rows.append(html.Tr([html.Td("Predicted Surface"), html.Td(road_record["surface_predicted"])]))
    if road_record.get("pop_5km") is not None:
        info_rows.append(html.Tr([html.Td("Population (5km)"), html.Td(f"{road_record['pop_5km']:,}")]))
    if road_record.get("urban_pct") is not None:
        label = "Urban" if road_record["urban_pct"] > 50 else "Rural"
        info_rows.append(html.Tr([html.Td("Urban/Rural"), html.Td(f"{label} ({road_record['urban_pct']:.0f}% urban)")]))
    if road_record.get("feeder_road_km") is not None:
        info_rows.append(html.Tr([html.Td("Feeder Roads (5km)"), html.Td(f"{road_record['feeder_road_km']:,.0f} km")]))
    info_table = html.Table([html.Tbody(info_rows)], className="tara-road-info")

    result_ui = html.Div([
        dbc.Alert(
            html.Strong(f"Selected: {road_record['name']}"),
            color="success", className="py-2",
        ),
        info_table,
    ])

    return (
        result_ui,
        _make_serializable(road_data),
        _make_serializable(facilities_data),
        map_result["children"],
        map_result["center"],
        map_result["zoom"],
        map_result.get("bounds"),
    )


def _extract_segment_coords(geom: dict) -> list[tuple[float, float]]:
    """Extract (lat, lon) coords from a single GeoJSON geometry."""
    coords = []
    if geom.get("type") == "LineString":
        for lon, lat, *_ in geom.get("coordinates", []):
            coords.append((lat, lon))
    elif geom.get("type") == "MultiLineString":
        for line in geom.get("coordinates", []):
            for lon, lat, *_ in line:
                coords.append((lat, lon))
    return coords


def _haversine_pair(c1: tuple, c2: tuple) -> float:
    """Haversine distance between two (lat, lon) tuples in km."""
    import math
    R = 6371
    dlat = math.radians(c2[0] - c1[0])
    dlon = math.radians(c2[1] - c1[1])
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(c1[0])) * math.cos(math.radians(c2[0])) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _build_segments_from_geometries(road_record: dict) -> list[dict]:
    """Convert road_database geometries list into segments for create_road_map."""
    segments = []
    for i, geom in enumerate(road_record.get("geometries", [])):
        coords = _extract_segment_coords(geom)
        length = sum(
            _haversine_pair(coords[j], coords[j + 1])
            for j in range(len(coords) - 1)
        ) if len(coords) > 1 else 0.0
        segments.append({
            "osm_id": road_record["osm_ids"][i] if i < len(road_record["osm_ids"]) else "",
            "name": road_record["name"],
            "highway_type": road_record["highway_class"],
            "surface": road_record["surface"] or "unknown",
            "width": road_record["width"] or "unknown",
            "lanes": road_record["lanes"] or "unknown",
            "coordinates": coords,
            "length_km": round(length, 3),
        })
    return segments


# --- Step 2: Pre-fill surface from OSM ---

@callback(
    Output("surface-type-select", "value"),
    Input("road-data-store", "data"),
    prevent_initial_call=True,
)
def prefill_surface(road_data):
    if not road_data or not road_data.get("found"):
        return "gravel"
    surfaces = road_data.get("attributes", {}).get("surface_types", [])
    if surfaces:
        s = surfaces[0].lower()
        if s in ("asphalt", "paved", "concrete"):
            return "asphalt"
        elif s in ("gravel", "compacted"):
            return "gravel"
        elif s in ("earth", "dirt", "sand", "ground"):
            return "earth"
    return "gravel"


# --- Step 2: Manual Condition Entry ---

IRI_DEFAULTS = {"good": 3.0, "fair": 6.0, "poor": 11.0, "very_poor": 16.0}


@callback(
    Output("condition-store", "data", allow_duplicate=True),
    Input("surface-type-select", "value"),
    Input("condition-rating-select", "value"),
    Input("iri-input", "value"),
    prevent_initial_call=True,
)
def store_manual_condition(surface_type, condition_rating, iri_override):
    """Store manual condition selections into condition-store."""
    iri = float(iri_override) if iri_override else IRI_DEFAULTS.get(condition_rating, 11.0)
    return {
        "source": "manual",
        "surface_type": surface_type or "gravel",
        "condition_rating": condition_rating or "poor",
        "iri": iri,
        "overall_condition": _iri_to_score(iri),
    }


def _iri_to_score(iri: float) -> int:
    """Convert IRI (m/km) to a 0-100 condition score (higher = better)."""
    if iri <= 2:
        return 95
    elif iri <= 4:
        return 80
    elif iri <= 8:
        return 60
    elif iri <= 14:
        return 35
    else:
        return 15


# --- Step 2: Dashcam Upload ---

@callback(
    Output("dashcam-result", "children"),
    Output("condition-store", "data", allow_duplicate=True),
    Input("dashcam-upload", "contents"),
    State("dashcam-upload", "filename"),
    State("road-data-store", "data"),
    prevent_initial_call=True,
)
def handle_dashcam_upload(contents, filename, road_data):
    if not contents:
        return no_update, no_update

    content_type, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)

    ext = filename.split(".")[-1].lower() if filename else "jpg"
    media_type = "image" if ext in ("jpg", "jpeg", "png") else "video"

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(decoded)
        tmp_path = tmp.name

    try:
        from skills.dashcam import analyze_dashcam_media
        result = analyze_dashcam_media(tmp_path, media_type=media_type, road_data=road_data)
        if result.get("found"):
            ui = dbc.Alert([
                html.Strong(f"Condition Score: {result.get('overall_condition', '?')}/100"),
                html.Br(),
                html.Small(
                    f"Surface: {result.get('surface_type', '?').title()} | "
                    f"Drainage: {result.get('drainage_condition', '?').title()}"
                ),
            ], color="info")
            return ui, result
        return dbc.Alert("Could not analyze the file.", color="warning"), None
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# --- Step 2: Preset dropdown → path inputs ---

@callback(
    Output("video-path-input", "value"),
    Output("gpx-path-input", "value"),
    Input("video-preset-dropdown", "value"),
    prevent_initial_call=True,
)
def populate_preset_paths(preset):
    """Populate path inputs from preset dataset selection."""
    if preset == "demo2":
        return (
            "data/videos/demo2_kasangati_loop/clips_compressed",
            "data/videos/12-Feb-2026-1537.gpx",
        )
    return "", ""


# --- Step 2: Video Pipeline Upload Status ---

@callback(
    Output("video-upload-status", "children"),
    Output("run-video-btn", "disabled"),
    Input("video-path-input", "value"),
    Input("gpx-path-input", "value"),
    prevent_initial_call=True,
)
def update_video_upload_status(video_path, gpx_path):
    """Show which paths are set and enable the run button when both present."""
    parts = []
    has_video = False
    has_gpx = False

    if video_path and video_path.strip():
        vp = video_path.strip()
        if os.path.exists(vp):
            if os.path.isdir(vp):
                mp4s = [f for f in os.listdir(vp) if f.lower().endswith((".mp4", ".avi", ".mov"))]
                parts.append(html.Small(f"Video path: {len(mp4s)} clips in {os.path.basename(vp)}/", className="text-success me-3"))
            else:
                parts.append(html.Small(f"Video path: {os.path.basename(vp)}", className="text-success me-3"))
            has_video = True
        else:
            parts.append(html.Small("Video path not found", className="text-danger me-3"))

    if gpx_path and gpx_path.strip():
        gp = gpx_path.strip()
        if os.path.exists(gp):
            parts.append(html.Small(f"GPX path: {os.path.basename(gp)}", className="text-success"))
            has_gpx = True
        else:
            parts.append(html.Small("GPX path not found", className="text-danger"))

    both_ready = has_video and has_gpx
    return html.Div(parts), not both_ready


# --- Step 2: Video Pipeline ---

@callback(
    Output("video-pipeline-result", "children"),
    Output("condition-store", "data", allow_duplicate=True),
    Output("video-condition-store", "data"),
    Output("main-map", "children", allow_duplicate=True),
    Output("map-bounds-store", "data", allow_duplicate=True),
    Input("run-video-btn", "n_clicks"),
    State("video-path-input", "value"),
    State("gpx-path-input", "value"),
    State("road-data-store", "data"),
    State("main-map", "children"),
    prevent_initial_call=True,
)
def run_video_pipeline(n_clicks, video_path_input, gpx_path_input,
                       road_data, current_map_children):
    """Run the full video + GPS analysis pipeline using local file paths."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    video_path = None
    gpx_path = None

    if video_path_input and video_path_input.strip():
        vp = video_path_input.strip()
        if not os.path.exists(vp):
            return (
                dbc.Alert(f"Video path not found: {vp}", color="danger"),
                no_update, no_update, no_update, no_update,
            )
        video_path = vp

    if gpx_path_input and gpx_path_input.strip():
        gp = gpx_path_input.strip()
        if not os.path.exists(gp):
            return (
                dbc.Alert(f"GPX path not found: {gp}", color="danger"),
                no_update, no_update, no_update, no_update,
            )
        gpx_path = gp

    if not video_path or not gpx_path:
        return (
            dbc.Alert("Please provide both video and GPX paths.", color="warning"),
            no_update, no_update, no_update, no_update,
        )

    try:

        from video.video_pipeline import run_pipeline
        result = run_pipeline(
            video_path=video_path,
            gpx_path=gpx_path,
            frame_interval=5,
            max_frames=20,
            use_mock=False,
        )

        # Handle pipeline error responses (size guards, memory errors, etc.)
        if result.get("error"):
            error_msg = result.get("message", "Unknown pipeline error")
            warnings = result.get("warnings", [])
            alert_children = [html.Strong("Pipeline Error: "), error_msg]
            if warnings:
                alert_children.append(html.Br())
                alert_children.append(html.Small("; ".join(warnings)))
            return (
                dbc.Alert(alert_children, color="danger"),
                no_update, no_update, no_update, no_update,
            )

        summary = result["summary"]
        geojson = result["geojson"]
        narrative = result.get("narrative", "")
        metadata = result.get("metadata", {})
        panel_data = result.get("panel_data", {})

        # --- Build result UI ---
        distress_list = summary.get("distress_types_found", [])
        distress_str = ", ".join(d.replace("_", " ").title() for d in distress_list) if distress_list else "None"

        # Condition bar — horizontal stacked bar from panel_data percentages
        cond_pcts = panel_data.get("condition_percentages", {})
        bar_colors = {"good": "#2d5f4a", "fair": "#9a6b2f", "poor": "#c4652a", "bad": "#a83a2f"}
        bar_segments = []
        for cond in ["good", "fair", "poor", "bad"]:
            pct = cond_pcts.get(cond, 0)
            if pct > 0:
                bar_segments.append(html.Div(
                    f"{pct}%",
                    style={
                        "width": f"{pct}%", "background": bar_colors[cond],
                        "color": "white", "textAlign": "center",
                        "fontSize": "0.7rem", "fontWeight": "600",
                        "padding": "2px 0", "display": "inline-block",
                    },
                ))
        condition_bar = html.Div(
            bar_segments,
            style={"display": "flex", "borderRadius": "3px", "overflow": "hidden",
                   "height": "22px", "marginBottom": "8px"},
        ) if bar_segments else html.Div()

        result_ui = html.Div([
            dbc.Alert([
                html.Strong("Video Analysis Complete"),
                html.Br(),
                html.Small(
                    f"{metadata.get('total_distance_km', '?')} km analysed in "
                    f"{metadata.get('processing_time_sec', '?')}s"
                ),
            ], color="success", className="py-2"),
            html.Div([
                _metric_card("Avg IRI", f"{summary.get('average_iri', '?')} m/km", "info"),
                _metric_card("Surface", summary.get("dominant_surface", "?").title(), "primary"),
                _metric_card("Condition", summary.get("dominant_condition", "?").title(),
                             "success" if summary.get("dominant_condition") == "good" else "warning"),
                _metric_card("Frames", str(summary.get("total_frames_assessed", 0)), "primary"),
            ], className="tara-metric-row"),
            condition_bar,
            html.Small(f"Distress: {distress_str}", className="text-muted d-block mb-2"),
            dbc.Card(dbc.CardBody([
                html.H6("Condition Narrative"),
                html.P(narrative, style={"fontSize": "0.85rem", "whiteSpace": "pre-line"}),
            ]), className="mb-2") if narrative else html.Div(),
        ])

        # --- Bridge to condition-store format ---
        avg_iri = summary.get("average_iri", 11.0)
        condition_data = {
            "source": "video_pipeline",
            "surface_type": summary.get("dominant_surface", "gravel"),
            "condition_rating": summary.get("dominant_condition", "poor"),
            "iri": avg_iri,
            "overall_condition": _iri_to_score(avg_iri),
            "defects": distress_list,
            "drainage_condition": "unknown",
        }

        # --- Build map layer ---
        from output.maps import build_condition_layer
        condition_markers = build_condition_layer(geojson)

        # Preserve existing map children and append condition markers
        map_children = list(current_map_children) if current_map_children else [
            dl.TileLayer(url=TILE_URL, attribution=TILE_ATTR)
        ]
        map_children.extend(condition_markers)

        # Add a simple legend
        legend_html = html.Div([
            html.Div("Condition:", style={"fontWeight": "bold", "fontSize": "0.75rem"}),
            html.Div([
                html.Span("\u25cf", style={"color": "#2d5f4a"}), " Good ",
                html.Span("\u25cf", style={"color": "#9a6b2f"}), " Fair ",
                html.Span("\u25cf", style={"color": "#c4652a"}), " Poor ",
                html.Span("\u25cf", style={"color": "#a83a2f"}), " Bad",
            ], style={"fontSize": "0.7rem"}),
        ], style={
            "position": "absolute", "bottom": "10px", "right": "10px",
            "background": "rgba(255,255,255,0.9)", "padding": "6px 10px",
            "borderRadius": "4px", "zIndex": "1000", "border": "1px solid #ccc",
        })
        map_children.append(legend_html)

        # Calculate bounds from condition sections (LineString or Point)
        bounds = None
        features = geojson.get("features", [])
        if features:
            all_lats, all_lons = [], []
            for feat in features:
                geom = feat["geometry"]
                if geom["type"] == "LineString":
                    for coord in geom["coordinates"]:
                        all_lons.append(coord[0])
                        all_lats.append(coord[1])
                elif geom["type"] == "Point":
                    all_lons.append(geom["coordinates"][0])
                    all_lats.append(geom["coordinates"][1])
            if all_lats:
                bounds = [
                    [min(all_lats) - 0.005, min(all_lons) - 0.005],
                    [max(all_lats) + 0.005, max(all_lons) + 0.005],
                ]

        return (
            result_ui,
            condition_data,
            _make_serializable({"summary": summary, "geojson": geojson, "panel_data": panel_data}),
            map_children,
            bounds,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            dbc.Alert(f"Video pipeline error: {str(e)}", color="danger"),
            no_update, no_update, no_update, no_update,
        )


# --- Step 4: Cost per km ---

@callback(
    Output("cost-per-km-display", "children"),
    Input("total-cost-input", "value"),
    Input("road-data-store", "data"),
)
def update_cost_per_km(total_cost, road_data):
    length = 10.0
    if road_data and road_data.get("total_length_km"):
        length = road_data["total_length_km"]
    if total_cost and length > 0:
        return html.Span(f"${total_cost / length:,.0f}/km", className="tara-metric-value positive",
                         style={"fontSize": "0.9rem"})
    return html.Span("\u2014")


# --- Input Validation Warnings ---

@callback(
    Output("traffic-warnings", "children"),
    Input("total-adt-input", "value"),
)
def validate_traffic(adt):
    """Show warnings for unusual traffic values."""
    if not adt:
        return html.Div()
    warnings = []
    if adt > 50000:
        warnings.append("Traffic seems very high (>50,000 ADT) \u2014 please verify.")
    elif adt < 10:
        warnings.append("Traffic seems very low (<10 ADT) \u2014 please verify.")
    if not warnings:
        return html.Div()
    return html.Div([
        dbc.Alert(w, color="warning", className="py-1 mb-1", style={"fontSize": "0.85rem"})
        for w in warnings
    ])


@callback(
    Output("cost-warnings", "children"),
    Input("total-cost-input", "value"),
    Input("discount-rate-input", "value"),
    Input("analysis-period-input", "value"),
    State("road-data-store", "data"),
)
def validate_costs(total_cost, discount_rate_pct, analysis_period, road_data):
    """Show warnings for unusual cost/parameter values."""
    warnings = []
    length = 10.0
    if road_data and road_data.get("total_length_km"):
        length = road_data["total_length_km"]
    if total_cost and length > 0:
        cost_per_km = total_cost / length
        if cost_per_km < 50000:
            warnings.append(f"Cost per km (${cost_per_km:,.0f}) seems very low for Uganda.")
        elif cost_per_km > 2000000:
            warnings.append(f"Cost per km (${cost_per_km:,.0f}) seems very high for Uganda.")
    if discount_rate_pct is not None:
        if discount_rate_pct < 6:
            warnings.append("Discount rate below 6% is unusually low.")
        elif discount_rate_pct > 18:
            warnings.append("Discount rate above 18% is unusually high.")
    if analysis_period is not None:
        if analysis_period > 30:
            warnings.append("Analysis period over 30 years may reduce reliability.")
        elif analysis_period < 10:
            warnings.append("Analysis period under 10 years is unusually short.")
    if not warnings:
        return html.Div()
    return html.Div([
        dbc.Alert(w, color="warning", className="py-1 mb-1", style={"fontSize": "0.85rem"})
        for w in warnings
    ])


# --- Step 5: Run CBA ---

@callback(
    Output("cba-results-area", "children"),
    Output("results-store", "data"),
    Output("right-panel-results", "children", allow_duplicate=True),
    Output("cba-inputs-store", "data"),
    Output("population-store", "data"),
    Output("equity-store", "data"),
    Input("run-cba-btn", "n_clicks"),
    State("road-data-store", "data"),
    State("facilities-data-store", "data"),
    State("condition-store", "data"),
    State("total-adt-input", "value"),
    State("growth-rate-input", "value"),
    State({"type": "traffic-pct", "vc": ALL}, "value"),
    State("total-cost-input", "value"),
    State("construction-years-input", "value"),
    State("discount-rate-input", "value"),
    State("analysis-period-input", "value"),
    State("base-year-input", "value"),
    prevent_initial_call=True,
)
def run_cba_callback(
    n_clicks, road_data, facilities_data, condition_data,
    adt, growth_rate_pct, traffic_pct_values,
    total_cost, construction_years,
    discount_rate_pct, analysis_period, base_year,
):
    from engine.cba import run_cba
    from engine.equity import calculate_equity_score
    from output.charts import (
        create_waterfall_chart, create_cashflow_chart, create_traffic_growth_chart,
    )

    if not adt or not total_cost:
        return (
            dbc.Alert("Please enter traffic (ADT) and construction cost.", color="warning"),
            no_update, no_update, no_update, no_update, no_update,
        )

    road_length = 10.0
    if road_data and road_data.get("total_length_km"):
        road_length = road_data["total_length_km"]

    growth_rate = (growth_rate_pct or 3.5) / 100.0
    discount_rate = (discount_rate_pct or 12.0) / 100.0

    # Build vehicle split from per-class percentage inputs
    vehicle_split = None
    if traffic_pct_values:
        raw_split = {}
        for i, vc in enumerate(VEHICLE_CLASSES):
            pct = traffic_pct_values[i] if i < len(traffic_pct_values) else 0
            raw_split[vc] = float(pct or 0)
        total_pct = sum(raw_split.values())
        if total_pct > 0:
            vehicle_split = {vc: v / total_pct for vc, v in raw_split.items()}

    cba_inputs = {
        "base_adt": float(adt),
        "growth_rate": growth_rate,
        "road_length_km": road_length,
        "construction_cost_total": float(total_cost),
        "construction_years": int(construction_years or 3),
        "discount_rate": discount_rate,
        "analysis_period": int(analysis_period or 20),
        "base_year": int(base_year or 2025),
        "vehicle_split": vehicle_split,
    }

    try:
        cba_results = run_cba(**cba_inputs)
    except Exception as e:
        return (
            dbc.Alert(f"CBA Error: {str(e)}", color="danger"),
            no_update, no_update, no_update, no_update, no_update,
        )

    # Population — prefer Kontur (local, fast) over WorldPop (API, slow)
    pop_data = None
    try:
        try:
            from skills.kontur_population import get_population
        except ImportError:
            from skills.worldpop import get_population
        if road_data and road_data.get("found"):
            pop_data = get_population(
                road_data.get("bbox", {}),
                road_coords=road_data.get("coordinates_all"),
            )
    except Exception:
        pass

    # Equity
    equity_results = None
    try:
        equity_results = calculate_equity_score(
            road_data or {}, facilities_data, pop_data, cba_results
        )
    except Exception:
        pass

    s = cba_results.get("summary", {})
    viable = s.get("economically_viable", False)
    verdict_cls = "tara-verdict viable" if viable else "tara-verdict not-viable"
    verdict_text = "ECONOMICALLY VIABLE" if viable else "NOT ECONOMICALLY VIABLE"

    npv_color = "positive" if cba_results.get("npv", 0) > 0 else "negative"
    eirr_color = "positive" if (s.get("eirr_pct") or 0) > discount_rate * 100 else "warning"
    bcr_color = "positive" if cba_results.get("bcr", 0) > 1 else "negative"

    metric_row = html.Div([
        _metric_card("NPV", f"${cba_results.get('npv', 0):,.0f}", "success" if npv_color == "positive" else "danger"),
        _metric_card("EIRR", f"{s.get('eirr_pct', 'N/A')}%", "success" if eirr_color == "positive" else "warning"),
        _metric_card("BCR", f"{cba_results.get('bcr', 0):.2f}", "success" if bcr_color == "positive" else "danger"),
        _metric_card("FYRR", f"{s.get('fyrr_pct', 'N/A')}%", "info"),
    ], className="tara-metric-row")

    verdict_badge = html.Div(verdict_text, className=verdict_cls)

    # Charts
    charts_ui = html.Div()
    try:
        waterfall = create_waterfall_chart(cba_results)
        cashflow = create_cashflow_chart(cba_results)
        traffic = create_traffic_growth_chart(cba_results)
        charts_ui = html.Div([
            dbc.Row([dbc.Col(
                dcc.Graph(figure=waterfall, config={"displayModeBar": False}), md=12)]),
            dbc.Row([
                dbc.Col(dcc.Graph(figure=cashflow, config={"displayModeBar": False}), md=6),
                dbc.Col(dcc.Graph(figure=traffic, config={"displayModeBar": False}), md=6),
            ]),
        ])
    except Exception:
        pass

    # Equity card
    equity_ui = html.Div()
    if equity_results:
        equity_ui = dbc.Card(dbc.CardBody([
            html.H6("Equity Assessment"),
            dbc.Progress(
                value=equity_results.get("overall_score", 0),
                label=f"{equity_results.get('overall_score', 0)}/100",
                color="success" if equity_results.get("overall_score", 0) >= 60 else "warning",
                className="mb-2", style={"height": "24px"},
            ),
            html.Small(equity_results.get("classification", ""), className="text-muted"),
        ]), className="mb-3")

    left_result = html.Div([verdict_badge, metric_row])
    right_panel = html.Div([metric_row, verdict_badge, equity_ui, charts_ui])

    return (
        left_result,
        _make_serializable(cba_results),
        right_panel,
        cba_inputs,
        _make_serializable(pop_data) if pop_data else None,
        _make_serializable(equity_results) if equity_results else None,
    )


# --- Step 6: Sensitivity Controls ---

@callback(
    Output("sensitivity-controls", "children"),
    Input("current-step-store", "data"),
    State("results-store", "data"),
)
def build_sensitivity_controls(current_step, results):
    if current_step != 6:
        return no_update
    if not results:
        return dbc.Alert("Run the appraisal in Step 5 first.", color="warning")

    return html.Div([
        dbc.Label("Construction Cost Change (%)"),
        dcc.Slider(id="sens-cost-slider", min=-30, max=50, step=5, value=0,
                   marks={i: f"{i:+d}%" for i in range(-30, 51, 10)},
                   tooltip={"placement": "bottom"}),
        dbc.Label("Traffic Volume Change (%)", className="mt-3"),
        dcc.Slider(id="sens-traffic-slider", min=-40, max=30, step=5, value=0,
                   marks={i: f"{i:+d}%" for i in range(-40, 31, 10)},
                   tooltip={"placement": "bottom"}),
        dbc.Label("Growth Rate Change (pp)", className="mt-3"),
        dcc.Slider(id="sens-growth-slider", min=-2, max=2, step=0.5, value=0,
                   marks={i: f"{i:+.0f}pp" for i in range(-2, 3)},
                   tooltip={"placement": "bottom"}),
        dbc.Button("Run Full Sensitivity Analysis", id="run-sensitivity-btn",
                   className="tara-btn-amber mt-3"),
    ])


# --- Step 6: Sensitivity Live + Full ---

@callback(
    Output("sensitivity-results-area", "children"),
    Output("sensitivity-store", "data"),
    Input("sens-cost-slider", "value"),
    Input("sens-traffic-slider", "value"),
    Input("sens-growth-slider", "value"),
    Input("run-sensitivity-btn", "n_clicks"),
    State("cba-inputs-store", "data"),
    State("results-store", "data"),
    prevent_initial_call=True,
)
def update_sensitivity(cost_chg, traffic_chg, growth_chg,
                       full_clicks, cba_inputs, base_results):
    if not cba_inputs or not base_results:
        return dbc.Alert("Run the appraisal in Step 5 first.", color="warning"), no_update

    trigger = ctx.triggered_id

    # Full sensitivity
    if trigger == "run-sensitivity-btn":
        from engine.sensitivity import run_sensitivity_analysis
        from output.charts import create_tornado_chart, create_scenario_chart

        try:
            sens = run_sensitivity_analysis(cba_inputs)
        except Exception as e:
            return dbc.Alert(f"Sensitivity error: {str(e)}", color="danger"), no_update

        charts = html.Div()
        try:
            tornado = create_tornado_chart(sens)
            scenario = create_scenario_chart(sens)
            charts = dbc.Row([
                dbc.Col(dcc.Graph(figure=tornado, config={"displayModeBar": False}), md=6),
                dbc.Col(dcc.Graph(figure=scenario, config={"displayModeBar": False}), md=6),
            ])
        except Exception:
            pass

        sv = sens.get("switching_values", {})
        sv_rows = []
        for var, val in sv.items():
            fmt = f"{val:+.1%} absolute" if var == "traffic_growth" else f"{val:+.0%}"
            sv_rows.append(html.Tr([
                html.Td(var.replace("_", " ").title()), html.Td(fmt, className="mono"),
            ]))

        sv_table = html.Div()
        if sv_rows:
            sv_table = html.Table([
                html.Thead(html.Tr([html.Th("Variable"), html.Th("Switching Value")])),
                html.Tbody(sv_rows),
            ], className="tara-table mt-2")

        summary = sens.get("summary", {})
        risk = dbc.Alert(summary.get("risk_assessment", ""), color="info", className="mt-2")

        return html.Div([charts, sv_table, risk]), _make_serializable(sens)

    # Live slider
    from engine.cba import run_cba as _run_cba

    modified = copy.deepcopy(cba_inputs)
    if cost_chg:
        modified["construction_cost_total"] *= (1 + cost_chg / 100.0)
    if traffic_chg:
        modified["base_adt"] *= (1 + traffic_chg / 100.0)
    if growth_chg:
        modified["growth_rate"] = modified.get("growth_rate", 0.035) + growth_chg / 100.0

    try:
        new = _run_cba(**modified)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), no_update

    base_npv = base_results.get("npv", 0)
    new_npv = new.get("npv", 0)
    delta = new_npv - base_npv
    dc = "success" if delta >= 0 else "danger"
    ns = new.get("summary", {})

    comparison = html.Div([
        _metric_card("Adjusted NPV", f"${new_npv:,.0f}", dc),
        _metric_card("NPV Change", f"${delta:+,.0f}", dc),
        _metric_card("Adjusted BCR", f"{new.get('bcr', 0):.2f}",
                     "success" if new.get("bcr", 0) > 1 else "danger"),
        _metric_card("Adjusted EIRR", f"{ns.get('eirr_pct', 'N/A')}%", "info"),
    ], className="tara-metric-row")
    return comparison, no_update


# --- Step 6: AI Interpretation ---

@callback(
    Output("ai-narrative-store", "data"),
    Input("ai-interpret-btn", "n_clicks"),
    State("results-store", "data"),
    State("sensitivity-store", "data"),
    State("road-data-store", "data"),
    prevent_initial_call=True,
)
def ai_interpretation(n_clicks, cba_results, sensitivity_results, road_data):
    if not cba_results:
        return no_update

    try:
        from agent.orchestrator import create_agent, process_message_sync

        road_name = road_data.get("name", "the road") if road_data else "the road"
        s = cba_results.get("summary", {})
        prompt = (
            f"Provide a 3-4 paragraph expert interpretation of the CBA results for {road_name}. "
            f"Key results: NPV ${cba_results.get('npv', 0):,.0f}, "
            f"EIRR {s.get('eirr_pct', 'N/A')}%, BCR {cba_results.get('bcr', 0):.2f}. "
        )
        if sensitivity_results:
            sm = sensitivity_results.get("summary", {})
            prompt += (
                f"Sensitivity: most sensitive to {sm.get('most_sensitive_variable', 'unknown')}. "
                f"Risk: {sm.get('risk_assessment', 'unknown')}. "
            )
        prompt += "Be specific and actionable. Write for a decision-maker."

        agent = create_agent()
        text, _, _ = process_message_sync(agent, prompt)

        return {"text": text, "targetId": "ai-narrative"}
    except Exception as e:
        # For errors, we can't use the typing animation, so return None
        # and set the error directly
        return no_update


# Error fallback for AI interpretation
@callback(
    Output("ai-narrative", "children"),
    Input("ai-interpret-btn", "n_clicks"),
    State("results-store", "data"),
    prevent_initial_call=True,
)
def ai_interpretation_error_fallback(n_clicks, cba_results):
    """Show error states directly (non-typing)."""
    if not cba_results:
        return dbc.Alert("Run the appraisal first.", color="warning")
    # If we get here without the store firing, show a loading state
    return html.Div([
        html.Span(className="tara-typing-dot"),
        html.Small(" Generating interpretation...", className="text-muted"),
    ])


# --- Step 7: PDF ---

@callback(
    Output("download-pdf", "data"),
    Output("report-result-area", "children"),
    Input("gen-pdf-btn", "n_clicks"),
    State("road-data-store", "data"),
    State("facilities-data-store", "data"),
    State("population-store", "data"),
    State("results-store", "data"),
    State("sensitivity-store", "data"),
    State("equity-store", "data"),
    State("condition-store", "data"),
    prevent_initial_call=True,
)
def generate_pdf_report(n_clicks, road_data, facilities_data, pop_data,
                        cba_results, sensitivity_results, equity_results, condition_data):
    from output.report import generate_report_pdf, get_report_summary

    try:
        pdf_bytes = generate_report_pdf(
            road_data=road_data,
            facilities_data=facilities_data,
            population_data=pop_data,
            cba_results=cba_results,
            sensitivity_results=sensitivity_results,
            equity_results=equity_results,
            condition_data=condition_data,
        )
        road_name = "Road"
        if road_data and road_data.get("name"):
            road_name = road_data["name"].replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"TARA_Report_{road_name}_{date_str}.pdf"

        summary = get_report_summary(cba_results, sensitivity_results, equity_results)
        return (
            dcc.send_bytes(pdf_bytes, filename),
            dbc.Alert([html.Strong("Report generated! "), html.Span(summary)], color="success"),
        )
    except Exception as e:
        return no_update, dbc.Alert(f"Error generating report: {str(e)}", color="danger")


# --- Step 7: CSV ---

@callback(
    Output("download-csv", "data"),
    Input("gen-csv-btn", "n_clicks"),
    State("results-store", "data"),
    State("road-data-store", "data"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, cba_results, road_data):
    if not cba_results or "yearly_cashflows" not in cba_results:
        return no_update

    import pandas as pd

    rows = []
    for cf in cba_results["yearly_cashflows"]:
        rows.append({
            "Year": cf["calendar_year"],
            "Construction_Cost": cf["costs"]["construction"],
            "Net_Maintenance": cf["costs"]["net_maintenance"],
            "VOC_Savings": cf["benefits"]["voc_savings"],
            "Time_Savings": cf["benefits"]["vot_savings"],
            "Accident_Savings": cf["benefits"]["accident_savings"],
            "Generated_Traffic": cf["benefits"]["generated_traffic"],
            "Residual_Value": cf["benefits"]["residual_value"],
            "Net_Benefit": cf["net_benefit"],
        })

    df = pd.DataFrame(rows)
    road_name = "Road"
    if road_data and road_data.get("name"):
        road_name = road_data["name"].replace(" ", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    return dcc.send_data_frame(df.to_csv, f"TARA_Cashflows_{road_name}_{date_str}.csv", index=False)


# --- Step 7: Report Preview ---

@callback(
    Output("report-summary", "children"),
    Input("results-store", "data"),
    Input("current-step-store", "data"),
)
def show_report_summary(cba_results, current_step):
    if current_step != 7 or not cba_results:
        return html.Div()

    from output.report import generate_report_markdown
    try:
        md = generate_report_markdown(cba_results=cba_results)
        preview = md[:2000]
        if len(md) > 2000:
            preview += "\n\n*... (truncated \u2014 download PDF for full report)*"
        return dbc.Card(dbc.CardBody([
            html.H6("Report Preview"),
            dcc.Markdown(preview, style={"fontSize": "0.8rem", "maxHeight": "400px",
                                         "overflowY": "auto"}),
        ]), className="mt-3")
    except Exception:
        return html.Div()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    app.run(debug=True, port=8050)
