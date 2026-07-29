import pytest
from datetime import date
from renewable_atlas.domain import (
    GridPoint,
    ClimateObservation,
    RenewableIndicators,
    BenchmarkResult,
    ExecutionMode,
)


class TestGridPoint:
    def test_valid_grid_point(self):
        point = GridPoint(latitude=14.5, longitude=-92.0, country="Guatemala")
        assert point.latitude == 14.5
        assert point.longitude == -92.0
        assert point.country == "Guatemala"

    def test_invalid_latitude(self):
        with pytest.raises(ValueError):
            GridPoint(latitude=91, longitude=-92.0, country="Guatemala")

    def test_invalid_longitude(self):
        with pytest.raises(ValueError):
            GridPoint(latitude=14.5, longitude=181, country="Guatemala")


class TestClimateObservation:
    def test_complete_observation(self):
        obs = ClimateObservation(
            date=date(2020, 1, 1),
            sw_dwn=150.0,
            dni=500.0,
            ws_50m=5.0,
            ws_100m=7.0,
        )
        assert obs.is_complete()

    def test_incomplete_observation(self):
        obs = ClimateObservation(
            date=date(2020, 1, 1),
            sw_dwn=150.0,
            dni=None,
            ws_50m=5.0,
            ws_100m=7.0,
        )
        assert not obs.is_complete()


class TestRenewableIndicators:
    def test_as_feature_dict(self):
        indicators = RenewableIndicators(
            point_id=1,
            latitude=14.5,
            longitude=-92.0,
            country="Guatemala",
            sw_dwn_mean=200.0,
            dni_mean=600.0,
            ws_50m_mean=4.0,
            ws_100m_mean=6.0,
            solar_score=0.75,
            wind_score=0.5,
            hybrid_score=0.65,
        )
        features = indicators.as_feature_dict()
        assert features["sw_dwn_mean"] == 200.0
        assert features["ws_100m_mean"] == 6.0


class TestBenchmarkResult:
    def test_valid_result(self):
        result = BenchmarkResult(
            mode=ExecutionMode.SEQUENTIAL,
            worker_count=1,
            execution_time_seconds=5.0,
            memory_usage_mb=100.0,
        )
        assert result.worker_count == 1

    def test_invalid_worker_count(self):
        with pytest.raises(ValueError):
            BenchmarkResult(
                mode=ExecutionMode.SEQUENTIAL,
                worker_count=0,
                execution_time_seconds=5.0,
                memory_usage_mb=100.0,
            )
