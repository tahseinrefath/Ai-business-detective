# Capability: Performance Dashboard (`analytics-dashboard`)

## ADDED Requirements

### Requirement: Interactive Filtered Analytics & Business Health Gauge
The `/dashboard` page SHALL display filtered KPIs, business pulse cards, a transparent 0-100 health score gauge, 7 interactive Plotly visualizations, trend projection, and the cleaning data-quality report.

#### Scenario: Load and filter dashboard data
- **WHEN** an authenticated user with an active `datasetId` opens `/dashboard` or updates `region`, `category`, `product`, `start`, or `end` (or clicks Reset)
- **THEN** `GET /api/dashboard?dataset=<id>&...` returns `DashboardResponse`
- **AND** the UI renders:
  1. Business Pulse highlights (`pulse`).
  2. Business Health Score SVG gauge (`score`, `grade`, and 4 breakdown bars: `Growth`, `Profitability`, `Stability`, `Data quality`).
  3. 6 animated KPI cards (`total_sales`, `total_profit`, `profit_margin`, `total_orders`, `units_sold`, `avg_order_value`).
  4. 7 `PlotlyChart` components (`cMonthly`, `cDaily` with 7-day rolling mean, `cProducts` & `cRegions` with `Profit`/`Sales` segmented toggle, `cHeat` region x product heatmap, `cCat` category donut, and `cDisc` discount bands when `discount_bands != null`).
  5. Next-month linear projection (`forecast`, or `< 3 months` notice when `null`).
  6. Data Quality report (`quality_score`, rows in/out/removed, and `issues` list).

#### Scenario: Empty filter combination
- **WHEN** `GET /api/dashboard` returns HTTP `422` (`No rows match these filters - try widening them.`)
- **THEN** the UI shows the error toast while keeping the filter controls editable so the user can widen filters.

#### Scenario: Export cleaned CSV
- **WHEN** the user clicks **Export cleaned CSV**
- **THEN** the browser downloads `/api/export/<datasetId>/clean.csv`.
