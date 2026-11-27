# Capability: Case Investigation & Evidence Explainer (`investigation-ai`)

## ADDED Requirements

### Requirement: Question-Driven & Period-Comparison Investigation
The `/investigation` page SHALL let users ask plain-English questions or compare any two months across `Auto`, `Profit`, or `Sales` metrics, presenting only evidence computed by Pandas/scikit-learn.

#### Scenario: Execute an investigation query
- **WHEN** the user submits a question (<=300 chars), clicks a preset question chip, changes `previous`/`current` month dropdowns, or toggles `metric` (`auto` | `profit` | `sales`)
- **THEN** `POST /api/ask` returns `{ investigation, findings, next_checks, explanation, question }`
- **AND** the UI displays:
  - Headline percentage verdict and period totals (`previous -> current`).
  - Plain-English explanation with source badge (`rule-based from evidence` vs `AI-written from evidence`) and `partial_warning` banner when present.
  - Interactive contributor chart (`PlotlyChart`) switchable across 4 dimensions (`segment`, `product`, `region`, `category`).
  - Inside-segment driver cards (`orders`, `units`, `avg_selling_price`, `margin`, `avg_discount`) coloring unhelpful changes in laser crimson.
  - Key findings list, flagged unusual days (`anomalies` from robust z-score + `IsolationForest`), and recommended `next_checks`.

#### Scenario: Export contributors or generate report from investigation
- **WHEN** the user clicks **Generate report** or **Contributors CSV**
- **THEN** **Generate report** sends `POST /api/report/<id>` with `{ metric, previous, current }` and opens the generated report URL; **Contributors CSV** downloads `/api/export/<id>/contributors.csv?metric=...&previous=...&current=...`.
