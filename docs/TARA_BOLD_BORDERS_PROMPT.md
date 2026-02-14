# TARA — Bold Border Treatment (CSS Only)

## What to change

Add bold 2px borders to container-level elements. Use TARA's primary dark green (#2d5f4a) instead of black. This gives the Gumroad-style graphic confidence while staying on-brand.

## CSS changes in `assets/style.css`

Add or update these selectors:

```css
/* Bold container borders — primary green */
.metric-card,
.equity-card,
.chart-container,
.report-preview,
.condition-summary,
.video-analysis-complete {
    border: 2px solid #2d5f4a !important;
}

/* Verdict banner — bold green border */
.verdict-banner,
[class*="verdict"] {
    border: 2px solid #2d5f4a !important;
}

/* Left panel main content card */
.left-panel-card,
.step-content-card {
    border: 2px solid #2d5f4a !important;
}
```

## What NOT to change

- Keep subtle 1px borders on: input fields, dropdowns, table rows, inner dividers
- Do NOT change border-radius (keep 3px)
- Do NOT change the equity concern cards' red left border — keep `border-left: 4px solid #a83a2f` but make the other 3 sides 2px solid #2d5f4a
- Do NOT change the map container border
- Do NOT touch any callback logic

## How to verify

Look at the metric cards (NPV, EIRR, BCR, FYRR), equity highlight cards, chart containers, and verdict banner. They should have a crisp 2px dark green border that makes them pop as defined data panels against the warm background.

This is ~10 lines of CSS. Should take under 5 minutes.
