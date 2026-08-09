"""Initial Streamlit entry point for the Renewable Energy Atlas dashboard."""

from __future__ import annotations

import streamlit as st

from dashboard.config import (
    APP_SUBTITLE,
    APP_TITLE,
    RESULTS_ENV_VAR,
    discover_experiments,
    results_root,
)
from dashboard.data_loader import discover_runs, discover_worker_counts, load_run, load_summary
from dashboard.validators import DashboardDataError


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f5f6f2; }
      [data-testid="stSidebar"] { background: #123c33; }
      [data-testid="stSidebar"] * { color: #f6fbf8; }
      .atlas-hero {
        padding: 1.6rem 1.8rem;
        border-radius: 1.2rem;
        background: linear-gradient(120deg, #123c33 0%, #236b57 68%, #69a775 100%);
        color: white;
        box-shadow: 0 16px 38px rgba(18, 60, 51, .14);
      }
      .atlas-hero h1 { margin: 0; color: white; font-size: clamp(2rem, 4vw, 3.25rem); }
      .atlas-hero p { margin: .55rem 0 0; color: #dcebe4; font-size: 1.05rem; }
      .atlas-stage {
        margin-top: 1.2rem;
        padding: 1.1rem 1.25rem;
        border: 1px solid #dce5df;
        border-radius: 1rem;
        background: white;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

root = results_root()
experiments = discover_experiments(root)

with st.sidebar:
    st.title("🌿 Atlas renovable")
    st.caption("Explorador de experimentos")
    st.divider()
    st.text_input("Directorio de resultados", value=str(root), disabled=True)
    if experiments:
        selected_name = st.selectbox(
            "Experimento",
            options=[path.name for path in experiments],
            help="Las carpetas se descubren automáticamente dentro del directorio de resultados.",
        )
        selected_path = root / selected_name
        worker_counts = discover_worker_counts(selected_path)
        selected_workers = st.selectbox(
            "Workers",
            options=worker_counts,
            format_func=lambda value: f"{value} worker" if value == 1 else f"{value} workers",
            disabled=not worker_counts,
        ) if worker_counts else None
        runs = discover_runs(selected_path, selected_workers) if selected_workers else []
        selected_run = st.selectbox(
            "Repetición",
            options=runs,
            format_func=lambda reference: f"Run {reference.repeat:02d}",
            disabled=not runs,
        ) if runs else None
    else:
        selected_name = None
        st.warning("No hay experimentos disponibles.")
    st.divider()
    st.caption(f"Ruta configurable con `{RESULTS_ENV_VAR}`")

st.markdown(
    f"""
    <section class="atlas-hero">
      <h1>{APP_TITLE}</h1>
      <p>{APP_SUBTITLE}</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if selected_name and selected_run:
    try:
        run_data = load_run(selected_run)
        summary = load_summary(selected_path)
    except DashboardDataError as error:
        st.error(str(error))
        st.stop()

    manifest = run_data.manifest
    indicators = run_data.indicators
    st.success(f"Corrida validada: **{selected_name} / {selected_run.path.parent.name} / {selected_run.path.name}**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Puntos", len(indicators))
    col2.metric("Países", indicators["country"].nunique())
    col3.metric("Fuente", str(manifest.get("source", "desconocida")).upper())
    col4.metric("Duración", f"{float(manifest.get('elapsed_seconds', 0)):.2f} s")

    st.markdown('<div class="atlas-stage"><strong>Datos cargados y validados</strong></div>', unsafe_allow_html=True)
    st.dataframe(
        indicators.head(10),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Detalles técnicos de la corrida"):
        st.json(manifest)
        st.write(f"Perfiles disponibles: **{len(run_data.profiles)}**")
        st.write(f"Filas en el resumen del experimento: **{len(summary)}**")
elif selected_name:
    st.warning("El experimento seleccionado no contiene corridas reconocibles.")
else:
    st.info(
        "El dashboard está listo. Ejecuta una prueba del pipeline o configura "
        f"`{RESULTS_ENV_VAR}` para comenzar."
    )

