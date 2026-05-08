# Profitability test file guide

## 1. sales_profitability_direct_cost.csv
Upload as main sales file. No master data required.
Expected approximate totals:
- Total Sales: 4,350.00
- COGS: 2,950.00
Expected Gross Profit: 1230
Expected Gross Margin: 28.3%
Expected Negative Margin Rows: 1

## 2. sales_profitability_with_product_master.csv + product_master_base_cost.csv + customer_master.csv
Upload sales file as main, product master as optional product master, customer_master as optional customer master.
Expected approximate totals after product-master cost fallback:
- Total Sales: 2,100.00
- COGS: 1,380.00
- Gross Profit: 720.00
- Gross Margin %: 34.3%
- Negative gross profit alert: 1 row, Widget C

## 3. sales_profitability_missing_cost.csv
Upload as main sales file only.
Expected behavior:
- Normal sales analysis should still work.
- Profitability should be unavailable or show a warning because neither unit_cost nor base_cost exists.

## 4. sales_profitability_edge_cases.csv
Upload as main sales file.
Expected behavior:
- Negative margin alert should trigger.
- Zero sales amount alert should trigger for Free Sample.
- Gross margin should avoid divide-by-zero crashes.
