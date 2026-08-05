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


def test_clustering_service_builds_country_breakdown_per_cluster():
    # Dos grupos bien separados: uno con paises de Centroamerica "solares",
    # otro con paises "eolicos", para verificar que el desglose por pais
    # queda asociado al cluster correcto.
    indicators_df = pd.DataFrame({
        "sw_dwn_mean": [300.0, 305.0, 295.0, 100.0, 105.0, 95.0],
        "dni_mean": [280.0, 285.0, 275.0, 90.0, 95.0, 85.0],
        "ws_50m_mean": [2.0, 2.5, 1.5, 8.0, 8.5, 7.5],
        "ws_100m_mean": [3.0, 3.5, 2.5, 9.0, 9.5, 8.5],
        "solar_score": [0.9, 0.92, 0.88, 0.2, 0.22, 0.18],
        "wind_score": [0.1, 0.12, 0.08, 0.9, 0.92, 0.88],
        "hybrid_score": [0.5, 0.52, 0.48, 0.55, 0.57, 0.53],
        "country": ["CR", "CR", "PA", "HN", "HN", "GT"],
    })

    service = ClusteringService(KMeansClusteringStrategy(n_clusters=2, random_state=0))
    labels, profiles = service.cluster(indicators_df)

    for profile in profiles:
        assert profile.country_breakdown, "cada cluster debe tener desglose por pais"
        total_points_in_breakdown = sum(c["count"] for c in profile.country_breakdown.values())
        assert total_points_in_breakdown == profile.size

        percentages = [c["percentage"] for c in profile.country_breakdown.values()]
        assert abs(sum(percentages) - 1.0) < 1e-9

        for country_stats in profile.country_breakdown.values():
            assert "avg_solar_score" in country_stats
            assert "avg_wind_score" in country_stats
            assert "avg_hybrid_score" in country_stats


def test_clustering_service_country_breakdown_sorted_by_count_desc():
    indicators_df = pd.DataFrame({
        "sw_dwn_mean": [300.0, 305.0, 295.0, 298.0],
        "dni_mean": [280.0, 285.0, 275.0, 278.0],
        "ws_50m_mean": [2.0, 2.5, 1.5, 2.2],
        "ws_100m_mean": [3.0, 3.5, 2.5, 3.2],
        "country": ["CR", "CR", "CR", "PA"],
    })

    service = ClusteringService(KMeansClusteringStrategy(n_clusters=1, random_state=0))
    labels, profiles = service.cluster(indicators_df)

    breakdown = profiles[0].country_breakdown
    countries_in_order = list(breakdown.keys())

    assert countries_in_order[0] == "CR"  # el pais con mas puntos va primero
    assert breakdown["CR"]["count"] == 3
    assert breakdown["PA"]["count"] == 1


def test_clustering_service_country_breakdown_empty_without_country_column():
    indicators_df = pd.DataFrame({
        "sw_dwn_mean": [1.0, 2.0, 3.0, 4.0],
        "dni_mean": [1.5, 2.5, 3.5, 4.5],
        "ws_50m_mean": [1.5, 2.5, 3.5, 4.5],
        "ws_100m_mean": [2.0, 3.0, 4.0, 5.0],
    })

    service = ClusteringService(KMeansClusteringStrategy(n_clusters=2, random_state=0))
    labels, profiles = service.cluster(indicators_df)

    assert all(profile.country_breakdown == {} for profile in profiles)