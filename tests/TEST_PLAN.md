# Test Plan — Business Data Analyzer



I’ll give you pytest files that use small in-memory DataFrames, so you don’t need fixture CSVs yet. A couple of these tests are intentionally strict: if they fail, they’ve found a real product-hardening issue rather than a test problem.

Install:
pip install pytest
SCIPTS...
One likely failure to watch for: if test_safe_left_join_reports_missing_right_key or unmatched join tests behave strangely, that means safe_left_join() needs a dedicated match-marker column rather than relying on the join key after merge.



## 1. Testing Goals

Ensure the app can:
- load supported files
- clean messy business data
- map columns correctly
- validate required fields
- detect risky joins
- calculate analytics accurately
- export reliable Excel reports
- avoid crashes on bad inputs

---

## 2. Test Levels

### Unit Tests
Test individual functions.

Target modules:
- data_cleaning/cleaner.py
- data_cleaning/validators_v2.py
- utils/column_mapping.py
- utils/joining.py
- utils/preflight.py
- analytics/sales_analysis.py
- analytics/inventory_analysis.py
- reporting/excel_report.py

---

### Integration Tests
Test full pipeline flows.

Scenarios:
- sales only
- inventory only
- sales + customer master
- sales + product master
- inventory + product master
- broken joins
- missing required fields

---

### UI Smoke Tests
Manual Streamlit checks.

Verify:
- upload works
- sheet selection works
- mapping UI appears
- preflight banner appears
- charts render
- export button behaves correctly

---

## 3. Core Test Cases

### File Loading

| Test | Expected |
|---|---|
| Load valid CSV | dataframe returned |
| Load valid XLSX | dataframe returned |
| Empty file | user-facing error |
| Unsupported file | rejected |
| Excel multi-sheet | sheet selector works |

---

### Cleaning

| Test | Expected |
|---|---|
| Messy column names | normalized snake_case |
| Blank rows | removed |
| Duplicate rows | removed or flagged |
| Currency strings | numeric conversion |
| Mixed dates | parsed or flagged |
| Missing values like N/A/null/- | standardized |

---

### Column Mapping

| Test | Expected |
|---|---|
| Sales Amt | maps to sales_amount |
| Qty Sold | maps to quantity |
| Product Code | maps to sku |
| Vendor | maps to supplier |
| Missing sales required field | blocked |
| Duplicate mapping target | warning |

---

### Validation

| Test | Expected |
|---|---|
| Sales missing quantity | error |
| Inventory missing stock_on_hand | error |
| Negative quantity | warning |
| Zero sales amount | warning |
| Invalid dates | warning |
| High missingness | warning |

---

### Joins

| Test | Expected |
|---|---|
| Perfect SKU join | 100% match |
| Missing product master keys | unmatched rows reported |
| Duplicate SKU in product master | warning |
| Row inflation | detected |
| Low match rate | preflight AMBER/RED |

---

### Sales Analytics

| Test | Expected |
|---|---|
| Total sales | correct sum |
| Units sold | correct sum |
| Monthly trend | correct aggregation |
| Top products | sorted descending |
| String currency amounts | no crash |

---

### Inventory Analytics

| Test | Expected |
|---|---|
| Out of stock item | alert |
| Low stock item | alert |
| Overstock item | alert |
| String stock values | no crash |
| Missing reorder level | no crash |

---

### Preflight

| Test | Expected |
|---|---|
| Clean run | GREEN |
| Warnings only | AMBER |
| Missing required fields | RED |
| Join below fail threshold | RED |
| Severe row inflation | RED |

---

### Excel Export

| Test | Expected |
|---|---|
| Export clean run | file downloads |
| Preflight sheet | present |
| Join summary | present |
| Validation report | present |
| Empty chart data | no crash |
| Sheet names >31 chars | safely truncated |

---

## 4. Performance Tests

Datasets:
- 10k rows
- 50k rows
- 100k rows
- 500k rows

Measure:
- load time
- clean time
- mapping time
- join time
- analysis time
- export time

Acceptable early targets:
- 50k rows under 15 seconds
- 100k rows under 30 seconds
- 500k rows under 90 seconds

---

## 5. Test Data

Use generated datasets:
- messy sales CSV
- messy inventory CSV
- customer master
- product master
- duplicate key master
- low match master
- missing required fields dataset

---

## 6. Automation

Recommended tools:
- pytest
- pandas testing utilities
- tempfile for export tests

Example command:

```bash
pytest tests/