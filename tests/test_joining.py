import pandas as pd

from utils.joining import enrich_sales_with_masters, safe_left_join


def test_safe_left_join_perfect_match():
    left = pd.DataFrame({
        "sku": ["SKU001", "SKU002"],
        "quantity": [1, 2],
    })
    right = pd.DataFrame({
        "sku": ["SKU001", "SKU002"],
        "category": ["Hardware", "Accessories"],
    })

    result = safe_left_join(
        left,
        right,
        left_key="sku",
        right_key="sku",
        join_name="test_join",
        left_dataset="sales",
        right_dataset="product_master",
    )

    assert result.report.match_rate == 1.0
    assert result.report.unmatched_rows == 0
    assert "category" in result.dataframe.columns


def test_safe_left_join_reports_missing_right_key():
    left = pd.DataFrame({"sku": ["SKU001"]})
    right = pd.DataFrame({"product_code": ["SKU001"]})

    result = safe_left_join(
        left,
        right,
        left_key="sku",
        right_key="sku",
        join_name="bad_join",
        left_dataset="sales",
        right_dataset="product_master",
    )

    assert result.report.match_rate == 0.0
    assert result.report.warnings


def test_duplicate_right_keys_are_reported():
    left = pd.DataFrame({"sku": ["SKU001"]})
    right = pd.DataFrame({
        "sku": ["SKU001", "SKU001"],
        "category": ["A", "B"],
    })

    result = safe_left_join(
        left,
        right,
        left_key="sku",
        right_key="sku",
        join_name="duplicate_join",
        left_dataset="sales",
        right_dataset="product_master",
    )

    assert result.report.duplicate_key_count_right > 0
    assert result.report.warnings


def test_sales_enrichment_with_product_master():
    sales = pd.DataFrame({
        "date": ["2025-01-01"],
        "product": ["Widget A"],
        "sku": ["SKU001"],
        "quantity": [2],
        "sales_amount": [100],
    })
    product_master = pd.DataFrame({
        "sku": ["SKU001"],
        "product_name": ["Widget A"],
        "category": ["Hardware"],
    })

    enriched, reports = enrich_sales_with_masters(
        sales,
        customer_master_df=None,
        product_master_df=product_master,
    )

    assert "category" in enriched.columns
    assert reports