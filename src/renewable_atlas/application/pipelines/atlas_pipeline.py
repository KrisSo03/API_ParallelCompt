import pandas as pd

from renewable_atlas.application.services import (
    ClusteringService,
    ClusterInterpretationService,
    DataTransformer,
    IndicatorCalculator,
    ScoringService,
)
from renewable_atlas.domain import (
    ClimateDataSource,
    DataRepository,
    ProcessingStrategy,
)


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

    def download(self, points, persist: bool = True):
        observations_by_point = {}
        raw_rows = []

        for point_id, point in enumerate(points):
            try:
                observations = self.data_source.fetch_observations(point)
            except Exception:
                observations = []

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
                        "date": obs.date,
                        "sw_dwn": obs.sw_dwn,
                        "dni": obs.dni,
                        "ws_50m": obs.ws_50m,
                        "ws_100m": obs.ws_100m,
                    }
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
    return IndicatorCalculator().calculate(
        point_id,
        point.latitude,
        point.longitude,
        point.country,
        df,
    )
