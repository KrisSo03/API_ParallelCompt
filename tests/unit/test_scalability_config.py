import pytest

from renewable_atlas.config.settings import DateRangeSettings, GridSettings
from renewable_atlas.infrastructure.grid.sample_grid import SampleGridProvider


def test_invalid_date_range_is_rejected():
    with pytest.raises(ValueError):
        DateRangeSettings(start_year=2023, end_year=2020)


def test_grid_provider_respects_max_points_limit():
    provider = SampleGridProvider(size=20, enable_sampling=True, sample_size=20)
    points = provider.generate(max_points=5)

    assert len(points) == 5
