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

if selected_name:
    selected_path = root / selected_name
    st.success(f"Experimento detectado: **{selected_name}**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Experimentos disponibles", len(experiments))
    col2.metric("Experimento activo", selected_name)
    col3.metric("Estado del dashboard", "Inicializado")
    st.markdown(
        f"""
        <div class="atlas-stage">
          <strong>Siguiente etapa</strong><br>
          Cargar y validar las corridas ubicadas en
          <code>{selected_path}</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info(
        "El dashboard está listo. Ejecuta una prueba del pipeline o configura "
        f"`{RESULTS_ENV_VAR}` para comenzar."
    )

