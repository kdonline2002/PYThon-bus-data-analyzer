import pandas as pd

from analytics.sales_analysis import add_profitability_metrics, analyze_sales


def test_profitability_uses_unit_cost():
    df = pd.DataFrame(
        {
            "product": ["A", "B"],
            "quantity": [2, 3],
            "sales_amount": [20.0, 45.0],
            "unit_cost": [4.0, 10.0],
        }
    )

    out, notes = add_profitability_metrics(df)

    assert out["cogs"].tolist() == [8.0, 30.0]
    assert out["gross_profit"].tolist() == [12.0, 15.0]
    assert out["profit_cost_source"].tolist() == ["unit_cost", "unit_cost"]
    assert "Profitability enabled using unit_cost." in notes


def test_profitability_falls_back_to_base_cost():
    df = pd.DataFrame(
        {
            "product": ["A"],
            "quantity": [5],
            "sales_amount": [100.0],
            "base_cost": [12.0],
        }
    )

    out, notes = add_profitability_metrics(df)

    assert out.loc[0, "cogs"] == 60.0
    assert out.loc[0, "gross_profit"] == 40.0
    assert out.loc[0, "profit_cost_source"] == "base_cost"
    assert any("base_cost" in note for note in notes)


def test_missing_cost_skips_profitability():
    df = pd.DataFrame(
        {
            "product": ["A"],
            "quantity": [5],
            "sales_amount": [100.0],
        }
    )

    out, notes = add_profitability_metrics(df)

    assert "gross_profit" not in out.columns
    assert any("no usable unit_cost or base_cost" in note for note in notes)


def test_negative_margin_alert_triggers():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01"],
            "product": ["A"],
            "quantity": [1],
            "sales_amount": [10.0],
            "unit_cost": [12.0],
        }
    )

    result = analyze_sales(df)

    assert "Gross Profit" in result.kpis
    assert "gross_profit" in result.cleaned_df.columns
    assert "Negative gross profit" in result.alerts["alert_type"].tolist()


def test_profitability_segments_products_and_customers():
    df = pd.DataFrame(
        {
            "product": ["A", "A", "B", "C"],
            "customer": ["Acme", "Acme", "Beta", "Gamma"],
            "quantity": [10, 5, 4, 2],
            "sales_amount": [1000.0, 500.0, 800.0, 100.0],
            "unit_cost": [50.0, 50.0, 120.0, 80.0],
        }
    )

    result = analyze_sales(df)

    product_segments = result.chart_data["product_profitability_segments"]
    customer_segments = result.chart_data["customer_profitability_segments"]
    bottom_products = result.chart_data["bottom_products_by_gross_profit"]

    assert set(product_segments["product"]) == {"A", "B", "C"}
    assert set(customer_segments["customer"]) == {"Acme", "Beta", "Gamma"}

    product_c = product_segments.loc[product_segments["product"] == "C"].iloc[0]
    assert product_c["gross_profit"] == -60.0
    assert product_c["profit_segment"] == "Loss-making"

    product_a = product_segments.loc[product_segments["product"] == "A"].iloc[0]
    assert product_a["revenue"] == 1500.0
    assert product_a["gross_profit"] == 750.0
    assert product_a["profit_segment"] == "High margin"

    assert bottom_products.iloc[0]["product"] == "C"


def test_profitability_segments_are_absent_without_cost():
    df = pd.DataFrame(
        {
            "product": ["A"],
            "customer": ["Acme"],
            "quantity": [10],
            "sales_amount": [1000.0],
        }
    )

    result = analyze_sales(df)

    assert result.chart_data["product_profitability_segments"].empty
    assert result.chart_data["customer_profitability_segments"].empty
