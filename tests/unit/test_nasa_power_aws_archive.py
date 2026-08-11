from dataclasses import dataclass

import numpy as np
import pandas as pd
import xarray as xr

from renewable_atlas.infrastructure.nasa_power.aws_archive import (
    METEOROLOGICAL_VARIABLES,
    POWER_VARIABLES,
    SOLAR_VARIABLES,
    NasaPowerAwsProcessor,
    NasaPowerAwsStager,
)


@dataclass
class Point:
    latitude: float
    longitude: float
    country: str


def _dataset(variables):
    times = pd.date_range("2023-01-01", periods=48, freq="h")
    coordinates = {"time": times, "lat": [10.0, 11.0], "lon": [-85.0, -84.0]}
    shape = (len(times), 2, 2)
    return xr.Dataset(
        {
            variable: (("time", "lat", "lon"), np.full(shape, index + 1.0))
            for index, variable in enumerate(variables)
        },
        coords=coordinates,
    )


def test_stager_preserves_18_variables_and_writes_outside_results(tmp_path):
    solar = _dataset(SOLAR_VARIABLES)
    meteorological = _dataset(METEOROLOGICAL_VARIABLES)

    def opener(url):
        return solar.copy() if "syn1deg" in url else meteorological.copy()

    output = tmp_path / "data" / "aws-staging" / "test"
    manifest = NasaPowerAwsStager(dataset_opener=opener).stage(
        points=[Point(10.1, -84.9, "Costa Rica")],
        output_dir=output,
        start_date="2023-01-01",
        end_date="2023-01-02 23:00:00",
        target_gib=0.000001,
    )

    parquet_path = next((output / "hourly").rglob("*.parquet"))
    frame = pd.read_parquet(parquet_path)
    assert manifest["variable_count"] == 18
    assert list(manifest["variables"]) == list(POWER_VARIABLES)
    assert set(POWER_VARIABLES).issubset(frame.columns)
    assert frame["T2M_MAX"].notna().all()
    assert frame["T2M_MIN"].notna().all()
    assert not (tmp_path / "results").exists()


def test_processor_keeps_dashboard_indicator_contract(tmp_path):
    hourly = tmp_path / "stage" / "hourly" / "year=2023" / "month=01"
    hourly.mkdir(parents=True)
    rows = []
    for point_id, country in [(0, "Costa Rica"), (1, "Panama")]:
        for hour in range(24):
            row = {
                "timestamp": pd.Timestamp("2023-01-01") + pd.Timedelta(hours=hour),
                "date": pd.Timestamp("2023-01-01"),
                "point_id": point_id,
                "latitude": 9.0 - point_id,
                "longitude": -84.0 + point_id,
                "country": country,
            }
            row.update(
                {
                    variable: float(index + point_id + 1)
                    for index, variable in enumerate(POWER_VARIABLES)
                }
            )
            rows.append(row)
    pd.DataFrame(rows).to_parquet(hourly / "part-000.parquet", index=False)

    indicators = NasaPowerAwsProcessor().process(tmp_path / "stage")
    expected = {
        "point_id",
        "latitude",
        "longitude",
        "country",
        "sw_dwn_mean",
        "dni_mean",
        "ws_50m_mean",
        "ws_100m_mean",
        "solar_score",
        "wind_score",
        "hybrid_score",
    }
    assert expected.issubset(indicators.columns)
    assert len(indicators) == 2
    assert "cluster_id" not in indicators
