import pytest

from renewable_atlas.application.pipelines.atlas_pipeline import (
    AtlasPipeline,
    _calculate_indicators,
    _prepare_climate_data,
)
from renewable_atlas.domain import (
    ClimateObservation,
    GridPoint,
    RenewableIndicators,
)


class DummyRepository:
    def __init__(self):
        self.saved = []

    def save(self, data, key):
        self.saved.append((key, data))


class DummyDataSource:
    def __init__(self):
        self.calls = 0

    def fetch_observations(self, point):
        self.calls += 1
        if point.latitude > 0:
            raise RuntimeError("temporary failure")
        return [ClimateObservation(date="2020-01-01", sw_dwn=1.0, dni=2.0, ws_50m=3.0, ws_100m=4.0)]


class DummyClusteringService:
    def cluster(self, indicators_df):
        return [], []


class DummyInterpretationService:
    def interpret(self, profiles):
        return profiles


def test_download_fails_when_one_point_has_no_real_data():
    source = DummyDataSource()
    repository = DummyRepository()
    pipeline = AtlasPipeline(
        data_source=source,
        repository=repository,
        clustering_service=DummyClusteringService(),
        interpretation_service=DummyInterpretationService(),
    )

    points = [
        GridPoint(latitude=1.0, longitude=2.0, country="Guatemala"),
        GridPoint(latitude=-1.0, longitude=-2.0, country="Belize"),
    ]

    with pytest.raises(RuntimeError, match="1/2 points succeeded"):
        pipeline.download(points)

    assert pipeline.last_download_report["successful_points"] == 1
    assert pipeline.last_download_report["total_observations"] == 1
    assert len(pipeline.last_download_report["failed_points"]) == 1
    assert repository.saved == []

def test_prepare_climate_data_reports_before_and_after_cleaning():
    observations = [
        ClimateObservation(
            date="2020-01-01",
            sw_dwn=100.0,
            dni=500.0,
            ws_50m=5.0,
            ws_100m=7.0,
        ),
        ClimateObservation(
            date="2020-01-01",
            sw_dwn=100.0,
            dni=500.0,
            ws_50m=5.0,
            ws_100m=7.0,
        ),
    ]

    clean_df, pre_report, post_report = _prepare_climate_data(observations)

    assert pre_report.duplicate_rows == 1
    assert post_report.duplicate_rows == 0
    assert len(clean_df) == 1


def test_calculate_indicators_keeps_return_contract():
    point = GridPoint(
        latitude=14.5,
        longitude=-92.0,
        country="Guatemala",
    )

    observations = [
        ClimateObservation(
            date="2020-01-01",
            sw_dwn=100.0,
            dni=500.0,
            ws_50m=5.0,
            ws_100m=7.0,
        )
    ]

    result = _calculate_indicators(
        (
            0,
            {
                "point": point,
                "observations": observations,
            },
        )
    )

    assert isinstance(result, RenewableIndicators)
