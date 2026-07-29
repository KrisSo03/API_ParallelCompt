import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from renewable_atlas.domain import BenchmarkResult


class BenchmarkReporter:
    def __init__(self, results: list[BenchmarkResult]):
        self.results = results

    def to_dataframe(self) -> pd.DataFrame:
        data = [
            {
                "mode": r.mode.value,
                "worker_count": r.worker_count,
                "execution_time_seconds": r.execution_time_seconds,
                "memory_usage_mb": r.memory_usage_mb,
                "speedup": r.speedup,
                "efficiency": r.efficiency,
            }
            for r in self.results
        ]
        return pd.DataFrame(data)

    def print_console_summary(self) -> None:
        df = self.to_dataframe()
        print("\n=== Benchmark Results ===")
        print(df.to_string(index=False))

    def save_csv(self, path: str) -> None:
        df = self.to_dataframe()
        df.to_csv(path, index=False)

    def save_parquet(self, path: str) -> None:
        df = self.to_dataframe()
        df.to_parquet(path)

    def save_plots(self, output_dir: str) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        df = self.to_dataframe()

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        df.groupby("worker_count")["execution_time_seconds"].mean().plot(
            ax=axes[0], marker="o"
        )
        axes[0].set_xlabel("Worker Count")
        axes[0].set_ylabel("Execution Time (seconds)")
        axes[0].set_title("Execution Time vs Workers")
        axes[0].grid(True)

        speedup_df = df[df["speedup"].notna()]
        if not speedup_df.empty:
            speedup_df.groupby("worker_count")["speedup"].mean().plot(ax=axes[1], marker="o")
            axes[1].set_xlabel("Worker Count")
            axes[1].set_ylabel("Speedup")
            axes[1].set_title("Speedup vs Workers")
            axes[1].grid(True)

        plt.tight_layout()
        plt.savefig(output_path / "benchmark_results.png", dpi=100)
        plt.close()
