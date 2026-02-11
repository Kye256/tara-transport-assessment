# TARA: Master Strategy & Planning Document
## Transport Assessment Assistant — Anthropic Claude Code Hackathon
**Last updated:** Tuesday February 10, 2026

---

## 1. PRODUCT DEFINITION

**Name:** TARA — Transport Assessment Assistant

**Tagline:** "From road data to investment decision — in minutes, not months."

**What it is:** An AI agent that autonomously gathers data, assesses road condition, runs economic analysis, and produces professional appraisal reports — with the engineer in the loop for decisions that require institutional knowledge.

**What it is NOT:** A calculator with a chatbot. Not a replacement for HDM-4. Not a simple report generator.

**Problem statements addressed:**
- Problem Statement 1 (Tool That Should Exist): The AI-native road appraisal workflow nobody has built
- Problem Statement 2 (Break the Barriers): Democratises transport appraisal expertise locked behind expensive software and specialist knowledge
- Problem Statement 3 (Amplify Human Judgment): Makes road engineers dramatically more capable without taking them out of the loop

**Core pain points solved (ranked):**
1. Data hunting & assembly — agent gathers 70% of inputs autonomously
2. HDM-4 workflow time — zero setup, natural language interaction
3. Data quality / garbage-in — active validation and cross-referencing
4. Sensitivity analysis done badly — context-aware, not mechanical ±20%
5. Report formatting busywork — auto-generated professional reports
6. No institutional memory — learns from every appraisal
7. Missing equity & environmental analysis — automated using open data
8. Appraisal disconnected from outcomes — monitoring framework (future)

---

## 2. DEMO STRATEGY

**Demo road:** Kasangati–Matugga road (part of Kira–Kasangati–Matugga UNRA project)
- ~10-20km section, peri-urban Wakiso District
- Currently under construction by CICO — mixed condition (complete + under construction + untouched)
- Real UNRA project with published design details
- Includes NMT facilities (cycle lanes, pedestrian walkways)

**Demo flow (3-minute video):**
```
0:00-0:30  Engineer: "Appraise the Kasangati-Matugga road"
           → TARA finds road on OSM, shows map, extracts geometry
           → TARA pulls population/facilities data
           
0:30-1:00  TARA presents findings, generates drive plan with waypoints
           "I need eyes on this road. Here's where to drive and what to look for."

1:00-1:30  [Cut to] Dashcam video uploaded
           → TARA analyses frames, shows condition scoring on map
           
1:30-2:15  TARA runs full analysis:
           → CBA results (NPV, EIRR, BCR)
           → Context-aware sensitivity analysis with reasoning
           → Equity dashboard (population served, accessibility improvements)
           
2:15-2:45  Report generated — PDF opens, professional format
           Agent explains key findings in plain language

2:45-3:00  "This took 5 minutes. It used to take 5 weeks."
```

**Video recording:** Thursday, February 13th. Phone dashcam, Kasangati-Matugga road.

---

## 3. RESOURCES AVAILABLE

### 3.1 Compute & API
| Resource | Details | Budget |
|----------|---------|--------|
| Claude Max subscription | Access to Claude Opus 4.6 via claude.ai / Claude Code | Existing subscription |
| Anthropic API tokens | For TARA's backend API calls (Opus 4.6 + Vision) | $500 budget |
| Claude Code | Agentic coding tool for building TARA | Included in Max |

### 3.2 Hardware
| Item | Status | Notes |
|------|--------|-------|
| Development machine | ✅ Have | Personal computer |
| Phone for dashcam recording | ✅ Have | Modern smartphone |
| **Phone dashboard mount** | ❓ NEED TO BUY | For stable dashcam recording |
| Backup phone/camera | Optional | In case primary phone fails |

### 3.3 Software & Services (all free/open-source)
| Tool | Purpose |
|------|---------|
| Python 3.11+ | Core language |
| Streamlit | Web UI / chat interface |
| Anthropic Python SDK | Claude Opus 4.6 API calls |
| Overpass API (OSM) | Road geometry & facilities data |
| WorldPop API/data | Population & poverty rasters |
| World Bank Open Data API | Transport indicators & benchmarks |
| Folium / Leaflet | Map visualisation |
| Plotly / Matplotlib | Charts |
| NumPy / Pandas | Calculations |
| OpenCV | Video frame extraction |
| ReportLab or python-docx | PDF/DOCX report generation |
| Git / GitHub | Version control & submission (must be open source) |

### 3.4 Data Sources (free, accessible)
| Source | Data | Access Method |
|--------|------|---------------|
| OpenStreetMap | Road geometry, surface type, width, facilities | Overpass API |
| WorldPop | Population density, poverty estimates | Raster download or API |
| World Bank | Transport indicators, project benchmarks | Open Data API |
| UBOS | Uganda population statistics | Public downloads |
| SRTM | Elevation data for terrain classification | Public download |
| Humanitarian Data Exchange | Health facilities, schools | CSV/API |

### 3.5 Reference Materials (uploaded/available)
| Document | Use |
|----------|-----|
| Highway-1 Excel model | CBA calculation structure & parameters |
| Philip Kazibwe writeup | Interpretation framework & benchmarks |
| UNRA HDM-4 Calibration 2024 | Uganda-specific vehicle fleet & deterioration parameters |
| Tim Schwanen equity slides | Equity assessment framework |
| HDM360 concept note | Original vision & pain points |
| Hackathon event details | Rules, judging criteria, schedule |

---

## 4. TECHNOLOGY STACK

```
FRONTEND:        Streamlit (Python)
                 - Chat interface (st.chat_message)
                 - Map display (Folium)
                 - File upload (dashcam video)
                 - Charts (Plotly)
                 - Report download

AGENT CORE:      Claude Opus 4.6 (via Anthropic API)
                 - Orchestration & reasoning
                 - Natural language interaction
                 - Data validation & interpretation
                 - Report narrative generation
                 - Dashcam video analysis (Vision API)

ANALYSIS ENGINE: Python
                 - NumPy/Pandas for calculations
                 - CBA module (VOC, VoT, accident savings, NPV, EIRR, BCR)
                 - Traffic forecasting module
                 - Sensitivity analysis module
                 - Equity scoring module

DATA SKILLS:     Python modules (agent invokes as tools)
                 - osm_road_lookup (Overpass API)
                 - osm_facilities (Overpass API)
                 - worldpop_corridor (raster extraction)
                 - worldbank_benchmarks (API)
                 - dashcam_assess (Claude Vision)

OUTPUT:          Python
                 - PDF report generator (ReportLab or FPDF)
                 - Chart generator (Plotly/Matplotlib)
                 - Map generator (Folium)

REPO:            GitHub (public, MIT license)
```

---

## 5. API TOKEN BUDGET

$500 total for Anthropic API. Estimated usage:

| Use Case | Model | Est. Tokens/Call | Est. Calls | Est. Cost |
|----------|-------|-----------------|------------|-----------|
| Agent orchestration | Opus 4.6 | ~4K in / ~2K out | ~200 during dev + demo | ~$120 |
| Data validation reasoning | Opus 4.6 | ~3K in / ~1K out | ~100 | ~$40 |
| Sensitivity narrative | Opus 4.6 | ~5K in / ~2K out | ~50 | ~$35 |
| Report narrative | Opus 4.6 | ~8K in / ~3K out | ~30 | ~$35 |
| Dashcam video analysis | Opus 4.6 Vision | ~10K in (images) / ~2K out | ~50 | ~$80 |
| Testing & iteration | Mixed | Various | Various | ~$100 |
| **Buffer** | | | | **~$90** |
| **TOTAL** | | | | **~$500** |

**Risk:** Vision API for dashcam could be expensive if processing many frames. Mitigation: sample frames (every 5-10 seconds, not every frame). Test costs early.

**QUESTION TO RESOLVE:** Check current Opus 4.6 API pricing. Confirm Vision API pricing for image inputs.

---

## 6. HARDWARE TO BUY

| Item | Est. Cost | Priority | Notes |
|------|-----------|----------|-------|
| Phone dashboard mount (suction cup) | $5-15 USD | **MUST HAVE** | For stable dashcam recording Thursday |
| Power bank / car charger | $0 (likely have) | Nice to have | Phone recording video drains battery |

**Action:** Buy phone mount by Wednesday evening at latest.

---

## 7. TEAM

| Role | Person | Notes |
|------|--------|-------|
| Domain expert / Product owner | You | Transport engineering, UNRA context, field recording |
| AI/Development | Claude (via Claude Code + this conversation) | Architecture, coding, agent design |
| Teammate (hackathon allows up to 2) | TBD | Check Discord for potential partner? |

**Decision needed:** Are you looking for a teammate or going solo? Deadline for team formation is ongoing.

---

## 8. BUILD PLAN — RISK-ADJUSTED

### The Golden Rule: At every stage, we have something presentable.

This is the critical insight. We don't build features in isolation — we build in **complete vertical slices** so that if we run out of time at any point, we have a working demo.

### Tier 1: MINIMUM VIABLE DEMO (Must complete by Saturday night)
**If everything goes wrong, this is what we present.**

- [ ] Streamlit app with chat interface
- [ ] User types road name → TARA finds it on OSM → shows map with road highlighted
- [ ] TARA displays road attributes (length, surface, width) and nearby facilities
- [ ] User provides traffic + cost inputs via chat
- [ ] CBA engine calculates NPV, EIRR, BCR
- [ ] Basic sensitivity analysis (construction cost, traffic, discount rate)
- [ ] Results displayed with charts
- [ ] AI-generated narrative summary of findings

**This alone is a working product.** It's a smart road appraisal tool that finds the road for you, validates your inputs, runs analysis, and explains the results. Not as impressive as the full loop, but submittable.

### Tier 2: STRONG DEMO (Target: complete by Sunday night)
**Adds the "wow" factor.**

Everything in Tier 1, PLUS:
- [ ] Dashcam video upload → Claude Vision analyses frames → condition scores
- [ ] Condition assessment displayed on map (colour-coded sections)
- [ ] Drive plan generation (TARA tells you where to drive and what to look for)
- [ ] Context-aware sensitivity analysis (agent reasons about which variables matter)
- [ ] Equity dashboard (population served, poverty data, accessibility changes)
- [ ] PDF report generation in professional format

### Tier 3: FULL VISION (Stretch — if time allows)
Everything in Tier 2, PLUS:
- [ ] International benchmark comparison (World Bank, UK Green Book)
- [ ] Institutional memory (store and recall past appraisals)
- [ ] Environmental/climate scoring
- [ ] Multiple roads / network comparison
- [ ] Advanced charts (sensitivity spiders, cumulative NPV curves)

---

## 9. DAILY BUILD SCHEDULE

### Tuesday Feb 10 (Today) — FOUNDATION
**Goal: Project scaffolding + OSM data skill working**
- [ ] Set up GitHub repo (public, MIT license)
- [ ] Streamlit app skeleton with chat interface
- [ ] OSM road lookup skill (Overpass API) — tested on Kasangati-Matugga
- [ ] OSM facilities skill (health, education, markets near corridor)
- [ ] Basic map display with road + facilities

**End of day check:** Can TARA find the Kasangati-Matugga road and show it on a map? ✅ = on track

### Wednesday Feb 11 — ANALYSIS ENGINE
**Goal: CBA engine + data validation working**
- [ ] CBA calculation module (VOC, VoT, accident savings → NPV, EIRR, BCR)
- [ ] Traffic forecasting module (compound growth + GDP elasticity)
- [ ] Basic sensitivity analysis (single variable + switching values)
- [ ] Input validation logic (cross-reference checks)
- [ ] WorldPop population data integration
- [ ] Wire chat interface to analysis engine

**End of day check:** Can user provide inputs → get CBA results with validation? ✅ = on track

**Live session 12:30-1:15 PM EST:** AMA with Cat Wu (Claude Code Product Lead) — worth attending

### Thursday Feb 13 — VIDEO + FIELD DAY
**Goal: Dashcam pipeline + you record video**
- [ ] Video frame extraction pipeline (OpenCV — sample every N seconds)
- [ ] Claude Vision analysis of road frames (surface type, distress, features)
- [ ] Condition scoring aggregation (frames → section scores → map)
- [ ] **YOU: Record dashcam video of Kasangati-Matugga road**

**End of day check:** Can TARA take a video and produce a condition map? ✅ = on track

### Friday Feb 14 — INTEGRATION
**Goal: Full loop working end-to-end**
- [ ] Connect: OSM lookup → drive plan → video upload → condition → CBA → results
- [ ] Equity scoring module (population, poverty, accessibility)
- [ ] Context-aware sensitivity (agent reasoning about uncertainty)
- [ ] Chart generation (benefit breakdown, sensitivity, equity dashboard)
- [ ] Test full flow with real Kasangati-Matugga data + video

**Live session 12:00-1:00 PM EST:** Live Coding with Thariq Shihipar — worth attending

**End of day check:** Full loop works? ✅ = on track for strong demo

### Saturday Feb 15 — REPORTS + POLISH
**Goal: Professional output + edge cases**
- [ ] PDF report generator (PIAR-style format)
- [ ] AI narrative generation for each section
- [ ] Error handling and edge cases
- [ ] Drive plan generator (GPS waypoints, sections of interest)
- [ ] International benchmarks (stretch)
- [ ] Test with different roads / parameters

**Live session 12:00-1:00 PM EST:** Tips & Tricks with Lydia Hallie — worth attending

### Sunday Feb 16 — DEMO PREP
**Goal: Demo video recorded and submitted**
- [ ] Final testing and bug fixes
- [ ] Rehearse 3-minute demo flow
- [ ] Record demo video
- [ ] Write 100-200 word summary
- [ ] Ensure GitHub repo is clean, documented, and public
- [ ] **SUBMIT by 3:00 PM EST Monday** (but aim to be ready Sunday night)

### Monday Feb 17 — BUFFER + SUBMIT
- [ ] Final polish if needed
- [ ] Submit via CV platform by 3:00 PM EST
- [ ] Breathe

---

## 10. RISK REGISTER

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Dashcam video analysis doesn't work well enough | Lose Tier 2 "wow" | Medium | Test early Thursday. Fallback: use pre-classified condition data |
| OSM data for Kasangati-Matugga is incomplete | Weakens data gathering demo | Low | Wikipedia + web search already shows good OSM coverage. Test today. |
| WorldPop data hard to integrate in time | Lose equity scoring | Medium | Fallback: use UBOS district-level population data (simpler) |
| API costs higher than expected | Run out of budget | Low-Medium | Monitor costs daily. Use Sonnet for non-critical calls. Cache responses. |
| Video recording fails Thursday | No dashcam demo | Low | Can re-record Friday/Saturday. Or use YouTube footage as backup. |
| Phone mount not available | Shaky unusable video | Low | Buy mount Wednesday. Worst case: passenger holds phone steady. |
| Full loop too complex to integrate | Half-working demo | Medium | Tier system ensures Tier 1 is always complete and presentable |
| Overpass API rate limits | Can't fetch OSM data | Low | Cache results. One-time fetch, store locally. |
| Claude Vision API changes or is slow | Dashcam analysis unreliable | Low-Medium | Test early. Pre-process frames. Have fallback condition data. |

---

## 11. JUDGING CRITERIA ALIGNMENT

| Criterion (Weight) | How TARA Scores |
|--------------------|-----------------|
| **Impact (25%)** | Every road agency in Africa faces these pain points. Turns 5-week process into 5 minutes. Open source, free. Direct beneficiaries: UNRA, MoWT, KCCA, district engineers, development partners, consulting firms. |
| **Opus 4.6 Use (25%)** | Deeply agentic: reasons about data quality, chooses analysis methods, interprets results in context, generates drive plans, uses Vision for dashcam, writes narrative reports. Multi-tool orchestration. Not just "generate text." |
| **Depth & Execution (20%)** | Real engineering methodology calibrated to Uganda. Real data sources (OSM, WorldPop). Real road (UNRA project). Novel equity dimension. International benchmarking. |
| **Demo (30%)** | Full loop: road name → autonomous data gathering → drive plan → dashcam upload → condition analysis → CBA + equity → professional report. "This took 5 minutes." |

---

## 12. SUBMISSION CHECKLIST

- [ ] 3-minute demo video (max)
- [ ] Open source repository (GitHub, MIT license)
- [ ] All components open source (backend, frontend, models, assets)
- [ ] Written summary (100-200 words)
- [ ] Submit via CV platform by Monday 3:00 PM EST
- [ ] No pre-existing code (all new work)

---

## 13. OPEN QUESTIONS

- [ ] Teammate: going solo or finding someone on Discord?
- [ ] Confirm Opus 4.6 API pricing (check current rates)
- [ ] Which specific section of Kasangati-Matugga to record?
- [ ] Do we need any Uganda-specific datasets downloaded in advance (WorldPop rasters)?
- [ ] Phone mount — where to buy locally before Thursday?
