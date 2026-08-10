# Dashboard

La guía de instalación, ejecución, interpretación, uso con Kabré y validación está disponible en
[docs/DASHBOARD.md](../docs/DASHBOARD.md).

## Responsabilidad

Este paquete descubre, valida, carga y visualiza experimentos terminados. No descarga datos ni
ejecuta el pipeline.

```text
dashboard/
├── app.py          # navegación y composición de las vistas
├── charts.py       # figuras Plotly
├── config.py       # etiquetas, colores y ruta configurable
├── data_loader.py  # descubrimiento y lectura de experimentos
├── metrics.py      # agregaciones para presentación
├── styles.py       # tema visual
└── validators.py   # contrato y errores comprensibles
```

## Entrada

El dashboard consume:

```text
results/<experimento>/summary.csv
results/<experimento>/workers-NNN/run-NN/indicators.parquet
results/<experimento>/workers-NNN/run-NN/cluster_profiles.json
results/<experimento>/workers-NNN/run-NN/manifest.json
```

La ruta raíz predeterminada es `results/` y puede sobrescribirse con `ATLAS_RESULTS_DIR`.

## Desarrollo

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run dashboard/app.py
python -m pytest tests/unit/test_dashboard_data_loader.py tests/unit/test_dashboard_metrics.py -q
```

Las reglas científicas pertenecen al pipeline. La interfaz traduce etiquetas, agrega valores para
presentación y utiliza las métricas de rendimiento ya escritas en `summary.csv`.
