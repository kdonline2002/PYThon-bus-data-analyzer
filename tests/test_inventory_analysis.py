import pandas as pd

from analytics.inventory_analysis import analyze_inventory


def test_inventory_analysis_calculates_stock_kpis():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "stock_on_hand": [10, 0],
        "reorder_level": [5, 10],
    })

    result = analyze_inventory(df)

    assert result.dataset_type == "inventory"
    assert result.kpis["Total Stock On Hand"] == "10"
    assert result.kpis["Out of Stock Items"] == "1"


def test_inventory_analysis_handles_string_stock_values():
    df = pd.DataFrame({
        "product": ["A", "B"],
        "stock_on_hand": ["1,000", "0"],
        "reorder_level": ["50", "10"],
    })

    result = analyze_inventory(df)

    assert result.kpis["Total Stock On Hand"] == "1,000"
    assert not result.chart_data["stock_by_product"].empty


def test_inventory_analysis_detects_low_stock():
    df = pd.DataFrame({
        "product": ["A"],
        "stock_on_hand": [5],
        "reorder_level": [10],
    })

    result = analyze_inventory(df)

    assert not result.alerts.empty
    assert "Low stock" in result.alerts["alert_type"].tolist()