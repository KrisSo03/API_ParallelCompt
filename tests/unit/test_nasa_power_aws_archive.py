from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from fsspec.registry import get_filesystem_class
from streamlit.testing.v1 import AppTest

from dashboard.data_loader import RunReference, load_run, load_summary
from renewable_atlas.cli import (
    _add_scaling_metrics,
    _execute_aws_run,
    _revalidate_aws_staging,
)
from renewable_atlas.composition import CompositionRoot
from renewable_atlas.config import Settings
from renewable_atlas.infrastructure.nasa_power.aws_archive import (
    METEOROLOGICAL_VARIABLES,
    POWER_VARIABLES,
    SOLAR_VARIABLES,
    NasaPowerAwsProcessor,
    NasaPowerAwsSequentialProcessor,
    NasaPowerAwsStager,
)


@dataclass
class Point:
    latitude: float
    longitude: float
    country: str


def test_http_filesystem_runtime_dependency_is_available():
    assert get_filesystem_class("https").__name__ == "HTTPFileSystem"


def test_partial_staging_can_be_revalidated_against_a_smaller_target():
    stored = {
        "status": "partial",
        "target_gib": 3.0,
        "size_basis": "logical",
        "logical_uncompressed_gib": 1.5802,
        "disk_gib": 0.8596,
    }

    validated = _revalidate_aws_staging(stored, 1.5, "logical")

    assert stored["status"] == "partial"
    assert stored["target_gib"] == 3.0
    assert validated["status"] == "success"
    assert validated["original_status"] == "partial"
    assert validated["original_target_gib"] == 3.0
    assert validated["target_gib"] == 1.5
    assert validated["reused_existing_staging"] is True


def _dataset(variables, periods=48):
    times = pd.date_range("2023-01-01", periods=periods, freq="h")
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


def test_stager_full_date_range_does_not_stop_at_target_size(tmp_path):
    periods = 24 * 33
    solar = _dataset(SOLAR_VARIABLES, periods=periods)
    meteorological = _dataset(METEOROLOGICAL_VARIABLES, periods=periods)

    def opener(url):
        return solar.copy() if "syn1deg" in url else meteorological.copy()

    output = tmp_path / "full-range"
    manifest = NasaPowerAwsStager(dataset_opener=opener).stage(
        points=[Point(10.1, -84.9, "Costa Rica")],
        output_dir=output,
        start_date="2023-01-01",
        end_date="2023-02-02 23:00:00",
        target_gib=0.000001,
        full_date_range=True,
    )

    assert manifest["status"] == "success"
    assert manifest["staging_mode"] == "full-date-range"
    assert manifest["target_gib"] is None
    assert manifest["partition_count"] == 2
    assert manifest["last_timestamp"] == "2023-02-02T23:00:00"


def test_full_date_range_staging_is_revalidated_by_requested_dates():
    stored = {
        "status": "success",
        "staging_mode": "full-date-range",
        "requested_start_date": "2023-01-01T00:00:00",
        "requested_end_date": "2023-12-31T00:00:00",
    }

    validated = _revalidate_aws_staging(
        stored,
        target_gib=5.0,
        size_basis="logical",
        full_date_range=True,
        start_date="2023-01-01",
        end_date="2023-12-31",
    )

    assert validated["status"] == "success"
    assert validated["reused_existing_staging"] is True


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

    sequential = NasaPowerAwsSequentialProcessor().process(tmp_path / "stage")
    pd.testing.assert_frame_equal(
        indicators.sort_index(axis=1),
        sequential.sort_index(axis=1),
        check_exact=False,
        check_dtype=False,
        rtol=1e-10,
    )


def test_aws_run_writes_an_experiment_consumed_by_streamlit(tmp_path, monkeypatch):
    staging_dir = tmp_path / "staging"
    hourly = staging_dir / "hourly" / "year=2023" / "month=01"
    hourly.mkdir(parents=True)
    rows = []
    for point_id in range(8):
        for hour in range(24):
            row = {
                "timestamp": pd.Timestamp("2023-01-01") + pd.Timedelta(hours=hour),
                "date": pd.Timestamp("2023-01-01"),
                "point_id": point_id,
                "latitude": 8.0 + point_id * 0.2,
                "longitude": -85.0 + point_id * 0.2,
                "country": "Costa Rica" if point_id < 4 else "Panama",
            }
            row.update(
                {
                    variable: float(index + point_id * 0.5 + hour * 0.01 + 1)
                    for index, variable in enumerate(POWER_VARIABLES)
                }
            )
            rows.append(row)
    pd.DataFrame(rows).to_parquet(hourly / "part-000.parquet", index=False)

    staging_manifest = {
        "status": "success",
        "source": "NASA POWER AWS Open Data",
        "variables": list(POWER_VARIABLES),
        "variable_count": 18,
        "point_count": 8,
        "row_count": len(rows),
        "logical_uncompressed_gib": 1.25,
        "disk_gib": 1.05,
    }
    experiment_dir = tmp_path / "results" / "aws-dashboard"
    settings = Settings.load()
    row = _execute_aws_run(
        staging_dir=staging_dir,
        staging_manifest=staging_manifest,
        experiment_dir=experiment_dir,
        workers=2,
        repeat=1,
        scheduler="threads",
        main_baseline=False,
        settings=settings,
        container=CompositionRoot(settings),
    )
    pd.DataFrame(_add_scaling_metrics([row])).to_csv(
        experiment_dir / "summary.csv", index=False
    )

    reference = RunReference(
        workers=2,
        repeat=1,
        path=experiment_dir / "workers-002" / "run-01",
    )
    loaded = load_run(reference)
    summary = load_summary(experiment_dir)

    assert len(loaded.indicators) == 8
    assert loaded.manifest["source"] == "nasa-aws"
    assert loaded.manifest["aws_staging"]["variable_count"] == 18
    assert not summary.empty
    assert summary.loc[0, "workers"] == 2

    monkeypatch.setenv("ATLAS_RESULTS_DIR", str(tmp_path / "results"))
    app_path = Path(__file__).parents[2] / "dashboard" / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Resumen general",
        "Atlas interactivo",
        "Comparación",
        "Calidad y metodología",
        "Rendimiento",
    ]
    metric_labels = [metric.label for metric in app.metric]
    assert "Tamaño real en disco" in metric_labels
    assert "Tamaño lógico" in metric_labels
    assert "Filas horarias" in metric_labels
    assert "Variables climáticas" in metric_labels
