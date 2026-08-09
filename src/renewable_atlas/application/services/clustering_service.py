import numpy as np
import pandas as pd

from renewable_atlas.domain import ClusteringStrategy, ClusterProfile, ClusterQualityReport

from .cluster_quality_service import ClusterQualityService


class ClusteringService:
    SCORE_COLUMNS = ("solar_score", "wind_score", "hybrid_score")

    def __init__(
        self,
        strategy: ClusteringStrategy,
        *,
        quality_service: ClusterQualityService | None = None,
        strategy_factory=None,
        auto_select: bool = False,
        min_clusters: int = 2,
        max_clusters: int = 10,
        random_state: int = 42,
        stability_runs: int = 0,
    ):
        self.strategy = strategy
        self.quality_service = quality_service
        self.strategy_factory = strategy_factory
        self.auto_select = auto_select
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.random_state = random_state
        self.stability_runs = stability_runs
        self.last_quality_report: ClusterQualityReport | None = None

    def cluster(self, indicators_df: pd.DataFrame) -> tuple[np.ndarray, list[ClusterProfile]]:
        feature_columns = [
            "sw_dwn_mean",
            "dni_mean",
            "ws_50m_mean",
            "ws_100m_mean",
        ]
        available_columns = [col for col in feature_columns if col in indicators_df.columns]
        if not available_columns:
            raise ValueError("No clustering feature columns available in indicators dataframe")

        features = indicators_df[available_columns].values

        strategy = self._select_strategy(features)
        labels = strategy.fit_predict(features)

        profiles = []
        centroids = strategy.centroids()

        for cluster_id in range(centroids.shape[0]):
            mask = labels == cluster_id
            size = np.sum(mask)
            centroid_values = []
            for idx, col in enumerate(available_columns):
                if idx < centroids.shape[1]:
                    centroid_values.append(float(centroids[cluster_id, idx]))
                else:
                    centroid_values.append(0.0)

            centroid_dict = dict(zip(available_columns, centroid_values))
            country_breakdown = self._build_country_breakdown(indicators_df, mask)
            profile = ClusterProfile(
                cluster_id=int(cluster_id),
                label=f"Cluster {cluster_id}",
                description=f"Cluster {cluster_id} with {size} points",
                size=int(size),
                centroid=centroid_dict,
                country_breakdown=country_breakdown,
            )
            profiles.append(profile)

        return labels, profiles

    def _select_strategy(self, features: np.ndarray) -> ClusteringStrategy:
        self.last_quality_report = None
        if not self.auto_select:
            return self.strategy
        if self.quality_service is None or self.strategy_factory is None:
            raise RuntimeError(
                "Automatic K selection requires a quality service and strategy factory"
            )

        k_values = list(range(self.min_clusters, self.max_clusters + 1))
        self.last_quality_report = self.quality_service.evaluate_k_range(
            features,
            k_values=k_values,
            random_state=self.random_state,
            stability_runs=self.stability_runs,
        )
        return self.strategy_factory(self.last_quality_report.recommended_k)

    def _build_country_breakdown(self, indicators_df: pd.DataFrame, mask: np.ndarray) -> dict:
        """Arma un desglose por pais para los puntos de un cluster: cuantos
        puntos aporta cada pais, que porcentaje del cluster representa, y
        (si estan disponibles) el promedio de solar_score/wind_score/
        hybrid_score de ese pais dentro del cluster.

        Si el dataframe no trae columna 'country', devuelve un dict vacio
        en vez de fallar, para no romper corridas con datos parciales.
        """
        if "country" not in indicators_df.columns:
            return {}

        cluster_rows = indicators_df.loc[mask]
        total = len(cluster_rows)
        if total == 0:
            return {}

        score_columns = [col for col in self.SCORE_COLUMNS if col in indicators_df.columns]

        breakdown = {}
        for country, group in cluster_rows.groupby("country"):
            entry = {
                "count": int(len(group)),
                "percentage": float(len(group) / total),
            }
            for col in score_columns:
                entry[f"avg_{col}"] = float(group[col].mean())
            breakdown[str(country)] = entry

        # Ordenar de mayor a menor aporte de puntos, para que el pais
        # dominante del cluster quede primero (util para el dashboard).
        return dict(sorted(breakdown.items(), key=lambda item: item[1]["count"], reverse=True))
