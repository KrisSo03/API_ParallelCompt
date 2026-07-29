from abc import ABC, abstractmethod
import numpy as np


class ClusteringStrategy(ABC):
    @abstractmethod
    def fit_predict(self, features: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def centroids(self) -> np.ndarray:
        pass
