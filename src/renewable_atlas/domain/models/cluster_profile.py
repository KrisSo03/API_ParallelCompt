from dataclasses import dataclass


@dataclass
class ClusterProfile:
    cluster_id: int
    label: str
    description: str
    size: int
    centroid: dict
