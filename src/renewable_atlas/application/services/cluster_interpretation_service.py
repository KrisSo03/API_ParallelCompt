import numpy as np
from renewable_atlas.domain import ClusterProfile


class ClusterInterpretationService:
    def interpret(self, profiles: list[ClusterProfile]) -> list[ClusterProfile]:
        for profile in profiles:
            centroid = profile.centroid
            sw_dwn = centroid.get("sw_dwn_mean", 0)
            ws_100m = centroid.get("ws_100m_mean", 0)

            solar_potential = sw_dwn
            wind_potential = ws_100m

            if solar_potential > wind_potential * 1.5:
                label = "Solar-dominant"
                description = "High solar potential, suitable for photovoltaic systems"
            elif wind_potential > solar_potential * 1.5:
                label = "Wind-dominant"
                description = "High wind potential, suitable for wind turbines"
            elif solar_potential > 150 and wind_potential > 5:
                label = "Hybrid-high"
                description = "Strong hybrid potential for solar-wind integration"
            else:
                label = "Lower-resource"
                description = "Moderate renewable energy potential"

            profile.label = label
            profile.description = description

        return profiles
