from dataclasses import dataclass, field


@dataclass
class ClusterProfile:
    cluster_id: int
    label: str
    description: str
    size: int
    centroid: dict
    confidence: float = 0.0
    solar_percentile: float = 0.5
    wind_percentile: float = 0.5
    country_breakdown: dict = field(default_factory=dict)