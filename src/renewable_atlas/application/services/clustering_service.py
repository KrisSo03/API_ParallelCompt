import pandas as pd
import numpy as np
from renewable_atlas.domain import ClusteringStrategy, ClusterProfile


class ClusteringService:
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
            profile = ClusterProfile(
                cluster_id=int(cluster_id),
                label=f"Cluster {cluster_id}",
                description=f"Cluster {cluster_id} with {size} points",
                size=int(size),
                centroid=centroid_dict,
            )
            profiles.append(profile)

        return labels, profiles
