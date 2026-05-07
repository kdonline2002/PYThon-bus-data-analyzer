Regression fixtures are small, controlled test files that you keep forever. When you change cleaning, mapping, joining, analytics, or reporting code, you rerun tests against these files to make sure you did not break behavior that used to work.

Why they matter

Your app deals with messy real-world data. Without fixtures, every code change is risky because you may fix one case and accidentally break another.

Fixtures give you a stable test set for:

cleaning
mapping
validation
joins
analytics
preflight
Excel export
Recommended fixture folder
tests/
└─ fixtures/
   ├─ sales_clean.csv
   ├─ sales_messy.csv
   ├─ inventory_messy.csv
   ├─ customer_master.csv
   ├─ product_master.csv
   ├─ product_master_duplicates.csv
   └─ sales_missing_required.csv
What each fixture should prove
sales_clean.csv

Purpose: baseline happy path.

This should represent a clean sales file that should pass easily.

Use it to test:

app detects sales
required fields exist
sales totals calculate correctly
monthly trend works
preflight should be GREEN

Example:

date,product,sku,customer_id,customer,quantity,unit_price,sales_amount,unit_cost
2025-01-01,Widget A,SKU001,CUST001,Acme Ltd,10,100,1000,60
2025-01-02,Widget B,SKU002,CUST002,Beta Stores,5,200,1000,120
2025-02-01,Widget A,SKU001,CUST001,Acme Ltd,8,100,800,60
2025-02-05,Widget C,SKU003,CUST003,Core Retail,3,300,900,180

Expected:

total sales = 3700
units sold = 26
no validation errors
preflight GREEN
sales_messy.csv

Purpose: prove messy files still work.

This should include real-world mess:

weird column names
currency strings
mixed date formats
blanks
negative quantities
zero sales
duplicate rows

Example:

Order Date,Product Name,Product Code,Customer ID,Customer,Qty Sold,Unit Price,Sales Amt,Cost Price
2025/01/01,Widget A,SKU001,CUST001,Acme Ltd,10,R100.00,R1,000.00,R60.00
01-02-2025,Widget B,SKU002,CUST002,Beta Stores,5,$200.00,$1,000.00,$120.00
2025-02-10,Widget A,SKU001,CUST001,Acme Ltd,8,100,800,60
2025-02-10,Widget A,SKU001,CUST001,Acme Ltd,8,100,800,60
,Widget C,SKU003,CUST003,Core Retail,3,300,900,180
2025-03-01,Widget D,SKU004,CUST004,Delta Wholesale,-2,150,-300,90
2025-03-02,Widget E,SKU005,CUST005,Echo Traders,0,250,0,140

Expected:

column mapping should suggest:
Order Date → date
Product Name → product
Product Code → sku
Qty Sold → quantity
Sales Amt → sales_amount
validation warnings:
invalid/missing date
negative quantity
zero sales amount
no app crash
preflight likely AMBER

Important note: CSV values with commas like R1,000.00 need quoting in real CSV:

"R1,000.00"

So use this safer version:

Order Date,Product Name,Product Code,Customer ID,Customer,Qty Sold,Unit Price,Sales Amt,Cost Price
2025/01/01,Widget A,SKU001,CUST001,Acme Ltd,10,R100.00,"R1,000.00",R60.00
01-02-2025,Widget B,SKU002,CUST002,Beta Stores,5,$200.00,"$1,000.00",$120.00
2025-02-10,Widget A,SKU001,CUST001,Acme Ltd,8,100,800,60
2025-02-10,Widget A,SKU001,CUST001,Acme Ltd,8,100,800,60
,Widget C,SKU003,CUST003,Core Retail,3,300,900,180
2025-03-01,Widget D,SKU004,CUST004,Delta Wholesale,-2,150,-300,90
2025-03-02,Widget E,SKU005,CUST005,Echo Traders,0,250,0,140
inventory_messy.csv

Purpose: test inventory validation and planning signals.

Include:

low stock
out of stock
negative stock
missing reorder level
messy stock column names

Example:

Product Name,Product Code,Category,Stock,Reorder Point,Cost Price,Supplier
Widget A,SKU001,Hardware,100,50,R60.00,Supplier One
Widget B,SKU002,Hardware,20,50,R120.00,Supplier Two
Widget C,SKU003,Accessories,0,25,R80.00,Supplier One
Widget D,SKU004,Accessories,-5,30,R90.00,Supplier Three
Widget E,SKU005,Electronics,300,40,R140.00,Supplier Two
Widget F,SKU006,Electronics,15,,R75.00,Supplier Four

Expected:

Product Name → product
Product Code → sku
Stock → stock_on_hand
Reorder Point → reorder_level
low stock alert
out of stock alert
negative stock warning
no crash when reorder level is missing
customer_master.csv

Purpose: test sales enrichment.

Example:

customer_id,customer_name,customer_tier,region,payment_terms,account_manager
CUST001,Acme Ltd,Enterprise,Gauteng,Net 30,N. Dlamini
CUST002,Beta Stores,SMB,Western Cape,COD,S. Naidoo
CUST003,Core Retail,Mid-Market,KwaZulu-Natal,Net 15,T. Mokoena
CUST004,Delta Wholesale,Enterprise,Gauteng,Net 45,L. van Wyk
CUST005,Echo Traders,SMB,Eastern Cape,COD,A. Petersen

Expected:

sales joined to customer master
high match rate
no row inflation
customer fields available in enriched dataframe
product_master.csv

Purpose: test sales and inventory enrichment.

Example:

sku,product_name,category,subcategory,supplier,supplier_id,lifecycle_stage,lead_time_days,reorder_point,base_price,base_cost
SKU001,Widget A,Hardware,Tools,Supplier One,SUP001,mature,14,50,100,60
SKU002,Widget B,Hardware,Tools,Supplier Two,SUP002,mature,21,50,200,120
SKU003,Widget C,Accessories,Cables,Supplier One,SUP001,growth,10,25,300,180
SKU004,Widget D,Accessories,Cables,Supplier Three,SUP003,new,30,30,150,90
SKU005,Widget E,Electronics,Sensors,Supplier Two,SUP002,mature,45,40,250,140
SKU006,Widget F,Electronics,Sensors,Supplier Four,SUP004,growth,20,20,125,75

Expected:

SKU join works
match rate high
no duplicate key warning
product attributes appear after enrichment
product_master_duplicates.csv

Purpose: test duplicate key detection.

This should intentionally contain duplicate SKUs.

Example:

sku,product_name,category,subcategory,supplier,supplier_id,lifecycle_stage,lead_time_days,reorder_point,base_price,base_cost
SKU001,Widget A,Hardware,Tools,Supplier One,SUP001,mature,14,50,100,60
SKU001,Widget A Duplicate,Hardware,Tools,Supplier Two,SUP002,mature,21,50,105,65
SKU002,Widget B,Hardware,Tools,Supplier Two,SUP002,mature,21,50,200,120
SKU003,Widget C,Accessories,Cables,Supplier One,SUP001,growth,10,25,300,180

Expected:

join still completes or warns depending your rules
duplicate key warning appears
preflight AMBER or RED depending thresholds
no silent failure

This fixture is very important because duplicate master keys are one of the easiest ways to corrupt analysis.

sales_missing_required.csv

Purpose: test blocking behavior.

This file should be missing one or more required sales fields.

Example missing quantity:

date,product,sku,customer_id,unit_price,sales_amount
2025-01-01,Widget A,SKU001,CUST001,100,1000
2025-01-02,Widget B,SKU002,CUST002,200,1000

Expected:

validation error
preflight RED
strict mode blocks
export disabled

This proves your app does not produce misleading reports when required fields are missing.

Suggested test expectations file

You can also create:

tests/fixtures/expected_results.json

Example:

{
  "sales_clean": {
    "dataset_type": "sales",
    "total_sales": 3700,
    "units_sold": 26,
    "preflight": "GREEN"
  },
  "sales_missing_required": {
    "preflight": "RED",
    "expected_errors": ["missing_required_field"]
  },
  "product_master_duplicates": {
    "expected_join_warning": true
  }
}

This makes tests easier to maintain.

How to use fixtures in tests

Example tests/test_sales_analysis.py:

from pathlib import Path

import pandas as pd

from analytics.sales_analysis import analyze_sales

FIXTURES = Path(__file__).parent / "fixtures"


def test_sales_clean_totals():
    df = pd.read_csv(FIXTURES / "sales_clean.csv")

    result = analyze_sales(df)

    assert result.dataset_type == "sales"
    assert result.kpis["Total Sales"] == "3,700.00"
    assert result.kpis["Units Sold"] == "26"

Example tests/test_pipeline.py:

from pathlib import Path

import pandas as pd

from services.pipeline_service import PipelineService

FIXTURES = Path(__file__).parent / "fixtures"


def test_sales_with_product_master_join():
    sales = pd.read_csv(FIXTURES / "sales_clean.csv")
    product_master = pd.read_csv(FIXTURES / "product_master.csv")

    pipeline = PipelineService()
    output = pipeline.run(
        sales,
        forced_dataset_type="sales",
        raw_product_df=product_master,
    )

    assert output.dataset_type == "sales"
    assert len(output.join_reports) == 1
    assert output.join_reports[0].match_rate == 1.0

Example duplicate master test:

def test_duplicate_product_master_keys_are_reported():
    sales = pd.read_csv(FIXTURES / "sales_clean.csv")
    product_master = pd.read_csv(FIXTURES / "product_master_duplicates.csv")

    pipeline = PipelineService()
    output = pipeline.run(
        sales,
        forced_dataset_type="sales",
        raw_product_df=product_master,
    )

    assert output.join_reports
    assert output.join_reports[0].duplicate_key_count_right > 0
How these protect you

When you later change:

cleaner logic
mapping aliases
join code
validation rules
analytics formulas
Excel export

you run:

pytest

If a fixture test fails, you know exactly what behavior changed.

Practical rule

Keep fixtures:

small
readable
intentional
version-controlled

Do not use giant random datasets for regression tests. Use those for performance tests only.

Regression fixtures should answer:

“Did we break a known business scenario?”

Performance datasets answer:

“Can the app still handle large files?”