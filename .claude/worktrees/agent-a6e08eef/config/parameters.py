"""
TARA Default Parameters for Uganda
Source: UNRA HDM-4 Calibration 2024, Highway-1 Excel Model, MoFPED guidelines
"""

# Economic parameters
EOCK = 0.12  # Economic Opportunity Cost of Capital (discount rate)
FEP = 0.075  # Foreign Exchange Premium
NTP = 0.01   # Non-Tradable Premium
SCF = 1 / (1 + FEP)  # Standard Conversion Factor = 0.930

# Analysis parameters
ANALYSIS_PERIOD = 20  # years from first year of operation
BASE_YEAR = 2026
RESIDUAL_VALUE_FACTOR = 0.75  # % of EPC as residual value at end of analysis

# Vehicle classes
VEHICLE_CLASSES = ["Cars", "Buses_LGV", "HGV", "Semi_Trailers"]

VEHICLE_CLASS_LABELS = {
    "Cars": "Cars / Light Vehicles",
    "Buses_LGV": "Buses & Light Goods Vehicles",
    "HGV": "Heavy Goods Vehicles",
    "Semi_Trailers": "Semi-Trailers / Articulated",
}

# Vehicle Operating Costs (USD/vehicle-km) — from Highway-1 model
# These are representative values; actual values depend on IRI/roughness
VOC_RATES = {
    "without_project": {
        "Cars": 0.180,
        "Buses_LGV": 0.490,
        "HGV": 0.930,
        "Semi_Trailers": 1.600,
    },
    "with_project": {
        "Cars": 0.126,
        "Buses_LGV": 0.343,
        "HGV": 0.650,
        "Semi_Trailers": 1.120,
    },
}

# Value of Time (USD/vehicle-km) — from Highway-1 model
VOT_RATES = {
    "without_project": {
        "Cars": 0.040,
        "Buses_LGV": 0.110,
        "HGV": 0.210,
        "Semi_Trailers": 0.353,
    },
    "with_project": {
        "Cars": 0.028,
        "Buses_LGV": 0.078,
        "HGV": 0.148,
        "Semi_Trailers": 0.247,
    },
}

# Accident Costs (USD/vehicle-km) — from Highway-1 model
ACCIDENT_RATES = {
    "without_project": {
        "Cars": 0.013,
        "Buses_LGV": 0.035,
        "HGV": 0.070,
        "Semi_Trailers": 0.114,
    },
    "with_project": {
        "Cars": 0.009,
        "Buses_LGV": 0.025,
        "HGV": 0.050,
        "Semi_Trailers": 0.080,
    },
}

# Traffic growth defaults
DEFAULT_TRAFFIC_GROWTH_RATE = 0.035  # 3.5% (GDP-linked)
GDP_GROWTH_RATE = 0.035  # Uganda average
TRAFFIC_GDP_ELASTICITY = 1.0  # Conservative default

# Generated traffic
PRICE_ELASTICITY_DEMAND = -0.5  # From Highway-1 model

# Maintenance costs (USD/km) — representative values
MAINTENANCE_COSTS = {
    "without_project": {
        "routine_annual": 2560,       # USD/km/year
        "major_periodic": 600000,     # USD/km
        "major_frequency_years": 10,
    },
    "with_project": {
        "routine_annual": 4500,       # USD/km/year
        "periodic": 91100,            # USD/km
        "periodic_frequency_years": 10,
        "major": 214795,              # USD/km (end of life)
    },
}

# Construction cost benchmarks (USD/km) — for validation
CONSTRUCTION_COST_BENCHMARKS = {
    "gravel_to_paved_rural": {"low": 250000, "typical": 400000, "high": 600000},
    "gravel_to_paved_urban": {"low": 500000, "typical": 800000, "high": 1500000},
    "rehabilitation_paved": {"low": 100000, "typical": 200000, "high": 400000},
    "new_dual_carriageway": {"low": 1000000, "typical": 2000000, "high": 4000000},
}

# Construction phasing defaults
DEFAULT_CONSTRUCTION_YEARS = 3
DEFAULT_CONSTRUCTION_PHASING = {1: 0.40, 2: 0.30, 3: 0.30}

# Economic conversion factors
ECONOMIC_CONVERSION = {
    "imported_materials_share": 0.40,
    "local_materials_share": 0.20,
    "skilled_labour_share": 0.15,
    "unskilled_labour_share": 0.15,
    "tax_share": 0.10,
    "shadow_wage_unskilled": 0.70,  # Factor applied to market wage
    "skilled_labour_factor": 1.00,
}

# Road capacity defaults (vehicles/day)
ROAD_CAPACITY = {
    "single_lane_gravel": 1000,
    "two_lane_gravel": 3000,
    "two_lane_paved": 8000,
    "dual_carriageway": 25000,
}

# IRI benchmarks by surface type (m/km)
IRI_BENCHMARKS = {
    "paved_good": {"min": 2, "max": 4},
    "paved_fair": {"min": 4, "max": 6},
    "paved_poor": {"min": 6, "max": 10},
    "gravel_good": {"min": 6, "max": 10},
    "gravel_fair": {"min": 10, "max": 14},
    "gravel_poor": {"min": 14, "max": 20},
    "earth": {"min": 12, "max": 25},
}

# Sensitivity analysis defaults
SENSITIVITY_VARIABLES = {
    "construction_cost": {"test_range": [-0.20, -0.10, 0.10, 0.20, 0.30]},
    "traffic_volume": {"test_range": [-0.30, -0.20, -0.10, 0.10, 0.20]},
    "traffic_growth": {"test_range": [-0.02, -0.01, 0.01, 0.02]},  # Absolute change
    "voc_savings": {"test_range": [-0.30, -0.20, -0.10, 0.10]},
    "discount_rate": {"test_values": [0.06, 0.08, 0.10, 0.12, 0.15, 0.18]},
    "construction_delay": {"test_values": [1, 2, 3]},  # Additional years
}

# WorldPop parameters
WORLDPOP_API_URL = "https://api.worldpop.org/v1/services/stats"
WORLDPOP_DATASET = "wpgppop"
WORLDPOP_YEAR = 2020
WORLDPOP_RASTER_URL = "https://data.worldpop.org/GIS/Population/Global_2000_2020/{year}/UGA/uga_ppp_{year}.tif"
WORLDPOP_RASTER_DIR = "data/worldpop"
POPULATION_BUFFERS_KM = [2.0, 5.0, 10.0]
UGANDA_POPULATION_GROWTH_RATE = 0.03  # ~3% per year for extrapolating 2020→current
WORLDPOP_POLL_TIMEOUT = 120  # seconds; increased from 60 to avoid truncation on large bounding boxes (>5000km2). Per STAB-05.

# Density classification thresholds (people/km²)
DENSITY_THRESHOLDS = {
    "rural": 150,       # < 150/km²
    "peri-urban": 1500,  # 150–1500/km²
    "urban": float("inf"),  # > 1500/km²
}

# Validation thresholds (engine/validation.py)
VALIDATION_THRESHOLDS = {
    # VALD-01: Traffic vs population
    "adt_pop_ratio_high": 0.5,        # ADT > population_2km * 0.5 = suspiciously high
    "adt_pop_ratio_low": 0.001,       # ADT < population_2km * 0.001 = suspiciously low
    # VALD-02: Capacity ratios
    "capacity_warning_ratio": 0.8,    # V/C > 0.8 = approaching capacity (warning)
    "capacity_error_ratio": 1.0,      # V/C > 1.0 = exceeds capacity (error)
    # VALD-03: IRI limits by surface
    "gravel_iri_min": 6.0,            # Gravel IRI < 6 = impossible (TMH12/HDM-4)
    "earth_iri_min": 12.0,            # Earth IRI < 12 = impossible
    "paved_iri_max_warning": 8.0,     # Paved IRI > 8 = unusually high
    "gravel_iri_max_warning": 20.0,   # Gravel IRI > 20 = extreme
    # VALD-04: Cost benchmark tolerance
    "cost_low_factor": 0.5,           # cost_per_km < benchmark.low * 0.5 = warning
    "cost_high_factor": 2.0,          # cost_per_km > benchmark.high * 2.0 = warning
    # VALD-05: VOC proportionality
    "voc_savings_max_pct": 0.20,      # VOC savings > 20% of benefits with IRI delta < 2 = warning
    "iri_delta_threshold": 2.0,       # IRI improvement < 2 m/km = "small improvement"
    # VALD-06: GDP elasticity range
    "elasticity_min": 1.0,
    "elasticity_max": 1.5,
    # VALD-07: EIRR threshold
    "eirr_high_threshold": 40.0,      # EIRR > 40% = verify inputs
    # VALD-01 existing inline thresholds (migrated from app.py)
    "adt_extreme_high": 50000,        # Existing: ADT > 50,000 = very high
    "adt_extreme_low": 10,            # Existing: ADT < 10 = very low
}

# Road type mapping: OSM surface tags -> ROAD_CAPACITY keys
SURFACE_TO_CAPACITY_KEY = {
    "gravel": "single_lane_gravel",
    "compacted": "single_lane_gravel",
    "earth": "single_lane_gravel",
    "dirt": "single_lane_gravel",
    "unpaved": "single_lane_gravel",
    "asphalt": "two_lane_paved",
    "concrete": "two_lane_paved",
    "paved": "two_lane_paved",
}

# Road type mapping: surface -> CONSTRUCTION_COST_BENCHMARKS key
SURFACE_TO_COST_BENCHMARK = {
    "gravel": "gravel_to_paved_rural",
    "compacted": "gravel_to_paved_rural",
    "earth": "gravel_to_paved_rural",
    "dirt": "gravel_to_paved_rural",
    "unpaved": "gravel_to_paved_rural",
    "asphalt": "rehabilitation_paved",
    "concrete": "rehabilitation_paved",
    "paved": "rehabilitation_paved",
}

# Uganda poverty estimates (UBOS 2019/20 survey)
POVERTY_HEADCOUNT_RATIO = {
    "rural": 0.24,
    "peri-urban": 0.16,
    "urban": 0.12,
    "national": 0.21,
}

# Equity parameters
POVERTY_LINE_USD_DAY = 2.15  # World Bank international poverty line
WALKING_SPEED_KMH = 4.5
CYCLING_SPEED_KMH = 15
VEHICLE_SPEED_GRAVEL_KMH = 40
VEHICLE_SPEED_PAVED_KMH = 70
