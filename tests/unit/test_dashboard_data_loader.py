import json
from pathlib import Path

import pandas as pd
import pytest

from dashboard.data_loader import (
    RunReference,
    discover_runs,
    discover_worker_counts,
    load_run,
    load_summary,
)
from dashboard.validators import DashboardDataError, validate_indicators


def _valid_indicators(cluster_column: str = "cluster_id") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "point_id": [0, 1],
            "latitude": [10.0, 11.0],
            "longitude": [-84.0, -85.0],
            "country": ["Costa Rica", "Costa Rica"],
            "sw_dwn_mean": [180.0, 190.0],
            "dni_mean": [450.0, 470.0],
            "ws_50m_mean": [5.0, 6.0],
            "ws_100m_mean": [7.0, 8.0],
            "solar_score": [0.2, 0.8],
            "wind_score": [0.3, 0.9],
            "hybrid_score": [0.25, 0.85],
            cluster_column: [0, 1],
        }
    )


def _write_run(run_dir: Path, cluster_column: str = "cluster_id") -> RunReference:
    run_dir.mkdir(parents=True)
    _valid_indicators(cluster_column).to_parquet(run_dir / "indicators.parquet", index=False)
    profiles = [
        {"cluster_id": cluster_id, "label": "Test", "description": "Test", "size": 1, "centroid": {}}
        for cluster_id in (0, 1)
    ]
    (run_dir / "cluster_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")
    manifest = {"status": "success", "point_count": 2, "workers": 1, "repeat": 1}
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return RunReference(workers=1, repeat=1, path=run_dir)


def test_discovers_workers_and_runs(tmp_path):
    experiment = tmp_path / "experiment"
    (experiment / "workers-004" / "run-02").mkdir(parents=True)
    (experiment / "workers-001" / "run-01").mkdir(parents=True)

    assert discover_worker_counts(experiment) == [1, 4]
    assert [run.repeat for run in discover_runs(experiment, 4)] == [2]


def test_load_run_normalizes_legacy_cluster_column(tmp_path):
    reference = _write_run(tmp_path / "workers-001" / "run-01", cluster_column="cluster")

    loaded = load_run(reference)

    assert "cluster_id" in loaded.indicators.columns
    assert "cluster" not in loaded.indicators.columns


def test_rejects_invalid_coordinates():
    indicators = _valid_indicators()
    indicators.loc[0, "latitude"] = 100.0

    with pytest.raises(DashboardDataError, match="latitude"):
        validate_indicators(indicators)


def test_rejects_failed_manifest(tmp_path):
    reference = _write_run(tmp_path / "workers-001" / "run-01")
    (reference.path / "manifest.json").write_text(
        json.dumps({"status": "failed", "error": "boom"}), encoding="utf-8"
    )

    with pytest.raises(DashboardDataError, match="boom"):
        load_run(reference)


def test_loads_single_and_array_summaries(tmp_path):
    pd.DataFrame([{"workers": 1, "repeat": 1, "run_dir": "one"}]).to_csv(
        tmp_path / "summary-workers-001.csv", index=False
    )
    pd.DataFrame([{"workers": 4, "repeat": 1, "run_dir": "four"}]).to_csv(
        tmp_path / "summary-workers-004.csv", index=False
    )

    summary = load_summary(tmp_path)

    assert summary["workers"].tolist() == [1, 4]

