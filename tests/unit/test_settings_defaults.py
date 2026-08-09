from renewable_atlas.config import Settings


def test_production_defaults_use_300_points_and_automatic_k(monkeypatch):
    for name in (
        "GRID_SIZE",
        "GRID_SAMPLE_SIZE",
        "CLUSTERING_AUTO_SELECT",
        "EXECUTION_SOURCE",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings()

    assert settings.grid.size == 300
    assert settings.grid.sample_size == 300
    assert settings.clustering.auto_select is True
    assert settings.execution.source == "nasa"
