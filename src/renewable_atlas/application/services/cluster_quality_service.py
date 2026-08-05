import numpy as np
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score

from renewable_atlas.domain import ClusterQualityReport
from renewable_atlas.infrastructure.clustering import KMeansClusteringStrategy


class ClusterQualityService:
    """Evalua la calidad de distintas configuraciones de K-Means.

    Implementa los criterios de validacion definidos por el equipo
    (ver Atlas_Energia_Plan_Integral, SUPUESTO 2 y SUPUESTO 3):
      - Silhouette score >= 0.5 en el K optimo.
      - Davies-Bouldin index < 2.0.
      - Estabilidad: Adjusted Rand Index >= 0.95 entre corridas con
        distinta semilla aleatoria, para el K elegido.
    """

    def __init__(
        self,
        silhouette_threshold: float = 0.5,
        davies_bouldin_threshold: float = 2.0,
        stability_ari_threshold: float = 0.95,
    ):
        self.silhouette_threshold = silhouette_threshold
        self.davies_bouldin_threshold = davies_bouldin_threshold
        self.stability_ari_threshold = stability_ari_threshold

    def evaluate_k_range(
        self,
        features: np.ndarray,
        k_values: list[int] | None = None,
        random_state: int = 42,
        stability_runs: int = 0,
    ) -> ClusterQualityReport:
        """Corre K-Means para cada K en k_values y calcula inercia,
        silhouette y Davies-Bouldin. Recomienda el K con mayor silhouette.

        Si stability_runs > 0, ademas evalua la estabilidad del K
        recomendado corriendo K-Means stability_runs veces con semillas
        distintas y comparando las etiquetas con Adjusted Rand Index.
        """
        if k_values is None:
            k_values = list(range(2, 11))

        n_samples = np.asarray(features).shape[0]
        valid_k_values = [k for k in k_values if 2 <= k < n_samples]
        notes: list[str] = []
        skipped = sorted(set(k_values) - set(valid_k_values))
        if skipped:
            notes.append(
                f"Se omitieron K={skipped} por ser >= al numero de puntos ({n_samples})."
            )
        if not valid_k_values:
            raise ValueError(
                "No hay valores de K validos para evaluar (revisa el tamano del dataset)."
            )

        inertia_by_k: dict[int, float] = {}
        silhouette_by_k: dict[int, float] = {}
        davies_bouldin_by_k: dict[int, float] = {}

        for k in valid_k_values:
            strategy = KMeansClusteringStrategy(n_clusters=k, random_state=random_state)
            labels = strategy.fit_predict(features)

            inertia_by_k[k] = strategy.inertia()

            n_unique_labels = len(set(labels))
            if n_unique_labels < 2:
                # silhouette y davies-bouldin no estan definidos con un solo cluster
                silhouette_by_k[k] = float("nan")
                davies_bouldin_by_k[k] = float("nan")
                notes.append(f"K={k} produjo un unico cluster; se omite de silhouette/DB.")
                continue

            silhouette_by_k[k] = float(
                silhouette_score(strategy.scaled_features, labels)
            )
            davies_bouldin_by_k[k] = float(
                davies_bouldin_score(strategy.scaled_features, labels)
            )

        scored_ks = [k for k in valid_k_values if not np.isnan(silhouette_by_k[k])]
        if not scored_ks:
            raise ValueError("Ningun K produjo un silhouette valido; revisa los datos de entrada.")

        recommended_k = max(scored_ks, key=lambda k: silhouette_by_k[k])

        stability_ari_mean = None
        stability_ari_std = None
        if stability_runs and stability_runs > 1:
            stability_ari_mean, stability_ari_std = self.evaluate_stability(
                features, n_clusters=recommended_k, n_runs=stability_runs
            )

        return ClusterQualityReport(
            k_values=valid_k_values,
            inertia_by_k=inertia_by_k,
            silhouette_by_k=silhouette_by_k,
            davies_bouldin_by_k=davies_bouldin_by_k,
            recommended_k=recommended_k,
            silhouette_at_recommended=silhouette_by_k[recommended_k],
            davies_bouldin_at_recommended=davies_bouldin_by_k[recommended_k],
            silhouette_threshold=self.silhouette_threshold,
            davies_bouldin_threshold=self.davies_bouldin_threshold,
            stability_ari_mean=stability_ari_mean,
            stability_ari_std=stability_ari_std,
            stability_ari_threshold=self.stability_ari_threshold,
            stability_runs=stability_runs if stability_ari_mean is not None else 0,
            notes=notes,
        )

    def evaluate_stability(
        self,
        features: np.ndarray,
        n_clusters: int,
        n_runs: int = 10,
        base_seed: int = 0,
    ) -> tuple[float, float]:
        """Corre K-Means n_runs veces con semillas distintas y compara
        cada par de corridas con Adjusted Rand Index. Devuelve (media, std)
        del ARI entre todas las corridas.
        """
        all_labels = []
        for i in range(n_runs):
            strategy = KMeansClusteringStrategy(n_clusters=n_clusters, random_state=base_seed + i)
            labels = strategy.fit_predict(features)
            all_labels.append(labels)

        ari_scores = []
        for i in range(len(all_labels)):
            for j in range(i + 1, len(all_labels)):
                ari_scores.append(adjusted_rand_score(all_labels[i], all_labels[j]))

        return float(np.mean(ari_scores)), float(np.std(ari_scores))
