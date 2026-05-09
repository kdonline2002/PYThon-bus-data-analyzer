from __future__ import annotations

import pandas as pd
import streamlit as st
import io

from config.settings import DEFAULT_PREFLIGHT_MODE
from data_cleaning.cleaner import SpreadsheetCleaner, get_excel_sheet_names, load_uploaded_file
from reporting.excel_report import build_excel_report
from reporting.visuals import render_bar_chart, render_line_chart
from services.pipeline_service import PipelineService
from utils.column_mapping import get_missing_required_fields_from_df, render_mapping_editor
from utils.mapping_profiles import MappingProfile, sanitize_profile_name, list_mapping_profiles, load_mapping_profile, save_mapping_profile
from utils.preflight import evaluate_preflight
from utils.demo_data import (
    get_demo_sales_data,
    get_demo_inventory_data,
    get_demo_customer_master,
    get_demo_product_master,
)

st.set_page_config(page_title="Business Data Analyzer", layout="wide")

with st.expander("ℹ️ How to use this tool", expanded=False):
    st.markdown("""
### What this app does
Upload your business data and get:
- Cleaned datasets
- Data quality checks
- Sales or inventory insights
- Profitability analysis (if cost data is available)

### Steps
1. Upload your main dataset
2. (Optional) Upload customer/product master data
3. Map your columns if needed
4. Review validation + preflight status
5. Explore insights and download report

### Profitability requirements
To calculate profit, you need:
- Quantity
- Either:
  - Unit Cost in your file, OR
  - Product master with cost data

If missing, profitability will be disabled.
""")

def choose_sheet(uploaded, label: str):
    if uploaded and uploaded.name.lower().endswith((".xlsx", ".xls")):
        names = get_excel_sheet_names(uploaded)
        selected = st.selectbox(f"Select sheet for {label}", names, index=0, key=f"sheet_{label}")
        uploaded.seek(0)
        return selected
    return None


def render_validation_report(report) -> None:
    if report is None or not getattr(report, "issues", None):
        st.success("No major data quality issues detected.")
        return

    severities = {"error": st.error, "warning": st.warning, "info": st.info}
    for issue in report.issues:
        renderer = severities.get(issue.severity, st.info)
        detail = issue.message
        if issue.column:
            detail += f" | column: {issue.column}"
        if issue.row_count is not None:
            detail += f" | rows: {issue.row_count}"
        renderer(detail)

        if issue.sample_rows is not None and not issue.sample_rows.empty:
            with st.expander(f"Sample rows for {issue.code}"):
                st.dataframe(issue.sample_rows, width="stretch")


def render_join_reports(join_reports) -> None:
    if not join_reports:
        st.info("No joins were applied.")
        return

    for report in join_reports:
        st.write(f"**{report.join_name}**")
        st.write(
            f"Match rate: {report.match_rate:.1%} | "
            f"Matched: {report.matched_rows:,} | "
            f"Unmatched: {report.unmatched_rows:,} | "
            f"Right-side duplicate key rows: {report.duplicate_key_count_right:,}"
        )
        for warning in report.warnings:
            st.warning(warning)
        if report.unmatched_sample is not None and not report.unmatched_sample.empty:
            with st.expander(f"Unmatched sample: {report.join_name}"):
                st.dataframe(report.unmatched_sample, width="stretch")


def render_preflight_banner(result) -> None:
    preflight = evaluate_preflight(result)

    # if preflight.overall_status == "GREEN":
    #     st.success(f"Preflight: GREEN | Risk score: {preflight.risk_score}")
    # elif preflight.overall_status == "AMBER":
    #     st.warning(f"Preflight: AMBER | Risk score: {preflight.risk_score}")
    # else:
    #     st.error(f"Preflight: RED | Risk score: {preflight.risk_score}")
    if preflight.overall_status == "GREEN":
        st.success("✅ Data is ready for analysis.")
    elif preflight.overall_status == "AMBER":
        st.warning("⚠️ Some issues detected. Results may need review.")
    else:
        st.error("⛔ High-risk data issues. Fix before trusting results.")



    cols = st.columns(4)
    cols[0].metric("Validation Errors", preflight.metrics["validation_errors"])
    cols[1].metric("Validation Warnings", preflight.metrics["validation_warnings"])
    cols[2].metric("Low-Match Joins", preflight.metrics["joins_below_warning_match"])
    cols[3].metric(
        "Severe Join Risks",
        preflight.metrics["joins_with_severe_row_inflation"]
        + preflight.metrics["joins_with_severe_duplicate_keys"],
    )

    if preflight.reasons:
        with st.expander("Why this status was assigned"):
            for reason in preflight.reasons[:12]:
                st.write(f"- {reason}")


def should_block_analysis(result) -> tuple[bool, list[str]]:
    preflight = evaluate_preflight(result)
    blocking_reasons: list[str] = []

    if preflight.metrics["validation_errors"] > 0:
        blocking_reasons.append("Validation errors must be fixed before trusting analysis.")

    if preflight.metrics["joins_below_fail_match"] > 0:
        blocking_reasons.append("One or more joins have match rates below the fail threshold.")

    if preflight.metrics["joins_with_severe_duplicate_keys"] > 0:
        blocking_reasons.append("One or more joins have severe duplicate-key issues on the right-side dataset.")

    if preflight.metrics["joins_with_severe_row_inflation"] > 0:
        blocking_reasons.append("One or more joins caused severe row inflation.")

    return (len(blocking_reasons) > 0, blocking_reasons)


def handle_preflight_gate(result, preflight_mode: str) -> bool:
    blocked, blocking_reasons = should_block_analysis(result)

    if not blocked:
        return False

    st.subheader("Blocking Issues")
    for reason in blocking_reasons:
        st.error(reason)

    if preflight_mode == "strict":
        st.stop()

    st.warning(
        "Review mode is enabled. Analysis will continue, but outputs should not be trusted until the blocking issues are fixed."
    )
    return True


def render_export_status_box(is_blocked: bool, preflight_mode: str) -> None:
    if is_blocked:
        if preflight_mode == "strict":
            st.error("Export Status: BLOCKED")
        else:
            st.warning("Export Status: REVIEW ONLY")
        st.caption("Fix the blocking issues before generating a shareable report.")
    else:
        st.success("Export Status: READY")
        st.caption("The dataset passed the current preflight rules for export.")


def render_run_summary(pipeline_output, result) -> None:
    validation_issue_count = (
        len(result.validation_report.issues)
        if result.validation_report is not None
        else 0
    )

    join_count = len(result.join_reports) if result.join_reports else 0
    matched_rows = sum(report.matched_rows for report in result.join_reports) if result.join_reports else 0
    unmatched_rows = sum(report.unmatched_rows for report in result.join_reports) if result.join_reports else 0

    preflight = evaluate_preflight(result)

    st.subheader("Run Summary")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Dataset Type", result.dataset_type.upper())
    col2.metric("Rows Loaded", f"{len(pipeline_output.main_bundle.raw):,}")
    col3.metric("Rows After Cleaning", f"{len(pipeline_output.main_bundle.cleaned):,}")
    col4.metric("Validation Issues", f"{validation_issue_count:,}")
    col5.metric("Joins Applied", f"{join_count:,}")
    col6.metric("Preflight", preflight.overall_status)

    if join_count > 0:
        col7, col8 = st.columns(2)
        col7.metric("Matched Rows", f"{matched_rows:,}")
        col8.metric("Unmatched Rows", f"{unmatched_rows:,}")


def main() -> None:
    st.title("Business Data Analyzer")
    st.caption("Clean messy spreadsheets and turn them into business-ready analysis reports.")

    with st.sidebar:
        st.header("Controls")
        # 11 Add sidebar help:
        st.markdown("---")
        st.markdown("### ℹ️ Help")
        st.markdown("""
        - Not sure what to upload? Start with sales or inventory data.
        - Missing columns? Use column mapping.
        - Profit not showing? Add cost data.
        """)
        forced_type = st.selectbox(
            "Primary dataset type",
            ["auto", "sales", "inventory", "general"],
            index=0,
        )

        preflight_mode = st.selectbox(
            "Preflight mode",
            ["strict", "review"],
            index=0 if DEFAULT_PREFLIGHT_MODE == "strict" else 1,
            help="Strict blocks high-risk runs. Review allows exploration with warnings.",
        )

        preview_rows = st.slider("Preview rows", min_value=5, max_value=100, value=20, step=5)
        enable_manual_mapping = st.checkbox("Enable manual column mapping", value=True)

        st.markdown("Upload one main dataset, then optionally enrich it with master data.")
        # st.code(
        #     "Main sales file: transactions\n"
        #     "Main inventory file: stock snapshot\n"
        #     "Optional: customer master + product master"
        # )


    # ---------------------------------------------------
    # Upload State
    # ---------------------------------------------------

    if "uploader_version" not in st.session_state:
        st.session_state["uploader_version"] = 0

    if "demo_choice" not in st.session_state:
        st.session_state["demo_choice"] = "None"


    # ---------------------------------------------------
    # File Uploads
    # ---------------------------------------------------

    st.subheader("📂 Upload Your Data")
    st.caption(
        "Start with your main dataset. "
        "You can optionally enrich it with customer and product master data."
    )

    col1, col2 = st.columns([2, 1])

    # ---------------------------------------------------
    # Main Upload
    # ---------------------------------------------------

    with col1:

        main_file = st.file_uploader(
            "Main dataset (sales, inventory, or general)",
            type=["csv", "xlsx", "xls"],
            key=f"main_file_{st.session_state['uploader_version']}",
        )

        # User uploaded real file while demo active
        if main_file and st.session_state["demo_choice"] != "None":
            st.session_state["demo_choice"] = "None"
            st.info("Switched from demo mode to uploaded file.")
            st.rerun()


    # ---------------------------------------------------
    # Demo Selector
    # ---------------------------------------------------

    with col2:

        demo_choice = st.selectbox(
            "🚀 Try Demo Data",
            ["None", "Sales", "Inventory", "Full (Sales + Masters)"],
            index=[
                "None",
                "Sales",
                "Inventory",
                "Full (Sales + Masters)",
            ].index(st.session_state["demo_choice"]),
        )

        if st.button("Load Demo"):

            st.session_state["demo_choice"] = demo_choice

            # Reset upload widgets
            st.session_state["uploader_version"] += 1

            st.success(f"{demo_choice} demo loaded.")
            st.rerun()

        if st.session_state["demo_choice"] != "None":

            st.info(f"Demo mode active: {st.session_state['demo_choice']}")

            if st.button("❌ Exit Demo Mode"):

                st.session_state["demo_choice"] = "None"

                # Reset upload widgets
                st.session_state["uploader_version"] += 1

                st.success("Exited demo mode.")
                st.rerun()


    # ---------------------------------------------------
    # Optional Master Files
    # ---------------------------------------------------

    customer_file = st.file_uploader(
        "Optional customer master",
        type=["csv", "xlsx", "xls"],
        key=f"customer_file_{st.session_state['uploader_version']}",
    )

    product_file = st.file_uploader(
        "Optional product master",
        type=["csv", "xlsx", "xls"],
        key=f"product_file_{st.session_state['uploader_version']}",
    )


    # ---------------------------------------------------
    # Demo Mode
    # ---------------------------------------------------

    demo_choice = st.session_state.get("demo_choice", "None")
    use_demo = demo_choice != "None"


    # ---------------------------------------------------
    # Empty State
    # ---------------------------------------------------

    if not main_file and not use_demo:
        st.info("Upload a dataset or try demo data to begin.")
        return




    # # 1 st.subheader("File Uploads")
    # st.subheader("📂 Upload Your Data")
    # st.caption("Start with your main dataset. You can optionally enrich it with master data.")
    
    # col1, col2 = st.columns([2, 1])

    # with col1:
    #     main_file = st.file_uploader(
    #         "Main dataset (sales, inventory, or general)",
    #         type=["csv", "xlsx", "xls"],
    #         key="main_file",
    #     )
    #     if main_file and st.session_state.get("demo_choice", "None") != "None":
    #         st.session_state["demo_choice"] = "None"
    #         st.info("Switched from demo mode to uploaded file.")

    # with col2:
    #     demo_choice = st.selectbox(
    #         "🚀 Try Demo Data",
    #         ["None", "Sales", "Inventory", "Full (Sales + Masters)"],
    #     )

    #     if st.button("Load Demo"):
    #         st.session_state["demo_choice"] = demo_choice

    #     if st.session_state.get("demo_choice", "None") != "None":
    #         if st.button("❌ Exit Demo Mode"):
    #             st.session_state["demo_choice"] = "None"
    #             st.session_state["use_demo_data"] = False
    #             st.rerun()


    # # main_file = st.file_uploader(
    # #     "Main dataset (sales, inventory, or general)",
    # #     type=["csv", "xlsx", "xls"],
    # #     key="main_file",
    # # )
    # customer_file = st.file_uploader(
    #     "Optional customer master",
    #     type=["csv", "xlsx", "xls"],
    #     key="customer_file",
    # )
    # product_file = st.file_uploader(
    #     "Optional product master",
    #     type=["csv", "xlsx", "xls"],
    #     key="product_file",
    # )

    # demo_choice = st.session_state.get("demo_choice", "None")

    # use_demo = demo_choice != "None"

    # if not main_file and not use_demo:
    #     st.info("Upload a dataset or try demo data to begin.")
    #     return

    main_sheet = choose_sheet(main_file, "main dataset")
    customer_sheet = choose_sheet(customer_file, "customer master") if customer_file else None
    product_sheet = choose_sheet(product_file, "product master") if product_file else None

    if use_demo:
        main_file = None
        st.info(
            f"You are viewing demo data: **{demo_choice}**. "
            "Upload your own file to analyze real data."
        )

        if demo_choice == "Sales":
            raw_df = get_demo_sales_data()
            customer_raw_df = None
            product_raw_df = None

        elif demo_choice == "Inventory":
            raw_df = get_demo_inventory_data()
            customer_raw_df = None
            product_raw_df = get_demo_product_master()

        elif demo_choice == "Full (Sales + Masters)":
            raw_df = get_demo_sales_data()
            customer_raw_df = get_demo_customer_master()
            product_raw_df = get_demo_product_master()

        st.success(f"Loaded demo: {demo_choice}")

    else:
        try:
            raw_df = load_uploaded_file(main_file, sheet_name=main_sheet)
        except Exception as exc:
            st.error(f"Could not load the main dataset: {exc}")
            return

    customer_raw_df = None
    product_raw_df = None

    if customer_file:
        try:
            customer_raw_df = load_uploaded_file(customer_file, sheet_name=customer_sheet)
        except Exception as exc:
            st.error(f"Could not load the customer master: {exc}")
            return

    if product_file:
        try:
            product_raw_df = load_uploaded_file(product_file, sheet_name=product_sheet)
        except Exception as exc:
            st.error(f"Could not load the product master: {exc}")
            return

    pipeline = PipelineService()

    main_mapping: dict[str, str] = {}
    customer_mapping: dict[str, str] = {}
    product_mapping: dict[str, str] = {}


    if use_demo:

        if demo_choice in ["Sales", "Full (Sales + Masters)"]:
            main_mapping = {
                "Order Date": "date",
                "Product Name": "product",
                "SKU Code": "sku",
                "Client Name": "customer",
                "Client ID": "customer_id",
                "Qty Sold": "quantity",
                "Selling Price": "unit_price",
                "Unit Cost": "unit_cost",
            }

        elif demo_choice == "Inventory":
            main_mapping = {
                "Product Name": "product",
                "SKU Code": "sku",
                "Category": "category",
                "Supplier": "supplier",
                "Supplier ID": "supplier_id",
                "Stock On Hand": "stock_on_hand",
                "Reorder Level": "reorder_level",
                "Cost": "cost",
            }

        customer_mapping = {
            "Customer ID": "customer_id",
            "Customer Name": "customer_name",
            "Customer Tier": "customer_tier",
            "Region": "region",
        }

        product_mapping = {
            "SKU": "sku",
            "Product Name": "product_name",
            "Category": "category",
            "Supplier": "supplier",
            "Supplier ID": "supplier_id",
            "Base Cost": "base_cost",
            "Base Price": "base_price",
        }


    selected_profile = None
    loaded_profile = None

    if enable_manual_mapping:
        # 2 st.subheader("Manual Column Mapping")
        st.subheader("🧭 Column Mapping")
        st.caption("Match your file’s column names to business fields (e.g., quantity, product, price).")

        available_profiles = list_mapping_profiles()
        profile_options = ["Do not load a saved profile"] + available_profiles
        selected_profile = st.selectbox(
            "Saved mapping profile",
            profile_options,
            index=0,
            key="selected_mapping_profile",
            help="Profiles are stored as local JSON files in ./mapping_profiles.",
        )
        st.caption(f"Profiles found: {len(available_profiles)}")

        if selected_profile != "Do not load a saved profile":
            try:
                loaded_profile = load_mapping_profile(selected_profile)
                st.success(f"Loaded mapping profile: {loaded_profile.name}")
            except Exception as exc:
                st.error(f"Could not load mapping profile '{selected_profile}': {exc}")
                loaded_profile = None

        profile_key_suffix = (
            sanitize_profile_name(selected_profile)
            if selected_profile and selected_profile != "Do not load a saved profile"
            else "manual"
        )

        guessed_type_output = pipeline.prepare_dataset(
            raw_df,
            dataset_name="main_preview",
            dataset_type=None if forced_type == "auto" else forced_type,
        )
        main_mapping_kind = guessed_type_output.metadata.get("dataset_type", "sales")
        if main_mapping_kind not in {"sales", "inventory"}:
            main_mapping_kind = "sales"

        cleaned_main_preview = SpreadsheetCleaner(raw_df).clean()
        _, main_mapping = render_mapping_editor(
            cleaned_main_preview,
            main_mapping_kind,
            f"mainmap_{profile_key_suffix}",
            initial_mapping=loaded_profile.main_mapping if loaded_profile else None,
        )

        if customer_raw_df is not None:
            cleaned_customer_preview = SpreadsheetCleaner(customer_raw_df).clean()
            _, customer_mapping = render_mapping_editor(
                cleaned_customer_preview,
                "customer_master",
                f"custmap_{profile_key_suffix}",
                initial_mapping=loaded_profile.customer_mapping if loaded_profile else None,
            )

        if product_raw_df is not None:
            cleaned_product_preview = SpreadsheetCleaner(product_raw_df).clean()
            _, product_mapping = render_mapping_editor(
                cleaned_product_preview,
                "product_master",
                f"prodmap_{profile_key_suffix}",
                initial_mapping=loaded_profile.product_mapping if loaded_profile else None,
            )

        with st.expander("Save current mapping as a local JSON profile"):
            default_profile_name = selected_profile if selected_profile and selected_profile != "Do not load a saved profile" else ""
            profile_name = st.text_input(
                "Profile name",
                value=default_profile_name,
                placeholder="Example: monthly_sales_export",
                key="mapping_profile_name",
            )
            if st.button("Save mapping profile", key="save_mapping_profile"):
                try:
                    saved_path = save_mapping_profile(
                        MappingProfile(
                            name=profile_name,
                            main_mapping=main_mapping,
                            customer_mapping=customer_mapping,
                            product_mapping=product_mapping,
                            main_dataset_type=main_mapping_kind,
                        )
                    )
                    st.success(f"Saved mapping profile to {saved_path}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save mapping profile: {exc}")

    blocking_errors: list[str] = []

    if enable_manual_mapping:
        main_required_kind = forced_type if forced_type in {"sales", "inventory"} else None
        if main_required_kind is None:
            guessed_type_output = pipeline.prepare_dataset(
                raw_df,
                dataset_name="main_required_check",
                dataset_type=None,
            )
            guessed_kind = guessed_type_output.metadata.get("dataset_type")
            if guessed_kind in {"sales", "inventory"}:
                main_required_kind = guessed_kind

        if main_required_kind in {"sales", "inventory"}:
            cleaned_main_preview = SpreadsheetCleaner(raw_df).clean()
            missing_main = get_missing_required_fields_from_df(
                cleaned_main_preview,
                main_mapping,
                main_required_kind,
            )
            if missing_main:
                blocking_errors.append(
                    f"Main dataset is missing required fields for {main_required_kind}: {missing_main}"
                )

    if blocking_errors:
        st.subheader("Blocking Issues")
        for err in blocking_errors:
            st.error(err)
        st.stop()

    pipeline_output = pipeline.run(
        raw_df,
        forced_dataset_type=forced_type,
        raw_customer_df=customer_raw_df,
        raw_product_df=product_raw_df,
        main_mapping=main_mapping,
        customer_mapping=customer_mapping,
        product_mapping=product_mapping,
    )

    # REM REMOVE comment out.
    with st.expander("Debug: Pipeline Internals"):
        st.write("Dataset type:", pipeline_output.dataset_type)
        st.write("Raw columns:", list(pipeline_output.main_bundle.raw.columns))
        st.write("Cleaned columns:", list(pipeline_output.main_bundle.cleaned.columns))
        st.write("Mapped columns:", list(pipeline_output.main_bundle.mapped.columns))
        st.write("Metadata:", pipeline_output.main_bundle.metadata)


    result = pipeline_output.analysis_result

    render_run_summary(pipeline_output, result)

    # 3 st.subheader("Preflight Status")
    st.subheader("🚦 Data Health Check")
    st.caption("We evaluate data quality, joins, and risks before analysis.")


    render_preflight_banner(result)
    is_blocked = handle_preflight_gate(result, preflight_mode)

    # 4 st.subheader("Join Summary")
    st.subheader("🔗 Data Enrichment Summary")
    st.caption("Shows how your data was combined with customer and product master data.")
    
    st.write(f"- Main dataset rows: {len(pipeline_output.main_bundle.cleaned):,}")
    if pipeline_output.customer_bundle is not None:
        st.write(f"- Customer master rows loaded: {len(pipeline_output.customer_bundle.cleaned):,}")
    if pipeline_output.product_bundle is not None:
        st.write(f"- Product master rows loaded: {len(pipeline_output.product_bundle.cleaned):,}")
    st.write(f"- Enriched dataset rows: {len(pipeline_output.enriched_df):,}")
    st.write(f"- Enriched dataset columns: {len(pipeline_output.enriched_df.columns):,}")

    if enable_manual_mapping:
        st.subheader("Mapping Summary")
        if main_mapping:
            st.write("Main dataset mappings applied:")
            st.json(main_mapping)
        if customer_mapping:
            st.write("Customer master mappings applied:")
            st.json(customer_mapping)
        if product_mapping:
            st.write("Product master mappings applied:")
            st.json(product_mapping)

    #  5 st.subheader("Overview")
    st.subheader("📊 Key Metrics")

    metric_items = list(result.kpis.items())
    cols = st.columns(4)
    for idx, col in enumerate(cols):
        if idx < len(metric_items):
            label, value = metric_items[idx]
            col.metric(label, value)

    st.subheader("Data Preview")
    tab1, tab2, tab3 = st.tabs(["Raw Main Data", "Cleaned Main Data", "Enriched/Analyzed Data"])
    with tab1:
        st.dataframe(raw_df.head(preview_rows), width="stretch")
    with tab2:
        st.dataframe(pipeline_output.main_bundle.cleaned.head(preview_rows), width="stretch")
    with tab3:
        st.dataframe(result.cleaned_df.head(preview_rows), width="stretch")

    st.subheader("Validation Report")
    render_validation_report(result.validation_report)

    st.subheader("Join Diagnostics")
    render_join_reports(result.join_reports)

    st.subheader("Alerts")
    if result.alerts.empty:
        st.info("No issues detected in your dataset.")
    else:
        st.dataframe(result.alerts, width="stretch")

    # 6 st.subheader("Charts")
    st.subheader("📈 Insights & Trends")
    # 9 Improve mapping UX (big win) Inside mapping section:
    st.info("""
    💡 Tips:
    - 'Qty', 'Units Sold' → Quantity
    - 'Price', 'Selling Price' → Unit Price
    - 'Cost', 'Unit Cost' → Unit Cost
    - 'Customer Name' → Customer
    """)

    if result.dataset_type == "sales":
        c1, c2 = st.columns(2)
        with c1:
            render_bar_chart(
                result.chart_data.get("top_products", pd.DataFrame()),
                "product",
                "sales_amount",
                "Top Products by Sales",
            )
        with c2:
            render_line_chart(
                result.chart_data.get("monthly_sales", pd.DataFrame()),
                "month",
                "sales_amount",
                "Monthly Sales Trend",
            )

        profit_by_product = result.chart_data.get("profit_by_product", pd.DataFrame())
        profit_by_customer = result.chart_data.get("profit_by_customer", pd.DataFrame())


        # 8 3. Add profitability explanation (very important) Right before charts or metrics:
        if "gross_profit" in result.cleaned_df.columns:
            st.info(
                "Profitability is calculated using sales and cost data. "
                "Negative margins may indicate pricing issues or incorrect cost data."
            )
        else:
            st.warning(
                "Profitability is not available. Add 'unit_cost' or a product master with cost data."
            )


        if not profit_by_product.empty or not profit_by_customer.empty:
            st.subheader("Profitability")
            p1, p2 = st.columns(2)
            with p1:
                if not profit_by_product.empty:
                    render_bar_chart(
                        profit_by_product,
                        "product",
                        "gross_profit",
                        "Top Products by Gross Profit",
                    )
                    with st.expander("Profit by product data"):
                        st.dataframe(profit_by_product, width="stretch")
                else:
                    st.info("Profit by product is unavailable because product or cost fields are missing.")
            with p2:
                if not profit_by_customer.empty:
                    render_bar_chart(
                        profit_by_customer,
                        "customer",
                        "gross_profit",
                        "Top Customers by Gross Profit",
                    )
                    with st.expander("Profit by customer data"):
                        st.dataframe(profit_by_customer, width="stretch")
                else:
                    st.info("Profit by customer is unavailable because customer or cost fields are missing.")

            product_segments = result.chart_data.get("product_profitability_segments", pd.DataFrame())
            customer_segments = result.chart_data.get("customer_profitability_segments", pd.DataFrame())
            bottom_products = result.chart_data.get("bottom_products_by_gross_profit", pd.DataFrame())
            bottom_customers = result.chart_data.get("bottom_customers_by_gross_profit", pd.DataFrame())

            with st.expander("Product profitability segmentation", expanded=False):
                if product_segments.empty:
                    st.info("Product segmentation is unavailable.")
                else:
                    st.dataframe(product_segments, width="stretch")

            with st.expander("Customer profitability segmentation", expanded=False):
                if customer_segments.empty:
                    st.info("Customer segmentation is unavailable.")
                else:
                    st.dataframe(customer_segments, width="stretch")

            c3, c4 = st.columns(2)
            with c3:
                if not bottom_products.empty:
                    st.write("**Lowest-profit products**")
                    st.dataframe(bottom_products, width="stretch")
            with c4:
                if not bottom_customers.empty:
                    st.write("**Lowest-profit customers**")
                    st.dataframe(bottom_customers, width="stretch")
        else:
            st.info("Profitability unlocks when quantity plus unit_cost or product-master base_cost are available.")
    elif result.dataset_type == "inventory":
        render_bar_chart(
            result.chart_data.get("stock_by_product", pd.DataFrame()),
            "product",
            "stock_on_hand",
            "Top Products by Stock On Hand",
        )
    else:
        st.info("Add sales or inventory columns to unlock charts.")

    # 7 st.subheader("Recommendations")
    st.subheader("💡 Recommendations")

    for rec in result.recommendations:
        st.write(f"- {rec}")

    #  10 st.subheader("Download Report")
    st.subheader("📥 Export Results")
    st.caption("Download a formatted Excel report with all insights and diagnostics.")

    render_export_status_box(is_blocked, preflight_mode)

    if is_blocked:
        st.info("Report export is disabled because the preflight checks found blocking issues.")
    else:
        excel_bytes = build_excel_report(result)
        st.download_button(
            label="Download Excel Report",
            data=excel_bytes,
            file_name=f"{result.dataset_type}_analysis_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if __name__ == "__main__":
    main()