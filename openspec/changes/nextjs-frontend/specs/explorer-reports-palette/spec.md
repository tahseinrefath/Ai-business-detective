# Capability: Data Explorer, Reports & Command Palette (`explorer-reports-palette`)

## ADDED Requirements

### Requirement: Searchable, Sortable & Paginated Data Explorer
The `/data` page SHALL browse cleaned rows via `GET /api/preview` and allow CSV export.

#### Scenario: Search, sort, and paginate rows
- **WHEN** the user types in the search box (debounced 250ms), clicks a column header (`order_date`, `product`, `category`, `region`, `quantity`, `sales`, `profit`, `discount_pct`), or clicks Prev/Next
- **THEN** `GET /api/preview?dataset=<id>&q=&sort=&dir=&page=&size=15` updates the table, row count, and page indicators.

---

### Requirement: Automated Reports Console
The `/reports` page SHALL list all datasets owned by the signed-in user and manage self-contained HTML report generation.

#### Scenario: Generate, view, and download HTML report
- **WHEN** the user opens `/reports`
- **THEN** `GET /api/datasets` lists all user datasets with active badge and quality score; clicking **Generate** triggers `POST /api/report/<id>`, revealing **View** (`/api/report/<id>`) and **Download** (`/api/report/<id>?download=1`) links.

---

### Requirement: Global Command Palette (`Ctrl+K` / `Cmd+K`)
The root layout SHALL provide a keyboard-accessible command palette matching the Obsidian · Chrome · Laser design system.

#### Scenario: Keyboard navigation in command palette
- **WHEN** the user presses `Ctrl+K` (or `Cmd+K`) or clicks the Quick actions trigger
- **THEN** the modal opens with search filtering, `ArrowUp`/`ArrowDown`/`Enter`/`Escape` navigation, auth-aware actions (navigation routes, **Load the demo case**, **Sign out** when signed in; **Sign in**, **Create account** when signed out).
