import pandas as pd
import numpy as np
from renewable_atlas.domain import ClusteringStrategy, ClusterProfile


class ClusteringService:
    SCORE_COLUMNS = ("solar_score", "wind_score", "hybrid_score")

    def __init__(self, strategy: ClusteringStrategy):
        self.strategy = strategy

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

        labels = self.strategy.fit_predict(features)

        profiles = []
        centroids = self.strategy.centroids()

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