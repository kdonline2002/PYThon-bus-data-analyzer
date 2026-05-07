import pandas as pd

from data_cleaning.validators_v2 import validate_dataset


def test_sales_missing_required_field_is_error():
    df = pd.DataFrame({
        "date": ["2025-01-01"],
        "product": ["Widget A"],
    })

    report = validate_dataset(df, "sales", dataset_name="sales_test")

    assert report.has_errors
    assert any(issue.code == "missing_required_field" for issue in report.issues)


def test_sales_negative_quantity_warning():
    df = pd.DataFrame({
        "date": ["2025-01-01"],
        "product": ["Widget A"],
        "quantity": [-5],
        "sales_amount": [100],
    })

    report = validate_dataset(df, "sales")

    assert any(issue.code == "negative_quantity" for issue in report.issues)


def test_inventory_negative_stock_warning():
    df = pd.DataFrame({
        "product": ["Widget A"],
        "stock_on_hand": [-10],
    })

    report = validate_dataset(df, "inventory")

    assert any(issue.code == "negative_stock" for issue in report.issues)


def test_empty_dataset_is_error():
    df = pd.DataFrame()

    report = validate_dataset(df, "sales")

    assert report.has_errors
    assert any(issue.code == "empty_dataset" for issue in report.issues)