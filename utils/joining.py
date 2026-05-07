from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from data_cleaning.cleaner import SpreadsheetCleaner
from utils.models import JoinReport


CANONICAL_ALIASES = {
    "customer_id": ["customer_id", "client_id", "cust_id", "account_id"],
    "customer_name": ["customer_name", "customer", "client_name", "account_name"],
    "sku": ["sku", "product_code", "item_code", "stock_code"],
    "product_name": ["product_name", "product", "item_name", "description"],
    "supplier": ["supplier", "vendor", "supplier_name"],
    "supplier_id": ["supplier_id", "vendor_id"],
    "lifecycle_stage": ["lifecycle_stage", "product_lifecycle", "stage"],
}


@dataclass
class JoinResult:
    dataframe: pd.DataFrame
    report: JoinReport


def _standardize_master_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = SpreadsheetCleaner(df).clean()
    rename_map: dict[str, str] = {}

    for canonical, aliases in CANONICAL_ALIASES.items():
        for col in out.columns:
            if col == canonical or col in aliases:
                rename_map[col] = canonical
                break

    return out.rename(columns=rename_map)


def _normalize_join_key(series: pd.Series) -> pd.Series:
    normalized = series.astype("string")
    normalized = normalized.str.strip().str.lower()
    normalized = normalized.str.replace(r"[^a-z0-9]+", " ", regex=True)
    normalized = normalized.str.replace(r"\s+", " ", regex=True).str.strip()
    return normalized


def _duplicate_key_count(df: pd.DataFrame, key: str) -> int:
    if key not in df.columns:
        return 0
    return int(df[key].duplicated(keep=False).sum())


def safe_left_join(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    *,
    left_key: str,
    right_key: str,
    join_name: str,
    left_dataset: str,
    right_dataset: str,
    normalize_keys: bool = False,
) -> JoinResult:
    left = left_df.copy()
    right = right_df.copy()
    warnings: list[str] = []

    if left_key not in left.columns:
        report = JoinReport(
            join_name=join_name,
            left_dataset=left_dataset,
            right_dataset=right_dataset,
            join_type="left",
            join_key_left=left_key,
            join_key_right=right_key,
            left_rows_before=len(left_df),
            left_rows_after=len(left_df),
            matched_rows=0,
            unmatched_rows=len(left_df),
            match_rate=0.0,
            duplicate_key_count_right=0,
            row_inflation=0,
            warnings=[f"Left join key '{left_key}' not found."],
            unmatched_sample=left_df.head(20),
        )
        return JoinResult(dataframe=left_df.copy(), report=report)

    if right_key not in right.columns:
        report = JoinReport(
            join_name=join_name,
            left_dataset=left_dataset,
            right_dataset=right_dataset,
            join_type="left",
            join_key_left=left_key,
            join_key_right=right_key,
            left_rows_before=len(left_df),
            left_rows_after=len(left_df),
            matched_rows=0,
            unmatched_rows=len(left_df),
            match_rate=0.0,
            duplicate_key_count_right=0,
            row_inflation=0,
            warnings=[f"Right join key '{right_key}' not found."],
            unmatched_sample=left_df.head(20),
        )
        return JoinResult(dataframe=left_df.copy(), report=report)

    work_left_key = left_key
    work_right_key = right_key

    if normalize_keys:
        work_left_key = f"__norm_{left_key}"
        work_right_key = f"__norm_{right_key}"
        left[work_left_key] = _normalize_join_key(left[left_key])
        right[work_right_key] = _normalize_join_key(right[right_key])

    duplicate_key_count_right = _duplicate_key_count(right, work_right_key)
    if duplicate_key_count_right:
        warnings.append(
            f"Right dataset '{right_dataset}' has {duplicate_key_count_right} duplicated join-key rows on '{right_key}'."
        )

    deduped_right = right.drop_duplicates(subset=[work_right_key], keep="first")
    right_cols = [c for c in deduped_right.columns if c not in left.columns or c == work_right_key]

    merged = left.merge(
        deduped_right[right_cols],
        how="left",
        left_on=work_left_key,
        right_on=work_right_key,
        suffixes=("", f"_{right_dataset}"),
    )

    matched_mask = (
        merged[work_right_key].notna()
        if work_right_key in merged.columns
        else pd.Series(False, index=merged.index)
    )

    matched_rows = int(matched_mask.sum())
    unmatched_rows = int((~matched_mask).sum())
    left_rows_before = len(left_df)
    left_rows_after = len(merged)
    row_inflation = left_rows_after - left_rows_before

    if row_inflation > 0:
        warnings.append(f"Join increased row count by {row_inflation}. Review master key uniqueness.")

    unmatched_sample = merged.loc[~matched_mask].head(20).copy() if unmatched_rows else None
    if unmatched_rows:
        warnings.append(f"{unmatched_rows} rows did not match during '{join_name}'.")

    if normalize_keys:
        merged = merged.drop(columns=[c for c in [work_left_key, work_right_key] if c in merged.columns])

    report = JoinReport(
        join_name=join_name,
        left_dataset=left_dataset,
        right_dataset=right_dataset,
        join_type="left",
        join_key_left=left_key,
        join_key_right=right_key,
        left_rows_before=left_rows_before,
        left_rows_after=left_rows_after,
        matched_rows=matched_rows,
        unmatched_rows=unmatched_rows,
        match_rate=(matched_rows / left_rows_before) if left_rows_before else 0.0,
        duplicate_key_count_right=duplicate_key_count_right,
        row_inflation=row_inflation,
        warnings=warnings,
        unmatched_sample=unmatched_sample,
    )

    return JoinResult(dataframe=merged, report=report)


def enrich_sales_with_masters(
    sales_df: pd.DataFrame,
    customer_master_df: Optional[pd.DataFrame] = None,
    product_master_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, list[JoinReport]]:
    enriched = sales_df.copy()
    reports: list[JoinReport] = []

    if customer_master_df is not None and not customer_master_df.empty:
        customer_master = _standardize_master_columns(customer_master_df)

        if "customer_id" in enriched.columns and "customer_id" in customer_master.columns:
            result = safe_left_join(
                enriched,
                customer_master,
                left_key="customer_id",
                right_key="customer_id",
                join_name="sales_to_customer_master",
                left_dataset="sales",
                right_dataset="customer_master",
            )
            enriched = result.dataframe
            reports.append(result.report)

        elif "customer" in enriched.columns and "customer_name" in customer_master.columns:
            result = safe_left_join(
                enriched,
                customer_master,
                left_key="customer",
                right_key="customer_name",
                join_name="sales_to_customer_master_name",
                left_dataset="sales",
                right_dataset="customer_master",
                normalize_keys=True,
            )
            enriched = result.dataframe
            reports.append(result.report)

    if product_master_df is not None and not product_master_df.empty:
        product_master = _standardize_master_columns(product_master_df)

        if "sku" in enriched.columns and "sku" in product_master.columns:
            result = safe_left_join(
                enriched,
                product_master,
                left_key="sku",
                right_key="sku",
                join_name="sales_to_product_master",
                left_dataset="sales",
                right_dataset="product_master",
            )
            enriched = result.dataframe
            reports.append(result.report)

        elif "product" in enriched.columns and "product_name" in product_master.columns:
            result = safe_left_join(
                enriched,
                product_master,
                left_key="product",
                right_key="product_name",
                join_name="sales_to_product_master_name",
                left_dataset="sales",
                right_dataset="product_master",
                normalize_keys=True,
            )
            enriched = result.dataframe
            reports.append(result.report)

    return enriched, reports


def enrich_inventory_with_product_master(
    inventory_df: pd.DataFrame,
    product_master_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, list[JoinReport]]:
    enriched = inventory_df.copy()
    reports: list[JoinReport] = []

    if product_master_df is None or product_master_df.empty:
        return enriched, reports

    product_master = _standardize_master_columns(product_master_df)

    if "sku" in enriched.columns and "sku" in product_master.columns:
        result = safe_left_join(
            enriched,
            product_master,
            left_key="sku",
            right_key="sku",
            join_name="inventory_to_product_master",
            left_dataset="inventory",
            right_dataset="product_master",
        )
        enriched = result.dataframe
        reports.append(result.report)

    elif "product" in enriched.columns and "product_name" in product_master.columns:
        result = safe_left_join(
            enriched,
            product_master,
            left_key="product",
            right_key="product_name",
            join_name="inventory_to_product_master_name",
            left_dataset="inventory",
            right_dataset="product_master",
            normalize_keys=True,
        )
        enriched = result.dataframe
        reports.append(result.report)

    return enriched, reports