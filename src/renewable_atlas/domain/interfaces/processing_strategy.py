from abc import ABC, abstractmethod
from typing import Any, Callable


class ProcessingStrategy(ABC):
    @property
    @abstractmethod
    def worker_count(self) -> int:
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        pass

    @abstractmethod
    def process(self, items: list, task: Callable) -> list:
        pass
