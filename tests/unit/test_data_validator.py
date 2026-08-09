import numpy as np
import pandas as pd

from renewable_atlas.application.services.data_validator import DataValidator


def test_data_validator_reports_general_quality_metrics():
    df = pd.DataFrame(
        {
            "date": [
                "2020-01-01",
                "2020-01-01",
                "invalid-date",
                "2020-01-04",
            ],
            "sw_dwn": [100.0, 100.0, 500.0, np.nan],
            "dni": [500.0, 500.0, np.inf, -999],
            "ws_50m": [5.0, 5.0, 5.0, 5.0],
            "ws_100m": [7.0, 7.0, 7.0, 7.0],
            "t2m": [24.0, 24.0, np.nan, 25.0],
            "cloud_amt": [None, None, None, None],
        }
    )

    report = DataValidator().validate(df)

    assert report.total_rows == 4
    assert report.duplicate_rows == 1
    assert report.invalid_date_rows == 1
    assert report.duplicate_date_rows == 1
    assert report.fully_empty_columns == ["cloud_amt"]

    assert report.nan_count_by_column["sw_dwn"] == 1
    assert report.nan_count_by_column["t2m"] == 1

    assert report.infinite_count_by_column["dni"] == 1
    assert report.sentinel_count_by_column["dni"] == 1

    assert report.out_of_range_count_by_column["sw_dwn"] == 1

def test_data_validator_uses_only_required_columns_for_completeness():
    df = pd.DataFrame(
        {
            "sw_dwn": [100.0, 110.0],
            "dni": [500.0, 510.0],
            "ws_50m": [5.0, 5.5],
            "ws_100m": [7.0, 7.5],
            "t2m": [None, None],
            "cloud_amt": [None, None],
        }
    )

    report = DataValidator().validate(
        df,
        required_columns=[
            "sw_dwn",
            "dni",
            "ws_50m",
            "ws_100m",
        ],
    )

    assert report.complete_rows == 2
    assert report.completeness_ratio == 1.0
    assert report.is_valid

def test_data_validator_rejects_insufficient_required_column_completeness():
    df = pd.DataFrame(
        {
            "sw_dwn": [100.0, None, None],
            "dni": [500.0, None, None],
            "ws_50m": [5.0, None, None],
            "ws_100m": [7.0, None, None],
            "t2m": [24.0, 25.0, 26.0],
        }
    )

    report = DataValidator().validate(
        df,
        required_columns=[
            "sw_dwn",
            "dni",
            "ws_50m",
            "ws_100m",
        ],
    )

    assert report.complete_rows == 1
    assert report.completeness_ratio == 1 / 3
    assert not report.is_valid
