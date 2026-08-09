import os
import threading

import psutil


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


class ProcessTreeMemorySampler:
    """Sample the combined RSS of the coordinator and its worker processes."""

    def __init__(self, interval_seconds: float = 0.05):
        self.interval_seconds = interval_seconds
        self.peak_memory_mb = 0.0
        self.includes_children = True
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._sample()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> float:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 4))
        self._sample()
        return self.peak_memory_mb

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self._sample()

    def _sample(self) -> None:
        try:
            process = psutil.Process(os.getpid())
            rss = process.memory_info().rss
            try:
                children = process.children(recursive=True)
            except (psutil.AccessDenied, PermissionError):
                self.includes_children = False
                children = []
            for child in children:
                try:
                    rss += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            self.peak_memory_mb = max(self.peak_memory_mb, rss / (1024 * 1024))
        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            return
