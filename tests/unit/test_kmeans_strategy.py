import numpy as np
import pandas as pd
from renewable_atlas.application.services import ClusteringService
from renewable_atlas.infrastructure.clustering.kmeans_strategy import KMeansClusteringStrategy


def test_kmeans_strategy_handles_missing_values():
    features = np.array([
        [1.0, 2.0, 3.0, 4.0],
        [1.5, np.nan, 2.5, 3.5],
        [2.0, 3.0, 4.0, 5.0],
        [2.5, 3.5, 4.5, 5.5],
    ])

    strategy = KMeansClusteringStrategy(n_clusters=2, random_state=0)
    labels = strategy.fit_predict(features)

    assert len(labels) == len(features)
    assert set(labels) <= {0, 1}


def test_clustering_service_handles_all_missing_feature_column():
    indicators_df = pd.DataFrame({
        "sw_dwn_mean": [1.0, 2.0, 3.0, 4.0],
        "dni_mean": [np.nan, np.nan, np.nan, np.nan],
        "ws_50m_mean": [1.5, 2.5, 3.5, 4.5],
        "ws_100m_mean": [2.0, 3.0, 4.0, 5.0],
    })

    service = ClusteringService(KMeansClusteringStrategy(n_clusters=2, random_state=0))
    labels, profiles = service.cluster(indicators_df)

    assert len(labels) == len(indicators_df)
    assert len(profiles) == 2
    assert all(isinstance(profile.centroid, dict) for profile in profiles)
    assert all("sw_dwn_mean" in profile.centroid for profile in profiles)
