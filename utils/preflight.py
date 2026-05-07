from __future__ import annotations

from dataclasses import dataclass, field

from config.settings import (
    DUPLICATE_RATIO_FAIL,
    DUPLICATE_RATIO_WARNING,
    DUPLICATE_FAIL_WEIGHT,
    DUPLICATE_WARNING_WEIGHT,
    LOW_MATCH_FAIL_WEIGHT,
    LOW_MATCH_WARNING_WEIGHT,
    MATCH_RATE_FAIL,
    MATCH_RATE_WARNING,
    RISK_STATUS_AMBER_MIN,
    RISK_STATUS_RED_MIN,
    ROW_INFLATION_RATIO_FAIL,
    ROW_INFLATION_RATIO_WARNING,
    ROW_INFLATION_FAIL_WEIGHT,
    ROW_INFLATION_WARNING_WEIGHT,
    VALIDATION_ERROR_WEIGHT,
    VALIDATION_WARNING_WEIGHT,
)
from utils.models import AnalysisResult


@dataclass
class PreflightResult:
    overall_status: str
    risk_score: int
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)


def evaluate_preflight(result: AnalysisResult) -> PreflightResult:
    validation_errors = 0
    validation_warnings = 0
    validation_infos = 0

    if result.validation_report is not None:
        validation_errors = sum(1 for issue in result.validation_report.issues if issue.severity == "error")
        validation_warnings = sum(1 for issue in result.validation_report.issues if issue.severity == "warning")
        validation_infos = sum(1 for issue in result.validation_report.issues if issue.severity == "info")

    total_join_reports = len(result.join_reports or [])
    low_match_joins = 0
    very_low_match_joins = 0
    duplicate_key_joins = 0
    severe_duplicate_key_joins = 0
    row_inflation_joins = 0
    severe_row_inflation_joins = 0
    total_join_warnings = 0

    risk_score = 0
    risk_reasons: list[str] = []

    for report in result.join_reports or []:
        total_join_warnings += len(report.warnings)

        if report.match_rate < MATCH_RATE_FAIL:
            very_low_match_joins += 1
            risk_score += LOW_MATCH_FAIL_WEIGHT
            risk_reasons.append(f"{report.join_name}: very low match rate ({report.match_rate:.1%})")
        elif report.match_rate < MATCH_RATE_WARNING:
            low_match_joins += 1
            risk_score += LOW_MATCH_WARNING_WEIGHT
            risk_reasons.append(f"{report.join_name}: moderate match rate ({report.match_rate:.1%})")

        if report.duplicate_key_count_right > 0:
            duplicate_key_joins += 1
            duplicate_ratio = (
                report.duplicate_key_count_right / report.left_rows_before
                if report.left_rows_before else 0
            )

            if duplicate_ratio >= DUPLICATE_RATIO_FAIL:
                severe_duplicate_key_joins += 1
                risk_score += DUPLICATE_FAIL_WEIGHT
                risk_reasons.append(
                    f"{report.join_name}: high duplicate-key ratio on right dataset ({duplicate_ratio:.1%})"
                )
            elif duplicate_ratio >= DUPLICATE_RATIO_WARNING:
                risk_score += DUPLICATE_WARNING_WEIGHT
                risk_reasons.append(
                    f"{report.join_name}: duplicate keys present on right dataset ({duplicate_ratio:.1%})"
                )

        if report.row_inflation > 0:
            row_inflation_joins += 1
            inflation_ratio = (
                report.row_inflation / report.left_rows_before
                if report.left_rows_before else 0
            )

            if inflation_ratio >= ROW_INFLATION_RATIO_FAIL:
                severe_row_inflation_joins += 1
                risk_score += ROW_INFLATION_FAIL_WEIGHT
                risk_reasons.append(f"{report.join_name}: severe row inflation ({inflation_ratio:.1%})")
            elif inflation_ratio >= ROW_INFLATION_RATIO_WARNING:
                risk_score += ROW_INFLATION_WARNING_WEIGHT
                risk_reasons.append(f"{report.join_name}: row inflation detected ({inflation_ratio:.1%})")

    if validation_errors > 0:
        risk_score += validation_errors * VALIDATION_ERROR_WEIGHT
        risk_reasons.append(f"{validation_errors} validation errors")

    if validation_warnings > 0:
        risk_score += validation_warnings * VALIDATION_WARNING_WEIGHT
        risk_reasons.append(f"{validation_warnings} validation warnings")

    if risk_score >= RISK_STATUS_RED_MIN:
        overall_status = "RED"
    elif risk_score >= RISK_STATUS_AMBER_MIN:
        overall_status = "AMBER"
    else:
        overall_status = "GREEN"

    return PreflightResult(
        overall_status=overall_status,
        risk_score=risk_score,
        reasons=risk_reasons,
        metrics={
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "validation_infos": validation_infos,
            "total_join_reports": total_join_reports,
            "joins_below_warning_match": low_match_joins,
            "joins_below_fail_match": very_low_match_joins,
            "joins_with_duplicate_keys": duplicate_key_joins,
            "joins_with_severe_duplicate_keys": severe_duplicate_key_joins,
            "joins_with_row_inflation": row_inflation_joins,
            "joins_with_severe_row_inflation": severe_row_inflation_joins,
            "join_warning_count": total_join_warnings,
        },
    )