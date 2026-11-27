# Capability: What-If Lab, Monthly Goals & Case Notes (`whatif-goals-notes`)

## ADDED Requirements

### Requirement: Single-Segment What-If Sensitivity Simulator
The `/lab` page SHALL load up to 12 latest-month segments via `GET /api/whatif/segments` and run non-predictive sensitivity illustrations via `POST /api/whatif`.

#### Scenario: Live slider drag vs commit on release
- **WHEN** the user adjusts `Orders` (`-80%`..`+100%`), `Average price per order` (`-30%`..`+30%`), or `Profit margin` (`-15`..`+15` pts)
- **THEN** debounced `input` events send `POST /api/whatif` with `commit: false` (preview only, no XP awarded) and update the Now vs Scenario `PlotlyChart`
- **AND** releasing a slider (`change`), changing the segment, or clicking **Match last month's orders** sends `POST /api/whatif` with `commit: true` (awarding `whatif` XP).

---

### Requirement: Monthly Goals & Private Case Notes
Users SHALL manage monthly `sales` / `profit` goals and dataset case notes privately per user and dataset.

#### Scenario: Create, update, and delete monthly goals
- **WHEN** the user submits a positive target (`PUT /api/goals` with `dataset`, `metric: "sales"|"profit"`, `amount`) or clicks delete (`DELETE /api/goals`)
- **THEN** the UI refreshes `GET /api/goals` showing circular progress rings, remaining target, and `needed_per_day` pace for remaining days in the latest month.

#### Scenario: Add and delete private case notes
- **WHEN** the user saves a note (1-500 chars, max 100 per dataset) via `POST /api/notes` or deletes via `DELETE /api/notes/<id>`
- **THEN** the UI refreshes `GET /api/notes` and renders all note text safely via React JSX escaping.
