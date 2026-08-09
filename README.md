# Atlas de Energía Renovable - Híbrido Solar-Eólico para Centroamérica

Prototipo listo para producción para el procesamiento paralelo de datos climáticos, con el fin de crear un atlas de potencial de energía renovable para Centroamérica.

## Descripción General del Proyecto

Este proyecto procesa datos climáticos de NASA POWER para ~300 puntos geográficos en Centroamérica, calcula indicadores de energía renovable (solar, eólica, híbrida), aplica clustering K-Means para análisis espacial, y evalúa el rendimiento del procesamiento paralelo usando Dask.

## Arquitectura

### Diseño por Capas (Domain-Driven Design)

```
┌─────────────────────────────────────┐
│     Presentación / CLI              │
├─────────────────────────────────────┤
│     Capa de Aplicación              │
│  (Servicios, Pipelines, Orquestación)
├─────────────────────────────────────┤
│     Capa de Infraestructura         │
│  (Integraciones externas, persistencia)
├─────────────────────────────────────┤
│     Capa de Dominio                 │
│  (Modelos, Interfaces, Lógica de negocio)
└─────────────────────────────────────┘
```

### Principios SOLID Aplicados

- **S**ingle Responsibility (Responsabilidad Única): Cada servicio tiene una sola función (validación, transformación, clustering, etc.)
- **O**pen/Closed (Abierto/Cerrado): Se pueden agregar nuevas estrategias de procesamiento sin modificar el código existente
- **L**iskov Substitution (Sustitución de Liskov): Todas las implementaciones de ProcessingStrategy son intercambiables
- **I**nterface Segregation (Segregación de Interfaces): Las interfaces son específicas (ClimateDataSource, DataRepository, etc.)
- **D**ependency Inversion (Inversión de Dependencias): La composition root conecta implementaciones concretas con abstracciones

## Características Principales

### Pipeline de Datos
- **Cliente NASA POWER**: Cliente HTTP con lógica de reintentos, manejo de timeouts y resiliencia ante errores
- **Validación de Datos**: Verificación de completitud, validación de rangos, detección de anomalías
- **Transformación de Datos**: Normalización de sentinels y valores no finitos,
  eliminación de duplicados y validación de rangos
- **Cálculo de Indicadores**: Índice de Potencial Solar, Índice de Potencial Eólico, puntuación híbrida

### Estrategias de Procesamiento
- **Línea Base Secuencial**: Procesamiento de un solo hilo para comparación
- **Paralelo con Dask**: Paralelización multi-worker (1, 2, 4, 8 workers configurables)
- **Benchmarking**: Medición de tiempo de ejecución, speedup, eficiencia y uso de memoria

### Clustering y Análisis
- **Clustering K-Means**: Determinación óptima de clusters con validación por silhouette
- **Interpretación de Clusters**: Etiquetado específico del dominio (Dominante-solar, Dominante-eólico, Híbrido-alto, Recurso-bajo)
- **Análisis Espacial**: Identificación de patrones a nivel de país y regionales

### Configuración
- Configuración basada en variables de entorno mediante pydantic-settings
- Configuración jerárquica (NasaPower, Grid, Scoring, Clustering, Benchmark, Paths)
- Totalmente externalizable para compatibilidad con HPC/supercomputadoras

## Instalación

### Requisitos
- Python 3.10+
- pip o conda

### Pasos

```bash
# Clonar el repositorio
git clone https://github.com/krisso03/api_parallelcompt.git
cd Proyecto_Paralela

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -e ".[dev]"

# Copiar plantilla de entorno
cp .env.example .env

# Editar .env con tu configuración (opcional)
```

## Uso

### Ejecutar el Pipeline Completo

```bash
python main.py run-all
```

Esto realizará lo siguiente:
1. Descargar datos climáticos reales de NASA POWER para 300 puntos por defecto
2. Limpiar y validar los datos
3. Calcular indicadores de energía renovable
4. Evaluar automáticamente K=2..10 y ejecutar K-Means con el mejor silhouette
5. Generar perfiles de clusters con etiquetas específicas del dominio

Los datos simulados son únicamente una opción reproducible para pruebas y
benchmarks sin depender de internet:

```bash
python main.py run-all --use-fake
```

### Ejecutar Benchmarking

```bash
python main.py benchmark
```

Compara la ejecución secuencial contra la paralela con 1, 2, 4 y 8 workers. Genera:
- Tiempo de ejecución por configuración
- Métricas de speedup
- Porcentaje de eficiencia
- Uso de memoria

### Ejecutar Etapas Individuales

```bash
python main.py download  # Adquisición de datos
python main.py process   # Limpieza y transformación
python main.py cluster   # Análisis K-Means
```

## Configuración

Edita el archivo `.env` para personalizar:

```bash
# API de NASA POWER
NASA_POWER_BASE_URL=https://power.larc.nasa.gov/api/
NASA_POWER_TIMEOUT_SECONDS=30
NASA_POWER_MAX_RETRIES=3

# Configuración de la grilla (300 puntos totales por defecto)
GRID_SIZE=300
GRID_ENABLE_SAMPLING=true
GRID_SAMPLE_SIZE=300

# Clustering
CLUSTERING_AUTO_SELECT=true
CLUSTERING_MIN_CLUSTERS=2
CLUSTERING_MAX_CLUSTERS=10
CLUSTERING_N_CLUSTERS=5   # respaldo si se desactiva la selección automática
CLUSTERING_RANDOM_STATE=42

# Benchmarking
BENCHMARK_WORKER_COUNTS=1,2,4,8
BENCHMARK_REPEATS_PER_CONFIG=3

# Rutas de Salida
PATH_DATA_DIR=./data
PATH_RESULTS_DIR=./results
```

## Rendimiento y escalabilidad

El proyecto mide por configuración y repetición: tiempo, memoria RSS pico del
proceso coordinador más sus workers, speedup y eficiencia. El baseline es el
promedio de las repeticiones con un worker, no una repetición aislada:

- `speedup = promedio(T_1_worker) / T_workers`
- `eficiencia = speedup / workers × 100`

Las cifras finales deben obtenerse en Kabré con el mismo commit, entrada y
checksum. No se publican valores estimados como si fueran resultados reales.
La corrida recomendada de 300 puntos genera la evidencia en
`results/<experimento>/summary.csv`; `sacct` complementa la memoria y el estado
reportados por Slurm. Consulte [la guía de Kabré](docs/KABRE.md).

## Pruebas

```bash
# Ejecutar todas las pruebas
pytest

# Ejecutar con cobertura
pytest --cov=src

# Ejecutar un módulo de pruebas específico
pytest tests/unit/test_domain_models.py
```

## Calidad de Código

```bash
# Verificación de tipos
mypy src/

# Linting
ruff check .

# Formateo
black src/ --check
```

## Estructura del Proyecto

```
Proyecto_Paralela/
├── src/renewable_atlas/
│   ├── domain/              # Modelos e interfaces principales
│   │   ├── models/          # GridPoint, ClimateObservation, RenewableIndicators
│   │   └── interfaces/      # Clases base abstractas (ClimateDataSource, DataRepository, etc.)
│   ├── infrastructure/      # Implementaciones
│   │   ├── nasa_power/      # Cliente de la API NASA POWER
│   │   ├── persistence/     # Repositorio Parquet
│   │   ├── processing/      # Procesadores secuencial y Dask
│   │   ├── clustering/      # Estrategia K-Means
│   │   ├── benchmarking/    # Medición de rendimiento
│   │   └── grid/            # Proveedor de grilla geográfica
│   ├── application/         # Lógica de negocio
│   │   ├── services/        # Validación, transformación y clustering de datos
│   │   └── pipelines/       # Orquestación del pipeline del atlas
│   ├── composition/         # Contenedor de inyección de dependencias
│   ├── config/              # Gestión de configuración
│   └── cli.py               # Interfaz de línea de comandos
├── tests/
│   ├── unit/                # Pruebas unitarias (sin I/O externo)
│   └── integration/         # Pruebas de integración (con mocks)
├── docs/
│   └── decisions/           # Registros de Decisiones de Arquitectura (ADRs)
├── scripts/                 # Scripts de utilidad
├── pyproject.toml           # Metadatos y dependencias del proyecto
├── .env.example             # Plantilla de configuración
└── README.md                # Este archivo
```

## Integración con la API de NASA POWER

### Variables disponibles

Se conservan las 18 variables solicitadas a NASA POWER: radiación solar,
viento, temperatura, presión, humedad, precipitación y nubosidad. Entre ellas
están `ALLSKY_SFC_SW_DWN`, `ALLSKY_SFC_SW_DNI`, `WS10M` y `WS50M`. NASA POWER
no entrega `WS100M` en esta consulta: `ws_100m` se deriva explícitamente desde
`WS50M` con la ley de potencia de exponente 1/7 y queda identificado así en el
código.

### Calidad de Datos
- Umbral técnico mínimo: ≥50% de datos válidos en `sw_dwn`, `dni`, `ws_50m`
  y `ws_100m`; por debajo de este valor se detiene el punto
- Objetivo metodológico de calidad: ≥85% de completitud, registrado como meta
  de la propuesta y no confundido con el umbral mínimo de ejecución
- Manejo de valores de relleno: -999 → None
- Reportes pre-clean y post-clean en memoria; la decisión usa el post-clean
- Validación de rangos aplicada durante el preprocesamiento

## Metodología

### Puntuación de Energía Renovable
Normalización min-max sobre la muestra:
- **Puntuación Solar**: (SW_DWN - min) / (max - min)
- **Puntuación Eólica**: (`ws_100m` derivada - min) / (max - min)
- **Puntuación Híbrida**: 0.5×Solar + 0.3×Eólica + 0.2×(Solar×Eólica)

### Validación de Clustering
- Coeficiente de silhouette ≥ 0.5 para calidad de cluster
- Índice de Davies-Bouldin < 2.0 para separación de clusters
- Índice de Rand Ajustado ≥ 0.95 en las corridas de estabilidad configuradas

### Procesamiento Paralelo
- Línea base: procesamiento secuencial (worker_count=1)
- Speedup = T_secuencial / T_paralelo
- Eficiencia = (Speedup / NúmeroDeWorkers) × 100%

## Limitaciones y Trabajo Futuro

### Limitaciones Actuales
- Los datos de NASA POWER están limitados a aproximaciones en grilla (~111 km de resolución)
- La validación del clustering requiere datos reales de proyectos (no disponibles)
- No hay análisis de tendencias temporales (se recomienda la prueba de Mann-Kendall)

### Mejoras Futuras
- Dashboard interactivo (se integra por medio de los CSV estables de `results/`)
- Exportación a GeoTIFF/NetCDF para integración con SIG
- Validación contra datos reales de rendimiento de proyectos
- Cuantificación de incertidumbre mediante métodos de conjunto (ensemble)
- Análisis estacional y de patrones sub-anuales

## Migración a HPC

Este código está diseñado para despliegue en supercomputadoras:

### Elementos Portables
- Configuración mediante variables de entorno
- Sin rutas de archivo codificadas de forma fija
- Abstracción del scheduler de Dask (local/distribuido)
- La inyección de dependencias permite intercambiar entre mocks y componentes reales

### Despliegue en HPC

La guía completa de Kabré está disponible en [`docs/KABRE.md`](docs/KABRE.md).
Incluye ambiente fijado, particiones Slurm, prueba debug, matriz de workers,
monitoreo y organización reproducible de resultados.

```bash
# Desde login: enviar el cálculo a Slurm; no instalar ni ejecutar el pipeline
EXPERIMENT_ID=kabre-carga-300 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_benchmark.slurm
```

La preparación del ambiente se realiza en una asignación de cómputo, como
explica la guía. El script `kabre_benchmark.slurm` es la fuente principal de
métricas comparables porque reutiliza una única descarga/entrada para toda la
matriz 1, 2, 4 y 8.

## Contratos de salida

Los comandos `run-all --use-fake` y `benchmark --use-fake` regeneran, sin
renombrar columnas existentes:

- `results/cluster_indicators.csv`: identidad, coordenadas, país, indicadores,
  scores y `cluster_id` por punto.
- `results/cluster_profiles.csv`: etiqueta y descripción por cluster.
- `results/benchmark/benchmark_results.csv`: tiempo, workers, memoria, speedup
  y eficiencia.

La selección automática de K y las métricas HPC no cambian los retornos
`process() -> indicators_df` ni
`run() -> (indicators_df, labels, profiles)`, por lo que el dashboard mantiene
su contrato.

## Contribuciones

1. Crea una rama de funcionalidad (`git checkout -b feature/tu-funcionalidad`)
2. Realiza cambios siguiendo los principios SOLID
3. Agrega pruebas unitarias para la nueva funcionalidad
4. Ejecuta la suite completa de pruebas: `pytest`
5. Haz commits atómicos y descriptivos
6. Haz push y crea un pull request
