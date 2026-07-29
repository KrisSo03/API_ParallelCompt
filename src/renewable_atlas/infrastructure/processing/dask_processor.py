import dask
from dask import delayed
from renewable_atlas.domain import ProcessingStrategy


class DaskProcessor(ProcessingStrategy):
    def __init__(self, num_workers: int = 4, scheduler: str = "processes"):
        self._num_workers = num_workers
        self.scheduler = scheduler

    @property
    def worker_count(self) -> int:
        return self._num_workers

    @property
    def mode_name(self) -> str:
        return f"dask-{self.scheduler}"

    def process(self, items: list, task) -> list:
        delayed_tasks = [delayed(task)(item) for item in items]
        results = dask.compute(
            *delayed_tasks,
            scheduler=self.scheduler,
            num_workers=self._num_workers,
        )
        return list(results)
