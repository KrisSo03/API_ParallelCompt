from collections import Counter

from shapely.geometry import Point

from renewable_atlas.infrastructure.grid.sample_grid import SampleGridProvider


def test_generates_exact_configurable_point_count() -> None:
    for requested in (1, 5, 7, 8, 20, 300):
        provider = SampleGridProvider(
            size=max(300, requested),
            enable_sampling=True,
            sample_size=requested,
        )

        assert len(provider.generate()) == requested


def test_distributes_points_evenly_across_countries() -> None:
    points = SampleGridProvider(size=300, sample_size=300).generate()
    counts = Counter(point.country for point in points)

    assert set(counts) == set(SampleGridProvider.COUNTRIES)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_every_point_is_inside_its_assigned_country() -> None:
    provider = SampleGridProvider(size=300, sample_size=300)

    for point in provider.generate():
        geometry = provider.country_geometries[point.country]
        assert geometry.covers(Point(point.longitude, point.latitude))


def test_generation_is_reproducible() -> None:
    first = SampleGridProvider(size=50, sample_size=50).generate()
    second = SampleGridProvider(size=50, sample_size=50).generate()

    assert first == second


def test_sampling_can_be_disabled_and_max_points_is_preserved() -> None:
    provider = SampleGridProvider(size=20, enable_sampling=False, sample_size=5)

    assert len(provider.generate()) == 20
    assert len(provider.generate(max_points=8)) == 8
