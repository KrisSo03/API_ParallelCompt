import pytest

from renewable_atlas.composition import CompositionRoot
from renewable_atlas.config import Settings
from renewable_atlas.domain import GridPoint
from renewable_atlas.infrastructure import FakeClimateDataSource
from renewable_atlas.infrastructure.grid import SampleGridProvider


class TestAtlasPipeline:
    @pytest.fixture
    def settings(self):
        return Settings.load()

    @pytest.fixture
    def container(self, settings):
        return CompositionRoot(settings)

    def test_full_pipeline_with_fake_data(self, container):
        pipeline = container.build_atlas_pipeline(use_fake=True)
        processor = container.build_sequential_processor()

        grid_provider = SampleGridProvider(size=4, enable_sampling=True, sample_size=4)
        points = grid_provider.generate()

        assert len(points) > 0

        indicators_df, labels, profiles = pipeline.run(points, processor)

        assert indicators_df is not None
        assert labels is not None
        assert len(profiles) > 0

    def test_fake_data_source(self):
        source = FakeClimateDataSource()
        point = GridPoint(latitude=14.5, longitude=-92.0, country="Guatemala")

        observations = source.fetch_observations(point)

        assert len(observations) > 0
        assert all(obs.is_complete() for obs in observations)
