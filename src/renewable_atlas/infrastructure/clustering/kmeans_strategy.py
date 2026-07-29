import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from renewable_atlas.domain import ClusteringStrategy


class KMeansClusteringStrategy(ClusteringStrategy):
    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.kmeans: KMeans | None = None
        self.scaled_features: np.ndarray | None = None

    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        self.scaled_features = self.scaler.fit_transform(features)
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state)
        labels = self.kmeans.fit_predict(self.scaled_features)
        return labels

    def centroids(self) -> np.ndarray:
        if self.kmeans is None:
            raise ValueError("Must call fit_predict before centroids()")
        return self.scaler.inverse_transform(self.kmeans.cluster_centers_)
