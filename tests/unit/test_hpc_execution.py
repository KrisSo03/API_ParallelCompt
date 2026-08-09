import json

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
    assert (run_dir / "indicators.parquet").exists()
