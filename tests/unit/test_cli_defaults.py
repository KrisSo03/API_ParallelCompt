import sys
import types
from unittest.mock import Mock

from renewable_atlas import cli


class DummyPipeline:
    def download(self, points):
        return {}


class DummyContainer:
    def __init__(self, settings):
        self.settings = settings

    def build_atlas_pipeline(self, use_fake=False):
        self.last_use_fake = use_fake
        return DummyPipeline()

    def build_sequential_processor(self):
        return object()

    def build_dask_processor(self, num_workers=1, scheduler="processes"):
        return object()

    def build_benchmark_service(self):
        return object()


class DummyGridProvider:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self):
        return [object()]


def test_cli_download_uses_real_data_source_by_default(monkeypatch):
    settings = types.SimpleNamespace(
        paths=types.SimpleNamespace(data_dir="data", results_dir="results"),
        grid=types.SimpleNamespace(size=1, enable_sampling=False, sample_size=1),
        benchmark=types.SimpleNamespace(worker_counts=[1], repeats_per_config=1),
        clustering=types.SimpleNamespace(n_clusters=2, random_state=0),
        nasa_power=types.SimpleNamespace(base_url="https://example.com/", timeout_seconds=30, max_retries=3),
    )

    container = DummyContainer(settings)

    monkeypatch.setattr(cli, "Settings", Mock(load=Mock(return_value=settings)))
    monkeypatch.setattr(cli, "CompositionRoot", lambda settings: container)
    monkeypatch.setattr(cli, "SampleGridProvider", DummyGridProvider)
    monkeypatch.setattr(sys, "argv", ["prog", "download"])

    cli.main()

    assert container.last_use_fake is False
