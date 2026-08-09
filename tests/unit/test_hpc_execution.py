import json

import pandas as pd

from renewable_atlas.cli import main


def test_hpc_run_persists_reproducible_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("DATE_RANGE_START_YEAR", "2023")
    monkeypatch.setenv("DATE_RANGE_END_YEAR", "2023")

    exit_code = main(
        [
            "hpc-run",
            "--experiment-id",
            "test-experiment",
            "--source",
            "fake",
            "--points",
            "5",
            "--workers",
            "1",
            "--results-dir",
            str(tmp_path),
        ]
    )

    run_dir = tmp_path / "test-experiment" / "workers-001" / "run-01"
    manifest = json.loads((run_dir / "manifest.json").read_text())

    assert exit_code == 0
    assert manifest["status"] == "success"
    assert manifest["point_count"] == 5
    assert manifest["download"]["successful_points"] == 5
    assert manifest["download"]["failed_points"] == []
    assert manifest["workers"] == 1
    assert manifest["peak_memory_mb"] > 0
    assert manifest["memory_scope"] in {"process_tree", "coordinator_only"}
    assert manifest["clustering_quality"]["recommended_k"] in {2, 3, 4}
    assert (run_dir / "indicators.parquet").exists()

    summary = pd.read_csv(tmp_path / "test-experiment" / "summary-workers-001.csv")
    assert summary.loc[0, "speedup"] == 1.0
    assert summary.loc[0, "efficiency_percent"] == 100.0
