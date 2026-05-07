from pathlib import Path

import pandas as pd

from analytics.sales_analysis import analyze_sales

FIXTURES = Path(__file__).parent / "fixtures"


def test_sales_clean_totals():
    df = pd.read_csv(FIXTURES / "sales_clean.csv")

    result = analyze_sales(df)

    assert result.dataset_type == "sales"
    assert result.kpis["Total Sales"] == "3,700.00"
    assert result.kpis["Units Sold"] == "26"