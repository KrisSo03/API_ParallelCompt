import numpy as np
import pytest

from renewable_atlas.application.services import ClusterQualityService


def make_well_separated_blobs(n_per_blob: int = 20, n_features: int = 4, seed: int = 0):
    """Genera 3 nubes de puntos bien separadas para poder verificar que
    el servicio recomienda K=3 y que el silhouette es alto."""
    rng = np.random.default_rng(seed)
    centers = np.array(
        [
            [0.0] * n_features,
            [20.0] * n_features,
            [-20.0] * n_features,
        ]
    )
    blobs = [center + rng.normal(scale=0.5, size=(n_per_blob, n_features)) for center in centers]
    return np.vstack(blobs)


def test_evaluate_k_range_recommends_correct_k_for_separated_blobs():
    features = make_well_separated_blobs()
    service = ClusterQualityService()

    report = service.evaluate_k_range(features, k_values=list(range(2, 6)))

    assert report.recommended_k == 3
    assert report.silhouette_at_recommended >= 0.5
    assert report.passes_silhouette
    assert report.passes_davies_bouldin


def test_evaluate_k_range_inertia_decreases_with_k():
    features = make_well_separated_blobs()
    service = ClusterQualityService()

    report = service.evaluate_k_range(features, k_values=[2, 3, 4, 5])

    inertias = [report.inertia_by_k[k] for k in [2, 3, 4, 5]]
    # la inercia debe ser monotonamente no creciente al aumentar K
    assert all(inertias[i] >= inertias[i + 1] for i in range(len(inertias) - 1))


def test_evaluate_k_range_skips_k_greater_or_equal_to_n_samples():
    features = make_well_separated_blobs(n_per_blob=2, n_features=2)  # 6 puntos
    service = ClusterQualityService()

    report = service.evaluate_k_range(features, k_values=[2, 3, 10])

    assert 10 not in report.k_values
    assert len(report.notes) >= 1


def test_evaluate_k_range_raises_on_empty_valid_range():
    features = make_well_separated_blobs(n_per_blob=1, n_features=2)  # 3 puntos
    service = ClusterQualityService()

    with pytest.raises(ValueError):
        service.evaluate_k_range(features, k_values=[5, 6, 7])


def test_evaluate_stability_with_well_separated_blobs_is_high():
    features = make_well_separated_blobs()
    service = ClusterQualityService()

    mean_ari, std_ari = service.evaluate_stability(features, n_clusters=3, n_runs=5)

    assert mean_ari >= service.stability_ari_threshold
    assert std_ari >= 0.0


def test_evaluate_k_range_with_stability_runs_populates_report_fields():
    features = make_well_separated_blobs()
    service = ClusterQualityService()

    report = service.evaluate_k_range(
        features, k_values=[2, 3, 4], stability_runs=5
    )

    assert report.stability_ari_mean is not None
    assert report.stability_runs == 5
    assert report.passes_stability is True


def test_report_summary_does_not_raise():
    features = make_well_separated_blobs()
    service = ClusterQualityService()
    report = service.evaluate_k_range(features, k_values=[2, 3, 4], stability_runs=3)

    text = report.summary()
    assert "K recomendado" in text
