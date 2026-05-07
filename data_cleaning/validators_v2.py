from __future__ import annotations

from typing import Optional

import pandas as pd

from utils.models import ValidationReport


REQUIRED_FIELDS = {
    "sales": ["date", "product", "quantity"],
    "inventory": ["product", "stock_on_hand"],
}


def validate_dataset(
    df: pd.DataFrame,
    dataset_type: str,
    dataset_name: Optional[str] = None,
) -> ValidationReport:
    name = dataset_name or dataset_type
    report = ValidationReport(dataset=name)

    if df is None or df.empty:
        report.add_issue(
            code="empty_dataset",
            severity="error",
            message="Dataset is empty after cleaning.",
        )
        return report

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        report.add_issue(
            code="duplicate_rows",
            severity="warning",
            message=f"{duplicate_rows} duplicate rows remain in the dataset.",
            row_count=duplicate_rows,
            sample_rows=df[df.duplicated(keep=False)].head(20),
        )

    duplicated_columns = pd.Index(df.columns)[pd.Index(df.columns).duplicated()].tolist()
    if duplicated_columns:
        report.add_issue(
            code="duplicate_columns",
            severity="error",
            message=f"Duplicate column names detected: {duplicated_columns}",
        )

    for field in REQUIRED_FIELDS.get(dataset_type, []):
        if field not in df.columns:
            report.add_issue(
                code="missing_required_field",
                severity="error",
                message=f"Missing required field: {field}",
                column=field,
            )

    missing_by_col = df.isna().sum()
    for col, count in missing_by_col.items():
        if count > len(df) * 0.4:
            report.add_issue(
                code="high_missingness",
                severity="warning",
                message=f"Column '{col}' has high missing values: {int(count)} rows.",
                column=str(col), #KEDIT
                row_count=int(count),
            )

    if dataset_type == "sales":
        _validate_sales(df, report)
    elif dataset_type == "inventory":
        _validate_inventory(df, report)

    return report


def _validate_sales(df: pd.DataFrame, report: ValidationReport) -> None:
    if "quantity" in df.columns:
        qty = pd.to_numeric(df["quantity"], errors="coerce")
        negative_qty = int(qty.lt(0).sum())
        if negative_qty:
            report.add_issue(
                code="negative_quantity",
                severity="warning",
                message=f"{negative_qty} rows have negative quantity.",
                column="quantity",
                row_count=negative_qty,
                sample_rows=df.loc[qty.lt(0)].head(20),
            )

    if "sales_amount" in df.columns:
        sales = pd.to_numeric(df["sales_amount"], errors="coerce")
        zero_sales = int(sales.fillna(0).eq(0).sum())
        if zero_sales:
            report.add_issue(
                code="zero_sales_amount",
                severity="warning",
                message=f"{zero_sales} rows have zero sales amount.",
                column="sales_amount",
                row_count=zero_sales,
                sample_rows=df.loc[sales.fillna(0).eq(0)].head(20),
            )

    if {"quantity", "unit_price", "sales_amount"}.issubset(df.columns):
        qty = pd.to_numeric(df["quantity"], errors="coerce")
        unit_price = pd.to_numeric(df["unit_price"], errors="coerce")
        sales = pd.to_numeric(df["sales_amount"], errors="coerce")
        expected = qty * unit_price
        mismatch_mask = expected.notna() & sales.notna() & (expected - sales).abs().gt(0.01)
        mismatch_count = int(mismatch_mask.sum())
        if mismatch_count:
            report.add_issue(
                code="sales_amount_mismatch",
                severity="warning",
                message=f"{mismatch_count} rows have sales amounts that do not match quantity × unit price.",
                row_count=mismatch_count,
                sample_rows=df.loc[mismatch_mask].head(20),
            )

    if "date" in df.columns:
        parsed_dates = pd.to_datetime(df["date"], errors="coerce")
        invalid_dates = int(parsed_dates.isna().sum())
        if invalid_dates:
            report.add_issue(
                code="invalid_dates",
                severity="warning",
                message=f"{invalid_dates} rows contain invalid dates.",
                column="date",
                row_count=invalid_dates,
                sample_rows=df.loc[parsed_dates.isna()].head(20),
            )


def _validate_inventory(df: pd.DataFrame, report: ValidationReport) -> None:
    if "stock_on_hand" in df.columns:
        stock = pd.to_numeric(df["stock_on_hand"], errors="coerce")
        negative_stock = int(stock.lt(0).sum())
        if negative_stock:
            report.add_issue(
                code="negative_stock",
                severity="warning",
                message=f"{negative_stock} rows have negative stock levels.",
                column="stock_on_hand",
                row_count=negative_stock,
                sample_rows=df.loc[stock.lt(0)].head(20),
            )

    if "reorder_level" in df.columns:
        reorder = pd.to_numeric(df["reorder_level"], errors="coerce")
        negative_reorder = int(reorder.lt(0).sum())
        if negative_reorder:
            report.add_issue(
                code="negative_reorder_level",
                severity="warning",
                message=f"{negative_reorder} rows have negative reorder levels.",
                column="reorder_level",
                row_count=negative_reorder,
                sample_rows=df.loc[reorder.lt(0)].head(20),
            )

    if {"stock_on_hand", "reorder_level"}.issubset(df.columns):
        stock = pd.to_numeric(df["stock_on_hand"], errors="coerce")
        reorder = pd.to_numeric(df["reorder_level"], errors="coerce")
        low_stock_mask = stock.notna() & reorder.notna() & stock.le(reorder)
        low_stock = int(low_stock_mask.sum())
        if low_stock:
            report.add_issue(
                code="low_stock_positions",
                severity="info",
                message=f"{low_stock} rows are at or below reorder level.",
                row_count=low_stock,
                sample_rows=df.loc[low_stock_mask].head(20),
            )