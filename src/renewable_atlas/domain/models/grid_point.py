from dataclasses import dataclass


@dataclass
class GridPoint:
    latitude: float
    longitude: float
    country: str

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
        if not isinstance(self.country, str) or len(self.country) < 2:
            raise ValueError(f"Country must be a valid string, got {self.country}")
