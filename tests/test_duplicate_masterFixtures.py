from pathlib import Path

import pandas as pd

from services.pipeline_service import PipelineService

FIXTURES = Path(__file__).parent / "fixtures"


def test_duplicate_product_master_keys_are_reported():
    sales = pd.read_csv(FIXTURES / "sales_clean.csv")
    product_master = pd.read_csv(FIXTURES / "product_master_duplicates.csv")

    pipeline = PipelineService()
    output = pipeline.run(
        sales,
        forced_dataset_type="sales",
        raw_product_df=product_master,
    )

    assert output.join_reports
    assert output.join_reports[0].duplicate_key_count_right > 0