import logging
from dataclasses import asdict

import pandas as pd

from renewable_atlas.application.services import (
    ClusteringService,
    ClusterInterpretationService,
    DataTransformer,
    DataValidator,
    IndicatorCalculator,
    ScoringService,
)
from renewable_atlas.domain import (
    ClimateDataSource,
    DataRepository,
    ProcessingStrategy,
)

logger = logging.getLogger(__name__)


class AtlasPipeline:
    def __init__(
        self,
        data_source: ClimateDataSource,
        repository: DataRepository,
        clustering_service: ClusteringService,
        interpretation_service: ClusterInterpretationService,
    ):
        self.data_source = data_source
        self.repository = repository
        self.clustering_service = clustering_service
        self.interpretation_service = interpretation_service
        self.last_download_report = {}

    def download(self, points, persist: bool = True):
        observations_by_point = {}
        raw_rows = []
        failed_points = []

        for point_id, point in enumerate(points):
            try:
                observations = self.data_source.fetch_observations(point)
            except Exception as exc:
                logger.exception("Climate download failed for point %s", point_id)
                failed_points.append(
                    {"point_id": point_id, "country": point.country, "error": str(exc)}
                )
                observations = []

            if not observations and not any(
                failure["point_id"] == point_id for failure in failed_points
            ):
                failed_points.append(
                    {"point_id": point_id, "country": point.country, "error": "no observations"}
                )

            observations_by_point[point_id] = {
                "point": point,
                "observations": observations,
            }

            for obs in observations:
                raw_rows.append(
                    {
                        "point_id": point_id,
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "country": point.country,
                        **asdict(obs),
                    }
                )

        successful_points = len(points) - len(failed_points)
        self.last_download_report = {
            "requested_points": len(points),
            "successful_points": successful_points,
            "failed_points": failed_points,
            "total_observations": len(raw_rows),
            "point_completeness": successful_points / len(points) if points else 0.0,
        }
        if failed_points:
            raise RuntimeError(
                f"Climate download incomplete: {successful_points}/{len(points)} points succeeded"
            )

        raw_df = pd.DataFrame(raw_rows)
        if persist:
            self.repository.save(raw_df, "raw_observations")
        return observations_by_point

    def process(
        self,
        observations_by_point,
        processor: ProcessingStrategy,
        persist: bool = True,
    ):
        items = list(observations_by_point.items())
        indicators = processor.process(items, _calculate_indicators)

        indicators_df = pd.DataFrame(
            [
                {
                    "point_id": ind.point_id,
                    "latitude": ind.latitude,
                    "longitude": ind.longitude,
                    "country": ind.country,
                    "sw_dwn_mean": ind.sw_dwn_mean,
                    "dni_mean": ind.dni_mean,
                    "ws_50m_mean": ind.ws_50m_mean,
                    "ws_100m_mean": ind.ws_100m_mean,
                    "solar_score": ind.solar_score,
                    "wind_score": ind.wind_score,
                    "hybrid_score": ind.hybrid_score,
                    "ws_10m_mean": ind.ws_10m_mean,
                    "sw_diff_mean": ind.sw_diff_mean,
                    "clr_sky_sw_dwn_mean": ind.clr_sky_sw_dwn_mean,
                    "allsky_kt_mean": ind.allsky_kt_mean,
                    "wd_10m_mean": ind.wd_10m_mean,
                    "wd_50m_mean": ind.wd_50m_mean,
                    "t2m_mean": ind.t2m_mean,
                    "t2m_max_mean": ind.t2m_max_mean,
                    "t2m_min_mean": ind.t2m_min_mean,
                    "t2mdew_mean": ind.t2mdew_mean,
                    "ps_mean": ind.ps_mean,
                    "rh2m_mean": ind.rh2m_mean,
                    "qv2m_mean": ind.qv2m_mean,
                    "prectotcorr_mean": ind.prectotcorr_mean,
                    "cloud_amt_mean": ind.cloud_amt_mean,
                }
                for ind in indicators
            ]
        )

        scored_df = ScoringService().score(indicators_df)
        if persist:
            self.repository.save(scored_df, "indicators")
        return scored_df

    def cluster(self, indicators_df):
        labels, profiles = self.clustering_service.cluster(indicators_df)
        profiles = self.interpretation_service.interpret(profiles)
        return labels, profiles

    def run(self, points, processor: ProcessingStrategy):
        observations = self.download(points)
        return self.run_from_observations(observations, processor)

    def run_from_observations(
        self, observations, processor: ProcessingStrategy, persist: bool = True
    ):
        """Reuse one immutable input for comparable worker configurations."""
        indicators_df = self.process(observations, processor, persist=persist)
        labels, profiles = self.cluster(indicators_df)
        return indicators_df, labels, profiles


def _calculate_indicators(item):
    """Top-level worker task, serializable by Dask's process scheduler."""
    point_id, payload = item
    point = payload["point"]
    observations = payload["observations"]
    df = DataTransformer.clean(DataTransformer.to_dataframe(observations))
    report = DataValidator().validate(df, required_columns=["sw_dwn", "dni", "ws_50m", "ws_100m"])
    if not report.is_valid:
        raise ValueError(
            f"Point {point_id} has insufficient climate data "
            f"({report.completeness_ratio:.1%} complete)"
        )
    return IndicatorCalculator().calculate(
        point_id,
        point.latitude,
        point.longitude,
        point.country,
        df,
    )
