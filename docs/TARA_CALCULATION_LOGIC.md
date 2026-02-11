# TARA: Calculation Logic Walkthrough
## For validation before coding — please flag anything wrong or missing

---

## STEP 0: Define Scenarios

Every appraisal compares two futures:
- **Without-project (Do-Minimum):** What happens if we only do routine/periodic maintenance on the existing road?
- **With-project (Do-Something):** What happens if we invest in the proposed improvement?

The economic benefit = the *difference* between these two scenarios.

**User defines:**
- Analysis period (default: 20 years from first year of operation)
- Construction period (e.g., 2-3 years)
- Base year (year of traffic count / cost estimates)
- Discount rate (EOCK — default 12% for Uganda)

---

## STEP 1: Traffic Forecasting

### 1.1 Base Traffic
User provides ADT (Average Daily Traffic) by vehicle class for base year:

| Vehicle Class | ADT (vehicles/day) |
|---|---|
| Cars / Light vehicles | e.g., 3,788 |
| Buses & Light Goods | e.g., 447 |
| Heavy Goods Vehicles | e.g., 633 |
| Semi-trailers / Artics | e.g., 781 |

Can be provided per section or per toll plaza if the road has varying traffic along its length (as in Highway-1 model with 4 plazas).

### 1.2 Normal Traffic Growth
Traffic in year t = Base ADT × (1 + growth_rate)^t

**Growth rate options:**
- **Direct:** User specifies annual growth rate (e.g., 1% for Highway-1)
- **GDP elasticity:** Growth rate = GDP_growth × elasticity_factor
  - Uganda GDP growth ~3.5%
  - Typical elasticity: 1.0-1.5 for cars, 0.8-1.2 for freight
  - So traffic growth = 3.5% × 1.2 = 4.2% for example

**QUESTION FOR YOU:** In Uganda practice, do you typically use a single growth rate for all vehicle classes, or differentiated rates? The Highway-1 model uses a single rate (1%) but that seems low for Uganda. What's typical in UNRA appraisals?

### 1.3 Generated (Induced) Traffic
New traffic that wouldn't have existed without the improvement (diverted + induced demand).

Generated traffic = Normal traffic × (Price elasticity × % change in generalised cost)

From Highway-1 model: Price elasticity = -0.5

Generalised cost change = (RUC_without - RUC_with - Toll) / RUC_without

**QUESTION:** Do UNRA appraisals typically include generated traffic, or is it sometimes omitted for simpler projects? How is it handled for non-tolled roads?

### 1.4 Capacity Check
If forecast traffic exceeds road capacity, cap it and flag congestion.

Capacity of new road = Capacity factor × old road capacity (Highway-1 uses factor of 2)

**Annual traffic volumes:**
AADT × 365 = Annual vehicle-days
Convert to vehicle-km: Annual vehicle-days × section length (km)

---

## STEP 2: Road User Cost Calculations

### 2.1 Vehicle Operating Costs (VOC)
The biggest benefit stream. VOC includes fuel, tyres, oil, maintenance, depreciation.

**Without project (existing road):**

| Vehicle Class | VOC (USD/km) |
|---|---|
| Cars | 0.180 |
| Buses & LGV | 0.490 |
| HGV | 0.930 |
| Semi-trailers | 1.600 |

**With project (improved road):**

| Vehicle Class | VOC (USD/km) |
|---|---|
| Cars | 0.126 |
| Buses & LGV | 0.343 |
| HGV | 0.650 |
| Semi-trailers | 1.120 |

**VOC Saving per vehicle-km** = VOC_without - VOC_with

| Vehicle Class | VOC Saving (USD/km) | % Reduction |
|---|---|---|
| Cars | 0.054 | 30% |
| Buses & LGV | 0.147 | 30% |
| HGV | 0.280 | 30% |
| Semi-trailers | 0.480 | 30% |

**Annual VOC Saving for a section:**
For each vehicle class c, in year t:
```
VOC_saving(c,t) = ADT(c,t) × 365 × section_length(km) × VOC_saving_per_km(c) / 1,000,000
```
(Result in USD millions)

**QUESTION:** In practice, are VOC rates provided as inputs by the user (from HDM-4 or from the unit cost study), or should TARA estimate them from IRI/roughness? The Highway-1 model takes them as direct inputs. For TARA to be truly useful, we might want both options — direct input OR estimated from condition.

### 2.2 Value of Time Savings (VoT)
Same structure as VOC:

**Without project:**

| Vehicle Class | VoT (USD/km) |
|---|---|
| Cars | 0.040 |
| Buses & LGV | 0.110 |
| HGV | 0.210 |
| Semi-trailers | 0.353 |

**With project:**

| Vehicle Class | VoT (USD/km) |
|---|---|
| Cars | 0.028 |
| Buses & LGV | 0.078 |
| HGV | 0.148 |
| Semi-trailers | 0.247 |

**Annual Time Saving** — same formula as VOC.

**QUESTION:** VoT expressed as USD/km implies a speed differential. Is it standard practice in Uganda to use VoT per km (derived from speed and wage rates), or per hour? The Highway-1 model uses per-km which simplifies calculation but hides the speed assumption.

### 2.3 Accident Cost Savings

**Without project:**

| Vehicle Class | Accident Cost (USD/km) |
|---|---|
| Cars | 0.013 |
| Buses & LGV | 0.035 |
| HGV | 0.070 |
| Semi-trailers | 0.114 |

**With project:**

| Vehicle Class | Accident Cost (USD/km) |
|---|---|
| Cars | 0.009 |
| Buses & LGV | 0.025 |
| HGV | 0.050 |
| Semi-trailers | 0.080 |

Same annual calculation approach.

### 2.4 Total Road User Cost (RUC) Summary

RUC = VOC + VoT + Accident Cost

This is the "generalised cost" from the user perspective (excluding tolls).

---

## STEP 3: Agency Cost Calculations (Road Authority)

### 3.1 Construction / Improvement Costs

From Highway-1 model (Moderate Scale):
- Road works: USD 267.53M
- Bridges: USD 24.26M
- Lighting: USD 1.68M
- Traffic signals: USD 3.16M
- Toll plazas: USD 4.85M
- Weighbridges: USD 7.28M
- Truck stops: USD 3.40M
- Construction labor: USD 55.09M
- **Total EPC: USD 367.25M**

Phased over construction period:
- Year 1: 40%, Year 2: 30%, Year 3: 30%

**For TARA, user provides:**
- Total construction cost (or cost per km × length)
- Construction duration
- Phasing schedule (% per year)
- Optional: cost breakdown by component for economic conversion

### 3.2 Maintenance Costs — Without Project

| Type | Cost per km | Frequency |
|---|---|---|
| Routine maintenance | USD 2,560/km/year | Annual |
| Major maintenance | USD 600,000/km | Every 10 years |

**Annual maintenance cost (without project):**
```
Routine: cost_per_km × road_length (every year)
Major: cost_per_km × road_length (in years when scheduled)
```

### 3.3 Maintenance Costs — With Project

| Type | Cost per km | Frequency |
|---|---|---|
| Routine maintenance | USD 4,500/km/year | Annual |
| Periodic maintenance | USD 91,100/km | Every 10 years |
| Major maintenance | USD 214,795/km | At end of concession (Year 23) |

Note: Maintenance costs WITH project are often higher because you're maintaining a higher-standard road.

### 3.4 Agency Cost Saving (or additional cost)

```
Net agency cost = (Construction cost + Maintenance_with) - Maintenance_without
```

This is typically a NET COST (construction outweighs maintenance savings), which is subtracted from user benefits.

**QUESTION:** For non-tolled public roads in Uganda (the more common case), there's no toll revenue. The appraisal is purely economic — costs to government vs. benefits to road users and society. Is that the standard framing for UNRA/MoFPED appraisals? The Highway-1 model includes financial analysis (FNPV, FIRR, debt service) because it's a PPP/concession, but most Ugandan road projects are publicly funded, right?

---

## STEP 4: Economic Conversion (Financial → Economic Prices)

Financial prices include taxes, duties, and market distortions. Economic prices reflect true resource costs to society.

### 4.1 Conversion Factors

From Highway-1 model:
- **Foreign Exchange Premium (FEP):** 7.5%
- **Standard Conversion Factor (SCF):** 1 / (1 + FEP) = 1 / 1.075 = 0.930
- **Premium on Non-tradable Outlays (NTP):** 1%
- **Shadow wage rate factor:** Typically 0.6-0.8 of market wage for unskilled labour in Uganda

### 4.2 Applying Conversion Factors

For each cost item, classify as:
- **Tradable:** Apply SCF (0.930) — e.g., bitumen, equipment, imported materials
- **Non-tradable:** Apply (1 + NTP) = 1.01 — e.g., local services
- **Labour (unskilled):** Apply shadow wage factor — e.g., 0.7
- **Labour (skilled):** Market wage (factor = 1.0)
- **Taxes:** Remove entirely (transfers, not real costs)

**Example: Construction cost conversion**
```
Financial cost: USD 367.25M
Breakdown:
  - Imported materials (40%): 367.25 × 0.40 × 0.930 = 136.62M
  - Local materials (20%): 367.25 × 0.20 × 1.01 = 74.18M
  - Skilled labour (15%): 367.25 × 0.15 × 1.00 = 55.09M
  - Unskilled labour (15%): 367.25 × 0.15 × 0.70 = 38.56M
  - Tax component (10%): removed = 0
Economic cost: 304.45M
```

**QUESTION:** Does UNRA use a standard cost breakdown template for applying conversion factors, or does each appraisal derive these fresh? For TARA, I'm thinking we offer both:
- Quick mode: Apply a single blended SCF to total cost
- Detailed mode: User breaks down costs by component type

### 4.3 Road User Benefits — Already Economic?

VOC, VoT, and Accident costs are typically already in economic prices (they represent real resource costs). But:
- VoT should use economic wage rates
- Accident costs should use willingness-to-pay values

**QUESTION:** Are the VOC/VoT/accident rates used in Uganda (from HDM-4 calibration) already in economic terms, or do they need conversion?

---

## STEP 5: Discounted Cash Flow & Decision Metrics

### 5.1 Year-by-Year Net Benefit Stream

For each year t (from Year 1 to Year T):

```
Net_Benefit(t) = [VOC_saving(t) + VoT_saving(t) + Accident_saving(t)]  ← User benefits
              + [Maintenance_saving(t)]                                   ← Agency benefits  
              + [Generated_traffic_benefit(t)]                            ← Consumer surplus
              + [Residual_value(T) if t = T]                              ← End value
              - [Construction_cost(t)]                                     ← Investment cost
```

All in economic prices.

During construction years: Net benefit is negative (costs, no benefits yet).
During operation years: Net benefit should be positive if project is viable.

### 5.2 Net Present Value (NPV)

```
NPV = Σ [Net_Benefit(t) / (1 + r)^t]  for t = 1 to T
```

Where r = discount rate (EOCK = 12% for Uganda)

**Decision rule:** NPV > 0 → project is economically viable

### 5.3 Economic Internal Rate of Return (EIRR)

The discount rate that makes NPV = 0.

```
Σ [Net_Benefit(t) / (1 + EIRR)^t] = 0
```

Solve numerically (Newton-Raphson or numpy's IRR function).

**Decision rule:** EIRR > EOCK (12%) → project is economically viable

### 5.4 Benefit-Cost Ratio (BCR)

```
BCR = PV(Benefits) / PV(Costs)
```

Where:
- PV(Benefits) = discounted sum of all user benefits + maintenance savings + residual value
- PV(Costs) = discounted sum of construction costs

**Decision rule:** BCR > 1.0 → project is economically viable

### 5.5 First Year Rate of Return (FYRR)

```
FYRR = Net_Benefit(first year of operation) / PV(Construction cost)
```

Used to assess whether the project should be implemented now or deferred.

**Decision rule:** FYRR > discount rate → proceed now; FYRR < discount rate → consider deferring

### 5.6 NPV per km

```
NPV_per_km = NPV / road_length
```

Used for network-level prioritisation when comparing projects of different lengths.

---

## STEP 6: Sensitivity Analysis

### 6.1 Single-Variable Sensitivity

Test each variable independently while holding others at base case:

| Variable | Test Range |
|---|---|
| Construction cost | -20% to +30% |
| Traffic / GDP growth | -2% to +2% from base |
| VOC savings | -30% to +10% |
| VoT savings | -30% to +10% |
| Discount rate | 6% to 18% |
| Construction delay | +1 to +3 years |

For each test point, recalculate NPV and EIRR.

### 6.2 Switching Values

For each variable, find the value that makes NPV = 0.

Example: "Construction costs can increase by 47% before the project becomes unviable."

This is the most useful single output for decision-makers.

### 6.3 Scenario Analysis

| Scenario | Description |
|---|---|
| Base case | All inputs at expected values |
| Optimistic | Low cost, high traffic, high savings |
| Pessimistic | High cost, low traffic, low savings |
| Worst case | Cost overrun + low traffic + construction delay |

### 6.4 Stakeholder Impact Matrix (from Highway-1 model)

For each sensitivity test, show impact on:
- Government (net fiscal impact)
- Road users by class (cars, buses, HGV, semi-trailers)
- Financiers/lenders (if applicable)

### 6.5 AI-Generated Risk Narrative

Opus 4.6 reviews the sensitivity results and generates:
- Which variables the project is most sensitive to
- Whether the project is robust or marginal
- What risks to monitor during implementation
- Recommendations for risk mitigation

---

## STEP 7: Report Generation

### 7.1 Outputs Produced

1. **Summary metrics table:** NPV, EIRR, BCR, FYRR, NPV/km
2. **Year-by-year cashflow table** (costs and benefits by category)
3. **Charts:**
   - Cumulative NPV over time (shows payback period)
   - Benefit composition pie chart (VOC vs. VoT vs. Accident vs. Maintenance)
   - Sensitivity spider diagram
   - Switching values bar chart
4. **Sensitivity tables** (variable × metric matrix)
5. **AI narrative** (executive summary, interpretation, recommendations)

### 7.2 Report Format

Primary: PDF report aligned with MoFPED PIAR structure
Secondary: Interactive HTML dashboard (stretch goal)
Data: CSV/Excel export of all calculations

---

## CALCULATION VALIDATION CHECKLIST

Please confirm or correct:

- [ ] Is 12% the current EOCK used by MoFPED?
- [ ] Is 20 years the standard analysis period?
- [ ] Is the FEP still 7.5%? NTP still 1%?
- [ ] Are VOC/VoT rates from HDM-4 already in economic prices?
- [ ] Is generated traffic typically included in Ugandan appraisals?
- [ ] For non-tolled roads, is it purely economic analysis (no financial)?
- [ ] What traffic growth rates are typical? (1% seems low)
- [ ] Is there a standard cost breakdown for economic conversion?
- [ ] Does MoFPED require FYRR, or just NPV/EIRR/BCR?
- [ ] Any other benefit streams I'm missing? (e.g., producer surplus, wider economic benefits)

---

## WHAT'S NOT IN THE HACKATHON MVP

These are real but we defer them:
- Road deterioration modelling (HDM-4's core strength — complex, needs calibrated models)
- Speed-flow modelling (congestion effects on VOC/VoT)
- Stochastic/Monte Carlo risk analysis
- Multi-criteria analysis
- Network optimisation
- Financial analysis (FNPV, FIRR, debt service — only for PPP projects)
