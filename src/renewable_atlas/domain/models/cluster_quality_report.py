from dataclasses import dataclass, field


@dataclass
class ClusterQualityReport:
    """Resultado de evaluar la calidad del clustering para un rango de K.

    Criterios de aprobación (definidos en el plan del equipo, SUPUESTO 2):
      - silhouette_score >= 0.5 en el K recomendado
      - davies_bouldin_score < 2.0 en el K recomendado
      - adjusted_rand_index (estabilidad) >= 0.95 entre corridas con distinta semilla
    """

    k_values: list[int]
    inertia_by_k: dict[int, float]
    silhouette_by_k: dict[int, float]
    davies_bouldin_by_k: dict[int, float]

    recommended_k: int
    silhouette_at_recommended: float
    davies_bouldin_at_recommended: float

    silhouette_threshold: float = 0.5
    davies_bouldin_threshold: float = 2.0

    stability_ari_mean: float | None = None
    stability_ari_std: float | None = None
    stability_ari_threshold: float = 0.95
    stability_runs: int = 0

    notes: list[str] = field(default_factory=list)

    @property
    def passes_silhouette(self) -> bool:
        return self.silhouette_at_recommended >= self.silhouette_threshold

    @property
    def passes_davies_bouldin(self) -> bool:
        return self.davies_bouldin_at_recommended < self.davies_bouldin_threshold

    @property
    def passes_stability(self) -> bool | None:
        if self.stability_ari_mean is None:
            return None
        return self.stability_ari_mean >= self.stability_ari_threshold

    @property
    def passes_all(self) -> bool:
        stability_ok = self.passes_stability
        return self.passes_silhouette and self.passes_davies_bouldin and (
            stability_ok is None or stability_ok
        )

    def summary(self) -> str:
        lines = [
            f"K recomendado: {self.recommended_k}",
            f"Silhouette({self.recommended_k}) = {self.silhouette_at_recommended:.3f} "
            f"({'PASA' if self.passes_silhouette else 'NO PASA'}, umbral >= {self.silhouette_threshold})",
            f"Davies-Bouldin({self.recommended_k}) = {self.davies_bouldin_at_recommended:.3f} "
            f"({'PASA' if self.passes_davies_bouldin else 'NO PASA'}, umbral < {self.davies_bouldin_threshold})",
        ]
        if self.stability_ari_mean is not None:
            passes = self.passes_stability
            lines.append(
                f"Estabilidad (ARI promedio de {self.stability_runs} corridas) = "
                f"{self.stability_ari_mean:.3f} +/- {self.stability_ari_std:.3f} "
                f"({'PASA' if passes else 'NO PASA'}, umbral >= {self.stability_ari_threshold})"
            )
        for note in self.notes:
            lines.append(f"Nota: {note}")
        return "\n".join(lines)
