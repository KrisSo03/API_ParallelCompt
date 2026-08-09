"""Streamlit entry point for the Renewable Energy Atlas dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.charts import (
    country_comparison_chart,
    profile_distribution,
    renewable_map,
    scalability_preview,
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

summary_tab, atlas_tab, comparison_tab, performance_tab = st.tabs(
    ["Resumen general", "Atlas interactivo", "Comparación", "Rendimiento"]
)

with summary_tab:
    st.header("¿Qué encontró el análisis?")
    solar = overview_metrics(indicators, "solar_score")
    wind = overview_metrics(indicators, "wind_score")
    hybrid = overview_metrics(indicators, "hybrid_score")

    cards = st.columns(5)
    cards[0].metric("Puntos analizados", len(indicators), delta=f"{indicators['country'].nunique()} países", delta_color="off")
    cards[1].metric("Potencial solar general", f"{solar.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
    cards[2].metric("Potencial eólico general", f"{wind.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
    cards[3].metric("Potencial híbrido general", f"{hybrid.average_score:.1%}", delta="promedio de todos los puntos", delta_color="off")
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
                st.write(f"{float(point[metric]):.1%} de potencial normalizado")
                st.caption(f"Perfil: {CLUSTER_LABELS.get(point['cluster_label'], point['cluster_label'])}")

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
        cards[1].metric("Solar visible", f"{filtered['solar_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")
        cards[2].metric("Eólico visible", f"{filtered['wind_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")
        cards[3].metric("Híbrido visible", f"{filtered['hybrid_score'].mean():.1%}", delta="promedio de la selección", delta_color="off")

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
    st.caption("Esta comparación utiliza el promedio de todos los puntos de cada país seleccionado.")
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
        baseline = performance[performance["workers"] == 1]
        best = performance.loc[performance["tiempo_mediano"].idxmin()]
        cards = st.columns(4)
        cards[0].metric("Configuraciones comparadas", len(performance))
        cards[1].metric("Mejor tiempo", f"{best['tiempo_mediano']:.2f} s", delta=f"{int(best['workers'])} workers", delta_color="off")
        cards[2].metric("Repeticiones", int(performance["repeticiones"].sum()))
        cards[3].metric(
            "Tiempo base con 1 worker",
            f"{float(baseline.iloc[0]['tiempo_mediano']):.2f} s" if not baseline.empty else "Sin datos",
            delta="referencia para comparar",
            delta_color="off",
        )
        st.plotly_chart(scalability_preview(summary), width="stretch")
        display = performance.rename(
            columns={
                "workers": "Workers",
                "tiempo_mediano": "Tiempo mediano (s)",
                "tiempo_promedio": "Tiempo promedio (s)",
                "repeticiones": "Repeticiones",
                "speedup": "Aceleración",
                "eficiencia": "Eficiencia",
            }
        )
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "Tiempo mediano (s)": st.column_config.NumberColumn(format="%.2f s"),
                "Tiempo promedio (s)": st.column_config.NumberColumn(format="%.2f s"),
                "Aceleración": st.column_config.NumberColumn(format="%.2fx"),
                "Eficiencia": st.column_config.NumberColumn(format="percent"),
            },
        )
        st.caption("Aceleración indica cuántas veces fue más rápido que usar 1 worker. Eficiencia indica cuánto se aprovecharon los workers.")

    with st.expander("Información técnica de la corrida"):
        st.json(manifest)
