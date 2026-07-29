import numpy as np
from renewable_atlas.domain import GridPoint


class SampleGridProvider:
    CENTRAL_AMERICA_POINTS = [
        (14.5, -92.0, "Guatemala"),
        (13.7, -88.9, "El Salvador"),
        (14.0, -87.2, "Honduras"),
        (15.2, -86.2, "Nicaragua"),
        (10.0, -84.3, "Costa Rica"),
        (8.5, -80.8, "Panama"),
        (17.0, -89.6, "Belize"),
    ]

    COUNTRY_BOUNDS = {
        "Guatemala": {"lat": (13.7, 17.8), "lon": (-92.2, -88.2)},
        "El Salvador": {"lat": (12.9, 14.5), "lon": (-90.1, -87.7)},
        "Honduras": {"lat": (12.9, 17.0), "lon": (-89.4, -83.0)},
        "Nicaragua": {"lat": (10.7, 15.5), "lon": (-87.6, -83.0)},
        "Costa Rica": {"lat": (8.0, 11.3), "lon": (-85.9, -82.6)},
        "Panama": {"lat": (7.2, 10.8), "lon": (-82.9, -77.0)},
        "Belize": {"lat": (15.5, 18.5), "lon": (-89.2, -87.5)},
    }

    def __init__(self, size: int = 20, enable_sampling: bool = True, sample_size: int = 10):
        self.size = size
        self.enable_sampling = enable_sampling
        self.sample_size = sample_size

    def generate(self) -> list[GridPoint]:
        points = self._generate_grid()
        if self.enable_sampling and len(points) > self.sample_size:
            points = self._evenly_spaced_subset(points, self.sample_size)
        return points

    def _generate_grid(self) -> list[GridPoint]:
        points = []
        for country, bounds in self.COUNTRY_BOUNDS.items():
            lat_range = bounds["lat"]
            lon_range = bounds["lon"]

            lat_points = np.linspace(lat_range[0], lat_range[1], self.size // 7 + 1)
            lon_points = np.linspace(lon_range[0], lon_range[1], self.size // 7 + 1)

            for lat in lat_points:
                for lon in lon_points:
                    points.append(GridPoint(latitude=float(lat), longitude=float(lon), country=country))

        return points

    def _evenly_spaced_subset(self, points: list[GridPoint], n: int) -> list[GridPoint]:
        if len(points) <= n:
            return points

        indices = np.linspace(0, len(points) - 1, n, dtype=int)
        return [points[i] for i in indices]
