"""
TARA Chart Generation
Creates Plotly charts for CBA results, sensitivity analysis, traffic forecasts, and cashflows.
Uses TARA brand colour palette and consistent layout.
"""

import plotly.graph_objects as go
from typing import Optional


# --- TARA Brand Colours ---
TARA_COLORS = [
    "#2d5f4a",  # primary green
    "#3d8b6e",  # light green
    "#9a6b2f",  # amber
    "#3a5a80",  # blue
    "#a83a2f",  # red
    "#6b8f71",  # sage
    "#c4956a",  # tan
]

TARA_COST_COLOR = "#a83a2f"     # red for costs
TARA_BENEFIT_COLOR = "#2d5f4a"  # green for benefits
TARA_NPV_COLOR = "#9a6b2f"     # amber for NPV line

# --- Global Chart Layout ---
TARA_CHART_LAYOUT = dict(
    font=dict(family="Source Sans 3, sans-serif", size=12, color="#2c2a26"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=60, r=20, t=50, b=60),
    title=dict(font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="left",
        x=0,
        font=dict(size=11),
    ),
    xaxis=dict(gridcolor="#f0eeea", linecolor="#ddd9d1", linewidth=1),
    yaxis=dict(gridcolor="#f0eeea", linecolor="#ddd9d1", linewidth=1),
)


def _apply_tara_layout(fig: go.Figure, **overrides) -> go.Figure:
    """Apply TARA chart layout with optional overrides."""
    layout = {**TARA_CHART_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


def create_tornado_chart(sensitivity_results: dict) -> go.Figure:
    """
    Create a tornado chart showing NPV sensitivity to each variable.

    Args:
        sensitivity_results: Output from engine.sensitivity.run_sensitivity_analysis()

    Returns:
        Plotly Figure with horizontal bars sorted by NPV impact magnitude
    """
    base_npv = sensitivity_results["base_case"]["npv"]
    single_var = sensitivity_results.get("single_variable", {})

    variables = []
    low_impacts = []
    high_impacts = []

    for var_name, results in single_var.items():
        if not results:
            continue

        npv_values = [r["npv"] for r in results if "npv" in r]
        if not npv_values:
            continue

        min_npv = min(npv_values)
        max_npv = max(npv_values)
        low_impact = min_npv - base_npv
        high_impact = max_npv - base_npv

        variables.append(_format_variable_name(var_name))
        low_impacts.append(low_impact)
        high_impacts.append(high_impact)

    # Sort by total swing magnitude (largest on top)
    swing = [abs(h - l) for h, l in zip(high_impacts, low_impacts)]
    sorted_indices = sorted(range(len(swing)), key=lambda i: swing[i])
    variables = [variables[i] for i in sorted_indices]
    low_impacts = [low_impacts[i] for i in sorted_indices]
    high_impacts = [high_impacts[i] for i in sorted_indices]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=variables,
        x=low_impacts,
        orientation="h",
        name="Downside",
        marker_color=TARA_COST_COLOR,
        hovertemplate="$%{x:,.0f}<extra>Downside</extra>",
    ))

    fig.add_trace(go.Bar(
        y=variables,
        x=high_impacts,
        orientation="h",
        name="Upside",
        marker_color=TARA_BENEFIT_COLOR,
        hovertemplate="$%{x:,.0f}<extra>Upside</extra>",
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="#8a8578")

    _apply_tara_layout(fig,
        title=dict(text="Sensitivity Analysis — NPV Impact by Variable",
                   font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
        xaxis_title="Change in NPV (USD)",
        yaxis_title="",
        barmode="overlay",
        height=350,
        margin=dict(l=150, r=30, t=50, b=70),
    )

    return fig


def create_waterfall_chart(cba_results: dict) -> go.Figure:
    """
    Create a waterfall chart showing benefit and cost components leading to NPV.

    Args:
        cba_results: Output from engine.cba.run_cba()

    Returns:
        Plotly Figure with waterfall from costs to NPV
    """
    cashflows = cba_results.get("yearly_cashflows", [])
    discount_rate = cba_results.get("discount_rate", 0.12)

    # Sum PV of each component across all years
    pv_construction = 0.0
    pv_maintenance = 0.0
    pv_voc = 0.0
    pv_vot = 0.0
    pv_accident = 0.0
    pv_generated = 0.0
    pv_residual = 0.0

    for cf in cashflows:
        t = cf["year_index"]
        df = 1 / (1 + discount_rate) ** t
        pv_construction -= cf["costs"]["construction"] * df
        pv_maintenance -= cf["costs"]["net_maintenance"] * df
        pv_voc += cf["benefits"]["voc_savings"] * df
        pv_vot += cf["benefits"]["vot_savings"] * df
        pv_accident += cf["benefits"]["accident_savings"] * df
        pv_generated += cf["benefits"]["generated_traffic"] * df
        pv_residual += cf["benefits"]["residual_value"] * df

    categories = [
        "Construction Cost",
        "Net Maintenance",
        "VOC Savings",
        "Time Savings",
        "Accident Savings",
        "Generated Traffic",
        "Residual Value",
        "NPV",
    ]
    values = [
        round(pv_construction),
        round(pv_maintenance),
        round(pv_voc),
        round(pv_vot),
        round(pv_accident),
        round(pv_generated),
        round(pv_residual),
        0,  # NPV will be "total"
    ]
    measure = ["relative"] * 7 + ["total"]

    fig = go.Figure(go.Waterfall(
        x=categories,
        y=values,
        measure=measure,
        connector={"line": {"color": "#ddd9d1"}},
        increasing={"marker": {"color": TARA_BENEFIT_COLOR}},
        decreasing={"marker": {"color": TARA_COST_COLOR}},
        totals={"marker": {"color": TARA_NPV_COLOR}},
        textposition="outside",
        text=[f"${v:,.0f}" if v != 0 else "" for v in values],
        hovertemplate="$%{y:,.0f}<extra>%{x}</extra>",
    ))

    _apply_tara_layout(fig,
        title=dict(text="Benefit & Cost Breakdown (Present Value)",
                   font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
        yaxis_title="Present Value (USD)",
        height=400,
        margin=dict(l=80, r=30, t=50, b=80),
        showlegend=False,
    )

    return fig


def create_traffic_growth_chart(cba_results: dict) -> go.Figure:
    """
    Create a traffic growth chart showing ADT over the analysis period.

    Args:
        cba_results: Output from engine.cba.run_cba() (contains traffic_forecast)

    Returns:
        Plotly Figure with line chart of ADT + capacity threshold
    """
    traffic = cba_results.get("traffic_forecast", {})
    yearly = traffic.get("yearly", [])
    capacity = traffic.get("capacity", 8000)

    if not yearly:
        return _empty_figure("No traffic data available")

    years = [y["calendar_year"] for y in yearly]
    total_adt = [y["total_adt"] for y in yearly]
    normal_adt = [y["normal_adt"] for y in yearly]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years, y=total_adt,
        mode="lines+markers",
        name="Total ADT",
        line=dict(color=TARA_BENEFIT_COLOR, width=3),
        marker=dict(size=4),
        hovertemplate="%{y:,.0f} vpd<extra>Total ADT</extra>",
    ))

    fig.add_trace(go.Scatter(
        x=years, y=normal_adt,
        mode="lines",
        name="Normal Traffic",
        line=dict(color="#b0bec5", width=1.5, dash="dash"),
        hovertemplate="%{y:,.0f} vpd<extra>Normal</extra>",
    ))

    # Capacity line
    fig.add_hline(
        y=capacity, line_dash="dash", line_color=TARA_COST_COLOR,
        annotation_text=f"Capacity ({capacity:,} vpd)",
        annotation_position="top right",
    )

    # Mark construction period with amber shading
    construction_years = traffic.get("construction_years", 0)
    if construction_years > 0 and len(years) > construction_years:
        fig.add_vrect(
            x0=years[0], x1=years[construction_years - 1],
            fillcolor="#f8f1e5", opacity=0.7,
            annotation_text="Construction", annotation_position="top left",
            line_width=0,
        )

    _apply_tara_layout(fig,
        title=dict(text="Traffic Forecast",
                   font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
        xaxis_title="Year",
        yaxis_title="Average Daily Traffic (vehicles/day)",
        height=350,
        margin=dict(l=80, r=30, t=50, b=70),
    )

    return fig


def create_cashflow_chart(cba_results: dict) -> go.Figure:
    """
    Create a cashflow chart with stacked bars (costs/benefits) and cumulative NPV line.

    Args:
        cba_results: Output from engine.cba.run_cba()

    Returns:
        Plotly Figure with stacked bars + cumulative NPV line
    """
    cashflows = cba_results.get("yearly_cashflows", [])
    discount_rate = cba_results.get("discount_rate", 0.12)

    if not cashflows:
        return _empty_figure("No cashflow data available")

    years = [cf["calendar_year"] for cf in cashflows]
    construction = [-cf["costs"]["construction"] for cf in cashflows]
    maintenance = [-cf["costs"]["net_maintenance"] for cf in cashflows]
    voc = [cf["benefits"]["voc_savings"] for cf in cashflows]
    vot = [cf["benefits"]["vot_savings"] for cf in cashflows]
    accident = [cf["benefits"]["accident_savings"] for cf in cashflows]

    # Cumulative discounted NPV
    cumulative_npv = []
    running = 0.0
    for cf in cashflows:
        t = cf["year_index"]
        df = 1 / (1 + discount_rate) ** t
        running += cf["net_benefit"] * df
        cumulative_npv.append(running)

    fig = go.Figure()

    fig.add_trace(go.Bar(x=years, y=construction, name="Construction", marker_color=TARA_COST_COLOR,
                         hovertemplate="$%{y:,.0f}<extra>Construction</extra>"))
    fig.add_trace(go.Bar(x=years, y=maintenance, name="Net Maintenance", marker_color="#c4956a",
                         hovertemplate="$%{y:,.0f}<extra>Maintenance</extra>"))
    fig.add_trace(go.Bar(x=years, y=voc, name="VOC Savings", marker_color=TARA_BENEFIT_COLOR,
                         hovertemplate="$%{y:,.0f}<extra>VOC Savings</extra>"))
    fig.add_trace(go.Bar(x=years, y=vot, name="Time Savings", marker_color="#3a5a80",
                         hovertemplate="$%{y:,.0f}<extra>Time Savings</extra>"))
    fig.add_trace(go.Bar(x=years, y=accident, name="Accident Savings", marker_color="#6b8f71",
                         hovertemplate="$%{y:,.0f}<extra>Accident Savings</extra>"))

    fig.add_trace(go.Scatter(
        x=years, y=cumulative_npv,
        mode="lines+markers",
        name="Cumulative NPV",
        line=dict(color=TARA_NPV_COLOR, width=3),
        marker=dict(size=4),
        yaxis="y2",
        hovertemplate="$%{y:,.0f}<extra>Cumulative NPV</extra>",
    ))

    _apply_tara_layout(fig,
        title=dict(text="Annual Cashflows & Cumulative NPV",
                   font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
        xaxis_title="Year",
        yaxis_title="Annual Amount (USD)",
        yaxis2=dict(
            title="Cumulative NPV (USD)",
            overlaying="y",
            side="right",
            gridcolor="#f0eeea",
        ),
        barmode="relative",
        height=400,
        margin=dict(l=80, r=80, t=50, b=70),
    )

    return fig


def create_scenario_chart(sensitivity_results: dict) -> go.Figure:
    """
    Create a grouped bar chart comparing scenarios (base/optimistic/pessimistic/worst).

    Args:
        sensitivity_results: Output from engine.sensitivity.run_sensitivity_analysis()

    Returns:
        Plotly Figure with grouped bars for each scenario's NPV
    """
    base = sensitivity_results.get("base_case", {})
    scenarios = sensitivity_results.get("scenarios", {})

    names = ["Base Case"]
    npvs = [base.get("npv", 0)]
    colors = [TARA_COLORS[3]]  # blue

    scenario_config = [
        ("optimistic", "Optimistic", TARA_BENEFIT_COLOR),
        ("pessimistic", "Pessimistic", TARA_NPV_COLOR),
        ("worst_case", "Worst Case", TARA_COST_COLOR),
    ]

    for key, label, color in scenario_config:
        if key in scenarios and "error" not in scenarios[key]:
            names.append(label)
            npvs.append(scenarios[key].get("npv", 0))
            colors.append(color)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=names,
        y=npvs,
        marker_color=colors,
        text=[f"${v:,.0f}" for v in npvs],
        textposition="outside",
        hovertemplate="$%{y:,.0f}<extra>%{x}</extra>",
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="#8a8578")

    _apply_tara_layout(fig,
        title=dict(text="Scenario Analysis — NPV Comparison",
                   font=dict(family="Libre Franklin, sans-serif", size=15, color="#2c2a26"), x=0, xanchor="left"),
        yaxis_title="NPV (USD)",
        height=350,
        margin=dict(l=80, r=30, t=50, b=60),
        showlegend=False,
    )

    return fig


def _format_variable_name(name: str) -> str:
    """Format a variable name for display."""
    labels = {
        "construction_cost": "Construction Cost",
        "traffic_volume": "Traffic Volume",
        "traffic_growth": "Traffic Growth Rate",
        "voc_savings": "VOC Savings",
        "discount_rate": "Discount Rate",
        "construction_delay": "Construction Delay",
    }
    return labels.get(name, name.replace("_", " ").title())


def _empty_figure(message: str) -> go.Figure:
    """Create an empty figure with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#8a8578"),
    )
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white", height=300,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
