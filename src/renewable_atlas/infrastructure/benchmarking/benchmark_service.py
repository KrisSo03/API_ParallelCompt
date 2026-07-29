import time
from renewable_atlas.domain import BenchmarkResult, ExecutionMode, ProcessingStrategy
from .metrics import compute_speedup, compute_efficiency, current_process_memory_mb


class BenchmarkService:
    def run(
        self,
        strategies: list[ProcessingStrategy],
        items: list,
        task,
        repeats: int = 3,
    ) -> list[BenchmarkResult]:
        results = []
        baseline_time: float | None = None

        for strategy in strategies:
            for _ in range(repeats):
                start_mem = current_process_memory_mb()
                start_time = time.time()

                strategy.process(items, task)

                elapsed = time.time() - start_time
                end_mem = current_process_memory_mb()
                memory_delta = max(0, end_mem - start_mem)

                mode = ExecutionMode.SEQUENTIAL if strategy.worker_count == 1 else ExecutionMode.DASK

                speedup = None
                efficiency = None

                if baseline_time is not None:
                    speedup = compute_speedup(baseline_time, elapsed)
                    efficiency = compute_efficiency(speedup, strategy.worker_count)

                if strategy.worker_count == 1:
                    baseline_time = elapsed

                result = BenchmarkResult(
                    mode=mode,
                    worker_count=strategy.worker_count,
                    execution_time_seconds=elapsed,
                    memory_usage_mb=memory_delta,
                    speedup=speedup,
                    efficiency=efficiency,
                )
                results.append(result)

        return results
