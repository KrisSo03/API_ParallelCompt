"""Compara la consistencia del clustering entre distintas configuraciones
de workers (1, 2, 4, 8) y repeticiones, dentro de un experimento HPC.

Uso:
    python hpc/compare_worker_consistency.py results/<experiment_id>

Lee cada results/<experiment_id>/workers-XXX/run-YY/indicators.parquet
(columna 'cluster', y 'point_id' para alinear puntos entre corridas) y su
cluster_profiles.json correspondiente (para mapear cluster_id -> label).

Para cada corrida contra una corrida base (la primera que se encuentra),
calcula:
  - Adjusted Rand Index (ARI) sobre los cluster_id crudos. Invariante a
    permutaciones de numeracion de cluster (K-Means puede numerar los
    mismos grupos distinto entre corridas). Criterio del equipo: >= 0.95.
  - Porcentaje de puntos con la MISMA etiqueta de negocio (ej.
    "Solar-dominant") en ambas corridas, tras mapear cluster_id -> label
    via cluster_profiles.json. Mas facil de explicar en el reporte final
    que el ARI.

Tambien evalua silhouette score y Davies-Bouldin de cada corrida usando
ClusterQualityService sobre las columnas de features reales, para poder
comparar calidad entre configuraciones de workers.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

FEATURE_COLUMNS = ["sw_dwn_mean", "dni_mean", "ws_50m_mean", "ws_100m_mean"]


def load_run(run_dir: Path) -> tuple[pd.DataFrame, dict]:
    indicators_path = run_dir / "indicators.parquet"
    if not indicators_path.exists():
        indicators_path = run_dir / "indicators.csv"  # fallback para pruebas locales

    if indicators_path.suffix == ".parquet":
        df = pd.read_parquet(indicators_path)
    else:
        df = pd.read_csv(indicators_path)

    df = df.sort_values("point_id").reset_index(drop=True)

    profiles_path = run_dir / "cluster_profiles.json"
    cluster_id_to_label = {}
    if profiles_path.exists():
        profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        cluster_id_to_label = {p["cluster_id"]: p["label"] for p in profiles}

    return df, cluster_id_to_label


def find_runs(experiment_dir: Path) -> list[Path]:
    return sorted(experiment_dir.glob("workers-*/run-*"))


def compare_runs(experiment_dir: Path) -> None:
    run_dirs = find_runs(experiment_dir)
    if not run_dirs:
        print(f"No se encontraron corridas en {experiment_dir}")
        return

    base_dir = run_dirs[0]
    base_df, base_labels_map = load_run(base_dir)
    base_labels_named = base_df["cluster"].map(base_labels_map)

    print(f"Corrida base: {base_dir}")
    print(f"Puntos: {len(base_df)}\n")

    header = f"{'corrida':45s} {'ARI':>8s} {'%% etiqueta igual':>18s} {'pasa (ARI>=0.95)':>18s}"
    print(header)
    print("-" * len(header))

    results = []
    for run_dir in run_dirs:
        if run_dir == base_dir:
            continue

        df, labels_map = load_run(run_dir)

        if len(df) != len(base_df) or not (df["point_id"].values == base_df["point_id"].values).all():
            print(f"{str(run_dir):45s} AVISO: point_id no coincide con la corrida base, se omite")
            continue

        ari = adjusted_rand_score(base_df["cluster"].values, df["cluster"].values)

        named_labels = df["cluster"].map(labels_map)
        match_pct = float((named_labels.values == base_labels_named.values).mean())

        passes = ari >= 0.95
        print(f"{str(run_dir):45s} {ari:8.3f} {match_pct:17.1%} {'SI' if passes else 'NO':>18s}")

        results.append({"run": str(run_dir), "ari": ari, "label_match_pct": match_pct, "passes": passes})

    if results:
        mean_ari = np.mean([r["ari"] for r in results])
        all_pass = all(r["passes"] for r in results)
        print("\nResumen:")
        print(f"  ARI promedio vs corrida base: {mean_ari:.3f}")
        print(f"  Todas las corridas pasan el umbral (ARI >= 0.95): {'SI' if all_pass else 'NO'}")


def compare_quality_across_configs(experiment_dir: Path) -> None:
    try:
        from renewable_atlas.application.services import ClusterQualityService
    except ImportError:
        print("\n(ClusterQualityService no disponible en este entorno; se omite comparacion de calidad)")
        return

    run_dirs = find_runs(experiment_dir)
    service = ClusterQualityService()

    print("\nCalidad de clustering por corrida (silhouette / Davies-Bouldin en el K real usado):")
    header = f"{'corrida':45s} {'K':>4s} {'silhouette':>12s} {'davies-bouldin':>16s}"
    print(header)
    print("-" * len(header))

    for run_dir in run_dirs:
        df, _ = load_run(run_dir)
        available_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
        if not available_cols:
            continue
        features = df[available_cols].values
        k_used = df["cluster"].nunique()

        try:
            report = service.evaluate_k_range(features, k_values=[k_used])
        except ValueError as exc:
            print(f"{str(run_dir):45s} No se pudo evaluar: {exc}")
            continue

        print(
            f"{str(run_dir):45s} {k_used:4d} "
            f"{report.silhouette_by_k[k_used]:12.3f} "
            f"{report.davies_bouldin_by_k[k_used]:16.3f}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python hpc/compare_worker_consistency.py <ruta al experimento>")
        sys.exit(1)

    experiment_dir = Path(sys.argv[1])
    compare_runs(experiment_dir)
    compare_quality_across_configs(experiment_dir)
