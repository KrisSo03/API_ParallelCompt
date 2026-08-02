import argparse
import logging
from pathlib import Path
from renewable_atlas.config import Settings
from renewable_atlas.composition import CompositionRoot
from renewable_atlas.infrastructure.benchmarking import BenchmarkReporter
from renewable_atlas.infrastructure.grid import SampleGridProvider
from renewable_atlas.infrastructure.reporting import ClusterReporter
from renewable_atlas.application.services import DataTransformer, IndicatorCalculator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Renewable Energy Atlas Generator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    download_parser = subparsers.add_parser("download", help="Download climate data from NASA POWER")
    download_parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Use fake climate data instead of NASA POWER",
    )

    process_parser = subparsers.add_parser("process", help="Process and clean climate data")
    process_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers to use for processing (1 = sequential, >1 = Dask)",
    )
    process_parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Use fake climate data instead of NASA POWER",
    )

    cluster_parser = subparsers.add_parser("cluster", help="Run K-Means clustering analysis")
    cluster_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers to use for processing before clustering",
    )
    cluster_parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Use fake climate data instead of NASA POWER",
    )

    benchmark_parser = subparsers.add_parser("benchmark", help="Run parallel benchmarking")
    benchmark_parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Use fake climate data instead of NASA POWER",
    )

    run_all_parser = subparsers.add_parser("run-all", help="Run complete pipeline")
    run_all_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers to use for processing (1 = sequential, >1 = Dask)",
    )
    run_all_parser.add_argument(
        "--use-fake",
        action="store_true",
        help="Use fake climate data instead of NASA POWER",
    )

    args = parser.parse_args()

    def build_processor(workers: int):
        if workers > 1:
            processor = container.build_dask_processor(num_workers=workers)
            logger.info(f"Using Dask processor with {workers} workers")
        else:
            processor = container.build_sequential_processor()
            logger.info("Using sequential processor")
        return processor

    settings = Settings.load()
    container = CompositionRoot(settings)
    grid_provider = SampleGridProvider(
        size=settings.grid.size,
        enable_sampling=settings.grid.enable_sampling,
        sample_size=settings.grid.sample_size,
    )
    points = grid_provider.generate()

    logger.info(f"Generated {len(points)} grid points for analysis")

    use_fake = getattr(args, "use_fake", False)

    if args.command == "download":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        observations = pipeline.download(points)
        logger.info(
            f"Downloaded climate observations for {len(observations)} points and saved raw data to {settings.paths.data_dir}/raw_observations.parquet"
        )

    elif args.command == "process":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        processor = build_processor(args.workers)
        observations = pipeline.download(points)
        indicators_df = pipeline.process(observations, processor)
        logger.info(
            f"Processed data for {len(indicators_df)} points and saved indicators to {settings.paths.data_dir}/indicators.parquet"
        )

    elif args.command == "cluster":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        processor = build_processor(args.workers)
        observations = pipeline.download(points)
        indicators_df = pipeline.process(observations, processor)
        labels, profiles = pipeline.cluster(indicators_df)
        logger.info(f"Clustering complete: {len(profiles)} clusters identified")

        results_dir = Path(settings.paths.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        reporter = ClusterReporter(indicators_df, labels, profiles)
        csv_path = results_dir / "cluster_indicators.csv"
        parquet_path = results_dir / "cluster_indicators.parquet"
        profile_path = results_dir / "cluster_profiles.csv"

        reporter.save_csv(csv_path)
        reporter.save_parquet(parquet_path)
        reporter.save_cluster_profiles(profile_path)
        reporter.save_plots(results_dir)

        logger.info(f"Saved cluster indicators to {csv_path}")
        logger.info(f"Saved cluster profiles to {profile_path}")
        logger.info(f"Saved cluster plots to {results_dir}")

    elif args.command == "run-all" or args.command is None:
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        processor = build_processor(args.workers)
        logger.info("Running complete pipeline...")
        indicators_df, labels, profiles = pipeline.run(points, processor)
        logger.info(f"Clustering complete: {len(profiles)} clusters identified")

        results_dir = Path(settings.paths.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        reporter = ClusterReporter(indicators_df, labels, profiles)
        csv_path = results_dir / "cluster_indicators.csv"
        parquet_path = results_dir / "cluster_indicators.parquet"
        profile_path = results_dir / "cluster_profiles.csv"

        reporter.save_csv(csv_path)
        reporter.save_parquet(parquet_path)
        reporter.save_cluster_profiles(profile_path)
        reporter.save_summary(results_dir)
        reporter.save_plots(results_dir)

        logger.info(f"Saved cluster indicators to {csv_path}")
        logger.info(f"Saved cluster profiles to {profile_path}")
        logger.info(f"Saved cluster plots to {results_dir}")

    elif args.command == "benchmark":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        sample_size = min(10, len(points))
        sample_points = points[:sample_size]

        logger.info(f"Benchmarking processing with {sample_size} points...")
        benchmark_service = container.build_benchmark_service()

        observations = pipeline.download(sample_points)

        def calculate_indicators(item):
            point_id, payload = item
            point = payload["point"]
            observations = payload["observations"]

            df = DataTransformer.to_dataframe(observations)
            df = DataTransformer.clean(df)

            calculator = IndicatorCalculator()
            return calculator.calculate(
                point_id,
                point.latitude,
                point.longitude,
                point.country,
                df,
            )

        items = list(observations.items())

        strategies = [container.build_sequential_processor()]
        for worker_count in settings.benchmark.worker_counts:
            if worker_count > 1:
                strategies.append(container.build_dask_processor(num_workers=worker_count))

        results = benchmark_service.run(
            strategies,
            items,
            calculate_indicators,
            repeats=settings.benchmark.repeats_per_config,
        )

        logger.info("Benchmark results:")
        for result in results:
            logger.info(
                f"  {result.mode.value}: {result.worker_count} workers, "
                f"{result.execution_time_seconds:.2f}s, "
                f"memory: {result.memory_usage_mb:.1f}MB"
            )

        report_dir = Path(settings.paths.results_dir) / "benchmark"
        report_dir.mkdir(parents=True, exist_ok=True)
        benchmark_reporter = BenchmarkReporter(results)
        benchmark_reporter.save_csv(report_dir / "benchmark_results.csv")
        benchmark_reporter.save_parquet(report_dir / "benchmark_results.parquet")
        benchmark_reporter.save_plots(report_dir)

        logger.info(f"Saved benchmark results to {report_dir}")


if __name__ == "__main__":
    main()
