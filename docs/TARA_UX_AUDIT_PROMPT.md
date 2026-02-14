# TARA App — UX Audit Report

Read the entire app and produce a report. Do NOT change any code. Only read and report.

## What to read

1. `app.py` — the full file, every line
2. Every file in `layouts/` if it exists
3. Every file in `callbacks/` if it exists
4. `assets/style.css` if it exists
5. `CLAUDE.md`

## What to report

Create a file called `UX_AUDIT.md` in the project docs folder with the following sections:

### 1. Step List
List every step in the wizard in order. For each step give:
- Step number and label (exactly as shown in the step navigation bar)
- What the user sees (UI components: dropdowns, tables, buttons, maps, charts, text)
- What data flows in (what stores/inputs does this step read from)
- What data flows out (what stores does this step write to)
- What API calls or heavy computation happens on this step (if any)

### 2. First Load Experience
Describe exactly what the user sees when they first open the app at localhost:8050:
- What is visible before any interaction?
- Is there a welcome message, empty state, or instructions?
- What is the map showing?
- What is the left panel showing?
- Can the user immediately understand what to do?

### 3. User Flow Map
Trace the complete happy path from app load to report download:
- What does the user click/type at each step?
- How long does each step take (instant, seconds, minutes)?
- Where does the user have to wait? What feedback do they get while waiting?
- Where can the flow break (errors, empty states, confusing choices)?

### 4. Step Transitions
For each step transition:
- What triggers moving to the next step? (button click, auto-advance, etc.)
- Are there any steps that auto-populate from previous steps?
- Can the user go back? What happens to their data if they do?
- Are any steps skippable?

### 5. Data Dependencies
Draw the data flow between steps:
- Which steps REQUIRE previous step data to function?
- Which steps could theoretically run independently?
- Where does the video pipeline output feed into the wizard?
- Where does the equity data appear?

### 6. Current Pain Points
List anything you notice that would confuse a first-time user:
- Empty states with no guidance
- Technical jargon without explanation
- Steps that feel redundant
- Long waits with no progress feedback
- Buttons that don't clearly indicate what they do
- Any dead ends or error states

### 7. Component Inventory
List every `dcc.Store` id and what it holds. List every major callback (Input → Output) with a one-line description.

## Format

Write the report in clean markdown. Use tables where helpful. Be specific — quote actual component IDs, button labels, and store names. This report will be used to redesign the user experience.

## IMPORTANT

Do NOT modify any files. Read only. Output only `UX_AUDIT.md`.
