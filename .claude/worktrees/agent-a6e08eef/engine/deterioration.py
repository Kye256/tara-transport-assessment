"""
TARA Deterioration Modeling
Predicts IRI progression over time for do-nothing vs with-project scenarios.
Uses HDM-4 style exponential deterioration with Uganda-calibrated coefficients.

This module is additive — it produces charts and narrative alongside the existing
CBA engine without replacing any calculation logic.
"""

import numpy as np
import plotly.graph_objects as go
from typing import Optional

from output.charts import (
    TARA_COLORS,
    TARA_COST_COLOR,
    TARA_BENEFIT_COLOR,
    TARA_NPV_COLOR,
    _apply_tara_layout,
)


# --- Surface Type Mapping ---
# Maps condition-store surface values to model categories
SURFACE_MAP = {
    "asphalt": "paved_fair",
    "paved": "paved_fair",
    "paved_asphalt": "paved_fair",
    "concrete": "paved_good",
    "gravel": "gravel",
    "murram": "gravel",
    "compacted": "gravel",
    "earth": "earth",
    "dirt": "earth",
}

# --- Deterioration Rate Coefficients (k) ---
# Annual exponential growth rate of IRI: IRI(t) = IRI_0 * e^(k*t)
# Calibrated from HDM-4 Uganda defaults
BASE_K = {
    "paved_good": 0.04,
    "paved_fair": 0.06,
    "paved_poor": 0.08,
    "gravel": 0.10,
    "earth": 0.12,
}

# IRI caps by surface type (m/km) — practical maximum roughness
IRI_CAP = {
    "paved_good": 16.0,
    "paved_fair": 18.0,
    "paved_poor": 20.0,
    "gravel": 24.0,
    "earth": 30.0,
}

# Post-construction IRI for with-project scenario (m/km)
POST_CONSTRUCTION_IRI = {
    "paved_good": 2.5,
    "paved_fair": 3.0,
    "paved_poor": 3.0,
    "gravel": 6.0,
    "earth": 8.0,
}

# With-project deterioration rate (slower due to better construction)
WITH_PROJECT_K = {
    "paved_good": 0.03,
    "paved_fair": 0.035,
    "paved_poor": 0.035,
    "gravel": 0.06,
    "earth": 0.08,
}

# Periodic maintenance resets IRI to this value (m/km)
MAINTENANCE_RESET_IRI = {
    "paved_good": 3.5,
    "paved_fair": 4.0,
    "paved_poor": 4.0,
    "gravel": 8.0,
    "earth": 10.0,
}


def compute_k(
    surface_type: str,
    adt: float = 1000,
    rainfall_zone: str = "moderate",
    material_quality: str = "average",
) -> float:
    """
    Compute deterioration rate coefficient adjusted for traffic and environment.

    Args:
        surface_type: One of 'paved_good', 'paved_fair', 'paved_poor', 'gravel', 'earth'
        adt: Average daily traffic (vehicles/day)
        rainfall_zone: 'low', 'moderate', or 'high'
        material_quality: 'poor', 'average', or 'good'

    Returns:
        Adjusted annual deterioration rate k
    """
    k_base = BASE_K.get(surface_type, 0.06)

    # Traffic adjustment: heavier traffic accelerates deterioration
    # Normalised to 1.0 at 1000 ADT
    traffic_factor = 0.8 + 0.2 * min(adt / 1000.0, 5.0)

    # Rainfall adjustment
    rainfall_factors = {"low": 0.85, "moderate": 1.0, "high": 1.20}
    rain_factor = rainfall_factors.get(rainfall_zone, 1.0)

    # Material quality adjustment
    quality_factors = {"poor": 1.25, "average": 1.0, "good": 0.80}
    quality_factor = quality_factors.get(material_quality, 1.0)

    return k_base * traffic_factor * rain_factor * quality_factor


def predict_iri(
    iri_initial: float,
    years: int,
    k: float,
    cap: float = 20.0,
) -> np.ndarray:
    """
    Predict IRI over time without any intervention (do-nothing scenario).

    Uses exponential model: IRI(t) = IRI_0 * e^(k*t), capped at maximum.

    Args:
        iri_initial: Starting IRI (m/km)
        years: Number of years to predict
        k: Annual deterioration rate coefficient
        cap: Maximum IRI (m/km)

    Returns:
        Array of IRI values for years 0..years
    """
    t = np.arange(years + 1, dtype=float)
    iri = iri_initial * np.exp(k * t)
    return np.minimum(iri, cap)


def predict_with_maintenance(
    iri_initial: float,
    years: int,
    k: float,
    construction_years: int = 3,
    post_construction_iri: float = 3.0,
    with_project_k: float = 0.035,
    maintenance_interval: int = 10,
    maintenance_reset_iri: float = 4.0,
    cap: float = 16.0,
) -> tuple[np.ndarray, list[int]]:
    """
    Predict IRI with project construction and periodic maintenance.

    During construction, IRI linearly transitions from current to post-construction.
    After construction, IRI grows at with_project_k rate.
    Periodic maintenance resets IRI to maintenance_reset_iri.

    Args:
        iri_initial: Starting IRI (m/km)
        years: Total analysis period (years)
        k: Do-nothing deterioration rate (unused, for interface consistency)
        construction_years: Duration of construction
        post_construction_iri: IRI after construction completes
        with_project_k: Deterioration rate after construction
        maintenance_interval: Years between periodic maintenance
        maintenance_reset_iri: IRI after periodic maintenance
        cap: Maximum IRI

    Returns:
        Tuple of (IRI array for years 0..years, list of maintenance event years)
    """
    iri = np.zeros(years + 1)
    iri[0] = iri_initial
    maintenance_events = []

    for t in range(1, years + 1):
        if t <= construction_years:
            # Linear transition during construction
            progress = t / construction_years
            iri[t] = iri_initial + progress * (post_construction_iri - iri_initial)
        else:
            years_since_open = t - construction_years
            # Check for periodic maintenance
            if maintenance_interval > 0 and years_since_open > 0 and years_since_open % maintenance_interval == 0:
                iri[t] = maintenance_reset_iri
                maintenance_events.append(t)
            else:
                # Exponential growth from previous year
                iri[t] = iri[t - 1] * np.exp(with_project_k)

        iri[t] = min(iri[t], cap)

    return iri, maintenance_events


def create_deterioration_chart(
    iri_current: float,
    surface_type: str,
    adt: float,
    analysis_period: int = 20,
    construction_years: int = 3,
    base_year: int = 2026,
    road_name: str = "Road",
    rainfall_zone: str = "moderate",
    material_quality: str = "average",
) -> go.Figure:
    """
    Create a Plotly chart showing IRI deterioration over time.

    Two curves:
    - Do-Nothing: road degrades from current IRI
    - With-Project: construction -> low IRI -> gradual degradation + maintenance

    Args:
        iri_current: Current IRI (m/km)
        surface_type: Mapped surface type
        adt: Average daily traffic
        analysis_period: Years of analysis
        construction_years: Construction duration
        base_year: Calendar start year
        road_name: Road name for title
        rainfall_zone: Rainfall zone
        material_quality: Material quality

    Returns:
        Plotly Figure
    """
    k = compute_k(surface_type, adt, rainfall_zone, material_quality)
    cap_do_nothing = IRI_CAP.get(surface_type, 20.0)
    cap_with = IRI_CAP.get(surface_type, 16.0)
    post_iri = POST_CONSTRUCTION_IRI.get(surface_type, 3.0)
    wp_k = WITH_PROJECT_K.get(surface_type, 0.035)
    maint_iri = MAINTENANCE_RESET_IRI.get(surface_type, 4.0)

    # Do-nothing curve
    iri_do_nothing = predict_iri(iri_current, analysis_period, k, cap_do_nothing)

    # With-project curve
    iri_with_project, maint_events = predict_with_maintenance(
        iri_initial=iri_current,
        years=analysis_period,
        k=k,
        construction_years=construction_years,
        post_construction_iri=post_iri,
        with_project_k=wp_k,
        maintenance_interval=10,
        maintenance_reset_iri=maint_iri,
        cap=cap_with,
    )

    years = np.arange(analysis_period + 1) + base_year

    fig = go.Figure()

    # Do-nothing line
    fig.add_trace(go.Scatter(
        x=years.tolist(),
        y=iri_do_nothing.tolist(),
        mode="lines",
        name="Do-Nothing",
        line=dict(color=TARA_COST_COLOR, width=3),
        hovertemplate="Year %{x}: IRI %{y:.1f} m/km<extra>Do-Nothing</extra>",
    ))

    # With-project line
    fig.add_trace(go.Scatter(
        x=years.tolist(),
        y=iri_with_project.tolist(),
        mode="lines",
        name="With-Project",
        line=dict(color=TARA_BENEFIT_COLOR, width=3),
        hovertemplate="Year %{x}: IRI %{y:.1f} m/km<extra>With-Project</extra>",
    ))

    # Shade the area between curves (the "benefit")
    fig.add_trace(go.Scatter(
        x=list(years) + list(years[::-1]),
        y=list(iri_do_nothing) + list(iri_with_project[::-1]),
        fill="toself",
        fillcolor="rgba(45, 95, 74, 0.1)",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Maintenance event markers
    if maint_events:
        maint_years = [base_year + e for e in maint_events]
        maint_iris = [iri_with_project[e] for e in maint_events]
        fig.add_trace(go.Scatter(
            x=maint_years,
            y=maint_iris,
            mode="markers",
            name="Periodic Maintenance",
            marker=dict(color=TARA_NPV_COLOR, size=10, symbol="diamond"),
            hovertemplate="Year %{x}: Maintenance reset to IRI %{y:.1f}<extra></extra>",
        ))

    # Construction period shading
    if construction_years > 0:
        fig.add_vrect(
            x0=base_year,
            x1=base_year + construction_years,
            fillcolor="#f8f1e5",
            opacity=0.7,
            annotation_text="Construction",
            annotation_position="top left",
            line_width=0,
        )

    # IRI threshold lines
    fig.add_hline(
        y=4.0, line_dash="dot", line_color="#b0bec5", line_width=1,
        annotation_text="Good (IRI 4)",
        annotation_position="bottom right",
        annotation_font=dict(size=9, color="#8a8578"),
    )
    fig.add_hline(
        y=10.0, line_dash="dot", line_color="#b0bec5", line_width=1,
        annotation_text="Poor (IRI 10)",
        annotation_position="bottom right",
        annotation_font=dict(size=9, color="#8a8578"),
    )

    _apply_tara_layout(
        fig,
        title=dict(
            text="Road Deterioration Forecast - IRI Over Time",
            font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"),
            x=0,
            xanchor="left",
        ),
        xaxis_title="Year",
        yaxis_title="International Roughness Index (m/km)",
        height=400,
        margin=dict(l=80, r=30, t=50, b=70),
        yaxis=dict(
            gridcolor="#f0eeea",
            linecolor="#ddd9d1",
            linewidth=1,
            rangemode="tozero",
        ),
    )

    return fig


def get_deterioration_summary(
    iri_current: float,
    surface_type: str,
    adt: float,
    analysis_period: int = 20,
    construction_years: int = 3,
    road_name: str = "Road",
    road_length_km: float = 10.0,
    rainfall_zone: str = "moderate",
    material_quality: str = "average",
) -> dict:
    """
    Compute summary statistics for deterioration analysis.

    Returns:
        Dict with keys: iri_current, iri_do_nothing_end, iri_with_project_end,
        iri_saving_end, years_until_poor, deterioration_rate_k, surface_type,
        road_name, road_length_km, analysis_period, construction_years
    """
    k = compute_k(surface_type, adt, rainfall_zone, material_quality)
    cap_do_nothing = IRI_CAP.get(surface_type, 20.0)
    cap_with = IRI_CAP.get(surface_type, 16.0)
    post_iri = POST_CONSTRUCTION_IRI.get(surface_type, 3.0)
    wp_k = WITH_PROJECT_K.get(surface_type, 0.035)
    maint_iri = MAINTENANCE_RESET_IRI.get(surface_type, 4.0)

    iri_do_nothing = predict_iri(iri_current, analysis_period, k, cap_do_nothing)
    iri_with_project, _ = predict_with_maintenance(
        iri_initial=iri_current,
        years=analysis_period,
        k=k,
        construction_years=construction_years,
        post_construction_iri=post_iri,
        with_project_k=wp_k,
        maintenance_interval=10,
        maintenance_reset_iri=maint_iri,
        cap=cap_with,
    )

    # Years until IRI exceeds 10 (poor) in do-nothing
    poor_threshold = 10.0
    years_until_poor = None
    for t in range(len(iri_do_nothing)):
        if iri_do_nothing[t] >= poor_threshold:
            years_until_poor = t
            break

    # Average IRI difference (the "benefit band")
    iri_diff = iri_do_nothing - iri_with_project
    avg_iri_saving = float(np.mean(iri_diff[construction_years:]))

    return {
        "iri_current": round(iri_current, 1),
        "iri_do_nothing_end": round(float(iri_do_nothing[-1]), 1),
        "iri_with_project_end": round(float(iri_with_project[-1]), 1),
        "iri_saving_end": round(float(iri_do_nothing[-1] - iri_with_project[-1]), 1),
        "avg_iri_saving": round(avg_iri_saving, 1),
        "years_until_poor": years_until_poor,
        "deterioration_rate_k": round(k, 4),
        "post_construction_iri": round(post_iri, 1),
        "surface_type": surface_type,
        "road_name": road_name,
        "road_length_km": round(road_length_km, 1),
        "analysis_period": analysis_period,
        "construction_years": construction_years,
    }


def generate_narrative(summary: dict) -> str:
    """
    Generate a plain-language paragraph describing the deterioration forecast.

    Args:
        summary: Output from get_deterioration_summary()

    Returns:
        Narrative string suitable for report or AI prompt context
    """
    name = summary.get("road_name", "The road")
    iri_now = summary["iri_current"]
    iri_end_dn = summary["iri_do_nothing_end"]
    iri_end_wp = summary["iri_with_project_end"]
    saving = summary["iri_saving_end"]
    years_poor = summary.get("years_until_poor")
    period = summary["analysis_period"]
    constr = summary["construction_years"]

    # Current condition description
    if iri_now <= 4:
        cond = "good"
    elif iri_now <= 6:
        cond = "fair"
    elif iri_now <= 10:
        cond = "poor"
    else:
        cond = "very poor"

    parts = []
    parts.append(
        f"{name} currently has an IRI of {iri_now:.1f} m/km ({cond} condition)."
    )

    if years_poor is not None and years_poor > 0:
        parts.append(
            f"Without intervention, the road will reach poor condition (IRI 10) "
            f"within {years_poor} year{'s' if years_poor != 1 else ''}."
        )
    elif iri_now >= 10:
        parts.append("The road is already in poor condition and deteriorating further.")

    parts.append(
        f"By year {period}, the do-nothing IRI is projected to reach {iri_end_dn:.1f} m/km, "
        f"while the with-project scenario maintains IRI at {iri_end_wp:.1f} m/km "
        f"- a saving of {saving:.1f} m/km in roughness."
    )

    parts.append(
        f"The {constr}-year construction period brings the road to IRI "
        f"{summary['post_construction_iri']:.1f} m/km, with periodic maintenance "
        f"preserving ride quality over the {period}-year analysis period."
    )

    return " ".join(parts)
