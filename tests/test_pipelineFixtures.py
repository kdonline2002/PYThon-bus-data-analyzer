from pathlib import Path

import pandas as pd

from services.pipeline_service import PipelineService

FIXTURES = Path(__file__).parent / "fixtures"


def test_sales_with_product_master_join():
    sales = pd.read_csv(FIXTURES / "sales_clean.csv")
    product_master = pd.read_csv(FIXTURES / "product_master.csv")

    pipeline = PipelineService()
    output = pipeline.run(
        sales,
        forced_dataset_type="sales",
        raw_product_df=product_master,
    )

    assert output.dataset_type == "sales"
    assert len(output.join_reports) == 1
    assert output.join_reports[0].match_rate == 1.0