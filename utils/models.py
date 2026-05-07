from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class ValidationIssue:
    code: str
    severity: str
    dataset: str
    message: str
    column: Optional[str] = None
    row_count: Optional[int] = None
    sample_rows: Optional[pd.DataFrame] = None


@dataclass
class ValidationReport:
    dataset: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(issue.severity == "warning" for issue in self.issues)

    def add_issue(
        self,
        code: str,
        severity: str,
        message: str,
        column: Optional[str] = None,
        row_count: Optional[int] = None,
        sample_rows: Optional[pd.DataFrame] = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                severity=severity,
                dataset=self.dataset,
                message=message,
                column=column,
                row_count=row_count,
                sample_rows=sample_rows,
            )
        )


@dataclass
class JoinReport:
    join_name: str
    left_dataset: str
    right_dataset: str
    join_type: str
    join_key_left: str
    join_key_right: str
    left_rows_before: int
    left_rows_after: int
    matched_rows: int
    unmatched_rows: int
    match_rate: float
    duplicate_key_count_right: int
    row_inflation: int
    warnings: list[str] = field(default_factory=list)
    unmatched_sample: Optional[pd.DataFrame] = None


@dataclass
class DatasetBundle:
    dataset_name: str
    raw: pd.DataFrame
    cleaned: pd.DataFrame
    mapped: pd.DataFrame
    validation_report: ValidationReport
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    dataset_type: str
    cleaned_df: pd.DataFrame
    quality_issues: list[str]
    kpis: dict[str, str]
    alerts: pd.DataFrame
    recommendations: list[str]
    chart_data: dict[str, pd.DataFrame]
    validation_report: Optional[ValidationReport] = None
    join_reports: list[JoinReport] = field(default_factory=list)