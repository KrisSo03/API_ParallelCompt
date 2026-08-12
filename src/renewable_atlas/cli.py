import argparse
import hashlib
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from renewable_atlas.application.services import DataTransformer, IndicatorCalculator
from renewable_atlas.composition import CompositionRoot
from renewable_atlas.config import Settings
from renewable_atlas.infrastructure.benchmarking import (
    BenchmarkReporter,
    ProcessTreeMemorySampler,
    compute_efficiency,
    compute_speedup,
)
from renewable_atlas.infrastructure.grid import SampleGridProvider
from renewable_atlas.infrastructure.nasa_power import NasaPowerAwsProcessor, NasaPowerAwsStager
from renewable_atlas.infrastructure.reporting import ClusterReporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Renewable Energy Atlas Generator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    download_parser = subparsers.add_parser(
        "download", help="Download climate data from NASA POWER"
    )
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

    hpc_run_parser = subparsers.add_parser(
        "hpc-run", help="Run one reproducible HPC worker configuration"
    )
    _add_hpc_arguments(hpc_run_parser)
    hpc_run_parser.add_argument("--workers", type=int, default=1)

    hpc_benchmark_parser = subparsers.add_parser(
        "hpc-benchmark", help="Run a reproducible worker matrix"
    )
    _add_hpc_arguments(hpc_benchmark_parser)
    hpc_benchmark_parser.add_argument(
        "--workers", default=None, help="Comma-separated worker counts"
    )

    aws_stage_parser = subparsers.add_parser(
        "aws-stage", help="Stage a large NASA POWER dataset from public AWS Zarr archives"
    )
    _add_aws_arguments(aws_stage_parser)

    aws_run_parser = subparsers.add_parser(
        "aws-run", help="Process staged NASA POWER AWS data with Dask"
    )
    _add_aws_arguments(aws_run_parser)
    aws_run_parser.add_argument(
        "--download",
        action="store_true",
        help="Download AWS partitions before processing them",
    )
    aws_run_parser.add_argument("--workers", default="1", help="Comma-separated worker counts")
    aws_run_parser.add_argument("--repeats", type=int, default=1)
    aws_run_parser.add_argument("--results-dir", default=None)
    aws_run_parser.add_argument(
        "--scheduler", choices=("threads", "processes"), default="threads"
    )

    args = parser.parse_args(argv)

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

    if args.command in {"hpc-run", "hpc-benchmark"}:
        return _run_hpc_command(args, settings, container)

    if args.command in {"aws-stage", "aws-run"}:
        return _run_aws_command(args, settings, container)

    grid_provider = SampleGridProvider(
        size=settings.grid.size,
        enable_sampling=settings.grid.enable_sampling,
        sample_size=settings.grid.sample_size,
    )
    points = grid_provider.generate()

    logger.info(f"Generated {len(points)} grid points for analysis")

    use_fake = getattr(args, "use_fake", False) or settings.execution.source == "fake"

    if args.command == "download":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        observations = pipeline.download(points)
        logger.info(
            "Downloaded climate observations for %s points; raw data: %s",
            len(observations),
            Path(settings.paths.data_dir) / "raw_observations.parquet",
        )

    elif args.command == "process":
        pipeline = container.build_atlas_pipeline(use_fake=use_fake)
        processor = build_processor(args.workers)
        observations = pipeline.download(points)
        indicators_df = pipeline.process(observations, processor)
        logger.info(
            "Processed data for %s points; indicators: %s",
            len(indicators_df),
            Path(settings.paths.data_dir) / "indicators.parquet",
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

    return 0


def _add_hpc_arguments(parser):
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source", choices=("fake", "nasa"), default="fake")
    parser.add_argument("--points", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--results-dir", default=None)
    parser.add_argument("--scheduler", choices=("processes", "threads"), default="processes")


def _add_aws_arguments(parser):
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--points", type=int, default=None)
    parser.add_argument("--start-date", default=None, help="Inclusive date, YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="Inclusive date, YYYY-MM-DD")
    parser.add_argument("--target-gib", type=float, default=5.0)
    parser.add_argument("--size-basis", choices=("logical", "disk"), default="logical")
    parser.add_argument("--staging-root", default=None)


def _run_aws_command(args, settings, container):
    experiment_id = _safe_experiment_id(args.experiment_id)
    point_count = args.points or settings.grid.sample_size
    points = SampleGridProvider(
        size=max(settings.grid.size, point_count),
        enable_sampling=True,
        sample_size=point_count,
    ).generate()
    staging_root = Path(args.staging_root or settings.paths.aws_staging_dir).resolve()
    staging_dir = staging_root / experiment_id
    start_date = args.start_date or f"{settings.date_range.start_year}-01-01"
    end_date = args.end_date or f"{settings.date_range.end_year}-12-31"

    if args.command == "aws-stage" or args.download:
        manifest = NasaPowerAwsStager().stage(
            points=points,
            output_dir=staging_dir,
            start_date=start_date,
            end_date=end_date,
            target_gib=args.target_gib,
            size_basis=args.size_basis,
        )
        logger.info(
            "AWS staging completed: %s rows, %.3f GiB logical, %.3f GiB on disk",
            manifest["row_count"],
            manifest["logical_uncompressed_gib"],
            manifest["disk_gib"],
        )

    if args.command == "aws-stage":
        return 0

    if not (staging_dir / "manifest.json").exists():
        raise FileNotFoundError(
            f"No staged dataset found at {staging_dir}; run aws-stage or use --download"
        )

    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")
    worker_counts = _worker_counts(args.workers, [1])
    experiment_dir = Path(args.results_dir or settings.paths.results_dir).resolve() / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    staging_manifest = json.loads((staging_dir / "manifest.json").read_text(encoding="utf-8"))
    if staging_manifest.get("status") != "success":
        raise RuntimeError(
            "AWS staging did not reach the requested size; inspect its manifest "
            "and use a wider date range or a smaller target"
        )
    rows = []
    for workers in worker_counts:
        for repeat in range(1, args.repeats + 1):
            rows.append(
                _execute_aws_run(
                    staging_dir=staging_dir,
                    staging_manifest=staging_manifest,
                    experiment_dir=experiment_dir,
                    workers=workers,
                    repeat=repeat,
                    scheduler=args.scheduler,
                    settings=settings,
                    container=container,
                )
            )

    rows = _add_scaling_metrics(rows)
    pd.DataFrame(rows).to_csv(experiment_dir / "summary.csv", index=False)
    logger.info("Streamlit-compatible AWS experiment completed: %s", experiment_dir)
    return 0


def _execute_aws_run(
    staging_dir,
    staging_manifest,
    experiment_dir,
    workers,
    repeat,
    scheduler,
    settings,
    container,
):
    run_dir = experiment_dir / f"workers-{workers:03d}" / f"run-{repeat:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    memory_sampler = ProcessTreeMemorySampler()
    memory_sampler.start()
    started = time.perf_counter()
    status = "failed"
    error = None
    point_count = int(staging_manifest["point_count"])
    pipeline = container.build_atlas_pipeline(use_fake=False)

    try:
        indicators = NasaPowerAwsProcessor().process(
            staging_dir,
            workers=workers,
            scheduler=scheduler,
        )
        labels, profiles = pipeline.cluster(indicators)
        _validate_hpc_result(indicators, labels, point_count)
        dashboard_indicators = indicators.copy()
        dashboard_indicators["cluster_id"] = labels
        dashboard_indicators.to_parquet(run_dir / "indicators.parquet", index=False)
        (run_dir / "cluster_profiles.json").write_text(
            json.dumps([asdict(profile) for profile in profiles], indent=2),
            encoding="utf-8",
        )
        status = "success"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("AWS processing run failed")

    elapsed = time.perf_counter() - started
    peak_memory_mb = memory_sampler.stop()
    quality_report = pipeline.clustering_service.last_quality_report
    manifest = {
        "status": status,
        "error": error,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory_mb,
        "memory_scope": (
            "process_tree" if memory_sampler.includes_children else "coordinator_only"
        ),
        "source": "nasa-aws",
        "point_count": point_count,
        "workers": workers,
        "scheduler": scheduler,
        "repeat": repeat,
        "aws_staging": staging_manifest,
        "git_commit": _git_commit(),
        "hostname": socket.gethostname(),
        "slurm_job_id": os.getenv("SLURM_JOB_ID"),
        "python": sys.version,
        "platform": platform.platform(),
        "settings": settings.snapshot(),
        "clustering_quality": asdict(quality_report) if quality_report else None,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if status == "failed":
        raise RuntimeError(f"AWS experiment failed; inspect {run_dir / 'manifest.json'}")
    return {
        "status": status,
        "workers": workers,
        "repeat": repeat,
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory_mb,
        "point_count": point_count,
        "run_dir": str(run_dir),
        "error": error,
    }


def _run_hpc_command(args, settings, container):
    _validate_hpc_args(args, settings)
    experiment_id = _safe_experiment_id(args.experiment_id)
    point_count = args.points or settings.grid.sample_size
    points = SampleGridProvider(
        size=max(settings.grid.size, point_count),
        enable_sampling=True,
        sample_size=point_count,
    ).generate()
    experiment_dir = Path(args.results_dir or settings.paths.results_dir).resolve() / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)

    pipeline = container.build_atlas_pipeline(use_fake=args.source == "fake")
    logger.info("Preparing one input with %s points", len(points))
    observations = pipeline.download(points, persist=False)
    worker_counts = (
        [args.workers]
        if args.command == "hpc-run"
        else _worker_counts(args.workers, settings.benchmark.worker_counts)
    )

    rows = []
    for workers in worker_counts:
        processor = (
            container.build_sequential_processor()
            if workers == 1
            else container.build_dask_processor(num_workers=workers, scheduler=args.scheduler)
        )
        for repeat in range(1, args.repeats + 1):
            rows.append(
                _execute_hpc_run(
                    pipeline,
                    observations,
                    points,
                    processor,
                    workers,
                    repeat,
                    args,
                    settings,
                    experiment_dir,
                )
            )

    summary_name = (
        f"summary-workers-{args.workers:03d}.csv" if args.command == "hpc-run" else "summary.csv"
    )
    rows = _add_scaling_metrics(rows)
    pd.DataFrame(rows).to_csv(experiment_dir / summary_name, index=False)
    logger.info("Experiment completed: %s", experiment_dir)
    return 0


def _execute_hpc_run(
    pipeline,
    observations,
    points,
    processor,
    workers,
    repeat,
    args,
    settings,
    experiment_dir,
):
    run_dir = experiment_dir / f"workers-{workers:03d}" / f"run-{repeat:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    memory_sampler = ProcessTreeMemorySampler()
    memory_sampler.start()
    started = time.perf_counter()
    status = "failed"
    error = None
    try:
        indicators, labels, profiles = pipeline.run_from_observations(
            observations, processor, persist=False
        )
        _validate_hpc_result(indicators, labels, len(points))
        indicators = indicators.copy()
        indicators["cluster_id"] = labels
        indicators.to_parquet(run_dir / "indicators.parquet", index=False)
        (run_dir / "cluster_profiles.json").write_text(
            json.dumps([asdict(profile) for profile in profiles], indent=2),
            encoding="utf-8",
        )
        status = "success"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.exception("HPC pipeline run failed")

    elapsed = time.perf_counter() - started
    peak_memory_mb = memory_sampler.stop()
    quality_report = pipeline.clustering_service.last_quality_report
    manifest = {
        "status": status,
        "error": error,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory_mb,
        "memory_scope": (
            "process_tree" if memory_sampler.includes_children else "coordinator_only"
        ),
        "source": args.source,
        "point_count": len(points),
        "download": pipeline.last_download_report,
        "workers": workers,
        "scheduler": "sequential" if workers == 1 else args.scheduler,
        "repeat": repeat,
        "input_checksum": _points_checksum(points),
        "git_commit": _git_commit(),
        "hostname": socket.gethostname(),
        "slurm_job_id": os.getenv("SLURM_JOB_ID"),
        "python": sys.version,
        "platform": platform.platform(),
        "settings": settings.snapshot(),
        "clustering_quality": asdict(quality_report) if quality_report else None,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if status == "failed":
        raise RuntimeError(f"Experiment failed; inspect {run_dir / 'manifest.json'}")
    return {
        "status": status,
        "workers": workers,
        "repeat": repeat,
        "elapsed_seconds": elapsed,
        "peak_memory_mb": peak_memory_mb,
        "point_count": len(points),
        "run_dir": str(run_dir),
        "error": error,
    }


def _validate_hpc_args(args, settings):
    point_count = args.points or settings.grid.sample_size
    minimum_points = (
        settings.clustering.min_clusters + 1
        if settings.clustering.auto_select
        else settings.clustering.n_clusters
    )
    if point_count < minimum_points:
        raise ValueError(f"--points must be at least {minimum_points} for clustering")
    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1")
    if args.command == "hpc-run" and args.workers < 1:
        raise ValueError("--workers must be at least 1")


def _validate_hpc_result(indicators, labels, expected_rows):
    if len(indicators) != expected_rows or len(labels) != expected_rows:
        raise RuntimeError("Pipeline returned an incomplete result")
    identity_columns = ["point_id", "latitude", "longitude", "country"]
    if indicators[identity_columns].isnull().any().any():
        raise RuntimeError("Pipeline result contains missing identity values")


def _add_scaling_metrics(rows):
    baseline_times = [
        row["elapsed_seconds"]
        for row in rows
        if row["status"] == "success" and row["workers"] == 1
    ]
    baseline = sum(baseline_times) / len(baseline_times) if baseline_times else None
    for row in rows:
        row["baseline_seconds"] = baseline
        if baseline is None or row["status"] != "success":
            row["speedup"] = None
            row["efficiency_percent"] = None
            continue
        speedup = compute_speedup(baseline, row["elapsed_seconds"])
        row["speedup"] = speedup
        row["efficiency_percent"] = compute_efficiency(speedup, row["workers"])
    return rows


def _worker_counts(raw, defaults):
    values = defaults if raw is None else [int(value.strip()) for value in raw.split(",")]
    if not values or any(value < 1 for value in values):
        raise ValueError("Worker counts must be positive integers")
    return list(dict.fromkeys(values))


def _safe_experiment_id(value):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not value or any(character not in allowed for character in value):
        raise ValueError("Experiment id may contain only letters, numbers, '-' and '_'")
    return value


def _points_checksum(points):
    payload = "\n".join(
        f"{point.latitude:.8f},{point.longitude:.8f},{point.country}" for point in points
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


if __name__ == "__main__":
    main()
