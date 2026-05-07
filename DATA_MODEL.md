# Data Model — Business Data Analyzer

## Core Runtime Objects

### DatasetBundle
Represents one uploaded dataset after each processing stage.

Fields:
- dataset_name
- raw
- cleaned
- mapped
- validation_report
- metadata

Stages:
raw → cleaned → mapped → validated

---

### AnalysisResult
Main output object from analysis.

Fields:
- dataset_type
- cleaned_df
- quality_issues
- kpis
- alerts
- recommendations
- chart_data
- validation_report
- join_reports

---

### ValidationReport
Represents all validation findings for one dataset.

Fields:
- dataset
- issues

---

### ValidationIssue
One validation issue.

Fields:
- code
- severity
- dataset
- message
- column
- row_count
- sample_rows

Severity:
- info
- warning
- error

---

### JoinReport
Represents one join attempt.

Fields:
- join_name
- left_dataset
- right_dataset
- join_type
- join_key_left
- join_key_right
- left_rows_before
- left_rows_after
- matched_rows
- unmatched_rows
- match_rate
- duplicate_key_count_right
- row_inflation
- warnings
- unmatched_sample

---

### PreflightResult
Risk score and trust status for a run.

Fields:
- overall_status
- risk_score
- reasons
- metrics

Statuses:
- GREEN
- AMBER
- RED

---

## Canonical Business Entities

### Sales Transaction

Required:
- date
- product
- quantity

Optional:
- sku
- customer
- customer_id
- category
- region
- unit_price
- sales_amount
- unit_cost

Derived:
- month
- gross_profit
- gross_margin

---

### Inventory Record

Required:
- product
- stock_on_hand

Optional:
- sku
- category
- supplier
- supplier_id
- reorder_level
- cost
- avg_monthly_demand
- days_cover

Derived:
- stock_status
- reorder_recommendation
- overstock_flag

---

### Customer Master

Fields:
- customer_id
- customer_name
- customer_tier
- region
- payment_terms
- account_manager

---

### Product Master

Fields:
- sku
- product_name
- category
- subcategory
- supplier
- supplier_id
- lifecycle_stage
- lead_time_days
- reorder_point
- base_price
- base_cost

---

## Processing Flow

Upload
→ Clean
→ Map
→ Validate
→ Join
→ Analyze
→ Preflight
→ Export

---

## Local Storage Model — Future

Optional local project folder:

project/
- raw/
- cleaned/
- reports/
- mappings/
- logs/

Example:
- raw/sales_jan.csv
- mappings/sap_sales_mapping.json
- reports/sales_report_2026_04_24.xlsx