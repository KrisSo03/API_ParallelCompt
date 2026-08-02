import pandas as pd

from renewable_atlas.application.services.data_transformer import DataTransformer


def test_clean_handles_missing_feature_columns():
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-01-02"],
        "sw_dwn": [100.0, 110.0],
        "dni": [50.0, 60.0],
    })

    cleaned = DataTransformer.clean(df)

    assert list(cleaned.columns) == ["date", "sw_dwn", "dni"]
    assert len(cleaned) == 2
