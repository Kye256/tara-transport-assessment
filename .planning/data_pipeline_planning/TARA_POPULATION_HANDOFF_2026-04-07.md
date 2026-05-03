# TARA Population Handoff

**Date:** April 7, 2026  
**Branch:** `Tara_Version_2`  
**Purpose:** Record what changed on the branch, what was reviewed, and why population integration is deferred for merge to `main`.

---

## 1. Branch Context

`Tara_Version_2` made three major data pipeline changes:

- Replaced live Overpass facility calls with local facility data.
- Switched road search and road selection to the local UNRA road dataset.
- Added a new population integration path using Kontur H3 population data plus UBOS subcounty overlays.

The first two changes are directionally correct and can move forward. The third requires more work before it is suitable for merge.

---

## 2. What Was Changed

### Roads

- Local UNRA road GeoJSON became the preferred road source.
- Road search was updated to use the local road database rather than remote OSM search.
- Road selection UI was updated to show UNRA-specific attributes such as road reference and UNRA class.

### Facilities

- Live Overpass queries were removed from the road selection flow.
- Facilities are now loaded from local GeoJSON files at startup.
- Facility counts continue to support map rendering and corridor context without internet dependency.

### Population

- A new `skills.population` path was added to compute corridor population from Kontur H3 hexagons.
- UBOS subcounty boundaries were introduced as the administrative reference layer.
- Equity, report, and UI components were updated to consume population outputs.

### Merge-Prep Change Made After Review

- Active population integration has been disabled for merge.
- Population-based equity metrics and report claims are deferred pending a verified Uganda population methodology.

---

## 3. Review Findings

The review identified four issues that make the current population path unsuitable for merge as an active feature:

1. The runtime path depends on geospatial Python packages that were not part of the branch runtime environment.
2. The implementation truncated road geometry, which makes many corridor population numbers unreliable.
3. The pipeline depended on modeled population surfaces that are useful for screening but not yet defensible as authoritative reported figures.
4. The branch risked depending on local processed artifacts that are not appropriate to assume on a clean checkout unless their role is explicitly managed.

The key conclusion was not that population analysis is impossible, but that it is not yet at the standard required for defended production reporting.

---

## 4. Discussion Summary

The following points came out of the review discussion:

- Concern raised: the population integration needed careful review because the underlying data sources might not be clean enough.
- Question raised: whether to wait for Uganda Bureau of Statistics data or proceed with UN/HDX modeled population data such as WorldPop or Kontur.
- Assessment: UBOS is likely to be the better source of authoritative administrative totals, but not necessarily a ready-made corridor-buffer population product.
- Assessment: WorldPop and Kontur can help spatially distribute population, but they are modeled surfaces and should not be presented as authoritative corridor population figures without validation.
- Conclusion reached: having a defensible number matters more than having a population feature now.
- Decision reached: do not merge `Tara_Version_2` with active population outputs turned on.

The branch should move forward without population analysis rather than ship a number that is difficult to defend.

---

## 5. Merge Decision

For merge into `main`:

- Keep roads integration.
- Keep local facilities integration.
- Disable active population integration.
- Remove population-based equity claims from runtime UI and reports.
- Keep equity only on non-population inputs for now.

Population is deferred, not abandoned.

---

## 6. What Was Changed For Merge

The merge-prep implementation now does the following:

- Stops calling the population pipeline in the app runtime flow.
- Removes the hard population import from the agent tool path.
- Stops advertising active agent population tooling.
- Reworks equity scoring to use accessibility and facility access only.
- Removes population counts, density, poverty counts, and population-derived equity indices from the UI/report output.
- Replaces those sections with an explicit note that population analysis is deferred pending verified methodology.

---

## 7. Re-entry Criteria

Population can return only when all of the following are true:

- An authoritative baseline source is agreed.
- The spatial allocation method is documented in plain language.
- Validation against UBOS administrative totals is completed and accepted.
- Public-facing wording clearly states source year, method, and limitations.
- There is no silent fallback from verified methodology to modeled data.

---

## 8. Recommended Next Step

Treat population as a separate hardening workstream.

The preferred future path is:

- use UBOS as the truth source for totals,
- use any gridded surface only as a spatial allocation layer if needed,
- validate corridor outputs before re-enabling the feature,
- then reintroduce the feature behind explicit methodology wording.
