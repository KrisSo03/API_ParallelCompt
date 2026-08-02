import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


class ClusterReporter:
    def __init__(self, indicators_df: pd.DataFrame, labels: pd.Series, profiles: list):
        self.indicators_df = indicators_df.copy()
        self.indicators_df["cluster_id"] = labels
        self.profiles = profiles

    def to_dataframe(self) -> pd.DataFrame:
        return self.indicators_df

    def save_csv(self, path: str) -> None:
        self.indicators_df.to_csv(path, index=False)

    def save_parquet(self, path: str) -> None:
        self.indicators_df.to_parquet(path, index=False)

    def save_cluster_profiles(self, path: str) -> None:
        profiles_df = pd.DataFrame(
            [
                {
                    "cluster_id": p.cluster_id,
                    "label": p.label,
                    "description": p.description,
                    "size": p.size,
                    **p.centroid,
                }
                for p in self.profiles
            ]
        )
        profiles_df.to_csv(path, index=False)

    def save_summary(self, output_dir: str) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        summary_df = (
            self.indicators_df.groupby("cluster_id")
            .agg(
                points=("point_id", "count"),
                solar_mean=("solar_score", "mean"),
                wind_mean=("wind_score", "mean"),
                hybrid_mean=("hybrid_score", "mean"),
            )
            .reset_index()
        )
        summary_df.to_csv(output_path / "cluster_summary.csv", index=False)

    def save_plots(self, output_dir: str) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        self.indicators_df.groupby("cluster_id")["solar_score"].mean().plot(
            kind="bar", ax=axes[0]
        )
        axes[0].set_title("Puntaje solar promedio por cluster")
        axes[0].set_xlabel("Cluster")
        axes[0].set_ylabel("Solar")
        axes[0].grid(True)

        self.indicators_df.groupby("cluster_id")["wind_score"].mean().plot(
            kind="bar", ax=axes[1]
        )
        axes[1].set_title("Puntaje eólico promedio por cluster")
        axes[1].set_xlabel("Cluster")
        axes[1].set_ylabel("Eólico")
        axes[1].grid(True)

        plt.tight_layout()
        plt.savefig(output_path / "cluster_profiles.png", dpi=100)
        plt.close()
