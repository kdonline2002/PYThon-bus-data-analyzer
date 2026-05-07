import pandas as pd

from utils.column_mapping import (
    apply_mapping_to_cleaned_df,
    get_missing_required_fields_from_df,
    score_column_to_field,
)


def test_alias_sales_amt_maps_to_sales_amount():
    df = pd.DataFrame({"Sales Amt": ["100", "200"]})

    score, reasons = score_column_to_field("Sales Amt", df["Sales Amt"], "sales_amount")

    assert score >= 0.75
    assert reasons


def test_qty_sold_maps_to_quantity():
    df = pd.DataFrame({"Qty Sold": [1, 2, 3]})

    score, _ = score_column_to_field("Qty Sold", df["Qty Sold"], "quantity")

    assert score >= 0.75


def test_apply_mapping_to_cleaned_df():
    df = pd.DataFrame({
        "sales_amt": [100, 200],
        "qty_sold": [1, 2],
    })

    mapped = apply_mapping_to_cleaned_df(df, {
        "sales_amt": "sales_amount",
        "qty_sold": "quantity",
    })

    assert "sales_amount" in mapped.columns
    assert "quantity" in mapped.columns


def test_missing_required_fields_from_df():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "sales_amt": [100, 200],
    })

    missing = get_missing_required_fields_from_df(
        df,
        mapping={"sales_amt": "sales_amount"},
        dataset_kind="sales",
    )

    assert "date" in missing
    assert "quantity" in missing