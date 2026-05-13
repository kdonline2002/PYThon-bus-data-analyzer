from __future__ import annotations

import pandas as pd
import streamlit as st

from data_cleaning.validators_v2 import validate_dataset
from utils.models import AnalysisResult

def _clean_currency_series(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace("R", "", regex=False)
    )


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def apply_sales_alias_fallbacks(df: pd.DataFrame) -> pd.DataFrame:
    """Create canonical sales columns from common aliases when mapping was not applied."""
    out = df.copy()

    alias_candidates = {
        "date": ["order_date", "invoice_date", "transaction_date", "sales_date", "posting_date"],
        "product": ["product_name", "item", "item_name", "description", "stock_item"],
        "sku": ["sku_code", "product_code", "item_code", "stock_code", "product_id"],
        "customer": ["client_name", "customer_name", "client", "account", "buyer"],
        "customer_id": ["client_id", "account_id", "cust_id"],
        "quantity": ["qty_sold", "qty", "quantity_sold", "units", "units_sold", "sales_qty", "sold_qty"],
        "unit_price": ["selling_price", "sell_price", "price", "rate", "unit_selling_price"],
        "sales_amount": ["revenue", "sales", "amount", "line_total", "turnover", "total_sales", "invoice_amount"],
        "unit_cost": ["cost_price", "purchase_cost", "cost", "unit_cost_price"],
        "base_cost": ["standard_cost", "default_cost"],
    }

    for canonical, candidates in alias_candidates.items():
        if canonical in out.columns:
            continue
        source = _first_existing_column(out, candidates)
        if source is not None:
            out[canonical] = out[source]

    return out


def ensure_sales_amount(df: pd.DataFrame) -> pd.DataFrame:
    out = apply_sales_alias_fallbacks(df)

    if "quantity" in out.columns:
        out["quantity"] = pd.to_numeric(out["quantity"], errors="coerce")

    if "unit_price" in out.columns:
        out["unit_price"] = pd.to_numeric(_clean_currency_series(out["unit_price"]), errors="coerce")

    if "sales_amount" in out.columns:
        out["sales_amount"] = pd.to_numeric(_clean_currency_series(out["sales_amount"]), errors="coerce")

    if "unit_cost" in out.columns:
        out["unit_cost"] = pd.to_numeric(_clean_currency_series(out["unit_cost"]), errors="coerce")

    if "base_cost" in out.columns:
        out["base_cost"] = pd.to_numeric(_clean_currency_series(out["base_cost"]), errors="coerce")

    if "sales_amount" not in out.columns and {"quantity", "unit_price"}.issubset(out.columns):
        out["sales_amount"] = out["quantity"] * out["unit_price"]

    return out


def add_profitability_metrics(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Add gross-profit fields when sales and cost inputs are available.

    Cost fallback priority is:
    1. unit_cost from the sales file
    2. base_cost from the product master join

    The function returns the updated dataframe plus user-facing notes so the
    UI/report can explain why profitability was enabled or skipped.
    """
    out = df.copy()
    notes: list[str] = []

    if "sales_amount" not in out.columns:
        notes.append("Profitability skipped because sales_amount is not available.")
        return out, notes

    if "quantity" not in out.columns:
        notes.append("Profitability skipped because quantity is not available.")
        return out, notes

    cost_column = None
    if "unit_cost" in out.columns and pd.to_numeric(out["unit_cost"], errors="coerce").notna().any():
        cost_column = "unit_cost"
    elif "base_cost" in out.columns and pd.to_numeric(out["base_cost"], errors="coerce").notna().any():
        cost_column = "base_cost"
        notes.append("Profitability used base_cost from product master because unit_cost was not available.")
    else:
        notes.append("Profitability skipped because no usable unit_cost or base_cost is available.")
        return out, notes

    revenue = pd.to_numeric(out["sales_amount"], errors="coerce")
    quantity = pd.to_numeric(out["quantity"], errors="coerce")
    unit_cost = pd.to_numeric(out[cost_column], errors="coerce")

    out["profit_cost_source"] = cost_column
    out["cogs"] = quantity * unit_cost
    out["gross_profit"] = revenue - out["cogs"]
    out["gross_margin_pct"] = (out["gross_profit"] / revenue).replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    notes.append(f"Profitability enabled using {cost_column}.")
    return out, notes


def build_profitability_segments(work: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build product and customer profitability segmentation tables.

    Segments are deliberately simple and explainable for V2:
    - Loss-making: gross profit below zero
    - Low margin: non-negative margin below 20%
    - Core profit: margin from 20% up to 40%
    - High margin: margin of 40% or more
    """
    empty = {
        "product_profitability_segments": pd.DataFrame(),
        "customer_profitability_segments": pd.DataFrame(),
        "bottom_products_by_gross_profit": pd.DataFrame(),
        "bottom_customers_by_gross_profit": pd.DataFrame(),
    }

    if not {"sales_amount", "gross_profit"}.issubset(work.columns):
        return empty

    def _segment_margin(value: float) -> str:
        if pd.isna(value):
            return "Unknown margin"
        if value < 0:
            return "Loss-making"
        if value < 0.20:
            return "Low margin"
        if value < 0.40:
            return "Core profit"
        return "High margin"

    def _build(group_col: str, output_col: str) -> pd.DataFrame:
        if group_col not in work.columns:
            return pd.DataFrame()

        temp = work.copy()
        temp["sales_amount"] = pd.to_numeric(temp["sales_amount"], errors="coerce")
        temp["gross_profit"] = pd.to_numeric(temp["gross_profit"], errors="coerce")
        if "quantity" in temp.columns:
            temp["quantity"] = pd.to_numeric(temp["quantity"], errors="coerce")
        else:
            temp["quantity"] = 0

        grouped = (
            temp.groupby(group_col, dropna=False)
            .agg(
                revenue=("sales_amount", "sum"),
                gross_profit=("gross_profit", "sum"),
                units=("quantity", "sum"),
                rows=("sales_amount", "size"),
            )
            .reset_index()
            .rename(columns={group_col: output_col})
        )
        grouped["gross_margin_pct"] = (grouped["gross_profit"] / grouped["revenue"]).replace(
            [float("inf"), float("-inf")],
            pd.NA,
        )
        grouped["profit_segment"] = grouped["gross_margin_pct"].apply(_segment_margin)
        return grouped.sort_values(["gross_profit", "revenue"], ascending=[False, False]).reset_index(drop=True)

    product_segments = _build("product", "product")
    customer_col = "customer" if "customer" in work.columns else "customer_name" if "customer_name" in work.columns else None
    customer_segments = _build(customer_col, "customer") if customer_col else pd.DataFrame()

    return {
        "product_profitability_segments": product_segments,
        "customer_profitability_segments": customer_segments,
        "bottom_products_by_gross_profit": product_segments.sort_values("gross_profit", ascending=True).head(10).reset_index(drop=True) if not product_segments.empty else pd.DataFrame(),
        "bottom_customers_by_gross_profit": customer_segments.sort_values("gross_profit", ascending=True).head(10).reset_index(drop=True) if not customer_segments.empty else pd.DataFrame(),
    }

@st.cache_data(show_spinner=False)
def analyze_sales_cached(df: pd.DataFrame) -> AnalysisResult:
    work = ensure_sales_amount(df)
    work, profitability_notes = add_profitability_metrics(work)

    if "date" in work.columns:
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work["month"] = work["date"].dt.to_period("M").astype(str)

    quantity = pd.to_numeric(work["quantity"], errors="coerce") if "quantity" in work.columns else pd.Series(dtype=float)
    sales = pd.to_numeric(work["sales_amount"], errors="coerce") if "sales_amount" in work.columns else pd.Series(dtype=float)

    total_sales = float(sales.fillna(0).sum()) if not sales.empty else 0.0
    total_units = float(quantity.fillna(0).sum()) if not quantity.empty else 0.0
    avg_order_value = float(sales.dropna().mean()) if not sales.empty and sales.dropna().shape[0] > 0 else 0.0

    gross_profit_total = 0.0
    gross_margin_pct = None
    if "gross_profit" in work.columns:
        gross_profit = pd.to_numeric(work["gross_profit"], errors="coerce")
        gross_profit_total = float(gross_profit.fillna(0).sum())
        gross_margin_pct = gross_profit_total / total_sales if total_sales else None

    top_products = pd.DataFrame()
    if {"product", "sales_amount"}.issubset(work.columns):
        temp = work.copy()
        temp["sales_amount"] = pd.to_numeric(temp["sales_amount"], errors="coerce")
        top_products = (
            temp.groupby("product", dropna=False)["sales_amount"]
            .sum(min_count=1)
            .fillna(0)
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

    monthly_sales = pd.DataFrame()
    if {"month", "sales_amount"}.issubset(work.columns):
        temp = work.copy()
        temp["sales_amount"] = pd.to_numeric(temp["sales_amount"], errors="coerce")
        monthly_sales = (
            temp.groupby("month", dropna=False)["sales_amount"]
            .sum(min_count=1)
            .fillna(0)
            .reset_index()
            .sort_values("month")
        )

    profit_by_product = pd.DataFrame()
    if {"product", "gross_profit"}.issubset(work.columns):
        temp = work.copy()
        temp["gross_profit"] = pd.to_numeric(temp["gross_profit"], errors="coerce")
        profit_by_product = (
            temp.groupby("product", dropna=False)["gross_profit"]
            .sum(min_count=1)
            .fillna(0)
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )

    profit_by_customer = pd.DataFrame()
    customer_col = "customer" if "customer" in work.columns else "customer_name" if "customer_name" in work.columns else None
    if customer_col and "gross_profit" in work.columns:
        temp = work.copy()
        temp["gross_profit"] = pd.to_numeric(temp["gross_profit"], errors="coerce")
        profit_by_customer = (
            temp.groupby(customer_col, dropna=False)["gross_profit"]
            .sum(min_count=1)
            .fillna(0)
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
            .rename(columns={customer_col: "customer"})
        )

    profitability_segments = build_profitability_segments(work)

    alerts = pd.DataFrame(columns=["alert_type", "details"])
    alert_rows = []

    if "sales_amount" in work.columns:
        zero_rows = int(pd.to_numeric(work["sales_amount"], errors="coerce").fillna(0).eq(0).sum())
        if zero_rows:
            alert_rows.append(
                {"alert_type": "Zero sales amount", "details": f"{zero_rows} rows have zero sales amount."}
            )

    if "quantity" in work.columns:
        negative_qty = int(pd.to_numeric(work["quantity"], errors="coerce").fillna(0).lt(0).sum())
        if negative_qty:
            alert_rows.append(
                {"alert_type": "Negative quantity", "details": f"{negative_qty} rows have negative quantity."}
            )

    if "gross_profit" in work.columns:
        negative_margin_rows = int(pd.to_numeric(work["gross_profit"], errors="coerce").fillna(0).lt(0).sum())
        if negative_margin_rows:
            alert_rows.append(
                {
                    "alert_type": "Negative gross profit",
                    "details": f"{negative_margin_rows} rows have negative gross profit.",
                }
            )

    if alert_rows:
        alerts = pd.DataFrame(alert_rows)

    recommendations = []

    if not monthly_sales.empty and len(monthly_sales) >= 2:
        latest = pd.to_numeric(monthly_sales["sales_amount"].iloc[-1], errors="coerce")
        previous = pd.to_numeric(monthly_sales["sales_amount"].iloc[-2], errors="coerce")

        if pd.notna(previous) and previous != 0 and pd.notna(latest):
            change = (latest - previous) / previous
            if change < -0.1:
                recommendations.append(
                    "Recent monthly sales declined by more than 10%. Review pricing, promotions, or customer demand shifts."
                )
            elif change > 0.1:
                recommendations.append(
                    "Recent monthly sales increased by more than 10%. Consider stocking more of the best-performing products."
                )

    if "gross_profit" in work.columns and gross_margin_pct is not None:
        if gross_margin_pct < 0:
            recommendations.append("Gross margin is negative overall. Review cost data, pricing, and loss-making products immediately.")
        elif gross_margin_pct < 0.2:
            recommendations.append("Gross margin is below 20%. Review pricing, discounts, and high-cost products.")
        else:
            recommendations.append("Profitability metrics are available. Review top and bottom margin products regularly.")
    else:
        recommendations.extend(profitability_notes)

    bottom_products = profitability_segments.get("bottom_products_by_gross_profit", pd.DataFrame())
    if not bottom_products.empty and (pd.to_numeric(bottom_products["gross_profit"], errors="coerce") < 0).any():
        recommendations.append("Review loss-making products and customers before increasing sales volume; revenue growth may be masking margin leakage.")

    if not top_products.empty:
        recommendations.append("Focus on your top-selling products for pricing, availability, and promotional planning.")

    if alerts.shape[0] > 0:
        recommendations.append("Resolve data anomalies before sharing final decisions with management.")

    if not recommendations:
        recommendations.append("Sales data looks usable. Track monthly trend, top products, and customer contribution regularly.")

    kpis = {
        "Total Sales": f"{total_sales:,.2f}",
        "Units Sold": f"{total_units:,.0f}",
        "Average Order Value": f"{avg_order_value:,.2f}",
        "Rows": f"{len(work):,}",
    }

    if "gross_profit" in work.columns:
        kpis = {
            "Total Sales": f"{total_sales:,.2f}",
            "Gross Profit": f"{gross_profit_total:,.2f}",
            "Gross Margin %": f"{gross_margin_pct:.1%}" if gross_margin_pct is not None else "n/a",
            "Rows": f"{len(work):,}",
        }

    chart_data = {
        "top_products": top_products,
        "monthly_sales": monthly_sales,
        "profit_by_product": profit_by_product,
        "profit_by_customer": profit_by_customer,
        **profitability_segments,
    }

    validation_report = validate_dataset(work, "sales", dataset_name="sales")

    return AnalysisResult(
        dataset_type="sales",
        cleaned_df=work,
        quality_issues=[issue.message for issue in validation_report.issues],
        kpis=kpis,
        alerts=alerts,
        recommendations=recommendations,
        chart_data=chart_data,
        validation_report=validation_report,
        join_reports=[],
    )
