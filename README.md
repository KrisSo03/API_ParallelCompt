# Atlas paralelo de potencial de energía renovable para Centroamérica

Pipeline reproducible que obtiene datos climáticos históricos de NASA POWER,
calcula indicadores de potencial solar, eólico e híbrido para 300 puntos,
agrupa regiones mediante K-Means y compara el procesamiento secuencial con
Dask usando 1, 2, 4 y 8 workers.

## Equipo

- Anyelin Arias
- Carolina Salas
- Guissel Betancur
- Iván Cespedes
- Kristhel Porras

## Problema y objetivo

Centroamérica posee recursos solares y eólicos importantes, pero identificar
zonas prioritarias requiere integrar y procesar grandes volúmenes de datos
climáticos espaciales y temporales. El proyecto busca responder:

> ¿Cómo puede un pipeline paralelo basado en datos históricos de NASA POWER
> identificar y clasificar zonas con potencial híbrido solar-eólico y reducir
> el costo computacional del análisis?

La solución genera indicadores comparables por ubicación, clasifica patrones
climáticos y produce evidencia de tiempo, speedup, eficiencia y memoria. Se
alinea con los ODS 7 (energía asequible y no contaminante) y 13 (acción por el
clima).

## Flujo real del sistema

```text
Grilla de 300 puntos
        ↓
Descarga NASA POWER (secuencial, con reintentos)
        ↓
Parseo y modelo ClimateObservation
        ↓
Validación pre-clean → limpieza → validación post-clean
        ↓
Indicadores por punto (secuencial o Dask)
        ↓
Scores solar, eólico e híbrido
        ↓
Selección automática de K por silhouette (K=2..10)
        ↓
K-Means, interpretación y archivos para el dashboard
```

Dask paraleliza la preparación y el cálculo de indicadores independientes por
punto. La descarga HTTP y el clustering se ejecutan actualmente en el proceso
coordinador. Esta delimitación es importante al interpretar el speedup.

## Inicio rápido local

### Requisitos

- Python 3.10 o superior; Python 3.12 es la versión usada en Kabré.
- Git y acceso HTTPS para usar NASA POWER.

### Instalación

```bash
git clone https://github.com/KrisSo03/API_ParallelCompt.git
cd API_ParallelCompt
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

En PowerShell, active el ambiente con:

```powershell
.venv\Scripts\Activate.ps1
```

### Verificación reproducible sin internet

```bash
ruff check .
pytest
python main.py run-all --use-fake
python main.py benchmark --use-fake
```

El flujo general también puede regenerar estos reportes históricos:

- `results/cluster_indicators.csv`
- `results/cluster_profiles.csv`
- `results/benchmark/benchmark_results.csv`

Estos CSV no son la entrada del dashboard. Para Streamlit utilice las salidas de `hpc-run` o
`hpc-benchmark` documentadas en [docs/DASHBOARD.md](docs/DASHBOARD.md).

### Ejecución con datos reales

La fuente normal es NASA POWER; no requiere API key:

```bash
python main.py run-all --workers 4
```

La configuración predeterminada consulta 300 puntos entre 2000 y 2023. Para
una validación real pequeña, modifique temporalmente `.env`, por ejemplo:

```dotenv
DATE_RANGE_START_YEAR=2023
DATE_RANGE_END_YEAR=2023
GRID_SIZE=5
GRID_SAMPLE_SIZE=5
```

No use `--use-fake` si el objetivo es demostrar acceso a NASA POWER.

## Comandos

| Comando | Propósito |
|---|---|
| `python main.py download` | Descargar y guardar observaciones reales |
| `python main.py process --workers 4` | Descargar, limpiar y calcular indicadores |
| `python main.py cluster --workers 4` | Procesar, agrupar y generar reportes |
| `python main.py run-all --workers 4` | Ejecutar el pipeline completo |
| `python main.py benchmark --use-fake` | Comparar estrategias con entrada reproducible |
| `python -m renewable_atlas hpc-benchmark ...` | Ejecutar una matriz HPC controlada |

`--use-fake` es una herramienta de prueba determinista, no la fuente del atlas
final.

## Datos y metodología

### Fuente y periodo

- Fuente: NASA POWER Daily API.
- Cobertura: Centroamérica.
- Periodo predeterminado: 2000–2023.
- Tamaño predeterminado: 300 puntos.
- Persistencia: Parquet y CSV.

Se conservan 18 variables de radiación, viento, temperatura, presión, humedad,
precipitación y nubosidad. Entre las variables centrales están
`ALLSKY_SFC_SW_DWN`, `ALLSKY_SFC_SW_DNI`, `WS10M` y `WS50M`.

La propuesta menciona `WS100M`, pero NASA POWER no la entrega en esta consulta.
El campo `ws_100m` se estima desde `WS50M` mediante la ley de potencia con
exponente 1/7. Esta derivación se conserva explícitamente en el código y en la
interpretación de resultados.

### Calidad de datos

Por cada punto se evalúan duplicados, faltantes, fechas, sentinels, infinitos y
rangos climáticos antes y después de la limpieza. La ejecución continúa según
el reporte post-clean.

- Variables requeridas: `sw_dwn`, `dni`, `ws_50m`, `ws_100m`.
- Umbral técnico mínimo: 50 % de completitud en variables requeridas.
- Objetivo metodológico: 85 % de completitud.

El 50 % evita detener innecesariamente una corrida; el 85 % es la meta de
calidad que debe reportarse. Un reporte pre-clean representa los datos después
del parseo de NASA, no el JSON HTTP original.

### Indicadores y clustering

Los scores se normalizan sobre la muestra:

- `solar_score`: potencial solar normalizado.
- `wind_score`: potencial eólico basado en `ws_100m` derivada.
- `hybrid_score`: combinación ponderada solar-eólica.

El pipeline normal evalúa automáticamente K entre 2 y 10 y selecciona el mayor
silhouette válido. También registra Davies-Bouldin y puede evaluar estabilidad
mediante Adjusted Rand Index. Los umbrales metodológicos son:

- Silhouette ≥ 0.5.
- Davies-Bouldin < 2.0.
- ARI ≥ 0.95 cuando se habilitan repeticiones de estabilidad.

No alcanzar un umbral se registra como resultado científico; no se oculta ni
se interpreta automáticamente como un fallo técnico del pipeline.

## Configuración reproducible

Las variables disponibles están documentadas sin secretos en `.env.example`.
Las más relevantes son:

```dotenv
DATE_RANGE_START_YEAR=2000
DATE_RANGE_END_YEAR=2023
GRID_SIZE=300
GRID_ENABLE_SAMPLING=true
GRID_SAMPLE_SIZE=300

CLUSTERING_AUTO_SELECT=true
CLUSTERING_MIN_CLUSTERS=2
CLUSTERING_MAX_CLUSTERS=10
CLUSTERING_N_CLUSTERS=5
CLUSTERING_RANDOM_STATE=42

BENCHMARK_WORKER_COUNTS=1,2,4,8
BENCHMARK_REPEATS_PER_CONFIG=3
EXECUTION_SOURCE=nasa
EXECUTION_RANDOM_SEED=42
```

Para poder comparar dos experimentos deben coincidir como mínimo:

| Elemento | Evidencia |
|---|---|
| Código | Commit de Git registrado en `manifest.json` |
| Entrada | Cantidad de puntos y `input_checksum` |
| Periodo y parámetros | Snapshot de configuración del manifiesto |
| Ambiente | Python y dependencias de `requirements-kabre.txt` |
| Recursos | Workers, scheduler, CPUs, memoria y partición Slurm |
| Repeticiones | Mismo número y fuente de datos |

## Ejecución en Kabré

No ejecute instalaciones, pruebas, descargas ni el pipeline en los nodos
`login`. Desde login solamente consulte Slurm y envíe trabajos. La preparación
del ambiente debe hacerse dentro de una asignación de cómputo, siguiendo
[docs/KABRE.md](docs/KABRE.md).

### Smoke test

```bash
EXPERIMENT_ID=smoke-kabre POINTS=8 REPEATS=1 WORKERS=1,2 \
  sbatch --partition=kura-debug --time=00:15:00 hpc/kabre_benchmark.slurm
```

### Experimento reproducible de escalabilidad

```bash
EXPERIMENT_ID=kabre-carga-300 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_benchmark.slurm
```

La entrada sintética determinista permite medir cómputo sin confundirlo con la
latencia o disponibilidad de NASA. Para verificar la integración real por
separado:

```bash
EXPERIMENT_ID=kabre-nasa-20 POINTS=20 REPEATS=1 SOURCE=nasa \
  sbatch hpc/kabre_benchmark.slurm
```

### Verificación

```bash
squeue -u "$USER"
sacct -j <job-id> --format=JobID,State,Elapsed,MaxRSS,AllocCPUS,ExitCode
cat results/kabre-carga-300/summary.csv
python hpc/compare_worker_consistency.py results/kabre-carga-300
```

Una corrida válida debe mostrar `COMPLETED`, `ExitCode=0:0`, manifiestos con
`status=success`, el mismo checksum y resultados consistentes entre workers.

## Métricas de rendimiento

`summary.csv` registra cada configuración y repetición:

- Tiempo de ejecución.
- Memoria RSS pico del coordinador y, cuando el sistema lo permite, sus hijos.
- Baseline promedio de las repeticiones con un worker.
- `speedup = promedio(T1) / Tp`.
- `eficiencia = speedup / p × 100`.

La memoria de `manifest.json` indica `memory_scope=process_tree` o
`coordinator_only`; `sacct MaxRSS` funciona como comprobación independiente.

### Resultados finales

Las cifras de esta sección deben copiarse exclusivamente del experimento final
de Kabré. No deben sustituirse por estimaciones ni por un smoke test local.

| Workers | Tiempo promedio (s) | Speedup | Eficiencia (%) | Memoria pico |
|---:|---:|---:|---:|---:|
| 1 | Pendiente de corrida final | 1.00 | 100.0 | Pendiente |
| 2 | Pendiente de corrida final | Pendiente | Pendiente | Pendiente |
| 4 | Pendiente de corrida final | Pendiente | Pendiente | Pendiente |
| 8 | Pendiente de corrida final | Pendiente | Pendiente | Pendiente |

## Contratos para el dashboard

El dashboard de Streamlit consume las salidas reproducibles de cada experimento:

- `summary.csv`: workers, repetición, tiempo, memoria, baseline, speedup y eficiencia.
- `workers-NNN/run-NN/indicators.parquet`: coordenadas, país, indicadores y `cluster_id`.
- `workers-NNN/run-NN/cluster_profiles.json`: perfiles interpretados.
- `workers-NNN/run-NN/manifest.json`: fuente, configuración, calidad y trazabilidad.

Los contratos públicos permanecen:

- `process() -> indicators_df`
- `run() -> (indicators_df, labels, profiles)`

La interfaz está implementada con Streamlit y Plotly. Consulte la guía de
[ejecución, interpretación y validación del dashboard](docs/DASHBOARD.md).

## Estructura

```text
API_ParallelCompt/
├── src/renewable_atlas/
│   ├── application/       # pipeline y servicios
│   ├── composition/       # ensamblaje de dependencias
│   ├── config/            # variables de entorno
│   ├── domain/            # modelos e interfaces
│   └── infrastructure/    # NASA, Dask, K-Means, persistencia y reportes
├── hpc/                   # scripts Slurm y validación entre workers
├── docs/KABRE.md          # guía operativa de Kabré
├── tests/                 # pruebas unitarias e integración
├── requirements-kabre.txt # dependencias fijadas para Kabré
├── .env.example           # configuración sin credenciales
└── pyproject.toml         # paquete y herramientas de calidad
```

## Calidad, seguridad y contribución

Antes de crear un pull request:

```bash
ruff check .
pytest
git diff --check
```

- No suba tokens, contraseñas, `.env`, ambientes virtuales ni resultados
  masivos.
- Trabaje en una rama y use commits pequeños y descriptivos.
- Mantenga `requirements-kabre.txt` sincronizado con dependencias de runtime.
- Documente commit, configuración, job ID y ruta del experimento final.
- Revise que los contratos del dashboard no hayan cambiado.

## Limitaciones

- La resolución espacial y los valores provienen de NASA POWER, no de sensores
  instalados en cada punto.
- `ws_100m` es una estimación, no una observación directa.
- La descarga aún no está paralelizada; los benchmarks aíslan principalmente
  limpieza, validación y cálculo de indicadores.
- El atlas identifica potencial climático y no sustituye estudios técnicos,
  ambientales, económicos o de conexión eléctrica.
- Los resultados definitivos de escalabilidad deben ejecutarse y documentarse
  en Kabré.
