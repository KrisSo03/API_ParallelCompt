from abc import ABC, abstractmethod
from renewable_atlas.domain.models import GridPoint, ClimateObservation


class ClimateDataSource(ABC):
    @abstractmethod
    def fetch_observations(self, point: GridPoint) -> list[ClimateObservation]:
        pass
