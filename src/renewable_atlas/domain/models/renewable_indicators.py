from dataclasses import dataclass


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
    ws_10m_mean: float = 0.0
    sw_diff_mean: float = 0.0
    clr_sky_sw_dwn_mean: float = 0.0
    allsky_kt_mean: float = 0.0
    wd_10m_mean: float = 0.0
    wd_50m_mean: float = 0.0
    t2m_mean: float = 0.0
    t2m_max_mean: float = 0.0
    t2m_min_mean: float = 0.0
    t2mdew_mean: float = 0.0
    ps_mean: float = 0.0
    rh2m_mean: float = 0.0
    qv2m_mean: float = 0.0
    prectotcorr_mean: float = 0.0
    cloud_amt_mean: float = 0.0

    def as_feature_dict(self) -> dict:
        return {
            "sw_dwn_mean": self.sw_dwn_mean,
            "dni_mean": self.dni_mean,
            "ws_50m_mean": self.ws_50m_mean,
            "ws_100m_mean": self.ws_100m_mean,
            "ws_10m_mean": self.ws_10m_mean,
            "sw_diff_mean": self.sw_diff_mean,
            "clr_sky_sw_dwn_mean": self.clr_sky_sw_dwn_mean,
            "allsky_kt_mean": self.allsky_kt_mean,
            "wd_10m_mean": self.wd_10m_mean,
            "wd_50m_mean": self.wd_50m_mean,
            "t2m_mean": self.t2m_mean,
            "t2m_max_mean": self.t2m_max_mean,
            "t2m_min_mean": self.t2m_min_mean,
            "t2mdew_mean": self.t2mdew_mean,
            "ps_mean": self.ps_mean,
            "rh2m_mean": self.rh2m_mean,
            "qv2m_mean": self.qv2m_mean,
            "prectotcorr_mean": self.prectotcorr_mean,
            "cloud_amt_mean": self.cloud_amt_mean,
        }
