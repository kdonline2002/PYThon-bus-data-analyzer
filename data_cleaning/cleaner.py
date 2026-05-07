from __future__ import annotations

import re
from typing import Optional

import pandas as pd

MISSING_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
    "-",
    "--",
    "unknown",
}

COLUMN_ALIASES = {
    "date": ["date", "order_date", "invoice_date", "transaction_date", "sales_date"],
    "product": ["product", "product_name", "item", "item_name", "sku_name", "description"],
    "sku": ["sku", "product_code", "item_code", "stock_code", "product_id"],
    "category": ["category", "product_category", "item_category", "department"],
    "customer": ["customer", "customer_name", "client", "buyer"],
    "region": ["region", "territory", "area", "location"],
    "quantity": ["quantity", "qty", "qty_sold", "units", "units_sold", "sales_qty", "sold_qty"],
    "unit_price": ["unit_price", "price", "selling_price", "rate"],
    "sales_amount": ["sales_amount", "sales_amt", "revenue", "sales", "amount", "total_sales", "line_total"],
    "stock_on_hand": ["stock_on_hand", "on_hand", "inventory", "stock", "qty_on_hand", "current_stock"],
    "reorder_level": ["reorder_level", "reorder_point", "min_stock", "minimum_stock"],
    "cost": ["cost", "unit_cost", "purchase_cost", "cost_price"],
}


class SpreadsheetCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def clean(self) -> pd.DataFrame:
        self._normalize_column_names()
        self._trim_whitespace()
        self._standardize_missing_values()
        self._drop_empty_rows_and_columns()
        self._remove_duplicate_rows()
        self._normalize_text_columns()
        self._fix_numeric_columns()
        self._fix_date_columns()
        self._standardize_column_aliases()
        return self.df

    def _normalize_column_names(self) -> None:
        cleaned = []
        seen: dict[str, int] = {}
        for col in self.df.columns:
            name = str(col).strip().lower()
            name = re.sub(r"[^a-z0-9]+", "_", name)
            name = re.sub(r"_+", "_", name).strip("_")
            if not name:
                name = "column"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 0
            cleaned.append(name)
        self.df.columns = cleaned

    def _trim_whitespace(self) -> None:
        for col in self.df.columns:
            if pd.api.types.is_object_dtype(self.df[col]):
                self.df[col] = self.df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    def _standardize_missing_values(self) -> None:
        for col in self.df.columns:
            self.df[col] = self.df[col].map(self._clean_missing_text)

    @staticmethod
    def _clean_missing_text(value):
        if pd.isna(value):
            return pd.NA

        if isinstance(value, str):
            text = value.strip()
            if text.lower() in MISSING_VALUES:
                return pd.NA

        return value

    def _drop_empty_rows_and_columns(self) -> None:
        self.df = self.df.dropna(axis=0, how="all")
        self.df = self.df.dropna(axis=1, how="all")

    def _remove_duplicate_rows(self) -> None:
        self.df = self.df.drop_duplicates()

    def _normalize_text_columns(self) -> None:
        for col in self.df.columns:
            if pd.api.types.is_object_dtype(self.df[col]):
                self.df[col] = self.df[col].map(self._clean_text)

    @staticmethod
    def _clean_text(value):
        if not isinstance(value, str):
            return value
        return re.sub(r"\s+", " ", value).strip()

    def _fix_numeric_columns(self) -> None:
        for col in self.df.columns:
            if not pd.api.types.is_object_dtype(self.df[col]):
                continue
            sample = self.df[col].dropna().astype(str)
            if sample.empty:
                continue
            converted = sample.map(self._parse_number)
            if converted.notna().mean() >= 0.8:
                self.df[col] = self.df[col].map(self._parse_number)

    @staticmethod
    def _parse_number(value):
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (int, float)):
            return value
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return pd.NA
        for symbol in [",", "$", "€", "£", "%", "R"]: #text = text.replace("R", "")
            text = text.replace(symbol, "")
        return pd.to_numeric(text, errors="coerce")

    def _fix_date_columns(self) -> None:
        for col in self.df.columns:
            if not pd.api.types.is_object_dtype(self.df[col]):
                continue
            if "date" not in col and "time" not in col:
                continue
            parsed = pd.to_datetime(self.df[col], errors="coerce")
            if parsed.notna().mean() >= 0.5:
                self.df[col] = parsed

    def _standardize_column_aliases(self) -> None:
        rename_map = {}
        used_targets = set()
        for canonical, aliases in COLUMN_ALIASES.items():
            for col in self.df.columns:
                if col in used_targets:
                    continue
                if col == canonical or col in aliases:
                    rename_map[col] = canonical
                    used_targets.add(canonical)
                    break
        self.df = self.df.rename(columns=rename_map)


def load_uploaded_file(uploaded_file, sheet_name: Optional[str] = None) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if file_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file, sheet_name=sheet_name or 0)
    raise ValueError("Unsupported file type. Please upload CSV or Excel.")


def get_excel_sheet_names(uploaded_file) -> list[str]:
    if uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        uploaded_file.seek(0)
        xls = pd.ExcelFile(uploaded_file)
        uploaded_file.seek(0)
        return [str(sheet_name) for sheet_name in xls.sheet_names]
    return []


def infer_dataset_type(df: pd.DataFrame) -> str:
    cols = set(df.columns)
    sales_score = sum(col in cols for col in ["sales_amount", "quantity", "customer", "date", "product"])
    inventory_score = sum(col in cols for col in ["stock_on_hand", "reorder_level", "sku", "product", "category"])

    if sales_score >= inventory_score and sales_score >= 2:
        return "sales"
    if inventory_score >= 2:
        return "inventory"
    return "general"
