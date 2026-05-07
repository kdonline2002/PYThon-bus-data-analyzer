from __future__ import annotations

import pandas as pd

from data_cleaning.validators_v2 import validate_dataset
from utils.models import AnalysisResult


def ensure_inventory_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    numeric_cols = [
        "stock_on_hand",
        "reorder_level",
        "cost",
        "unit_cost",
        "qty_on_order",
        "available_stock",
        "reserved_stock",
        "days_cover",
        "avg_monthly_demand",
        "inventory_value",
        "suggested_reorder_qty",
    ]

    for col in numeric_cols:
        if col in out.columns:
            out[col] = (
                out[col]
                .astype("string")
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace("€", "", regex=False)
                .str.replace("£", "", regex=False)
                .str.replace("R", "", regex=False)
            )
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def analyze_inventory(df: pd.DataFrame) -> AnalysisResult:
    work = ensure_inventory_numeric(df)

    total_stock = (
        float(work["stock_on_hand"].fillna(0).sum())
        if "stock_on_hand" in work.columns
        else 0.0
    )

    low_stock = pd.DataFrame()
    out_of_stock = pd.DataFrame()
    overstock = pd.DataFrame()

    if {"stock_on_hand", "reorder_level"}.issubset(work.columns):
        stock = pd.to_numeric(work["stock_on_hand"], errors="coerce")
        reorder = pd.to_numeric(work["reorder_level"], errors="coerce")
        low_stock = work.loc[stock.notna() & reorder.notna() & stock.le(reorder)].copy()

    if "stock_on_hand" in work.columns:
        stock = pd.to_numeric(work["stock_on_hand"], errors="coerce")
        out_of_stock = work.loc[stock.fillna(0).le(0)].copy()

        positive_stock = stock[stock.notna() & stock.gt(0)]
        if not positive_stock.empty:
            threshold = positive_stock.median() * 2
            overstock = work.loc[stock.gt(threshold)].copy()

    alerts_list = []

    if not out_of_stock.empty:
        alerts_list.append(
            {
                "alert_type": "Out of stock",
                "details": f"{len(out_of_stock)} items are out of stock.",
            }
        )

    if not low_stock.empty:
        alerts_list.append(
            {
                "alert_type": "Low stock",
                "details": f"{len(low_stock)} items are at or below reorder level.",
            }
        )

    if not overstock.empty:
        alerts_list.append(
            {
                "alert_type": "Possible overstock",
                "details": f"{len(overstock)} items appear significantly overstocked.",
            }
        )

    alerts = (
        pd.DataFrame(alerts_list)
        if alerts_list
        else pd.DataFrame(columns=["alert_type", "details"])
    )

    recommendations = []

    if not low_stock.empty:
        recommendations.append(
            "Review the low-stock list and place replenishment orders for items near or below reorder level."
        )

    if not out_of_stock.empty:
        recommendations.append(
            "Prioritize out-of-stock items that are essential or frequently sold."
        )

    if not overstock.empty:
        recommendations.append(
            "Investigate possible overstock items and consider promotions, bundling, or supplier order adjustments."
        )

    if not recommendations:
        recommendations.append(
            "Inventory looks stable. Monitor reorder levels and stock aging on a regular cycle."
        )

    kpis = {
        "Total Stock On Hand": f"{total_stock:,.0f}",
        "Low Stock Items": f"{len(low_stock):,}",
        "Out of Stock Items": f"{len(out_of_stock):,}",
        "Rows": f"{len(work):,}",
    }

    stock_by_product = pd.DataFrame()
    if {"product", "stock_on_hand"}.issubset(work.columns):
        temp = work.copy()
        temp["stock_on_hand"] = pd.to_numeric(temp["stock_on_hand"], errors="coerce")
        stock_by_product = (
            temp.groupby("product", dropna=False)["stock_on_hand"]
            .sum(min_count=1)
            .fillna(0)
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

    chart_data = {
        "stock_by_product": stock_by_product,
        "low_stock": low_stock.head(20),
        "out_of_stock": out_of_stock.head(20),
        "overstock": overstock.head(20),
    }

    validation_report = validate_dataset(work, "inventory", dataset_name="inventory")

    return AnalysisResult(
        dataset_type="inventory",
        cleaned_df=work,
        quality_issues=[issue.message for issue in validation_report.issues],
        kpis=kpis,
        alerts=alerts,
        recommendations=recommendations,
        chart_data=chart_data,
        validation_report=validation_report,
        join_reports=[],
    )