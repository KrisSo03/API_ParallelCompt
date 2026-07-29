from dataclasses import dataclass, asdict


@dataclass
class RenewableIndicators:
    point_id: int
    latitude: float
    longitude: float
    country: str
    sw_dwn_mean: float
    dni_mean: float
    ws_50m_mean: float
    ws_100m_mean: float
    solar_score: float
    wind_score: float
    hybrid_score: float

    def as_feature_dict(self) -> dict:
        return {
            "sw_dwn_mean": self.sw_dwn_mean,
            "dni_mean": self.dni_mean,
            "ws_50m_mean": self.ws_50m_mean,
            "ws_100m_mean": self.ws_100m_mean,
        }
