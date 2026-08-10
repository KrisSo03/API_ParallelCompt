"""Streamlit entry point for the Renewable Energy Atlas dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.charts import (
    country_comparison_chart,
    davies_bouldin_quality_chart,
    efficiency_chart,
    memory_chart,
    profile_distribution,
    renewable_map,
    scalability_preview,
    silhouette_quality_chart,
    speedup_chart,
)
from dashboard.config import (
    APP_TITLE,
    CLUSTER_LABELS,
    METRICS,
    discover_experiments,
    results_root,
)
from dashboard.data_loader import discover_runs, discover_worker_counts, load_run, load_summary
from dashboard.metrics import (
    country_comparison,
    enrich_indicators,
    overview_metrics,
    performance_summary,
)
from dashboard.styles import APP_CSS
from dashboard.validators import DashboardDataError


ALL_COUNTRIES = "Todos los países"
ALL_PROFILES = "Todos los perfiles"


def _reset_atlas_filters() -> None:
    st.session_state.atlas_country = ALL_COUNTRIES
    st.session_state.atlas_profile = ALL_PROFILES


def _best_point(data: pd.DataFrame, metric: str) -> pd.Series:
    return data.loc[data[metric].idxmax()]


st.set_page_config(page_title=APP_TITLE, page_icon="🌎", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)

root = results_root()
experiments = discover_experiments(root)
selected_name = None
selected_path = None
selected_run = None

with st.sidebar:
    st.title("🌿 Atlas renovable")
    st.caption("Selecciona el experimento que deseas consultar")
    st.divider()
    if experiments:
        selected_name = st.selectbox("Experimento", [path.name for path in experiments])
        selected_path = root / selected_name
        workers = discover_worker_counts(selected_path)
        if workers:
            for worker_count in workers:
                runs = discover_runs(selected_path, worker_count)
                if runs:
                    selected_run = runs[0]
                    break
        else:
            st.warning("El experimento no contiene configuraciones de procesamiento.")
    else:
        st.warning("No hay experimentos disponibles.")

if not selected_name or selected_path is None or selected_run is None:
    st.info("Ejecuta o selecciona una corrida completa para abrir el dashboard.")
    st.stop()

try:
    run_data = load_run(selected_run)
    summary = load_summary(selected_path)
except DashboardDataError as error:
    st.error(str(error))
    st.stop()

manifest = run_data.manifest
indicators = enrich_indicators(run_data.indicators, run_data.profiles)
source = str(manifest.get("source", "desconocida")).upper()
source_label = "Datos simulados" if source == "FAKE" else f"Fuente {source}"
run_label = selected_name

st.markdown(
    f"""
    <section class="atlas-hero">
      <h1>Atlas de energía renovable</h1>
      <p>Explora dónde existe mayor potencial solar, eólico e híbrido en Centroamérica.</p>
      <div class="atlas-run">Resultados consultados: {run_label}</div>
      <span class="atlas-status">● Corrida completa · {source_label}</span>
    </section>
    """,
    unsafe_allow_html=True,
)

summary_tab, atlas_tab, comparison_tab, quality_tab, performance_tab = st.tabs(
    ["Resumen general", "Atlas interactivo", "Comparación", "Calidad y metodología", "Rendimiento"]
)

with summary_tab:
    st.header("¿Qué encontró el análisis?")
    solar = overview_metrics(indicators, "solar_score")
    wind = overview_metrics(indicators, "wind_score")
    hybrid = overview_metrics(indicators, "hybrid_score")

    cards = st.columns(5)
    cards[0].metric("Puntos analizados", len(indicators), delta=f"{indicators['country'].nunique()} países", delta_color="off")
    cards[1].metric("Índice solar relativo", f"{solar.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
    cards[2].metric("Índice eólico relativo", f"{wind.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
    cards[3].metric("Índice híbrido relativo", f"{hybrid.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
    most_common = indicators["cluster_label"].mode().iloc[0]
    cards[4].metric("Perfil más frecuente", CLUSTER_LABELS.get(most_common, most_common), delta="clasificación energética", delta_color="off")

    distribution_col, findings_col = st.columns([1, 1.15], vertical_alignment="top")
    with distribution_col:
        st.subheader("Distribución de perfiles")
        st.caption("Los clusters numéricos con la misma interpretación se presentan como un solo perfil.")
        st.plotly_chart(profile_distribution(indicators), width="stretch")
    with findings_col:
        st.subheader("Resultados destacados")
        for metric, label in (
            ("solar_score", "Mayor potencial solar"),
            ("wind_score", "Mayor potencial eólico"),
            ("hybrid_score", "Mejor equilibrio híbrido"),
        ):
            point = _best_point(indicators, metric)
            with st.container(border=True):
                st.markdown(f"**{label}: {point['country']} · Punto {int(point['point_id'])}**")
                st.write(f"{float(point[metric]):.1%} de índice relativo")
                st.caption(f"Perfil regional: {CLUSTER_LABELS.get(point['cluster_label'], point['cluster_label'])}")

with atlas_tab:
    st.header("¿Dónde están los puntos con mayor potencial?")
    st.caption("Los controles de esta sección afectan únicamente el mapa, sus indicadores y su tabla.")

    country_options = [ALL_COUNTRIES, *sorted(indicators["country"].astype(str).unique())]
    profile_values = sorted(indicators["cluster_label"].astype(str).unique())
    profile_options = [ALL_PROFILES, *profile_values]
    if st.session_state.get("atlas_country") not in country_options:
        st.session_state.atlas_country = ALL_COUNTRIES
    if st.session_state.get("atlas_profile") not in profile_options:
        st.session_state.atlas_profile = ALL_PROFILES

    filters = st.columns([1, 1, 0.45, 2], vertical_alignment="bottom")
    with filters[0]:
        country = st.selectbox("País", country_options, key="atlas_country")
    with filters[1]:
        profile = st.selectbox(
            "Tipo de potencial",
            profile_options,
            format_func=lambda value: ALL_PROFILES if value == ALL_PROFILES else CLUSTER_LABELS.get(value, value),
            key="atlas_profile",
        )
    with filters[2]:
        st.button("Limpiar", on_click=_reset_atlas_filters, width="stretch")
    with filters[3]:
        st.caption("El color identifica el perfil energético de cada punto.")

    filtered = indicators.copy()
    if country != ALL_COUNTRIES:
        filtered = filtered[filtered["country"] == country]
    if profile != ALL_PROFILES:
        filtered = filtered[filtered["cluster_label"] == profile]

    if filtered.empty:
        st.warning("No existen puntos que cumplan los filtros seleccionados.")
    else:
        cards = st.columns(4)
        cards[0].metric("Puntos visibles", len(filtered), delta=f"de {len(indicators)} totales", delta_color="off")
        cards[1].metric("Índice solar visible", f"{filtered['solar_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")
        cards[2].metric("Índice eólico visible", f"{filtered['wind_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")
        cards[3].metric("Índice híbrido visible", f"{filtered['hybrid_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")

        st.caption(
            "El color representa el perfil. El porcentaje de cada punto corresponde a su perfil: "
            "solar, eólico o híbrido. Los porcentajes son índices relativos a los puntos del experimento."
        )
        st.plotly_chart(renewable_map(filtered), width="stretch")

        st.subheader("Puntos incluidos en la selección")
        ranking = filtered.sort_values("hybrid_score", ascending=False).copy()
        ranking["Ubicación"] = ranking.apply(lambda row: f"{row['country']} · Punto {int(row['point_id'])}", axis=1)
        ranking["Perfil regional"] = ranking["cluster_label"].map(CLUSTER_LABELS).fillna(ranking["cluster_label"])
        for column in ("solar_score", "wind_score", "hybrid_score"):
            ranking[column] *= 100
        st.dataframe(
            ranking[["Ubicación", "Perfil regional", "solar_score", "wind_score", "hybrid_score"]],
            width="stretch",
            hide_index=True,
            column_config={
                "solar_score": st.column_config.NumberColumn("Índice solar relativo", format="%.1f%%"),
                "wind_score": st.column_config.NumberColumn("Índice eólico relativo", format="%.1f%%"),
                "hybrid_score": st.column_config.NumberColumn("Índice híbrido relativo", format="%.1f%%"),
            },
        )

with comparison_tab:
    st.header("¿Cómo se comparan los países?")
    st.caption("Compara índices relativos promedio; no representan porcentajes absolutos de energía disponible.")
    countries = sorted(indicators["country"].astype(str).unique())
    defaults = countries[: min(2, len(countries))]
    selected_countries = st.multiselect(
        "Países a comparar",
        countries,
        default=defaults,
        max_selections=3,
        help="Selecciona entre dos y tres países.",
    )
    if len(selected_countries) < 2:
        st.info("Selecciona al menos dos países para realizar la comparación.")
    else:
        comparison = country_comparison(indicators, selected_countries)
        st.plotly_chart(country_comparison_chart(comparison), width="stretch")
        table = comparison.rename(
            columns={"country": "País", "solar_score": "Solar", "wind_score": "Eólico", "hybrid_score": "Híbrido"}
        )
        for column in ("Solar", "Eólico", "Híbrido"):
            table[column] *= 100
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={column: st.column_config.NumberColumn(column, format="%.1f%%") for column in ("Solar", "Eólico", "Híbrido")},
        )

with quality_tab:
    st.header("¿Qué tan confiables son los grupos encontrados?")
    quality = manifest.get("clustering_quality")
    if not quality:
        st.info("Este experimento no contiene métricas de calidad del clustering.")
    else:
        recommended_k = int(quality["recommended_k"])
        silhouette = float(quality["silhouette_at_recommended"])
        silhouette_threshold = float(quality["silhouette_threshold"])
        davies_bouldin = float(quality["davies_bouldin_at_recommended"])
        davies_threshold = float(quality["davies_bouldin_threshold"])
        stability = quality.get("stability_ari_mean")
        stability_threshold = float(quality.get("stability_ari_threshold", 0.95))

        cards = st.columns(4)
        cards[0].metric(
            "Mejor K observado",
            recommended_k,
            delta="mayor separación encontrada",
            delta_color="off",
        )
        cards[1].metric(
            "Separación de grupos",
            f"{silhouette:.3f}",
            delta="Cumple el objetivo" if silhouette >= silhouette_threshold else f"Objetivo: {silhouette_threshold:.2f}",
            delta_color="off",
        )
        cards[2].metric(
            "Compactación de grupos",
            f"{davies_bouldin:.3f}",
            delta="Dentro del límite" if davies_bouldin < davies_threshold else f"Máximo: {davies_threshold:.2f}",
            delta_color="off",
        )
        cards[3].metric(
            "Estabilidad",
            f"{float(stability):.3f}" if stability is not None else "No evaluada",
            delta=f"Objetivo: {stability_threshold:.2f}" if stability is not None else "Requiere varias semillas",
            delta_color="off",
        )

        silhouette_column, davies_column = st.columns(2)
        with silhouette_column:
            st.subheader("Separación por cantidad de clusters")
            st.caption("Silhouette: valores más altos representan grupos mejor separados.")
            st.plotly_chart(silhouette_quality_chart(quality), width="stretch")
        with davies_column:
            st.subheader("Dispersión por cantidad de clusters")
            st.caption("Davies–Bouldin: valores más bajos representan grupos más compactos.")
            st.plotly_chart(davies_bouldin_quality_chart(quality), width="stretch")

        with st.expander("Cómo interpretar estas métricas"):
            st.markdown(
                """
                - **Mejor K observado:** cantidad de clusters que obtuvo la mayor separación entre las alternativas evaluadas. No implica por sí sola que cumpla el objetivo de calidad.
                - **Silhouette:** varía aproximadamente entre -1 y 1; un valor mayor indica mejor separación.
                - **Davies–Bouldin:** empieza en 0; un valor menor indica grupos más compactos y diferenciados.
                - **Estabilidad ARI:** comprueba si el resultado se mantiene al repetir K-Means con distintas semillas.
                """
            )

        st.subheader("Cómo se construyen estos resultados")
        source_description = (
            "datos climáticos simulados para pruebas"
            if source == "FAKE"
            else "observaciones climáticas obtenidas de NASA POWER"
        )
        st.markdown(
            f"""
            1. **Fuente:** esta corrida utiliza {source_description}.
            2. **Preparación:** el pipeline limpia las observaciones y calcula promedios climáticos por punto.
            3. **Índices relativos:** radiación solar y viento se normalizan entre el mínimo y el máximo de los puntos del experimento.
            4. **Índice híbrido:** combina `0.5 × solar + 0.3 × eólico + 0.2 × (solar × eólico)`.
            5. **Clustering:** K-Means agrupa radiación, irradiancia y viento después de estandarizar sus escalas.
            6. **Interpretación:** cada cluster se traduce a un perfil solar, eólico, híbrido o de bajo potencial.
            7. **Visualización:** Streamlit lee los archivos terminados; no vuelve a calcular ni modificar los clusters.
            """
        )
        st.caption(
            "Un índice de 100 % identifica el valor más alto dentro de esta corrida; no equivale a un potencial absoluto de 100 %."
        )

with performance_tab:
    st.header("¿Cómo se procesaron los datos?")
    st.caption("Esta sección evalúa el procesamiento paralelo; no cambia el potencial energético del mapa.")
    performance = performance_summary(summary)
    if performance.empty:
        st.info("Este experimento no contiene resultados suficientes de rendimiento.")
    elif len(performance) < 2:
        st.warning(
            "Solo existe una configuración de workers. Se necesita ejecutar el mismo experimento "
            "con 1, 2, 4 y 8 workers para evaluar escalabilidad."
        )
        st.metric("Tiempo de la corrida", f"{float(manifest.get('elapsed_seconds', 0) or 0):.2f} s")
    else:
        best = performance.loc[performance["tiempo_mediano"].idxmin()]
        parallel = performance[performance["workers"] > 1]
        best_parallel = parallel.loc[parallel["speedup"].idxmax()]
        has_memory = (
            "memoria_mediana_mb" in performance.columns
            and performance["memoria_mediana_mb"].notna().any()
        )

        cards = st.columns(4)
        cards[0].metric(
            "Tiempo base con 1 worker",
            f"{float(performance.iloc[0]['tiempo_base']):.2f} s",
            delta="valor calculado por el pipeline",
            delta_color="off",
        )
        cards[1].metric(
            "Mejor tiempo observado",
            f"{best['tiempo_mediano']:.2f} s",
            delta=f"{int(best['workers'])} workers",
            delta_color="off",
        )
        cards[2].metric(
            "Mejor aceleración paralela",
            f"{best_parallel['speedup']:.2f}×",
            delta=f"{int(best_parallel['workers'])} workers",
            delta_color="off",
        )
        cards[3].metric(
            "Mayor memoria observada",
            f"{performance['memoria_mediana_mb'].max():.1f} MB" if has_memory else "Sin datos",
            delta=f"{int(performance.loc[performance['memoria_mediana_mb'].idxmax(), 'workers'])} workers" if has_memory else None,
            delta_color="off",
        )

        time_column, memory_column = st.columns(2)
        with time_column:
            st.subheader("Tiempo de procesamiento")
            st.caption("Una barra más corta representa una ejecución más rápida.")
            st.plotly_chart(scalability_preview(summary), width="stretch")
        with memory_column:
            st.subheader("Consumo de memoria")
            if has_memory:
                st.caption("Memoria máxima mediana registrada para cada configuración.")
                st.plotly_chart(memory_chart(performance), width="stretch")
            else:
                st.info("El experimento no registró memoria.")

        speedup_column, efficiency_column = st.columns(2)
        with speedup_column:
            st.subheader("Aceleración")
            st.caption("Compara la mejora real con la mejora ideal esperada.")
            st.plotly_chart(speedup_chart(performance), width="stretch")
        with efficiency_column:
            st.subheader("Eficiencia")
            st.caption("Indica qué porcentaje de la capacidad agregada se aprovechó.")
            st.plotly_chart(efficiency_chart(performance), width="stretch")

        st.subheader("Detalle por configuración")
        display = performance.rename(
            columns={
                "workers": "Workers",
                "tiempo_mediano": "Tiempo mediano (s)",
                "tiempo_promedio": "Tiempo promedio (s)",
                "repeticiones": "Repeticiones",
                "tiempo_base": "Tiempo base (s)",
                "speedup": "Aceleración",
                "eficiencia": "Eficiencia",
                "memoria_mediana_mb": "Memoria mediana (MB)",
            }
        )
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "Tiempo mediano (s)": st.column_config.NumberColumn(format="%.2f s"),
                "Tiempo promedio (s)": st.column_config.NumberColumn(format="%.2f s"),
                "Tiempo base (s)": st.column_config.NumberColumn(format="%.2f s"),
                "Aceleración": st.column_config.NumberColumn(format="%.2fx"),
                "Eficiencia": st.column_config.NumberColumn(format="percent"),
                "Memoria mediana (MB)": st.column_config.NumberColumn(format="%.1f MB"),
            },
        )
        st.caption(
            "Una aceleración menor que 1× significa que la configuración paralela fue más lenta "
            "que la ejecución con 1 worker."
        )

    with st.expander("Información técnica de la corrida"):
        st.json(manifest)
