import importlib.util
from pathlib import Path

import pandas as pd
import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "hpc" / "compare_worker_consistency.py"
SPEC = importlib.util.spec_from_file_location("compare_worker_consistency", SCRIPT_PATH)
worker_consistency = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(worker_consistency)


def _write_indicators(run_dir: Path, cluster_column: str) -> None:
    run_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "point_id": [2, 1],
            cluster_column: [1, 0],
            "sw_dwn_mean": [5.0, 4.0],
            "dni_mean": [6.0, 5.0],
            "ws_50m_mean": [3.0, 2.0],
            "ws_100m_mean": [3.5, 2.5],
        }
    ).to_csv(run_dir / "indicators.csv", index=False)


@pytest.mark.parametrize("cluster_column", ["cluster_id", "cluster"])
def test_load_run_normalizes_cluster_column(tmp_path, cluster_column):
    run_dir = tmp_path / "workers-001" / "run-01"
    _write_indicators(run_dir, cluster_column)

    indicators, _ = worker_consistency.load_run(run_dir)

    assert indicators["point_id"].tolist() == [1, 2]
    assert indicators["cluster_id"].tolist() == [0, 1]
    assert "cluster" not in indicators.columns


def test_load_run_rejects_missing_cluster_column(tmp_path):
    run_dir = tmp_path / "workers-001" / "run-01"
    run_dir.mkdir(parents=True)
    pd.DataFrame({"point_id": [1]}).to_csv(run_dir / "indicators.csv", index=False)

    with pytest.raises(ValueError, match="cluster_id.*cluster"):
        worker_consistency.load_run(run_dir)
