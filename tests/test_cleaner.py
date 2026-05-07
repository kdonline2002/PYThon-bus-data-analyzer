import pandas as pd

from data_cleaning.cleaner import SpreadsheetCleaner

def test_cleaner_normalizes_columns_and_missing_values():
    df = pd.DataFrame({
        " Product Name ": [" Widget A ", "N/A", ""],
        "Sales Amt": ["R1,200.50", "-", "300"],
        "Order Date": ["2025-01-01", "", "2025/01/03"],
    })

    cleaned = SpreadsheetCleaner(df).clean()

    # print(cleaned.columns.tolist())
    # print(cleaned.head())


    assert "product" in cleaned.columns or "product_name" in cleaned.columns
    assert "sales_amount" in cleaned.columns
    assert "date" in cleaned.columns or "order_date" in cleaned.columns
    assert cleaned.isna().sum().sum() > 0


def test_cleaner_removes_duplicate_rows():
    df = pd.DataFrame({
        "Product": ["A", "A", "B"],
        "Qty": [1, 1, 2],
    })

    cleaned = SpreadsheetCleaner(df).clean()
    
    # print(cleaned.columns.tolist())
    # print(cleaned.head())

    assert len(cleaned) == 2