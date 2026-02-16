# TARA — Demo Narrative & Storyline
## Working Document (will be updated section by section)
**Status:** Section 1 drafted, Sections 2-7 outline only

---

## SECTION 1: THE PROBLEM

### The Continent-Scale Context

Africa invests only 4% of its GDP in infrastructure, compared to 14% in China. The AfDB now estimates the continent needs $181–221 billion per year between 2023 and 2030 — and transport infrastructure accounts for the largest share of the gap at 72.9%. In 2018 — the last year with comprehensive tracking — total infrastructure commitments reached a record $100.8 billion, with $32.5 billion going to transport. The AfDB alone has invested over $44 billion over the last seven years in road corridors, ports, railways and power interconnections. As of 2022, it had financed 25 transport corridors, constructed over 18,000 km of roads, 27 border posts and 16 bridges.

These are serious numbers. But the scale of what's needed dwarfs what's being delivered. 80% of African goods move by road and 90% of passenger traffic travels on roads, yet only 53% of roads on the continent are paved and just 43% of the rural population has access to an all-season road. Road freight tariffs are twice those in the United States, and transport costs add 30–40% to the final price of commodities traded within Africa. Poor infrastructure has resulted in an estimated 40% loss in productivity and up to a 2-percentage-point reduction in annual economic growth.

Billions flow into African road infrastructure every year. The problem isn't a lack of ambition or even a lack of money. The problem sits upstream: **project preparation**.

### The Project Preparation Bottleneck

The problem isn't a shortage of roads that need building. It's a shortage of **bankable projects** — projects that have been studied, appraised, and documented well enough to meet financier requirements. According to McKinsey, less than 10% of African infrastructure projects reach financial close. 80% fail at the feasibility stage. Up to 90% fail before financial close.

Project preparation — the pre-feasibility studies, feasibility studies, economic appraisals, environmental assessments — costs 5–12% of total project value and can take up to seven years to complete. For a $50 million road project, that's $2.5–6 million and years of consultant time before a single meter of road gets built.

The NEPAD Infrastructure Project Preparation Facility (NEPAD-IPPF) was created in 2002 specifically to address this — a $126 million multi-donor fund hosted by the AfDB to prepare regional infrastructure projects. Since 2004, it has approved 106 grants totalling $115 million, mobilising $11.35 billion in downstream investment. But it is perpetually under-resourced: by 2019, cumulative donor contributions of $102 million had been almost entirely committed, with the fund warning it could no longer support new project preparation without fresh contributions.

The AfDB alone has invested over $50 billion in infrastructure over eight years. Transport is the largest sector in its portfolio at 25%. Yet the Center for Global Development notes that neither the Global Gateway nor the G7's PGII have dedicated plans for project preparation — the very step that determines whether projects can attract financing.

### The Road Appraisal Problem Specifically

Zoom into the road sector and the bottleneck becomes even clearer. Every road investment decision — whether to upgrade, what standard to build to, whether the benefits justify the costs — requires an economic appraisal. The standard tool is HDM-4 (Highway Development and Management), developed over 55 years of World Bank research and used in over 100 countries. It is the de facto standard required by multilateral development banks for road investment appraisal.

But HDM-4 has problems:

- **It hasn't had a major upgrade in 20 years.** The World Bank and partners (AsDB, FCDO, EIB, PIARC) are working on an upgrade, but the current version is missing functionality demanded by 21st-century users — including socio-economic analysis, climate resilience, and cloud-based access.
- **It requires specialist knowledge.** Operating HDM-4 requires training (offered by TRL once or twice a year at specific locations) and significant calibration effort. Three levels of calibration exist, from desk-based estimates to major field surveys. Most road agencies in Africa rely on external consultants to run it.
- **It's licensed software** distributed exclusively through TRL, with pricing based on country category and end-user type. For Special Consideration Countries (most of Sub-Saharan Africa), discounted pricing exists, but the broader ecosystem of training, calibration, and consultant fees adds up.
- **The data requirements are enormous.** Road geometry, traffic counts, vehicle fleet composition, pavement condition, deterioration parameters, vehicle operating cost relationships, value of time — all must be assembled, validated, and formatted before HDM-4 can run. This data gathering is where 70% of the time goes.

The Cabo Verde Roads and Bridges evaluation found that alternative methodologies to HDM-4 can be more cost-effective and more suitable for some countries' contexts. But the alternatives (like the World Bank's Roads Economic Decision model) are simpler tools that sacrifice analytical depth.

### What This Means on the Ground

A district engineer in rural Uganda who knows their roads intimately — which sections flood in the rains, where the gravel has worn through to earth, which communities are cut off — cannot translate that knowledge into an investment case without:

1. Hiring a consultant (often international) who knows HDM-4
2. Commissioning traffic counts ($5,000–15,000 per count station)
3. Commissioning a road condition survey ($10,000–50,000 depending on equipment)
4. Waiting weeks or months for the analysis
5. Receiving a report they may not fully understand

The result: roads that desperately need investment sit in a queue because nobody can prepare the appraisal. Projects that do get appraised take so long that the data is outdated by the time the report is complete. And the few agencies that can afford the tools and consultants end up reappraising the same high-profile corridors while secondary and rural roads — the ones that connect communities to health facilities, schools, and markets — never make it into the pipeline.

**This is the gap TARA was built to address.**

---

## SECTION 2: THE INSIGHT / OPPORTUNITY
*[TO BE FILLED — covers why Opus 4.6 is the right technology for this problem]*

### Key points to develop:
- Road appraisal is a **reasoning** problem, not a calculation problem
- The hard part is knowing which data matters, whether inputs are plausible, what risks are real for this context
- Opus 4.6 can reason across domains simultaneously (engineering, economics, demographics, geography)
- Vision API turns a $15 phone mount into a road condition survey tool
- Open data revolution (OSM, WorldPop, World Bank) provides 70% of inputs — but nobody built the agent to assemble it
- The 20-year gap in HDM-4 development = opportunity for a fundamentally different approach
- Not replacing HDM-4 — complementing it. TARA is the "junior engineer who does the legwork" so the senior engineer can focus on judgment

---

## SECTION 3: THE BUILD STORY
*[TO BE FILLED — the journey of building TARA during the hackathon]*

### Key points to develop:
- Started with search-first workflow (type a road name)
- Pivoted to video-first after recording dashcam footage of Kasangati-Matugga road (active UNRA construction project)
- The pivot insight: the user does ONE thing (uploads a drive-through), the agent does everything else — that's truly agentic
- Built with Claude Code using multi-agent architecture (orchestrator + specialised sub-agents)
- Sub-agents working in parallel on separate modules: frame extraction, GPS matching, vision analysis, section grouping, intervention recommendation
- Hooks for autonomous operation (auto-approve safe commands, block destructive ones, builder-critic loop)
- Real field data: drove the roads, recorded with phone dashcam + GPS tracker app
- Two routes recorded: Kasangati→Matugga (12.5km, UNRA project road) and Matugga→Kiteezi (7.6km, different surface/condition)
- Homogeneous sectioning emerged as key insight — breaking drives into sections by surface type and condition, each with its own intervention

---

## SECTION 4: HOW IT WORKS
*[TO BE FILLED — the demo walkthrough, step by step]*

### Key points to develop:
- **Upload:** Dashcam footage + GPX track from phone
- **Frame extraction:** OpenCV samples every 5 seconds, resizes to 1280px, encodes as base64
- **GPS matching:** Parse GPX trackpoints, match each frame by timestamp, interpolate coordinates
- **Claude Vision analysis:** Each frame assessed for surface type, condition class, IRI estimate, distress types, road features — structured JSON output
- **Homogeneous sectioning:** Group frames by surface type changes, condition changes, and distance limits. Each section = separate analysis unit
- **Per-section intervention:** Uganda-calibrated costs (regravelling $60k/km, DBST $800k/km, AC $1M/km, dualling+NMT $2.5M/km)
- **Full CBA:** NPV, EIRR, BCR, FYRR with calibrated VOC/VoT from 2024 UNRA HDM-4 study
- **Context-aware sensitivity:** Opus reasons about which variables are uncertain for THIS project
- **Equity overlay:** OSM facilities (health, education, markets) along corridor + population data
- **Report generation:** PDF with AI narrative, charts, equity summary

---

## SECTION 5: WHAT MAKES THIS DIFFERENT
*[TO BE FILLED — not a calculator with a chatbot]*

### Key points to develop:
- **Video-first workflow** — phone replaces survey vehicle
- **Autonomous data assembly** — agent gathers, doesn't wait for forms
- **Homogeneous sectioning from video** — automatic, per-section interventions
- **Active validation with reasoning** — not just range checks, but contextual flags with explanations
- **Context-aware sensitivity** — AI reasons about project-specific uncertainty
- **Equity built in** — not an afterthought
- **Cost: under $6 per road survey** vs $10,000–50,000 for traditional condition survey
- **Time: 5 minutes** vs weeks/months for traditional appraisal
- **Open source** — democratises expertise locked behind licensed software

---

## SECTION 6: WHERE THIS GOES / IMPACT
*[TO BE FILLED — future vision and real-world impact]*

### Key points to develop:
- Every road agency in Sub-Saharan Africa faces these pain points
- Construction supervision use case — drive weekly, compare to last week, flag quality issues
- Network-level screening — run TARA on 100 roads to identify where investment gives best returns
- Institutional memory — 50th appraisal is dramatically better than the first
- Deterioration modelling on roadmap
- Could transform the project preparation bottleneck — if you can appraise a road in 5 minutes, you can build a pipeline of bankable projects
- Direct link to NEPAD-IPPF mission: "address the lack of investment-ready projects"
- Potential to shift equity analysis from afterthought to standard practice

---

## SECTION 7: OPUS 4.6 USAGE
*[TO BE WOVEN THROUGHOUT — not a separate section in the final narrative]*

### Where Opus 4.6 is used:
- **Vision API:** Frame-by-frame road condition assessment from dashcam footage
- **Data validation reasoning:** Cross-referencing inputs against benchmarks, flagging outliers with explanations
- **Sensitivity reasoning:** Context-aware analysis of which variables are uncertain for this specific project
- **Intervention selection:** Reasoning about appropriate treatment based on surface type, condition, traffic context
- **Narrative generation:** 5+ distinct reasoning tasks:
  1. Condition assessment narrative
  2. CBA interpretation
  3. Sensitivity explanation
  4. Equity context
  5. Executive summary
- **Built with Claude Code:** Multi-agent workflow, hooks, sub-agents for parallel development

---

## 200-WORD SUMMARY (DRAFT — to be refined after all sections are complete)

*[TO BE WRITTEN after narrative is finalized]*

### Target structure:
- Sentence 1-2: The problem (project preparation bottleneck, billions stuck)
- Sentence 3-4: What TARA is (autonomous agent, not a calculator)
- Sentence 5-7: How it works (video-first, Vision API, autonomous data, per-section analysis)
- Sentence 8-9: What makes it different (reasoning not just calculating, equity built in)
- Sentence 10-11: Impact and Claude usage
- Sentence 12: The punchline

---

## RESEARCH NOTES (for reference)

### Key Statistics
- **AfDB revised estimate (2023-2030):** $181–221 billion/year infrastructure needs
- **Transport share of financing gap:** 72.9% (largest sector) — AEO 2024
- **Annual financing gap to close for structural transformation:** $402.2 billion (AEO 2024)
- **Actual spending (2018 peak):** $100.8 billion total infrastructure commitments
- **Transport sector spending (2018):** $32.5 billion
- **AfDB transport track record:** $44B invested over 7 years; 25 corridors, 18,000km roads, 27 border posts
- **Africa invests only 4% of GDP in infrastructure** vs 14% in China
- Only 53% of roads paved, 43% rural population with access to all-season road
- 80% goods transported by road, 90% passenger traffic
- Transport costs = 30–40% of final commodity price (intra-Africa trade)
- Poor infrastructure = 40% productivity loss, 2pp reduction in annual growth
- Less than 10% of infrastructure projects reach financial close (McKinsey)
- 80% of projects fail at feasibility stage
- Up to 90% fail before financial close
- Project preparation costs 5–12% of project value, up to 7 years
- NEPAD-IPPF: $126.4M fund, approved 106 grants totalling $115M, mobilised $11.35B
- HDM-4: 55 years of development, used in 100+ countries, 20 years since major upgrade
- **Uganda-specific:** Road project costs vary wildly — Parliament found costs ranged from $1.4M to $3.8M per km for similar roads (Auditor General 2023-24)

### Key Sources
- McKinsey: "Solving Africa's infrastructure paradox" (2020)
- CGD: "Bottlenecks in Africa's Infrastructure Financing" 
- CGD: "Designing Roads for Africa's Future"
- ISS Africa Futures: "Large Infrastructure"
- AfDB/NEPAD-IPPF reports and oversight committee minutes
- World Bank: HDM-4 Phase II upgrade documentation
- TRL: HDM-4 software distribution
- AUDA-NEPAD: "The Missing Connection" white paper

### Key Institutions
- NEPAD-IPPF (project preparation facility, $126M fund)
- Africa50 (AfDB infrastructure investment fund)
- PIDA (Programme for Infrastructure Development in Africa, $160.8B for 2021-2030)
- AUDA-NEPAD (African Union Development Agency)
- ICA (Infrastructure Consortium for Africa)
- Global Infrastructure Facility (G20)
- EU Global Gateway (€150B for Africa)
- G7 PGII (Partnership for Global Infrastructure and Investment)
