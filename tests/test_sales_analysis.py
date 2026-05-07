import pandas as pd

from analytics.sales_analysis import analyze_sales


def test_sales_analysis_calculates_basic_kpis():
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02"],
        "product": ["A", "B"],
        "quantity": [2, 3],
        "sales_amount": [100, 150],
    })

    result = analyze_sales(df)

    assert result.dataset_type == "sales"
    assert result.kpis["Total Sales"] == "250.00"
    assert result.kpis["Units Sold"] == "5"


def test_sales_analysis_handles_currency_strings():
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-02-01"],
        "product": ["A", "A"],
        "quantity": ["2", "3"],
        "sales_amount": ["R100.00", "R150.00"],
    })

    result = analyze_sales(df)

    assert result.kpis["Total Sales"] == "250.00"
    assert not result.chart_data["monthly_sales"].empty


def test_sales_analysis_detects_negative_quantity():
    df = pd.DataFrame({
        "date": ["2025-01-01"],
        "product": ["A"],
        "quantity": [-1],
        "sales_amount": [-100],
    })

    result = analyze_sales(df)

    assert not result.alerts.empty
    assert "Negative quantity" in result.alerts["alert_type"].tolist()