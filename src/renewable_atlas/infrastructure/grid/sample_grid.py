import json
from functools import cached_property
from importlib.resources import files

from shapely.geometry import Point, shape

from renewable_atlas.domain import GridPoint


class SampleGridProvider:
    """Generate reproducible points located inside Central American countries."""

    COUNTRIES = (
        "Belize",
        "Guatemala",
        "El Salvador",
        "Honduras",
        "Nicaragua",
        "Costa Rica",
        "Panama",
    )
    GEOJSON_NAME = "central_america.geojson"

    def __init__(self, size: int = 20, enable_sampling: bool = True, sample_size: int = 10):
        self.size = size
        self.enable_sampling = enable_sampling
        self.sample_size = sample_size

    def generate(self, max_points: int | None = None) -> list[GridPoint]:
        requested = self.sample_size if self.enable_sampling else self.size
        if max_points is not None:
            requested = min(requested, max_points)
        if requested < 1:
            return []

        allocation = self._allocate_points(requested)
        points: list[GridPoint] = []
        for country_index, country in enumerate(self.COUNTRIES):
            points.extend(
                self._sample_country(
                    country,
                    allocation[country],
                    sequence_offset=country_index * 997,
                )
            )
        return points

    @cached_property
    def country_geometries(self) -> dict:
        resource = files(__package__).joinpath("data", self.GEOJSON_NAME)
        data = json.loads(resource.read_text(encoding="utf-8"))
        geometries = {
            feature["properties"]["country"]: shape(feature["geometry"])
            for feature in data["features"]
        }
        missing = set(self.COUNTRIES) - set(geometries)
        if missing:
            raise ValueError(f"Missing country geometries: {sorted(missing)}")
        return geometries

    def _allocate_points(self, total: int) -> dict[str, int]:
        base, remainder = divmod(total, len(self.COUNTRIES))
        return {
            country: base + (index < remainder)
            for index, country in enumerate(self.COUNTRIES)
        }

    def _sample_country(
        self,
        country: str,
        count: int,
        sequence_offset: int,
    ) -> list[GridPoint]:
        if count == 0:
            return []

        geometry = self.country_geometries[country]
        min_lon, min_lat, max_lon, max_lat = geometry.bounds
        selected: list[GridPoint] = []
        candidate_index = sequence_offset + 1
        max_attempts = max(10_000, count * 1_000)

        for _ in range(max_attempts):
            lon_fraction = self._radical_inverse(candidate_index, 2)
            lat_fraction = self._radical_inverse(candidate_index, 3)
            longitude = min_lon + lon_fraction * (max_lon - min_lon)
            latitude = min_lat + lat_fraction * (max_lat - min_lat)
            candidate_index += 1

            if geometry.covers(Point(longitude, latitude)):
                selected.append(
                    GridPoint(
                        latitude=float(latitude),
                        longitude=float(longitude),
                        country=country,
                    )
                )
                if len(selected) == count:
                    return selected

        raise RuntimeError(f"Could not generate {count} points inside {country}")

    @staticmethod
    def _radical_inverse(index: int, base: int) -> float:
        result = 0.0
        factor = 1.0 / base
        while index:
            index, digit = divmod(index, base)
            result += digit * factor
            factor /= base
        return result
