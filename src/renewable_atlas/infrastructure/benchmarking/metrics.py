import psutil
import os


def compute_speedup(baseline_time: float, parallel_time: float) -> float:
    if parallel_time == 0:
        return 0.0
    return baseline_time / parallel_time


def compute_efficiency(speedup: float, num_workers: int) -> float:
    if num_workers == 0:
        return 0.0
    return (speedup / num_workers) * 100


def current_process_memory_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)
