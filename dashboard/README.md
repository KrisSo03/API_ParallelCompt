# Dashboard del Atlas de Energía Renovable

## Estado actual

Este directorio contiene la base ejecutable del dashboard interactivo. Las etapas 1 y 2 están
terminadas: Streamlit levanta correctamente, descubre experimentos, workers y repeticiones, carga
las salidas de una corrida y valida su contenido. Las visualizaciones se implementarán en las
etapas siguientes. Este documento registra el alcance, las decisiones y el orden de trabajo para
que el desarrollo pueda continuar sin depender del historial de una conversación.

Rama de trabajo recomendada:

```text
feature/streamlit-dashboard
```

El prototipo HTML creado anteriormente fue solamente una prueba visual y no forma parte de la
solución final.

## Objetivo

Construir una aplicación web con Streamlit y Plotly que permita explorar los resultados del Atlas
de Energía Renovable producidos localmente o en la supercomputadora Kabré.

El dashboard no debe descargar datos, ejecutar Dask ni realizar el clustering. Su responsabilidad
es descubrir, validar, cargar y visualizar experimentos terminados.

```text
Pipeline ejecutado localmente o con Slurm en Kabré
                         |
                         v
            Archivos por experimento y corrida
                         |
                         v
               Dashboard de Streamlit
```

## Tecnologías

- **Streamlit:** estructura de la aplicación, navegación, filtros, tarjetas y estado de sesión.
- **Plotly:** mapas y gráficas interactivas.
- **Pandas:** lectura, filtrado y agregación de resultados.
- **PyArrow:** lectura de archivos Parquet.

Plotly, Pandas y PyArrow ya estaban declarados en el proyecto. Se agregó Streamlit 1.60.0, con
`streamlit>=1.60.0,<2.0.0` en `pyproject.toml` y `streamlit==1.60.0` en
`requirements-kabre.txt`. La importación, `pip check` y una respuesta HTTP local del servidor se
validaron con Python 3.12.10.

El entorno local único utilizado para validar compatibilidad con Kabré es `.venv`, creado con
Python 3.12.10. Kabré utiliza Python 3.12.11.

## Separación de responsabilidades

### Pipeline

- Obtiene o simula observaciones climáticas.
- Limpia y transforma los datos.
- Calcula indicadores y scores.
- Ejecuta K-Means.
- Genera perfiles de clusters.
- Guarda los resultados.

### Kabré

- Ejecuta el pipeline mediante Slurm.
- Compara diferentes cantidades de workers.
- Produce experimentos reproducibles.
- Registra manifiestos, configuración y resultados.

### Dashboard

- Descubre experimentos disponibles.
- Permite seleccionar workers y repeticiones.
- Valida las salidas antes de mostrarlas.
- Presenta el atlas, los clusters y la escalabilidad.
- Indica claramente si la fuente es simulada o NASA POWER.

## Resultados disponibles

Se realizaron pruebas locales pequeñas con el mismo comando utilizado por la lógica de Kabré. Los
resultados se encuentran en `results/`, carpeta excluida de Git.

Ejemplos de experimentos locales:

```text
results/
├── dashboard-smoke/
└── dashboard-benchmark/
```

La prueba de benchmark utiliza una estructura similar a:

```text
results/dashboard-benchmark/
├── summary.csv
├── workers-001/
│   ├── run-01/
│   ├── run-02/
│   └── run-03/
├── workers-002/
│   ├── run-01/
│   ├── run-02/
│   └── run-03/
└── workers-004/
    ├── run-01/
    ├── run-02/
    └── run-03/
```

Cada corrida contiene:

```text
workers-004/run-01/
├── indicators.parquet
├── cluster_profiles.json
└── manifest.json
```

## Contrato de entrada del dashboard

### `indicators.parquet`

Es la fuente principal del mapa. Se esperan estas columnas:

| Columna | Descripción |
|---|---|
| `point_id` | Identificador del punto geográfico |
| `latitude` | Latitud |
| `longitude` | Longitud |
| `country` | País |
| `sw_dwn_mean` | Radiación solar promedio |
| `dni_mean` | Irradiancia directa promedio |
| `ws_50m_mean` | Viento promedio a 50 metros |
| `ws_100m_mean` | Viento promedio a 100 metros |
| `solar_score` | Potencial solar normalizado |
| `wind_score` | Potencial eólico normalizado |
| `hybrid_score` | Potencial híbrido normalizado |
| `cluster` o `cluster_id` | Cluster asignado |

Existe una inconsistencia en el código actual: la ejecución normal usa `cluster_id` y la ejecución
HPC usa `cluster`. El cargador del dashboard debe aceptar ambos nombres y normalizarlos internamente
a `cluster_id`.

### `cluster_profiles.json`

Cada perfil puede contener:

```text
cluster_id
label
description
size
centroid
confidence
solar_percentile
wind_percentile
country_breakdown
```

El dashboard nunca debe asumir que `cluster_id == 0` significa potencial solar. Debe relacionar el
identificador con el perfil de la corrida. Actualmente se esperan categorías como:

```text
Solar-dominant
Wind-dominant
Hybrid-high
Lower-resource
```

Pueden existir cinco clusters y solamente cuatro categorías; más de un cluster puede compartir la
misma categoría.

### `manifest.json`

Describe la corrida y permite comprobar que es válida. Incluye campos como:

```text
status
source
point_count
workers
scheduler
repeat
elapsed_seconds
git_commit
hostname
slurm_job_id
settings
```

El dashboard debe mostrar únicamente corridas con `status == "success"` y debe identificar
visualmente si `source` es `fake` o `nasa`.

### `summary.csv`

Resume todas las configuraciones y repeticiones de un experimento:

```text
status
workers
repeat
elapsed_seconds
point_count
run_dir
error
```

En corridas creadas con `hpc-run`, el resumen puede llamarse
`summary-workers-001.csv`. El cargador debe reconocer ambos patrones.

## Estructura planeada

```text
dashboard/
├── README.md
├── __init__.py
├── app.py
├── config.py
├── data_loader.py
├── validators.py
├── metrics.py
├── charts.py
└── styles.py
```

### `app.py`

Punto de entrada de Streamlit. Configura la página, crea la barra lateral, organiza las pestañas y
conecta los componentes. Debe contener poca lógica de datos.

### `config.py`

Contendrá la ruta predeterminada, nombres en español, paleta de colores y configuración visual.

### `data_loader.py`

Responsabilidades:

- descubrir directorios de experimentos;
- descubrir configuraciones `workers-NNN`;
- descubrir directorios `run-NN`;
- leer Parquet, JSON y CSV;
- normalizar `cluster` a `cluster_id`;
- localizar `summary.csv` o `summary-workers-*.csv`;
- devolver estructuras independientes de la ruta local o de Kabré.

### `validators.py`

Validará:

- existencia de archivos;
- columnas obligatorias;
- coordenadas válidas;
- scores numéricos entre 0 y 1;
- correspondencia entre puntos y perfiles;
- estado exitoso en el manifiesto.

Los errores deben convertirse en mensajes comprensibles para el usuario, no en trazas técnicas.

### `metrics.py`

Calculará:

```text
tiempo promedio y mediano
variación entre repeticiones
speedup = tiempo de 1 worker / tiempo de N workers
eficiencia = speedup / N * 100
mejor configuración observada
```

### `charts.py`

Contendrá funciones Plotly para:

- mapa de potencial renovable;
- comparación solar, eólica e híbrida;
- distribución de puntos por país;
- tamaño y composición de clusters;
- tiempo por workers;
- speedup;
- eficiencia.

### `styles.py`

Contendrá CSS y componentes visuales reutilizables para tarjetas, encabezados, avisos y colores.

## Interfaz planeada

La barra lateral permitirá seleccionar:

```text
Experimento
Workers
Repetición
País
Cluster
Variable solar, eólica o híbrida
```

La zona principal tendrá inicialmente cuatro pestañas:

1. **Resumen:** tarjetas con puntos, países, scores, fuente, duración y estado.
2. **Atlas:** mapa Plotly, filtros y tabla de puntos.
3. **Clusters:** etiquetas, perfiles, percentiles, confianza y distribución por país.
4. **Rendimiento:** tiempos, repeticiones, speedup y eficiencia.

## Comportamiento del mapa

El mapa utilizará:

```text
latitude
longitude
country
cluster_id
solar_score
wind_score
hybrid_score
```

Los puntos se colorearán según el perfil del cluster y su tamaño o intensidad dependerá de la
variable seleccionada. La información emergente mostrará país, cluster, scores e indicadores
climáticos.

El mapa con fondo cartográfico puede necesitar acceso a Internet para obtener teselas. Antes del
despliegue se debe validar la política de red de Kabré y preparar, si hace falta, una visualización
alternativa sin teselas externas.

## Descubrimiento de experimentos

El nombre de un experimento no estará escrito en el código. La aplicación buscará subdirectorios en
una ruta configurable, por defecto:

```text
results/
```

La ruta podrá sobrescribirse con:

```powershell
$env:ATLAS_RESULTS_DIR="results"
```

En Linux/Kabré:

```bash
export ATLAS_RESULTS_DIR="$PWD/results"
```

Ejemplos de nombres que el dashboard podría descubrir:

```text
dashboard-benchmark
kabre-smoke-8
kabre-fake-300-20260809
kabre-nasa-20-20260810
```

## Errores que deben manejarse

La aplicación no debe cerrarse si:

- no existe la carpeta de resultados;
- no hay experimentos;
- una corrida está incompleta;
- falta un archivo;
- el manifiesto indica fallo;
- faltan valores climáticos;
- no hay puntos para un filtro;
- cambia la cantidad de clusters;
- falta el resumen de rendimiento.

Debe presentar mensajes como:

```text
No se encontraron experimentos.
La corrida seleccionada no contiene indicators.parquet.
No hay puntos disponibles para los filtros seleccionados.
```

## Desarrollo local

El entorno local de referencia se prepara con las versiones de Kabré:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-kabre.txt
python -m pip install --no-deps -e .
python -m pip check
```

La aplicación se levanta con:

```powershell
python -m streamlit run dashboard/app.py
```

## Prueba local pequeña

Para producir datos sin exigir demasiado a una computadora local:

```powershell
$env:DATE_RANGE_START_YEAR="2023"
$env:DATE_RANGE_END_YEAR="2023"

python main.py hpc-benchmark `
  --experiment-id dashboard-benchmark `
  --source fake `
  --points 12 `
  --workers "1,2,4" `
  --repeats 3 `
  --results-dir results `
  --scheduler processes
```

Después de la prueba:

```powershell
Remove-Item Env:DATE_RANGE_START_YEAR
Remove-Item Env:DATE_RANGE_END_YEAR
```

## Ejecución y visualización en Kabré

El cálculo debe enviarse a Slurm; no se debe ejecutar el pipeline directamente en un nodo de
login. Ejemplo:

```bash
EXPERIMENT_ID=kabre-fake-300-20260809 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_job_array.slurm
```

Después se debe comprobar que los trabajos y manifiestos terminaron correctamente. El dashboard
leerá los archivos ya producidos.

La forma de servir Streamlit desde Kabré depende de las políticas de red del centro. Las opciones
son:

1. ejecutar Streamlit en un nodo permitido y acceder mediante túnel SSH;
2. procesar en Kabré, descargar los resultados y ejecutar Streamlit localmente.

La segunda opción es la más sencilla y robusta para una defensa. La primera debe validarse con la
administración de Kabré.

## Orden de implementación y commits

### Etapa 1: inicialización

- Agregar Streamlit a las dependencias.
- Crear `app.py`, `config.py` y una página mínima.
- Confirmar que abre en el navegador.

Commit sugerido:

```text
feat: initialize Streamlit dashboard
```

### Etapa 2: carga y validación

- Descubrir experimentos, workers y repeticiones.
- Leer las salidas reales.
- Validar archivos y columnas.

Commit sugerido:

```text
feat: load and validate experiment results
```

Estado: implementada. `data_loader.py` descubre configuraciones y lee Parquet/JSON/CSV;
`validators.py` verifica manifiestos, columnas, coordenadas, scores, perfiles y cantidad de puntos.
La interfaz permite seleccionar experimento, workers y repetición. Se agregaron cinco pruebas
unitarias y la suite completa pasa con 52 pruebas.

### Etapa 3: resumen y atlas

- Agregar tarjetas, filtros, mapa Plotly y tabla de puntos.

Commit sugerido:

```text
feat: add interactive renewable atlas
```

### Etapa 4: perfiles

- Mostrar etiquetas, descripciones, confianza, percentiles y distribución por país.

Commit sugerido:

```text
feat: add cluster profile analysis
```

### Etapa 5: escalabilidad

- Mostrar tiempos, repeticiones, speedup y eficiencia.

Commit sugerido:

```text
feat: add scalability visualizations
```

### Etapa 6: documentación y pruebas

- Documentar la ejecución local y en Kabré.
- Agregar pruebas para carga, normalización y validación.

Commit sugerido:

```text
docs: document dashboard execution
```

## Decisiones pendientes

Antes del despliegue final se debe acordar:

1. Unificación de la columna `cluster`/`cluster_id` en el pipeline.
2. Si Streamlit se ejecutará dentro de Kabré o localmente con resultados descargados.
3. Estrategia de mapa cuando no haya acceso a teselas externas.
4. Qué experimento se considera oficial para la defensa.
5. Si el dashboard podrá observar experimentos en ejecución o solamente corridas terminadas.

## Punto de continuación

Las etapas 1 y 2 quedaron implementadas y validadas. El siguiente paso es la Etapa 3:

1. crear `dashboard/charts.py`, `dashboard/metrics.py` y `dashboard/styles.py`;
2. agregar filtros por país, cluster y tipo de potencial;
3. construir las tarjetas de resumen;
4. crear el mapa interactivo con Plotly;
5. agregar una tabla de puntos filtrados;
6. realizar el tercer commit.
