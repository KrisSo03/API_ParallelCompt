from dataclasses import dataclass
from enum import Enum


class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    DASK = "dask"


@dataclass
class BenchmarkResult:
    mode: ExecutionMode
    worker_count: int
    execution_time_seconds: float
    memory_usage_mb: float
    speedup: float | None = None
    efficiency: float | None = None

    def __post_init__(self) -> None:
        if self.worker_count < 1:
            raise ValueError("worker_count must be >= 1")
        if self.execution_time_seconds < 0:
            raise ValueError("execution_time_seconds must be >= 0")
        if self.memory_usage_mb < 0:
            raise ValueError("memory_usage_mb must be >= 0")
