from renewable_atlas.domain import ProcessingStrategy


class SequentialProcessor(ProcessingStrategy):
    @property
    def worker_count(self) -> int:
        return 1

    @property
    def mode_name(self) -> str:
        return "sequential"

    def process(self, items: list, task) -> list:
        return [task(item) for item in items]
