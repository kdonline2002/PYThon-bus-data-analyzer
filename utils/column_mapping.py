from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
import streamlit as st


CANONICAL_FIELDS = {
    "sales": [
        "date",
        "product",
        "sku",
        "customer",
        "customer_id",
        "category",
        "region",
        "quantity",
        "unit_price",
        "sales_amount",
        "unit_cost",
    ],
    "inventory": [
        "product",
        "sku",
        "category",
        "supplier",
        "supplier_id",
        "stock_on_hand",
        "reorder_level",
        "cost",
    ],
    "customer_master": [
        "customer_id",
        "customer_name",
        "customer_tier",
        "region",
        "payment_terms",
        "account_manager",
    ],
    "product_master": [
        "sku",
        "product_name",
        "category",
        "subcategory",
        "supplier",
        "supplier_id",
        "lifecycle_stage",
        "lead_time_days",
        "reorder_point",
        "base_price",
        "base_cost",
    ],
}

REQUIRED_FIELDS = {
    "sales": ["date", "product", "quantity"],
    "inventory": ["product", "stock_on_hand"],
    "customer_master": [],
    "product_master": [],
}


FIELD_ALIASES = {
    "date": [
        "date",
        "order date",
        "invoice date",
        "transaction date",
        "sales date",
        "posting date",
    ],
    "product": [
        "product",
        "product name",
        "item",
        "item name",
        "description",
        "stock item",
    ],
    "product_name": [
        "product",
        "product name",
        "item",
        "item name",
        "description",
        "stock item",
    ],
    "sku": [
        "sku",
        "product code",
        "item code",
        "stock code",
        "product id",
        "sku code",
    ],
    "customer": [
        "customer",
        "customer name",
        "client",
        "client name",
        "account",
        "buyer",
    ],
    "customer_name": [
        "customer",
        "customer name",
        "client",
        "client name",
        "account",
        "buyer",
    ],
    "customer_id": [
        "customer id",
        "client id",
        "account id",
        "cust id",
    ],
    "category": [
        "category",
        "product category",
        "item category",
        "department",
    ],
    "subcategory": [
        "subcategory",
        "sub category",
        "product subcategory",
    ],
    "region": [
        "region",
        "territory",
        "area",
        "location",
        "zone",
    ],
    "quantity": [
        "quantity",
        "qty",
        "qty sold",
        "units",
        "units sold",
        "sales qty",
        "sold qty",
    ],
    "unit_price": [
        "unit price",
        "price",
        "selling price",
        "sell price",
        "rate",
    ],
    "sales_amount": [
        "sales amount",
        "sales amt",
        "revenue",
        "sales",
        "amount",
        "line total",
        "turnover",
        "total sales",
        "invoice amount",
    ],
    "unit_cost": [
        "unit cost",
        "cost price",
        "cost",
        "purchase cost",
        "base cost",
    ],
    "cost": [
        "unit cost",
        "cost price",
        "cost",
        "purchase cost",
        "base cost",
    ],
    "stock_on_hand": [
        "stock",
        "stock on hand",
        "on hand",
        "inventory",
        "qty on hand",
        "current stock",
        "available stock",
    ],
    "reorder_level": [
        "reorder level",
        "reorder point",
        "minimum stock",
        "min stock",
        "safety stock",
    ],
    "reorder_point": [
        "reorder point",
        "reorder level",
        "minimum stock",
        "min stock",
        "safety stock",
    ],
    "supplier": [
        "supplier",
        "vendor",
        "supplier name",
        "vendor name",
    ],
    "supplier_id": [
        "supplier id",
        "vendor id",
    ],
    "customer_tier": [
        "customer tier",
        "tier",
        "segment",
        "customer segment",
    ],
    "payment_terms": [
        "payment terms",
        "terms",
    ],
    "account_manager": [
        "account manager",
        "sales rep",
        "salesperson",
        "owner",
    ],
    "lifecycle_stage": [
        "lifecycle stage",
        "product lifecycle",
        "stage",
    ],
    "lead_time_days": [
        "lead time days",
        "lead time",
    ],
    "base_price": [
        "base price",
        "list price",
        "standard price",
    ],
    "base_cost": [
        "base cost",
        "standard cost",
        "default cost",
    ],
}


def normalize_name(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def tokenize(value: str) -> set[str]:
    return set(normalize_name(value).split())


def apply_manual_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    rename_map = {source: target for source, target in mapping.items() if source and target and source != target}
    if not rename_map:
        return df
    return df.rename(columns=rename_map)

# def get_missing_required_fields(mapping: dict[str, str], dataset_kind: str) -> list[str]:
#     required_fields = REQUIRED_FIELDS.get(dataset_kind, [])
#     assigned = set(mapping.values())
#     return [field for field in required_fields if field not in assigned]
def get_missing_required_fields_from_df(
    df: pd.DataFrame,
    mapping: dict[str, str],
    dataset_kind: str,
) -> list[str]:
    required_fields = REQUIRED_FIELDS.get(dataset_kind, [])
    mapped_df = apply_mapping_to_cleaned_df(df, mapping)
    return [field for field in required_fields if field not in mapped_df.columns]


def apply_mapping_to_cleaned_df(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    rename_map = {}
    used_targets: set[str] = set()

    for source, target in mapping.items():
        if not source or not target:
            continue
        if source not in df.columns:
            continue
        if target in used_targets:
            continue
        if source == target:
            used_targets.add(target)
            continue

        rename_map[source] = target
        used_targets.add(target)

    if not rename_map:
        return df

    return df.rename(columns=rename_map)


def profile_matches_field(series: pd.Series, field: str) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False

    sample = non_null.head(100)

    if field in {
        "quantity",
        "unit_price",
        "sales_amount",
        "unit_cost",
        "cost",
        "stock_on_hand",
        "reorder_level",
        "reorder_point",
        "base_price",
        "base_cost",
        "lead_time_days",
    }:
        numeric = pd.to_numeric(sample, errors="coerce")
        return numeric.notna().mean() >= 0.7

    if field == "date":
        # parsed = pd.to_datetime(sample, errors="coerce")
        # return parsed.notna().mean() >= 0.6
        parsed = pd.to_datetime(
            series.astype(str).str.strip(),
            errors="coerce",
            format="mixed"
        )
        return parsed.notna().mean() >= 0.6
    return True


# def score_column_to_field(column_name: str, series: pd.Series, field: str) -> tuple[float, list[str]]:
#     reasons: list[str] = []
#     score = 0.0

#     col_norm = normalize_name(column_name)
#     field_norm = normalize_name(field)
#     aliases = [normalize_name(a) for a in FIELD_ALIASES.get(field, [])]

#     if col_norm == field_norm:
#         score += 1.0
#         reasons.append("exact field name match")

#     if col_norm in aliases:
#         score += 0.95
#         reasons.append("exact alias match")

#     col_tokens = tokenize(column_name)

#     if field_norm in col_norm and field_norm != col_norm:
#         score += 0.35
#         reasons.append("field name contained in column name")

#     alias_token_scores = []
#     for alias in aliases:
#         alias_tokens = tokenize(alias)
#         if alias_tokens:
#             overlap = len(col_tokens & alias_tokens) / len(alias_tokens)
#             alias_token_scores.append(overlap)

#     if alias_token_scores:
#         best_overlap = max(alias_token_scores)
#         if best_overlap >= 0.5:
#             score += best_overlap * 0.5
#             reasons.append("token overlap with alias")

#     if profile_matches_field(series, field):
#         score += 0.2
#         reasons.append("data profile compatible")

#     return score, reasons

def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_column_to_field(column_name: str, series: pd.Series, field: str) -> tuple[float, list[str]]:
    reasons: list[str] = []

    col_norm = normalize_name(column_name)
    field_norm = normalize_name(field)
    aliases = [normalize_name(a) for a in FIELD_ALIASES.get(field, [])]

    col_tokens = tokenize(column_name)
    field_tokens = tokenize(field_norm)

    # --- Signals ---
    exact_match = col_norm == field_norm
    alias_exact = col_norm in aliases

    # Token similarity (best alias match)
    token_scores = []
    for alias in aliases + [field_norm]:
        alias_tokens = tokenize(alias)
        score = jaccard_similarity(col_tokens, alias_tokens)
        token_scores.append(score)

    token_similarity = max(token_scores) if token_scores else 0.0

    # Substring signal
    substring_match = field_norm in col_norm or any(alias in col_norm for alias in aliases)

    # Data profile
    profile_match = profile_matches_field(series, field)

    # --- Weighted score ---
    score = 0.0

    if exact_match:
        score = 1.0
        reasons.append("exact field name match")
        return score, reasons

    if alias_exact:
        score = 0.9
        reasons.append("exact alias match")

    # Token similarity (scaled)
    if token_similarity > 0:
        score += token_similarity * 0.6
        reasons.append(f"token similarity ({token_similarity:.2f})")

    # Substring boost
    if substring_match:
        score += 0.3
        reasons.append("substring match")

    # Data profile
    if profile_match:
        score += 0.2
        reasons.append("data profile compatible")

    # --- Clamp to 1.0 ---
    score = min(score, 1.0)

    return score, reasons



# def suggest_mapping(columns: Iterable[str], df: pd.DataFrame, canonical_fields: list[str]) -> dict[str, str]:
#     suggestions: dict[str, str] = {}
#     assigned_targets: set[str] = set()

#     for col in columns:
#         if col not in df.columns:
#             continue

#         best_field = ""
#         best_score = 0.0

#         for field in canonical_fields:
#             if field in assigned_targets:
#                 continue
#             score, _ = score_column_to_field(col, df[col], field)
#             if score > best_score:
#                 best_score = score
#                 best_field = field

#         if best_field and best_score >= 0.75:
#             suggestions[col] = best_field
#             assigned_targets.add(best_field)

#     return suggestions
def suggest_mapping(columns: Iterable[str], df: pd.DataFrame, canonical_fields: list[str]) -> dict[str, str]:
    suggestions: dict[str, str] = {}
    assigned_targets: set[str] = set()

    for col in columns:
        if col not in df.columns:
            continue

        best_field = ""
        best_score = 0.0

        for field in canonical_fields:
            if field in assigned_targets:
                continue

            score, _ = score_column_to_field(col, df[col], field)

            if score > best_score:
                best_score = score
                best_field = field

        # ✅ Only auto-map high confidence
        if best_field and best_score >= 0.8:
            suggestions[col] = best_field
            assigned_targets.add(best_field)

    return suggestions

def build_mapping_diagnostics(df: pd.DataFrame, canonical_fields: list[str]) -> pd.DataFrame:
    rows = []
    assigned_targets: set[str] = set()

    for col in df.columns:
        best_field = ""
        best_score = 0.0
        best_reasons: list[str] = []

        for field in canonical_fields:
            score, reasons = score_column_to_field(col, df[col], field)
            if score > best_score:
                best_score = score
                best_field = field
                best_reasons = reasons

        if best_field in assigned_targets and best_score >= 0.75:
            suggested = ""
        else:
            suggested = best_field if best_score >= 0.6 else ""
            if suggested:
                assigned_targets.add(suggested)

        dtype_str = str(df[col].dtype)
        sample_values = ", ".join(df[col].dropna().astype(str).head(3).tolist())

        rows.append(
            {
                "source_column": col,
                "suggested_target": suggested,
                "confidence": round(best_score, 2), #"confidence": f"{score_to_confidence(best_score)} ({best_score:.2f})",
                "dtype": dtype_str,
                "sample_values": sample_values,
                "reasons": "; ".join(best_reasons),
            }
        )

    return pd.DataFrame(rows)

def score_to_confidence(score: float) -> str:
    try:
        score = float(score)
    except Exception:
        return "⚪ Unknown"

    if score >= 0.75:
        return "🟢 High"
    elif score >= 0.5:
        return "🟡 Medium"
    else:
        return "🔴 Low"

def validate_mapping(mapping: dict[str, str], required_fields: list[str]) -> list[str]:
    problems: list[str] = []
    assigned = [target for target in mapping.values() if target]

    duplicates = sorted({target for target in assigned if assigned.count(target) > 1})
    if duplicates:
        problems.append(f"Duplicate mapping targets selected: {duplicates}")

    missing_required = [field for field in required_fields if field not in assigned]
    if missing_required:
        problems.append(f"Missing required mapped fields: {missing_required}")

    return problems


def render_mapping_editor(
    df: pd.DataFrame,
    dataset_kind: str,
    key_prefix: str,
    initial_mapping: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    if dataset_kind not in CANONICAL_FIELDS:
        return df, {}

    st.markdown(f"#### Column Mapping: {dataset_kind.replace('_', ' ').title()}")
    st.caption("Map uploaded columns to the business fields your analysis expects.")

    auto_map_enabled = st.toggle(
        "⚡ Auto-map high confidence columns",
        value=True,
        key=f"{key_prefix}_auto_map"
    )
    
    canonical_fields = CANONICAL_FIELDS[dataset_kind]
    required_fields = REQUIRED_FIELDS.get(dataset_kind, [])
    diagnostics = build_mapping_diagnostics(df, canonical_fields)

    # initial_mapping = initial_mapping or {}
    # auto_mapping = suggest_mapping(df.columns, df, canonical_fields)
    # initial_mapping = {**auto_mapping, **(initial_mapping or {})}
    # Auto-mapping layer
    if auto_map_enabled:
        auto_mapping = suggest_mapping(df.columns, df, canonical_fields)
    else:
        auto_mapping = {}

    # Merge priority:
    # 1. saved/user mapping (highest priority)
    # 2. auto-mapping (fallback)
    initial_mapping = {**auto_mapping, **(initial_mapping or {})}
    
    mapping: dict[str, str] = {}
    used_targets: set[str] = set()

    if required_fields:
        st.info(f"Required fields for {dataset_kind}: {', '.join(required_fields)}")

    for _, row in diagnostics.iterrows():
        source_col = row["source_column"]
        suggested_target = row["suggested_target"] if pd.notna(row["suggested_target"]) else ""
        confidence = row["confidence"]
        confidence_label = score_to_confidence(confidence)
        dtype_str = row["dtype"]
        sample_values = row["sample_values"]
        reasons = row["reasons"]

        # label_suffix = " (required suggestion)" if suggested_target in required_fields else ""
        confidence_label = score_to_confidence(row["confidence"])
        auto_flag = "⚡ auto-mapped" if initial_mapping.get(source_col) else ""
        with st.expander(
            f"{source_col} → {suggested_target or '—'}  {confidence_label} ({confidence:.2f})  {auto_flag}" #f"{source_col}  →  {suggested_target or '—'}  {confidence_label} {auto_flag}"
        ):
            st.caption("You can override this mapping if needed.")    

            if suggested_target:
                if st.button(f"Reset to suggested for {source_col}", key=f"reset_{key_prefix}_{source_col}"):
                    mapping[source_col] = suggested_target
                    st.rerun()

            st.write(f"**dtype:** {dtype_str}")
            if sample_values:
                st.write(f"**sample values:** {sample_values}")
            if reasons:
                st.write(f"**why suggested:** {reasons}")

            options = [""] + canonical_fields
            saved_target = initial_mapping.get(source_col, "")
            default_target = saved_target if saved_target in options else suggested_target
            default_index = options.index(default_target) if default_target in options else 0
            selected_target = st.selectbox(
                f"Map '{source_col}' to",
                options=options,
                index=default_index,
                key=f"{key_prefix}_{source_col}",
            )

            if selected_target:
                if selected_target in used_targets:
                    st.warning(f"'{selected_target}' is already assigned. Only the first mapping will be used.")
                else:
                    mapping[source_col] = selected_target
                    used_targets.add(selected_target)



    mapped_df = apply_mapping_to_cleaned_df(df, mapping)

    problems = []
    duplicate_targets = sorted({t for t in mapping.values() if t and list(mapping.values()).count(t) > 1})
    if duplicate_targets:
        problems.append(f"Duplicate mapping targets selected: {duplicate_targets}")

    missing_required = [field for field in required_fields if field not in mapped_df.columns]
    if missing_required:
        problems.append(f"Missing required mapped fields: {missing_required}")

    for problem in problems:
        st.warning(problem)

    if not problems and required_fields:
        st.success("Required fields are mapped.")

    st.dataframe(diagnostics, width="stretch")
    return mapped_df, mapping



    # problems = validate_mapping(mapping, required_fields=required_fields)
    # for problem in problems:
    #     st.warning(problem)

    # if not problems and required_fields:
    #     st.success("Required fields are mapped.")

    # mapped_df = apply_mapping_to_cleaned_df(df, mapping)
    # st.dataframe(diagnostics, width="stretch")
    # return mapped_df, mapping