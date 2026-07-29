from abc import ABC, abstractmethod
import pandas as pd


class DataRepository(ABC):
    @abstractmethod
    def save(self, data: pd.DataFrame, key: str) -> None:
        pass

    @abstractmethod
    def load(self, key: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def metadata(self, key: str) -> dict:
        pass
