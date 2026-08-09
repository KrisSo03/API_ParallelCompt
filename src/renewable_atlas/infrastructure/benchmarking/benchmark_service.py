import time

from renewable_atlas.domain import BenchmarkResult, ExecutionMode, ProcessingStrategy

from .metrics import ProcessTreeMemorySampler, compute_efficiency, compute_speedup


class BenchmarkService:
    def run(
        self,
        strategies: list[ProcessingStrategy],
        items: list,
        task,
        repeats: int = 3,
    ) -> list[BenchmarkResult]:
        measurements = []

        for strategy in strategies:
            for _ in range(repeats):
                memory_sampler = ProcessTreeMemorySampler()
                memory_sampler.start()
                start_time = time.perf_counter()

                try:
                    strategy.process(items, task)
                finally:
                    peak_memory_mb = memory_sampler.stop()

                elapsed = time.perf_counter() - start_time
                measurements.append((strategy.worker_count, elapsed, peak_memory_mb))

        baseline_times = [elapsed for workers, elapsed, _ in measurements if workers == 1]
        baseline_time = sum(baseline_times) / len(baseline_times) if baseline_times else None
        results = []
        for workers, elapsed, peak_memory_mb in measurements:
            mode = ExecutionMode.SEQUENTIAL if workers == 1 else ExecutionMode.DASK
            speedup = compute_speedup(baseline_time, elapsed) if baseline_time is not None else None
            efficiency = compute_efficiency(speedup, workers) if speedup is not None else None

            results.append(
                BenchmarkResult(
                    mode=mode,
                    worker_count=workers,
                    execution_time_seconds=elapsed,
                    memory_usage_mb=peak_memory_mb,
                    speedup=speedup,
                    efficiency=efficiency,
                )
            )

        return results
