# Capability: Data Ingestion & Interactive Column Mapping (`dataset-ingestion`)

## ADDED Requirements

### Requirement: Demo Cases & Multi-Format File Upload
Authenticated users on `/` SHALL be able to load planted demo cases or upload sales files up to 50 MB in `.csv`, `.tsv`, `.txt`, `.xlsx`, `.xlsm`, `.xls`, `.ods`, `.json`, `.pdf`, or `.pbix` formats.

#### Scenario: Load clean or dirty demo dataset
- **WHEN** an authenticated user clicks **Open the demo case** (`kind: "clean"`) or **See it fix messy data** (`kind: "dirty"`)
- **THEN** `POST /api/sample` returns `{ dataset, months, source_note }`
- **AND** `AuthProvider.setActiveDataset(dataset.id, dataset.filename)` persists the dataset under `abd_dataset_<uid>` in `localStorage` and displays the quality summary with links to `/dashboard` and `/investigation`.

#### Scenario: Upload valid file
- **WHEN** the user drops or chooses a valid file (`<= 50 MB`)
- **THEN** `POST /api/upload` (`FormData` field `file`) cleans the dataset without imputing missing profits as `0`, returns `200`, and sets the active dataset.

#### Scenario: Unrecognized headers trigger interactive column mapper
- **WHEN** `POST /api/upload` returns HTTP `422` with `needs_mapping: true`
- **THEN** the UI displays the 5-row data `preview` table and dropdown selectors for `order_date` (required), `sales` (required), `profit`, `product`, `category`, `region`, `quantity`, and `discount_pct` pre-filled from `suggestions`
- **AND** submitting sends `POST /api/upload/map` with `{ token, filename, mapping }`, ensuring both `order_date` and `sales` are chosen and no source column is assigned to multiple targets.
