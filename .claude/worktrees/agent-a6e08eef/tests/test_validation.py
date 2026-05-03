"""
Unit tests for engine/validation.py — VALD-01 through VALD-07 plus migrated adt_range.
All tests are pure-function assertions with no UI or Dash dependencies.
"""

import pytest
from engine.validation import (
    validate_traffic_population,
    validate_traffic_capacity,
    validate_iri_surface,
    validate_cost_benchmarks,
    validate_voc_proportionality,
    validate_growth_elasticity,
    validate_eirr_reasonableness,
    validate_adt_range,
)


# ── VALD-01: validate_traffic_population ──────────────────────────────────────

class TestValidateTrafficPopulation:
    def test_vald01_high_adt_low_population_warning(self):
        """ADT >> small population should trigger a warning."""
        results = validate_traffic_population(5000, {"population_2km": 200})
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-01"

    def test_vald01_reasonable_ratio_empty(self):
        """ADT=500 with large population is normal — no warning."""
        results = validate_traffic_population(500, {"population_2km": 50000})
        assert results == []

    def test_vald01_no_pop_data(self):
        """No population data — skip validation, return empty."""
        results = validate_traffic_population(500, None)
        assert results == []

    def test_vald01_no_adt(self):
        """No ADT — skip validation, return empty."""
        results = validate_traffic_population(None, {"population_2km": 1000})
        assert results == []

    def test_vald01_missing_population_key(self):
        """Population dict without population_2km key — skip gracefully."""
        results = validate_traffic_population(5000, {"population_5km": 50000})
        assert results == []


# ── VALD-02: validate_traffic_capacity ────────────────────────────────────────

class TestValidateTrafficCapacity:
    def test_vald02_acceptance(self):
        """ADT 15000 on single-lane gravel exceeds capacity (1000) by 15x — error."""
        results = validate_traffic_capacity(15000, "single_lane_gravel")
        assert len(results) == 1
        assert results[0]["level"] == "error"
        assert results[0]["code"] == "VALD-02"
        assert "15" in results[0]["message"]
        assert "exceed" in results[0]["message"].lower() or "exceed" in results[0]["message"].lower()

    def test_vald02_approaching_capacity_warning(self):
        """ADT=850 on single-lane gravel (85% of 1000) — approaching capacity warning."""
        results = validate_traffic_capacity(850, "single_lane_gravel")
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-02"

    def test_vald02_normal_no_warning(self):
        """ADT=500 on single-lane gravel (50%) — fine, empty."""
        results = validate_traffic_capacity(500, "single_lane_gravel")
        assert results == []

    def test_vald02_two_lane_paved_normal(self):
        """ADT=7000 on two-lane paved (87.5%) — still under 1.0 vc_ratio warning threshold for error."""
        results = validate_traffic_capacity(7000, "two_lane_paved")
        # 7000/8000 = 0.875 > 0.8, so should produce a warning (not error)
        assert len(results) == 1
        assert results[0]["level"] == "warning"

    def test_vald02_unknown_road_type_default(self):
        """Unknown road type defaults to two_lane_paved — ADT=500 no warning."""
        results = validate_traffic_capacity(500, "unknown_type")
        assert results == []

    def test_vald02_none_adt(self):
        """None ADT — skip, return empty."""
        results = validate_traffic_capacity(None, "single_lane_gravel")
        assert results == []


# ── VALD-03: validate_iri_surface ─────────────────────────────────────────────

class TestValidateIriSurface:
    def test_vald03_gravel_iri_3_error(self):
        """IRI=3.0 on gravel is physically impossible (min 6 m/km) — error."""
        results = validate_iri_surface("gravel", 3.0)
        assert len(results) == 1
        assert results[0]["level"] == "error"
        assert results[0]["code"] == "VALD-03"
        assert "impossible" in results[0]["message"].lower()
        assert "6" in results[0]["message"]

    def test_vald03_earth_iri_8_error(self):
        """IRI=8.0 on earth road is impossible (min 12 m/km) — error."""
        results = validate_iri_surface("earth", 8.0)
        assert len(results) == 1
        assert results[0]["level"] == "error"
        assert results[0]["code"] == "VALD-03"

    def test_vald03_asphalt_iri_10_warning(self):
        """IRI=10.0 on paved road — unusually high, warning."""
        results = validate_iri_surface("asphalt", 10.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-03"

    def test_vald03_gravel_iri_10_valid(self):
        """IRI=10.0 on gravel — valid gravel range, empty."""
        results = validate_iri_surface("gravel", 10.0)
        assert results == []

    def test_vald03_gravel_iri_22_warning(self):
        """IRI=22.0 on gravel — extreme, warning."""
        results = validate_iri_surface("gravel", 22.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-03"

    def test_vald03_none_iri_skip(self):
        """None IRI — skip, return empty."""
        results = validate_iri_surface("gravel", None)
        assert results == []

    def test_vald03_concrete_iri_10_warning(self):
        """IRI=10.0 on concrete (paved) — unusually high, warning."""
        results = validate_iri_surface("concrete", 10.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"


# ── VALD-04: validate_cost_benchmarks ─────────────────────────────────────────

class TestValidateCostBenchmarks:
    def test_vald04_cost_too_low_warning(self):
        """$500k total / 10km = $50k/km < gravel_to_paved_rural low ($250k)*0.5=$125k — warning."""
        results = validate_cost_benchmarks(total_cost=500000, road_length_km=10, road_type="gravel")
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-04"

    def test_vald04_cost_in_range_empty(self):
        """$4M / 10km = $400k/km — within gravel_to_paved_rural range, empty."""
        results = validate_cost_benchmarks(total_cost=4000000, road_length_km=10, road_type="gravel")
        assert results == []

    def test_vald04_cost_too_high_warning(self):
        """$20M / 10km = $2M/km > gravel_to_paved_rural high ($600k)*2=$1.2M — warning."""
        results = validate_cost_benchmarks(total_cost=20000000, road_length_km=10, road_type="gravel")
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-04"

    def test_vald04_zero_length_skip(self):
        """Zero road length — skip to avoid division by zero, return empty."""
        results = validate_cost_benchmarks(total_cost=1000000, road_length_km=0, road_type="gravel")
        assert results == []

    def test_vald04_none_cost_skip(self):
        """None total_cost — skip, return empty."""
        results = validate_cost_benchmarks(total_cost=None, road_length_km=10, road_type="gravel")
        assert results == []

    def test_vald04_none_length_skip(self):
        """None road_length_km — skip, return empty."""
        results = validate_cost_benchmarks(total_cost=1000000, road_length_km=None, road_type="gravel")
        assert results == []


# ── VALD-05: validate_voc_proportionality ─────────────────────────────────────

class TestValidateVocProportionality:
    def test_vald05_disproportionate_warning(self):
        """IRI delta=1 (small), VOC savings 50% — disproportionate, warning."""
        results = validate_voc_proportionality(iri_before=10.0, iri_after=9.0, voc_savings_pct=0.5)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-05"

    def test_vald05_large_improvement_empty(self):
        """IRI delta=10 (large), VOC savings 50% — improvement justifies savings, empty."""
        results = validate_voc_proportionality(iri_before=14.0, iri_after=4.0, voc_savings_pct=0.5)
        assert results == []

    def test_vald05_none_iri_before_skip(self):
        """None iri_before — skip, return empty."""
        results = validate_voc_proportionality(iri_before=None, iri_after=9.0, voc_savings_pct=0.5)
        assert results == []

    def test_vald05_none_iri_after_skip(self):
        """None iri_after — skip, return empty."""
        results = validate_voc_proportionality(iri_before=10.0, iri_after=None, voc_savings_pct=0.5)
        assert results == []

    def test_vald05_none_voc_savings_skip(self):
        """None voc_savings_pct — skip, return empty."""
        results = validate_voc_proportionality(iri_before=10.0, iri_after=9.0, voc_savings_pct=None)
        assert results == []

    def test_vald05_small_improvement_small_savings_empty(self):
        """IRI delta=1 but VOC savings only 10% — under threshold, empty."""
        results = validate_voc_proportionality(iri_before=10.0, iri_after=9.0, voc_savings_pct=0.10)
        assert results == []


# ── VALD-06: validate_growth_elasticity ───────────────────────────────────────

class TestValidateGrowthElasticity:
    def test_vald06_high_elasticity_warning(self):
        """Growth 7% / GDP 3.5% = elasticity 2.0 — outside 1.0-1.5, warning."""
        results = validate_growth_elasticity(7.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-06"
        assert "2.0" in results[0]["message"] or "2." in results[0]["message"]

    def test_vald06_normal_growth_empty(self):
        """Growth 3.5% / GDP 3.5% = elasticity 1.0 — normal, empty."""
        results = validate_growth_elasticity(3.5)
        assert results == []

    def test_vald06_zero_growth_skip(self):
        """Zero growth rate — skip, return empty."""
        results = validate_growth_elasticity(0)
        assert results == []

    def test_vald06_low_elasticity_warning(self):
        """Growth 2% / GDP 3.5% = elasticity 0.57 — below 1.0, warning."""
        results = validate_growth_elasticity(2.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-06"

    def test_vald06_none_growth_skip(self):
        """None growth_rate_pct — skip, return empty."""
        results = validate_growth_elasticity(None)
        assert results == []


# ── VALD-07: validate_eirr_reasonableness ─────────────────────────────────────

class TestValidateEirrReasonableness:
    def test_vald07_high_eirr_warning(self):
        """EIRR=45% — exceptionally high, warning."""
        results = validate_eirr_reasonableness(45.0)
        assert len(results) == 1
        assert results[0]["level"] == "warning"
        assert results[0]["code"] == "VALD-07"
        assert "45" in results[0]["message"]
        assert "verify" in results[0]["message"].lower()

    def test_vald07_normal_eirr_empty(self):
        """EIRR=25% — normal range, empty."""
        results = validate_eirr_reasonableness(25.0)
        assert results == []

    def test_vald07_none_eirr_skip(self):
        """None EIRR — skip, return empty."""
        results = validate_eirr_reasonableness(None)
        assert results == []

    def test_vald07_negative_eirr_empty(self):
        """EIRR=-5% — negative EIRR not flagged by this validator, empty."""
        results = validate_eirr_reasonableness(-5.0)
        assert results == []

    def test_vald07_exactly_threshold_empty(self):
        """EIRR exactly 40% — at threshold boundary, not triggered (>40% required)."""
        results = validate_eirr_reasonableness(40.0)
        assert results == []


# ── validate_adt_range (migrated from app.py) ─────────────────────────────────

class TestValidateAdtRange:
    def test_adt_range_extreme_high_warning(self):
        """ADT > 50,000 — extreme high, warning."""
        results = validate_adt_range(60000)
        assert len(results) == 1
        assert results[0]["level"] == "warning"

    def test_adt_range_extreme_low_warning(self):
        """ADT < 10 — extreme low, warning."""
        results = validate_adt_range(5)
        assert len(results) == 1
        assert results[0]["level"] == "warning"

    def test_adt_range_normal_empty(self):
        """ADT=1000 — normal range, empty."""
        results = validate_adt_range(1000)
        assert results == []

    def test_adt_range_none_skip(self):
        """None ADT — skip, return empty."""
        results = validate_adt_range(None)
        assert results == []
