# Atlas paralelo de potencial de energía renovable para Centroamérica

Sistema reproducible para construir un atlas de potencial energético relativo solar–eólico para Centroamérica utilizando datos climáticos históricos de NASA POWER.

La solución genera una grilla regional, prepara datos solares y meteorológicos, procesa las observaciones secuencialmente con pandas y paralelamente con Dask, calcula indicadores energéticos, clasifica las ubicaciones mediante K-Means y presenta los resultados en un dashboard interactivo desarrollado con Streamlit.

## Equipo

- Anyelin Arias
- Carolina Salas
- Guissel Betancur
- Iván Cespedes
- Kristhel Porras

## Problema y objetivo

Centroamérica cuenta con condiciones favorables para aprovechar recursos solares y eólicos. Sin embargo, identificar zonas prioritarias requiere integrar y procesar grandes cantidades de información climática espacial y temporal.

El objetivo del proyecto es desarrollar un sistema paralelo para construir un atlas de potencial de energía renovable híbrida solar–eólica mediante datos históricos de NASA POWER y técnicas de aprendizaje automático.

La pregunta que guía el proyecto es:

> ¿Cómo puede un pipeline paralelo basado en datos históricos de NASA POWER identificar y clasificar zonas con potencial híbrido solar–eólico en Centroamérica y reducir el tiempo de procesamiento sin afectar la consistencia de los resultados?

Los indicadores producidos representan potenciales climáticos relativos. No sustituyen estudios técnicos, económicos, ambientales o de conexión eléctrica para seleccionar emplazamientos definitivos.

## Objetivos de Desarrollo Sostenible

El proyecto se relaciona con:

- ODS 7: Energía asequible y no contaminante.
- ODS 9: Industria, innovación e infraestructura.
- ODS 11: Ciudades y comunidades sostenibles.
- ODS 13: Acción por el clima.

## Flujo general de la solución

```text
Grilla regional
        ↓
NASA POWER en AWS
        ↓
Preparación e integración
        ↓
Parquet mensual
        ↓
pandas / Dask
        ↓
Indicadores energéticos
        ↓
K-Means e interpretación
        ↓
Resultados reproducibles
        ↓
Atlas en Streamlit
```

El flujo completo se puede resumir en nueve etapas:

1. Generación reproducible de 300 puntos dentro de los siete países de Centroamérica.
2. Lectura de datos climáticos horarios de NASA POWER disponibles en AWS.
3. Selección espacial e integración temporal de variables solares y meteorológicas.
4. Almacenamiento intermedio en archivos Parquet mensuales.
5. Procesamiento secuencial con pandas y paralelo con Dask.
6. Cálculo de indicadores relativos solar, eólico e híbrido.
7. Agrupamiento mediante K-Means e interpretación de perfiles.
8. Persistencia de resultados y métricas reproducibles.
9. Visualización del atlas y del rendimiento mediante Streamlit.

## Fuentes de datos

El proyecto mantiene dos rutas de adquisición, utilizadas con propósitos diferentes.

### NASA POWER Point API

El Point API se utiliza para pruebas funcionales pequeñas. Esta ruta realiza solicitudes HTTP por ubicación y permite validar:

- Conexión con NASA POWER.
- Parseo de respuestas.
- Construcción de objetos `ClimateObservation`.
- Validación previa a la limpieza.
- Limpieza y validación posterior.
- Cálculo de indicadores por punto.

La configuración predeterminada del flujo Point API utiliza datos diarios entre 2000 y 2023. Esta ruta no fue la utilizada para el experimento masivo final.

### NASA POWER Open Data en AWS

La ruta masiva utilizada en el experimento final accede mediante HTTPS a archivos Zarr públicos:

- `syn1deg`: variables solares y nubosidad.
- MERRA-2: variables meteorológicas.
- Xarray: selección de celdas climáticas.
- `fsspec`: acceso remoto.
- PyArrow: lectura y escritura de Parquet.
- Zstandard: compresión de las particiones.

La preparación se realiza por bloques mensuales. Las fuentes solares y meteorológicas se integran mediante el identificador del punto y la marca temporal.

Esta estrategia permite reutilizar exactamente la misma entrada en todas las configuraciones y evita incorporar la latencia de descarga al cálculo del speedup.

## Variables climáticas

El conjunto final conserva 18 variables relacionadas con:

- Radiación solar global.
- Irradiancia directa normal.
- Radiación difusa.
- Radiación de cielo despejado.
- Índice de claridad.
- Nubosidad.
- Velocidad del viento.
- Dirección del viento.
- Temperatura.
- Temperatura de punto de rocío.
- Humedad relativa.
- Humedad específica.
- Presión atmosférica.
- Precipitación.

Las variables centrales del análisis energético son:

- `ALLSKY_SFC_SW_DWN`
- `ALLSKY_SFC_SW_DNI`
- `WS50M`
- `WS100M`

NASA POWER no entrega directamente `WS100M` en la fuente utilizada. El pipeline la estima a partir de `WS50M` mediante una transformación de perfil vertical.

Las variables `T2M_MAX` y `T2M_MIN` se derivan a partir de las observaciones horarias de temperatura.

## Preparación y calidad

La preparación depende de la fuente utilizada.

### Calidad en el flujo Point API

El flujo basado en observaciones individuales utiliza `DataValidator` para revisar:

- Valores faltantes.
- Duplicados.
- Fechas inválidas o duplicadas.
- Orden temporal.
- Valores infinitos.
- Valores sentinela.
- Rangos climáticos plausibles.
- Columnas completamente vacías.
- Completitud de las variables requeridas.

Las variables requeridas son:

- `sw_dwn`
- `dni`
- `ws_50m`
- `ws_100m`

El umbral técnico mínimo de completitud es 50 %. El objetivo metodológico es 85 %.

La decisión de continuar se toma utilizando el reporte posterior a la limpieza.

### Preparación en la ruta AWS

La ruta AWS procesa directamente los arreglos Zarr por bloques mensuales. En esta etapa:

- Se seleccionan las celdas cercanas a cada punto.
- Se integran las fuentes por punto y fecha.
- Se comprueba la presencia de las variables esperadas.
- Se conserva la identidad geográfica.
- Se generan las variables derivadas.
- Se escriben las particiones mensuales.

La validación pre-clean/post-clean del Point API no debe atribuirse directamente a la ruta AWS, ya que ambas utilizan procesos de preparación diferentes.

## Almacenamiento intermedio

Las observaciones horarias se almacenan en archivos Parquet:

- Compresión: Zstandard.
- Particionado: año y mes.
- Ubicación recomendada en Kabré:

```text
/data/$USER/renewable-atlas/aws-staging/
```

El almacenamiento intermedio permite:

- Reutilizar la misma entrada.
- Evitar nuevas consultas a AWS.
- Separar adquisición y benchmark.
- Procesar los datos por particiones.
- Mantener trazabilidad del volumen y periodo.

## Procesamiento secuencial y paralelo

El proyecto compara dos estrategias sobre la misma entrada.

### Línea base secuencial

- Motor: pandas.
- Workers: 1.
- Identificador: `main-sequential`.

### Procesamiento paralelo

- Motor: Dask DataFrame.
- Workers evaluados: 2, 4 y 8.
- Scheduler utilizado en el experimento final: `threads`.
- Identificador: `aws-dask`.

La ruta AWS utiliza `dd.read_parquet` para construir un Dask DataFrame sobre las particiones mensuales.

Dask distribuye las operaciones de lectura y agregación. Al finalizar, `compute()` materializa únicamente el resultado reducido: una fila por cada uno de los 300 puntos.

La descarga desde AWS y la construcción inicial del staging no forman parte de los tiempos utilizados para calcular speedup y eficiencia.

## Indicadores energéticos

Por cada punto se calculan, entre otras estadísticas:

- `sw_dwn_mean`
- `dni_mean`
- `ws_50m_mean`
- `ws_100m_mean`

El índice solar se obtiene mediante normalización min–max de `sw_dwn_mean`.

El índice eólico se obtiene mediante normalización min–max de `ws_100m_mean`.

Cuando todos los valores de una variable son iguales, se utiliza un valor neutral de 0.5.

El índice híbrido se calcula como:

```text
H = 0.5S + 0.3W + 0.2(SW)
```

Donde:

- `S`: índice solar.
- `W`: índice eólico.
- `H`: índice híbrido.

El término de interacción favorece ubicaciones donde ambos recursos presentan valores relativos altos.

## Clustering

K-Means utiliza las siguientes características:

- `sw_dwn_mean`
- `dni_mean`
- `ws_50m_mean`
- `ws_100m_mean`

Antes del agrupamiento:

1. Los valores faltantes se imputan mediante la mediana de cada columna.
2. Una columna completamente vacía se sustituye por cero.
3. Las características se estandarizan con `StandardScaler`.

El pipeline evalúa automáticamente valores de K entre 2 y 10.

El K recomendado corresponde al valor con mayor coeficiente Silhouette válido. Davies–Bouldin se conserva como métrica complementaria.

Los umbrales exploratorios son:

- Silhouette ≥ 0.5.
- Davies–Bouldin < 2.0.
- ARI ≥ 0.95 cuando se comparan corridas.

No alcanzar un umbral se registra como resultado científico y no se oculta como un fallo técnico.

## Interpretación de perfiles

Los clusters se interpretan mediante dos índices compuestos:

- Índice solar: combina `sw_dwn_mean` y `dni_mean`.
- Índice eólico: combina `ws_50m_mean` y `ws_100m_mean`.

Los centroides se convierten en puntuaciones estandarizadas y posteriormente en percentiles relativos.

Las categorías utilizadas son:

- `Hybrid-high`
- `Solar-dominant`
- `Wind-dominant`
- `Lower-resource`

Cada perfil conserva:

- Etiqueta.
- Descripción.
- Centroides.
- Percentiles solar y eólico.
- Confianza relativa.
- Distribución por país.
- País dominante.

## Experimento final en Kabré

El experimento utilizado como referencia para el informe y la presentación es:

```text
aws-geographic-300-full-range-v1
```

### Infraestructura

| Parámetro | Valor |
|---|---|
| Supercomputadora | Kabré |
| Partición | `kura` |
| Nodo asignado | `kura-1b.cnca` |
| Job Slurm | `600690` |
| Nodos | 1 |
| CPUs | 8 |
| Memoria solicitada | 32 GiB |
| Python | 3.12.11 |
| Scheduler Dask | `threads` |
| Estado | `COMPLETED` |
| Exit code | `0:0` |
| Duración total | 1:15:56 |

El código utilizado corresponde al commit:

```text
1ba46fbbe81a5a4146f6cfd5c6310c00e49fbf33
```

### Conjunto final

| Propiedad | Resultado |
|---|---:|
| Fuente | NASA POWER Open Data en AWS |
| Periodo | 2001-01-01 a 2026-08-14 |
| Resolución | Horaria |
| Puntos | 300 |
| Países | 7 |
| Variables | 18 |
| Observaciones | 67,363,500 |
| Particiones mensuales | 308 |
| Tamaño lógico | 1.833 GiB |
| Tamaño físico Parquet | 1.403 GiB |
| Modo | `full-date-range` |

El modo `full-date-range` recorre el periodo temporal completo solicitado. El experimento final no terminó al alcanzar un tamaño específico.

### Diseño experimental

Se evaluaron:

```text
Workers: 1, 2, 4 y 8
Repeticiones: 3 por configuración
Total de corridas: 12
Semilla K-Means: 42
Rango de K: 2–10
```

Todas las configuraciones utilizaron:

- El mismo conjunto Parquet.
- Los mismos 300 puntos.
- Las mismas 18 variables.
- El mismo periodo.
- La misma lógica de agregación.
- La misma semilla.
- El mismo ambiente.
- La misma versión del código.

## Resultados de rendimiento

| Workers | Estrategia | Tiempo promedio (s) | Speedup | Eficiencia (%) | Memoria (MiB) |
|---:|---|---:|---:|---:|---:|
| 1 | pandas secuencial | 26.07 | 1.00 | 100.03 | 9,291.40 |
| 2 | Dask | 14.87 | 1.75 | 87.71 | 10,417.93 |
| 4 | Dask | 10.50 | 2.48 | 62.10 | 14,338.02 |
| 8 | Dask | 8.92 | 2.92 | 36.55 | 20,374.23 |

### Interpretación

- Ocho workers produjeron el menor tiempo.
- Dos workers ofrecieron el mejor equilibrio entre velocidad, eficiencia y memoria.
- Cuatro workers representaron una alternativa intermedia.
- El speedup fue sublineal.
- La eficiencia disminuyó al aumentar los workers.
- La memoria aumentó con el paralelismo.

El valor de 100.03 % con un worker se debe a pequeñas diferencias entre el promedio de referencia y las corridas individuales. No representa una eficiencia física superior al 100 %.

## Calidad y consistencia del clustering

| Métrica | Resultado |
|---|---:|
| K recomendado | 5 |
| Silhouette | 0.441 |
| Davies–Bouldin | 0.822 |
| ARI | 1.000 |
| Coincidencia de etiquetas | 100 % |
| Semilla | 42 |

Interpretación:

- Silhouette indica una separación moderada.
- El valor quedó por debajo del objetivo exploratorio de 0.5.
- Davies–Bouldin cumplió el criterio de ser menor que 2.0.
- ARI demuestra que las asignaciones fueron consistentes entre workers y repeticiones.
- El paralelismo no modificó los clusters.

El experimento utilizó una semilla fija. Por tanto, el ARI no representa una prueba de estabilidad con múltiples semillas aleatorias.

## Perfiles obtenidos

| Cluster | Perfil | Puntos | País dominante |
|---:|---|---:|---|
| 0 | Híbrido alto | 59 | El Salvador |
| 1 | Bajo potencial relativo | 47 | Costa Rica |
| 2 | Solar dominante | 98 | Guatemala |
| 3 | Eólico dominante | 44 | Panamá |
| 4 | Híbrido alto | 52 | Belice |

## Organización de resultados

Los resultados se organizan por experimento, cantidad de workers y repetición:

```text
results/<experimento>/
├── summary.csv
├── workers-001/
│   ├── run-01/
│   │   ├── indicators.parquet
│   │   ├── cluster_profiles.json
│   │   └── manifest.json
│   ├── run-02/
│   └── run-03/
├── workers-002/
├── workers-004/
└── workers-008/
```

### Artefactos

- `indicators.parquet`: coordenadas, país, indicadores, scores y `cluster_id`.
- `cluster_profiles.json`: etiquetas, descripciones y perfiles.
- `manifest.json`: configuración, trazabilidad, estado y calidad.
- `summary.csv`: tiempo, memoria, baseline, speedup y eficiencia.

Esta organización evita sobrescrituras y permite reconstruir las tablas y visualizaciones.

## Dashboard en Streamlit

El dashboard consume los resultados agregados y no las 67.36 millones de observaciones horarias.

Permite:

- Seleccionar un experimento.
- Visualizar los 300 puntos en un mapa.
- Filtrar por país y perfil.
- Consultar scores solar, eólico e híbrido.
- Revisar los perfiles de los clusters.
- Consultar K, Silhouette y Davies–Bouldin.
- Comparar tiempo, memoria, speedup y eficiencia.

### Ejecutar localmente

```bash
python -m streamlit run dashboard/app.py
```

Para mostrar el resultado final debe existir:

```text
results/aws-geographic-300-full-range-v1/
```

Consulte también [docs/DASHBOARD.md](docs/DASHBOARD.md).

## Instalación local

### Requisitos

- Python 3.10 o superior.
- Python 3.12 recomendado.
- Git.
- Acceso HTTPS para utilizar NASA POWER.

### Clonar el repositorio

```bash
git clone https://github.com/KrisSo03/API_ParallelCompt.git
cd API_ParallelCompt
```

### Crear el ambiente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

En PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Verificación local

Las pruebas deterministas no requieren acceso a NASA POWER:

```bash
ruff check .
pytest
python main.py run-all --use-fake
python main.py benchmark --use-fake
```

`--use-fake` se utiliza para pruebas reproducibles y no representa la fuente del atlas final.

El flujo local tradicional puede generar:

```text
results/cluster_indicators.csv
results/cluster_indicators.parquet
results/cluster_profiles.csv
results/benchmark/benchmark_results.csv
results/benchmark/benchmark_results.parquet
```

Estas salidas no deben confundirse con la estructura experimental utilizada por el dashboard.

## Ejecución con Point API

NASA POWER no requiere API key:

```bash
python main.py run-all --workers 4
```

Para una prueba pequeña, configure temporalmente `.env`:

```dotenv
DATE_RANGE_START_YEAR=2023
DATE_RANGE_END_YEAR=2023
GRID_SIZE=5
GRID_SAMPLE_SIZE=5
```

No utilice `--use-fake` cuando el objetivo sea demostrar acceso a NASA POWER.

## Comandos principales

| Comando | Propósito |
|---|---|
| `python main.py download` | Descargar observaciones mediante Point API |
| `python main.py process --workers 4` | Preparar y calcular indicadores |
| `python main.py cluster --workers 4` | Agrupar y generar reportes |
| `python main.py run-all --workers 4` | Ejecutar el pipeline tradicional |
| `python main.py benchmark --use-fake` | Ejecutar benchmark determinista |
| `python -m renewable_atlas hpc-benchmark ...` | Ejecutar una matriz HPC |
| `python -m renewable_atlas aws-run ...` | Procesar un staging AWS |

## Prueba pequeña de AWS

Una prueba local pequeña o ejecutada dentro de un nodo de cómputo puede utilizar:

```bash
python -m renewable_atlas aws-run \
  --experiment-id aws-smoke \
  --points 8 \
  --start-date 2023-01-01 \
  --end-date 2023-01-07 \
  --target-gib 0.001 \
  --workers 1,2 \
  --download
```

Cada identificador de experimento debe ser único para evitar sobrescribir un staging existente.

## Ejecución en Kabré

> No ejecute instalaciones, pruebas, descargas ni el pipeline en los nodos de login.

Desde un nodo de login solamente se debe:

- Actualizar el repositorio.
- Enviar trabajos con `sbatch`.
- Consultar trabajos con `squeue` o `sacct`.
- Revisar logs y archivos terminados.

El trabajo computacional debe ejecutarse en un nodo asignado por Slurm.

### Preparar el ambiente

La creación o actualización del ambiente debe hacerse dentro de una asignación de cómputo:

```bash
module purge
module load mamba/python-3.12.11
source .venv-kabre/bin/activate
python -m pip check
```

Consulte [docs/KABRE.md](docs/KABRE.md) para la guía completa.

### Smoke test

Desde login, envíe el trabajo:

```bash
EXPERIMENT_ID=smoke-kabre \
POINTS=8 \
REPEATS=1 \
WORKERS=1,2 \
sbatch \
  --partition=kura-debug \
  --time=00:15:00 \
  hpc/kabre_benchmark.slurm
```

### Benchmark determinista

```bash
EXPERIMENT_ID=kabre-carga-300 \
POINTS=300 \
REPEATS=3 \
WORKERS=1,2,4,8 \
SOURCE=fake \
sbatch \
  --partition=kura \
  --time=04:00:00 \
  --mem=16G \
  hpc/kabre_benchmark.slurm
```

### Ruta masiva AWS

La adquisición y procesamiento se envían mediante:

```bash
sbatch \
  --partition=kura \
  --time=1-00:00:00 \
  --mem=32G \
  hpc/kabre_aws_5gb.slurm
```

La configuración específica del experimento debe definirse mediante las variables aceptadas por el script. Use un identificador nuevo para una nueva descarga.

La modalidad limitada por `TARGET_GIB` se conserva para pruebas exploratorias. El experimento final utilizó el modo `full-date-range` y no terminó por tamaño.

## Verificación en Kabré

### Consultar estado

```bash
squeue -u "$USER"
```

### Consultar una ejecución terminada

```bash
sacct -j <job-id> \
  --format=JobID,JobName,Partition,State,Elapsed,MaxRSS,AllocCPUS,ExitCode
```

### Revisar resultados

```bash
cat results/<experimento>/summary.csv
```

### Comparar consistencia

```bash
python hpc/compare_worker_consistency.py \
  results/<experimento>
```

Para el experimento final:

```bash
sacct -j 600690 \
  --format=JobID,JobName,Partition,State,Elapsed,MaxRSS,AllocCPUS,ExitCode

cat results/aws-geographic-300-full-range-v1/summary.csv

python hpc/compare_worker_consistency.py \
  results/aws-geographic-300-full-range-v1
```

Una corrida válida debe mostrar:

- Slurm: `COMPLETED`.
- Exit code: `0:0`.
- Manifiestos: `status: success`.
- Archivos generados para cada corrida.
- Resultados consistentes entre workers.

## Configuración

Las variables disponibles están documentadas en `.env.example`.

Ejemplo para el flujo Point API:

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

No incluya contraseñas, tokens o secretos dentro de `.env.example`.

## Reproducibilidad

La solución utiliza:

- GitHub para control de versiones.
- Ramas para trabajo independiente.
- Pull requests para revisión.
- Commits descriptivos.
- `requirements-kabre.txt` para dependencias en Kabré.
- `.env.example` para configuración sin secretos.
- Scripts Slurm para recursos computacionales.
- Semilla fija para K-Means.
- Manifiestos por corrida.
- Resultados separados por workers y repetición.
- Tres repeticiones por configuración.
- El mismo conjunto Parquet para todas las comparaciones.

Para comparar dos experimentos deben coincidir:

| Elemento | Evidencia |
|---|---|
| Código | Commit registrado en `manifest.json` |
| Entrada | Puntos, periodo y variables |
| Ambiente | Python y dependencias |
| Recursos | Workers, scheduler, CPUs y memoria |
| Algoritmo | Semilla y rango de K |
| Repeticiones | Misma cantidad por configuración |

## Estructura del proyecto

```text
API_ParallelCompt/
├── dashboard/              # aplicación Streamlit
├── src/renewable_atlas/
│   ├── application/        # pipeline y servicios
│   ├── composition/        # ensamblaje de dependencias
│   ├── config/             # configuración
│   ├── domain/             # modelos e interfaces
│   └── infrastructure/     # NASA, AWS, Dask, K-Means y persistencia
├── hpc/                    # scripts Slurm y validación
├── docs/
│   ├── KABRE.md            # guía operativa de Kabré
│   └── DASHBOARD.md        # guía del dashboard
├── tests/                  # pruebas automatizadas
├── requirements-kabre.txt  # dependencias de Kabré
├── .env.example            # configuración sin secretos
├── main.py                 # punto de entrada
└── pyproject.toml          # paquete y herramientas
```

## Calidad y seguridad

Antes de crear un pull request:

```bash
ruff check .
pytest
git diff --check
```

Buenas prácticas aplicadas:

- Código modular por capas.
- Interfaces para desacoplar servicios.
- Dependencias definidas.
- Pruebas unitarias y de integración.
- Análisis estático con Ruff.
- Variables de entorno.
- Ausencia de credenciales en el repositorio.
- Identificadores de experimento validados.
- Resultados masivos fuera de Git.
- Ejecución intensiva únicamente mediante Slurm.

No suba:

- Contraseñas.
- Tokens.
- Archivos `.env`.
- Ambientes virtuales.
- Datos masivos.
- Resultados temporales innecesarios.

## Limitaciones

- Los valores climáticos provienen de NASA POWER y no de sensores instalados en cada punto.
- `WS100M` es una estimación.
- Los indicadores son relativos al conjunto procesado.
- Silhouette quedó por debajo del objetivo exploratorio de 0.5.
- El experimento utilizó una semilla fija y no evaluó estabilidad con múltiples semillas.
- La aceleración fue sublineal.
- El consumo de memoria aumentó con los workers.
- El análisis no incluye terreno, red eléctrica, restricciones ambientales ni costos.
- El atlas no sustituye un estudio definitivo de factibilidad.

## Trabajo futuro

- Evaluar múltiples semillas de K-Means.
- Comparar otros algoritmos de clustering.
- Ejecutar el pipeline en más de un nodo.
- Explorar otras configuraciones del scheduler de Dask.
- Incorporar variables de infraestructura y restricciones territoriales.
- Añadir análisis estacionales y series temporales.
- Exportar ubicaciones prioritarias desde el dashboard.
