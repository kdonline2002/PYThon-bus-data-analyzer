import pandas as pd

from utils.models import AnalysisResult, JoinReport, ValidationReport
from utils.preflight import evaluate_preflight


def make_result(validation_report=None, join_reports=None):
    return AnalysisResult(
        dataset_type="sales",
        cleaned_df=pd.DataFrame({"a": [1]}),
        quality_issues=[],
        kpis={},
        alerts=pd.DataFrame(),
        recommendations=[],
        chart_data={},
        validation_report=validation_report,
        join_reports=join_reports or [],
    )


def test_preflight_green_for_clean_result():
    report = ValidationReport(dataset="sales")
    result = make_result(validation_report=report)

    preflight = evaluate_preflight(result)

    assert preflight.overall_status == "GREEN"


def test_preflight_red_for_validation_error():
    report = ValidationReport(dataset="sales")
    report.add_issue(
        code="missing_required_field",
        severity="error",
        message="Missing quantity",
    )

    result = make_result(validation_report=report)

    preflight = evaluate_preflight(result)

    assert preflight.overall_status in {"AMBER", "RED"}
    assert preflight.metrics["validation_errors"] == 1


def test_preflight_detects_low_match_join():
    join_report = JoinReport(
        join_name="sales_to_product",
        left_dataset="sales",
        right_dataset="product_master",
        join_type="left",
        join_key_left="sku",
        join_key_right="sku",
        left_rows_before=100,
        left_rows_after=100,
        matched_rows=50,
        unmatched_rows=50,
        match_rate=0.50,
        duplicate_key_count_right=0,
        row_inflation=0,
        warnings=["low match"],
    )

    result = make_result(join_reports=[join_report])

    preflight = evaluate_preflight(result)

    assert preflight.metrics["joins_below_fail_match"] == 1
    assert preflight.overall_status in {"AMBER", "RED"}