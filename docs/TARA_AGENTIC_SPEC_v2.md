# TARA: Transport Appraisal & Road Assessment
## Agentic Architecture Specification v2.0
*"The junior engineer who does the legwork."*

---

## 1. Core Concept

TARA is not a calculator with a chatbot. TARA is an AI agent that autonomously assembles data, runs analysis, validates results, and produces reports — with the engineer in the loop for decisions and institutional knowledge that only humans have.

**The interaction model:**
```
Engineer: "Appraise the upgrade of Gulu-Atiak road from gravel to paved"

TARA: [autonomously]
  → Finds road on OpenStreetMap (47km, gravel, 6m width)
  → Pulls population along corridor from WorldPop (120,000 people)
  → Identifies 3 health centres, 8 schools, 2 markets within 5km
  → Estimates traffic range from road class + population benchmarks
  → Searches World Bank data for comparable project benchmarks
  → Assembles everything into a draft input dataset

TARA: "Here's what I've found. I need you to confirm or correct:
  - Traffic: I'm estimating 350-500 ADT. Do you have actual counts?
  - Cost: What's the estimated construction cost per km?
  - Condition: Current IRI? Or upload a dashcam video and I'll estimate it."

Engineer: "Traffic count from last year was 420. Cost is $280k/km. IRI about 12."

TARA: [autonomously]
  → Validates inputs (IRI 12 on gravel = reasonable, flags if not)
  → Runs full CBA with Uganda-calibrated parameters
  → Performs sensitivity analysis, identifies critical variables
  → Scores equity impact using population/poverty/accessibility data
  → Generates formatted report with narrative interpretation
  → Cross-references results against international benchmarks

TARA: "The project has an EIRR of 22% and NPV of $14.2M. It's robust — 
  viable even if costs overrun by 40% or traffic is 30% lower than expected.
  The equity score is high: this road serves 120,000 people currently 
  3+ hours from the nearest hospital. Here's the full report."
```

---

## 2. Pain Points → Agent Behaviours

| Rank | Pain Point | Agent Behaviour |
|------|-----------|-----------------|
| 1 | **Data hunting & assembly** | Autonomous data gathering from OSM, WorldPop, World Bank. Agent assembles 70% of inputs without user action. |
| 2 | **HDM-4 workflow time** | Zero setup. Natural language input. Agent handles all data preparation, formatting, and parameter selection. |
| 3 | **Data quality / garbage-in** | Active validation: cross-references inputs against benchmarks, flags outliers, explains why something looks wrong, suggests corrections. |
| 4 | **Sensitivity analysis done badly** | Context-aware sensitivity: agent reasons about which variables are actually uncertain for THIS project and tests those, not arbitrary ±20%. |
| 5 | **Report formatting busywork** | Auto-generated report in MoFPED/donor format with charts, tables, and narrative. Export to PDF/Word. |
| 6 | **No institutional memory** | Agent learns from every appraisal. Builds knowledge base of parameters, benchmarks, and lessons across projects. |
| 7 | **Missing equity & environment** | Autonomous equity scoring using population, poverty, accessibility data the agent gathers itself. |
| 8 | **Disconnected from outcomes** | Post-appraisal monitoring framework: compare predictions vs. actual (future phase). |

---

## 3. Agentic Capabilities

### 3.1 Autonomous Data Gathering

**What TARA gets on its own:**

| Data | Source | What It Extracts |
|------|--------|-----------------|
| Road geometry | OpenStreetMap (Overpass API) | Length, width, surface type, number of lanes, bridges, junctions |
| Road alignment | OSM + SRTM elevation | Rise & fall, curvature, terrain classification |
| Population served | WorldPop raster data | Population within 5km/10km buffer of corridor, poverty headcount |
| Accessibility | OSM + WorldPop | Travel time to nearest health facility, school, market — before and after improvement |
| Climate | Open climate data | Rainfall, temperature, moisture zone classification for pavement design |
| Benchmarks | World Bank Open Data | Transport indicators, comparable project EIRRs by country and road type |
| Facilities | OSM / Humanitarian Data Exchange | Health centres, schools, markets, water points along corridor |

**What TARA estimates when data is missing:**

| Missing Data | Estimation Method | Confidence |
|-------------|-------------------|------------|
| Traffic (ADT) | Road class × population served × regional benchmarks | Low — flags for user confirmation |
| Road condition (IRI) | Surface type × age × climate zone (deterioration model) OR dashcam video analysis | Medium (model) / Medium-High (dashcam) |
| VOC rates | Function of IRI and vehicle class using calibrated relationships from UNRA HDM-4 study | Medium — uses published calibration |
| VoT rates | GDP per capita × occupancy × speed differential | Medium |
| Construction cost/km | Road type × terrain × Uganda unit cost benchmarks | Low-Medium — flags for user input |

**What TARA asks the user for:**

| Data | Why It Can't Be Autonomous |
|------|---------------------------|
| Actual traffic counts | Locked in UNRA institutional systems |
| Detailed road condition survey | Requires field data (unless dashcam is used) |
| Construction cost estimate | Project-specific, from feasibility study |
| Design standard | Engineering decision |
| Specific maintenance strategy | Policy/institutional decision |

### 3.2 Active Data Validation

This is where Opus 4.6 reasoning makes TARA more than a tool.

**Cross-reference checks the agent performs automatically:**

| Check | Logic |
|-------|-------|
| Traffic vs. population | ADT of 5,000 on a road serving 10,000 people? Flag: "Traffic seems high relative to catchment population." |
| Traffic vs. road class | 10,000 ADT on a single-lane gravel road? Flag: "This exceeds typical capacity. Verify count or check if road has been upgraded." |
| IRI vs. surface type | IRI of 3 on a gravel road? Flag: "Unusually smooth for gravel. Expected range is 6-16 m/km." |
| Cost vs. benchmarks | $800k/km for a rural gravel-to-paved upgrade? Flag: "Above typical range of $250-500k/km for Uganda. Includes bridges or difficult terrain?" |
| VOC savings vs. IRI change | 50% VOC reduction for a 2-point IRI improvement? Flag: "Savings seem high. Typical relationship suggests 25-35% for this IRI change." |
| Growth rate vs. GDP | Traffic growth of 8% with GDP growth of 3.5%? Flag: "Implied elasticity of 2.3 is unusually high. Typical range is 1.0-1.5." |
| EIRR reasonableness | EIRR of 65%? Flag: "Exceptionally high. Only 5% of World Bank road projects exceed 40%. Review inputs for errors." |

**The agent doesn't just flag — it explains its reasoning and suggests what to check.** This is the "amplify human judgment" angle from Problem Statement 3.

### 3.3 Context-Aware Sensitivity Analysis

Instead of mechanical ±20% on everything, the agent reasons:

```
"For this project, I've identified the following key risks:

1. TRAFFIC VOLUME (High uncertainty): This is a gravel road with no 
   permanent count station. The count you provided (420 ADT) is a single 
   observation. I'm testing ±30% range and finding the switching value.

2. CONSTRUCTION COST (Medium uncertainty): Uganda road construction has 
   experienced 15-25% overruns in recent years. Testing up to +40%.

3. TRAFFIC GROWTH (Medium uncertainty): The corridor connects to South 
   Sudan border. Cross-border traffic is volatile. Testing GDP elasticity 
   range of 0.8-1.5 rather than a fixed growth rate.

4. MAINTENANCE EXECUTION (Often overlooked): If periodic maintenance is 
   delayed from Year 10 to Year 15, benefits erode significantly. I'm 
   testing this scenario because maintenance backlogs are common in Uganda.

I'm NOT heavily testing discount rate or VOC rates because:
- Discount rate is set by MoFPED policy (12%) — unlikely to change
- VOC rates are well-calibrated from the 2024 UNRA HDM-4 study"
```

This is reasoning, not calculation. It's what a senior economist would do but a junior one wouldn't think to do.

### 3.4 Institutional Memory

Every appraisal TARA runs adds to its knowledge base:

- **Parameter library:** VOC rates, growth rates, unit costs used across projects — with source and date
- **Benchmark database:** EIRR/BCR/NPV ranges by road type, region, and traffic level
- **Lessons learned:** "On the last 5 gravel-to-paved upgrades in Northern Uganda, actual traffic growth was 60% of forecast. Consider using conservative growth assumptions for this region."
- **Data quality patterns:** "Traffic counts from Station X have historically been 20% higher than corroborating data. Consider adjustment."

This accumulates over time. The 50th appraisal TARA runs is dramatically better than the first because it has context from the previous 49.

### 3.5 Autonomous Equity & Accessibility Scoring

Because TARA gathers population, poverty, and facility data autonomously, equity assessment happens automatically — not as an add-on the engineer has to do manually.

**What the agent calculates without being asked:**

| Metric | Method |
|--------|--------|
| Population impact | WorldPop: people within 5km/10km of corridor |
| Poverty-weighted benefit | Population × poverty headcount ratio × benefit per capita |
| Health accessibility change | Travel time to nearest health facility: before vs. after (using OSM routing) |
| Education accessibility change | Travel time to nearest school: before vs. after |
| Market access change | Travel time to nearest market: before vs. after |
| Gender impact estimate | Differential weighting for NMT trips (predominantly women in rural Uganda) |
| Equity-weighted NPV | Standard NPV adjusted with distributional weights (UK Green Book method) |

**Output:** A simple equity dashboard alongside the economic analysis:
```
EQUITY IMPACT SUMMARY — Gulu-Atiak Road

Population served:         120,000 (of which 68% below poverty line)
Health access improvement: Average travel time to health centre drops 
                          from 3.2 hours to 1.1 hours
Education access:          12 schools become accessible within 1 hour 
                          (previously 4)
Market access:             Weekly market reachable by 85% of corridor 
                          population (previously 40%)

Equity-Weighted NPV:       $18.7M (vs standard NPV of $14.2M)
→ This project disproportionately benefits disadvantaged populations,
  which increases its social value by 32% under distributional weighting.
```

This is the kind of output that wins development partner funding. And the engineer didn't have to do any of it — the agent assembled the data and ran the analysis.

---

## 4. Technical Architecture

```
┌─────────────────────────────────────────────────┐
│                 TARA AGENT                       │
│            (Opus 4.6 Orchestrator)               │
│                                                   │
│  Understands intent → Plans actions → Executes    │
│  → Validates → Reports → Learns                  │
└───────────────┬───────────────────────────────────┘
                │
    ┌───────────┼───────────────────────┐
    │           │                       │
    ▼           ▼                       ▼
┌─────────┐ ┌──────────┐ ┌──────────────────────┐
│  DATA   │ │ ANALYSIS │ │      OUTPUT          │
│ SKILLS  │ │ ENGINE   │ │      SKILLS          │
├─────────┤ ├──────────┤ ├──────────────────────┤
│ OSM     │ │ CBA Core │ │ Report Generator     │
│ WorldPop│ │ Traffic  │ │ Chart Engine         │
│ World   │ │ Forecast │ │ Narrative Writer     │
│  Bank   │ │ Sensitiv.│ │ PDF/DOCX Export      │
│ Climate │ │ Equity   │ │ Dashboard (HTML)     │
│ Dashcam │ │ Environ. │ │ Data Export (CSV)    │
│ (Vision)│ │ Benchmark│ │                      │
└─────────┘ └──────────┘ └──────────────────────┘
                │
                ▼
        ┌──────────────┐
        │   MEMORY     │
        │              │
        │ Parameters   │
        │ Benchmarks   │
        │ Past projects│
        │ Lessons      │
        └──────────────┘
```

### 4.1 Agent Skills (modular, extensible)

Each skill is a self-contained capability the agent can invoke:

**Data Skills:**
- `osm_road_lookup` — Find road, extract geometry, surface, width
- `osm_facilities` — Find health, education, market facilities near corridor
- `worldpop_corridor` — Extract population and poverty data for buffer zone
- `worldbank_benchmarks` — Pull transport indicators and project benchmarks
- `dashcam_assess` — Analyse video frames for road condition (Claude Vision)
- `climate_lookup` — Get rainfall/temperature for corridor location

**Analysis Skills:**
- `traffic_forecast` — Compound growth or GDP elasticity projection
- `cba_calculate` — Full economic cost-benefit analysis
- `sensitivity_analyse` — Context-aware sensitivity with switching values
- `equity_score` — Distributional impact assessment
- `environmental_score` — Lifecycle carbon and climate resilience
- `benchmark_compare` — Cross-reference with international standards

**Output Skills:**
- `report_generate` — Formatted PDF/DOCX in PIAR structure
- `chart_create` — NPV curves, sensitivity spiders, benefit breakdowns
- `narrative_write` — Plain-language interpretation of results
- `dashboard_build` — Interactive HTML summary

### 4.2 Agent Decision Flow

```
1. UNDERSTAND
   - Parse user request (road name, location, intervention type)
   - Determine scope (single road, corridor, network)

2. GATHER
   - Invoke data skills in parallel
   - OSM → road geometry + facilities
   - WorldPop → population + poverty
   - World Bank → benchmarks
   - Estimate missing values with confidence levels

3. PRESENT & ASK
   - Show user what was found
   - Highlight gaps that need human input
   - Suggest estimates for missing data with reasoning
   - Ask targeted questions (not a blank form)

4. VALIDATE
   - Cross-reference all inputs against benchmarks
   - Flag outliers with explanations
   - Suggest corrections
   - Iterate with user if needed

5. ANALYSE
   - Run CBA with validated inputs
   - Perform context-aware sensitivity analysis
   - Calculate equity and environmental scores
   - Compare against benchmarks

6. REPORT
   - Generate formatted report
   - Write narrative interpretation
   - Produce charts and summary dashboard
   - Export in required format

7. LEARN
   - Store parameters, results, and context
   - Update benchmark database
   - Record any corrections user made (improves future estimates)
```

---

## 5. Hackathon Build Plan (Revised)

### Priority 1: The "Wow" Demo (Days 1-3)
- [ ] Agent takes a road name → finds it on OSM → extracts geometry
- [ ] Agent pulls WorldPop population data for corridor
- [ ] Agent presents findings and asks targeted questions
- [ ] Agent validates user inputs against benchmarks
- [ ] CBA engine runs and produces results
- [ ] Context-aware sensitivity analysis with reasoning
- [ ] Formatted report with AI narrative

### Priority 2: Depth (Days 4-5)
- [ ] Dashcam video → condition assessment (Claude Vision)
- [ ] Equity scoring with accessibility analysis
- [ ] International benchmark comparison
- [ ] Institutional memory (store and recall past appraisals)

### Priority 3: Polish (Day 6)
- [ ] Demo flow optimisation
- [ ] Report formatting refinement
- [ ] 3-minute video recording

---

## 6. What Makes This Win the Hackathon

**Impact:** Every road agency in Africa faces these exact pain points. TARA turns a 2-week process into 2 hours.

**Opus 4.6 Use:** This is deeply agentic — the LLM reasons about data quality, chooses analysis methods, interprets results in context, and uses vision for dashcam analysis. It's not just generating text — it's making engineering decisions.

**Depth & Execution:** Real methodology, real data sources, real institutional context. This isn't a toy.

**Demo:** "I said 'appraise the Gulu-Atiak road' and the agent went and found the road, gathered population data, estimated traffic, asked me three questions, ran a full economic analysis, scored the equity impact, and produced a report. The whole thing took 5 minutes."

That's not a calculator with a chatbot. That's an AI that actually does things.
