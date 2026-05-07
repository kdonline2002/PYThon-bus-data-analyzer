from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from analytics.inventory_analysis import analyze_inventory
from analytics.sales_analysis import analyze_sales
from data_cleaning.cleaner import SpreadsheetCleaner, infer_dataset_type
from data_cleaning.validators_v2 import validate_dataset
from utils.column_mapping import apply_mapping_to_cleaned_df
from utils.joining import enrich_inventory_with_product_master, enrich_sales_with_masters
from utils.models import AnalysisResult, DatasetBundle, JoinReport


@dataclass
class PipelineOutput:
    dataset_type: str
    main_bundle: DatasetBundle
    customer_bundle: Optional[DatasetBundle]
    product_bundle: Optional[DatasetBundle]
    enriched_df: pd.DataFrame
    join_reports: list[JoinReport]
    analysis_result: AnalysisResult


class PipelineService:
    def prepare_dataset(
        self,
        raw_df: pd.DataFrame,
        *,
        dataset_name: str,
        dataset_type: Optional[str] = None,
        mapping: Optional[dict[str, str]] = None,
    ) -> DatasetBundle:
        cleaned = SpreadsheetCleaner(raw_df).clean()
        mapped = apply_mapping_to_cleaned_df(cleaned, mapping or {})
        resolved_type = dataset_type or infer_dataset_type(mapped)
        report = validate_dataset(mapped, resolved_type, dataset_name=dataset_name)

        return DatasetBundle(
            dataset_name=dataset_name,
            raw=raw_df,
            cleaned=cleaned,
            mapped=mapped,
            validation_report=report,
            metadata={
                "dataset_type": resolved_type,
                "mapping_applied": mapping or {},
            },
        )

    def run(
        self,
        raw_main_df: pd.DataFrame,
        *,
        forced_dataset_type: Optional[str] = None,
        raw_customer_df: Optional[pd.DataFrame] = None,
        raw_product_df: Optional[pd.DataFrame] = None,
        main_mapping: Optional[dict[str, str]] = None,
        customer_mapping: Optional[dict[str, str]] = None,
        product_mapping: Optional[dict[str, str]] = None,
    ) -> PipelineOutput:
        main_bundle = self.prepare_dataset(
            raw_main_df,
            dataset_name="main",
            dataset_type=forced_dataset_type if forced_dataset_type and forced_dataset_type != "auto" else None,
            mapping=main_mapping,
        )

        dataset_type = (
            forced_dataset_type
            if forced_dataset_type and forced_dataset_type != "auto"
            else main_bundle.metadata["dataset_type"]
        )

        customer_bundle = (
            self.prepare_dataset(
                raw_customer_df,
                dataset_name="customer_master",
                dataset_type="general",
                mapping=customer_mapping,
            )
            if raw_customer_df is not None
            else None
        )

        product_bundle = (
            self.prepare_dataset(
                raw_product_df,
                dataset_name="product_master",
                dataset_type="general",
                mapping=product_mapping,
            )
            if raw_product_df is not None
            else None
        )

        join_reports: list[JoinReport] = []
        enriched_df = main_bundle.mapped.copy()

        if dataset_type == "sales":
            enriched_df, join_reports = enrich_sales_with_masters(
                main_bundle.mapped,
                customer_bundle.mapped if customer_bundle else None,
                product_bundle.mapped if product_bundle else None,
            )
            analysis_result = analyze_sales(enriched_df)

        elif dataset_type == "inventory":
            enriched_df, join_reports = enrich_inventory_with_product_master(
                main_bundle.mapped,
                product_bundle.mapped if product_bundle else None,
            )
            analysis_result = analyze_inventory(enriched_df)

        else:
            analysis_result = AnalysisResult(
                dataset_type="general",
                cleaned_df=enriched_df,
                quality_issues=[issue.message for issue in main_bundle.validation_report.issues],
                kpis={
                    "Rows": f"{len(enriched_df):,}",
                    "Columns": f"{len(enriched_df.columns):,}",
                },
                alerts=pd.DataFrame(columns=["alert_type", "details"]),
                recommendations=["Map your columns to sales or inventory fields to unlock deeper business analysis."],
                chart_data={},
                validation_report=main_bundle.validation_report,
                join_reports=join_reports,
            )

        analysis_result.validation_report = main_bundle.validation_report
        analysis_result.join_reports = join_reports

        return PipelineOutput(
            dataset_type=dataset_type,
            main_bundle=main_bundle,
            customer_bundle=customer_bundle,
            product_bundle=product_bundle,
            enriched_df=enriched_df,
            join_reports=join_reports,
            analysis_result=analysis_result,
        )