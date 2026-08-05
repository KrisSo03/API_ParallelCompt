import numpy as np
from renewable_atlas.domain import ClusterProfile


class ClusterInterpretationService:
    """Etiqueta cada cluster segun su potencial solar/eolico RELATIVO a
    los demas clusters obtenidos en la misma corrida, en vez de comparar
    contra umbrales absolutos fijos (ej. "> 150", "> 5") que no se ajustan
    a la escala real de los datos y que ademas ignoraban 2 de las 4
    variables climaticas disponibles.

    Logica (ver ADR-002 en docs/decisions/):
      1. Para cada cluster se arma un indice compuesto de "potencial solar"
         combinando sw_dwn_mean y dni_mean, y un indice de "potencial
         eolico" combinando ws_50m_mean y ws_100m_mean. Cada variable se
         normaliza a z-score ANTES de combinarse, para que variables con
         unidades distintas (W/m2 vs m/s) pesen de forma comparable.
      2. Esos indices se convierten a percentiles relativos (0 = el
         cluster con menor potencial de ese tipo, 1 = el de mayor) dentro
         del conjunto de clusters evaluado.
      3. Se clasifica cada cluster segun si su percentil solar y eolico
         estan por encima o por debajo de la mediana (0.5), lo que arma
         un "cuadrante" de 4 categorias, exactamente las que pide el
         proyecto: Solar-dominant, Wind-dominant, Hybrid-high,
         Lower-resource.
      4. Se calcula un "confidence" (0 a 1): que tan lejos esta el cluster
         del punto de corte (mediana) en ambas dimensiones. Un cluster con
         percentiles cercanos a 0.5 en ambas variables es una clasificacion
         menos "limpia" que uno en los extremos.
    """

    SOLAR_VARIABLES = ("sw_dwn_mean", "dni_mean")
    WIND_VARIABLES = ("ws_50m_mean", "ws_100m_mean")

    MEDIAN_PERCENTILE = 0.5

    def interpret(self, profiles: list[ClusterProfile]) -> list[ClusterProfile]:
        if not profiles:
            return profiles

        solar_index = self._composite_index(profiles, self.SOLAR_VARIABLES)
        wind_index = self._composite_index(profiles, self.WIND_VARIABLES)

        solar_percentiles = self._percentile_ranks(solar_index)
        wind_percentiles = self._percentile_ranks(wind_index)

        for profile in profiles:
            cid = profile.cluster_id
            solar_pct = solar_percentiles[cid]
            wind_pct = wind_percentiles[cid]

            label, description = self._classify(solar_pct, wind_pct, profile)

            profile.label = label
            profile.description = description
            profile.solar_percentile = solar_pct
            profile.wind_percentile = wind_pct
            profile.confidence = self._confidence(solar_pct, wind_pct)

        return profiles

    def _composite_index(
        self, profiles: list[ClusterProfile], variable_names: tuple[str, ...]
    ) -> dict[int, float]:
        """Combina 1 o mas variables en un solo indice por cluster.
        Cada variable se normaliza a z-score entre los clusters antes de
        promediar, para no mezclar escalas distintas directamente."""
        z_scored_variables = []
        for var in variable_names:
            values = np.array(
                [profile.centroid.get(var, np.nan) for profile in profiles], dtype=float
            )
            if np.all(np.isnan(values)):
                continue
            mean = np.nanmean(values)
            std = np.nanstd(values)
            z = (values - mean) / std if std > 1e-9 else np.zeros_like(values)
            z_scored_variables.append(np.nan_to_num(z, nan=0.0))

        if not z_scored_variables:
            return {profile.cluster_id: 0.0 for profile in profiles}

        composite = np.mean(z_scored_variables, axis=0)
        return {
            profile.cluster_id: float(value) for profile, value in zip(profiles, composite)
        }

    def _percentile_ranks(self, index_by_cluster: dict[int, float]) -> dict[int, float]:
        """Convierte valores absolutos del indice compuesto a un percentil
        relativo (0 = minimo, 1 = maximo) entre los clusters evaluados.
        Con un solo cluster, no hay nada que comparar: se asigna 0.5."""
        cluster_ids = list(index_by_cluster.keys())
        values = np.array([index_by_cluster[cid] for cid in cluster_ids])
        n = len(values)

        if n <= 1:
            return {cid: 0.5 for cid in cluster_ids}

        order = values.argsort()
        ranks = np.empty(n)
        ranks[order] = np.arange(n)
        percentiles = ranks / (n - 1)
        return {cid: float(pct) for cid, pct in zip(cluster_ids, percentiles)}

    def _classify(
        self, solar_pct: float, wind_pct: float, profile: ClusterProfile
    ) -> tuple[str, str]:
        solar_above_median = solar_pct >= self.MEDIAN_PERCENTILE
        wind_above_median = wind_pct >= self.MEDIAN_PERCENTILE

        if solar_above_median and wind_above_median:
            label = "Hybrid-high"
            summary = "potencial hibrido: solar y eolico ambos por encima de la mediana"
        elif solar_above_median and not wind_above_median:
            label = "Solar-dominant"
            summary = "potencial predominantemente solar"
        elif wind_above_median and not solar_above_median:
            label = "Wind-dominant"
            summary = "potencial predominantemente eolico"
        else:
            label = "Lower-resource"
            summary = "potencial bajo relativo a los demas clusters"

        description = (
            f"{summary.capitalize()} ({profile.size} puntos). "
            f"Percentil solar: {solar_pct:.0%}, percentil eolico: {wind_pct:.0%} "
            f"respecto a los demas clusters de esta corrida."
        )

        dominant_country = self._dominant_country(profile)
        if dominant_country is not None:
            country_name, country_pct = dominant_country
            description += (
                f" Pais dominante: {country_name} ({country_pct:.0%} de los puntos "
                f"de este cluster)."
            )

        return label, description

    def _dominant_country(self, profile: ClusterProfile) -> tuple[str, float] | None:
        """Devuelve (pais, porcentaje) del pais con mas puntos en el
        cluster, o None si no hay desglose por pais disponible (Tarea D,
        se llena en ClusteringService)."""
        if not profile.country_breakdown:
            return None
        top_country, stats = next(iter(profile.country_breakdown.items()))
        return top_country, stats["percentage"]

    def _confidence(self, solar_pct: float, wind_pct: float) -> float:
        """Que tan lejos esta el cluster del punto de corte (mediana) en
        ambas dimensiones, normalizado a [0, 1]. 1 = clasificacion muy
        clara (extremos), 0 = justo en el limite entre categorias."""
        solar_distance = abs(solar_pct - self.MEDIAN_PERCENTILE) * 2
        wind_distance = abs(wind_pct - self.MEDIAN_PERCENTILE) * 2
        return float(min(1.0, (solar_distance + wind_distance) / 2))