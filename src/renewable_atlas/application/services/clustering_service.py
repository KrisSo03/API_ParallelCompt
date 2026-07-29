import pandas as pd
import numpy as np
from renewable_atlas.domain import ClusteringStrategy, ClusterProfile


class ClusteringService:
    def __init__(self, strategy: ClusteringStrategy):
        self.strategy = strategy

    def cluster(self, indicators_df: pd.DataFrame) -> tuple[np.ndarray, list[ClusterProfile]]:
        features = indicators_df[["sw_dwn_mean", "dni_mean", "ws_50m_mean", "ws_100m_mean"]].values

        labels = self.strategy.fit_predict(features)

        profiles = []
        centroids = self.strategy.centroids()

        for cluster_id in range(self.strategy.centroids().shape[0]):
            mask = labels == cluster_id
            size = np.sum(mask)
            centroid_dict = {
                "sw_dwn_mean": float(centroids[cluster_id, 0]),
                "dni_mean": float(centroids[cluster_id, 1]),
                "ws_50m_mean": float(centroids[cluster_id, 2]),
                "ws_100m_mean": float(centroids[cluster_id, 3]),
            }

            profile = ClusterProfile(
                cluster_id=int(cluster_id),
                label=f"Cluster {cluster_id}",
                description=f"Cluster {cluster_id} with {size} points",
                size=int(size),
                centroid=centroid_dict,
            )
            profiles.append(profile)

        return labels, profiles
