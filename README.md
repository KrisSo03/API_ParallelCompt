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
- **Transformación de Datos**: Eliminación de outliers, interpolación, normalización
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
1. Descargar datos climáticos de NASA POWER (o usar datos simulados para pruebas sin conexión)
2. Limpiar y validar los datos
3. Calcular indicadores de energía renovable
4. Ejecutar clustering K-Means
5. Generar perfiles de clusters con etiquetas específicas del dominio

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

# Configuración de la Grilla
GRID_SIZE=20              # Puntos por país
GRID_ENABLE_SAMPLING=true
GRID_SAMPLE_SIZE=20

# Clustering
CLUSTERING_N_CLUSTERS=4
CLUSTERING_RANDOM_STATE=42

# Benchmarking
BENCHMARK_WORKER_COUNTS=1,2,4,8
BENCHMARK_REPEATS_PER_CONFIG=3

# Rutas de Salida
PATH_DATA_DIR=./data
PATH_RESULTS_DIR=./results
```

## Rendimiento

Probado a escala:
- **20 puntos × 2 años**: ~2.3 segundos en modo secuencial
- **300 puntos × 1 año**: ~3.5 segundos en modo secuencial
- **Speedup (4 workers)**: 3.2x típico
- **Eficiencia (4 workers)**: 80% típico

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
ruff check src/

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

### Variables Disponibles
- `SW_DWN`: Flujo de onda corta descendente en superficie (W/m²)
- `DNI`: Irradiancia Normal Directa (W/m²)
- `WS50M`: Velocidad del viento a 50m (m/s)
- `WS100M`: Velocidad del viento a 100m (m/s)

### Calidad de Datos
- Objetivo de completitud: ≥85% de valores válidos por punto
- Manejo de valores de relleno: -999 → None
- Validación de rangos aplicada durante el preprocesamiento

## Metodología

### Puntuación de Energía Renovable
Normalización min-max sobre la muestra:
- **Puntuación Solar**: (SW_DWN - min) / (max - min)
- **Puntuación Eólica**: (WS100M - min) / (max - min)
- **Puntuación Híbrida**: 0.5×Solar + 0.3×Eólica + 0.2×(Solar×Eólica)

### Validación de Clustering
- Coeficiente de silhouette ≥ 0.5 para calidad de cluster
- Índice de Davies-Bouldin < 2.0 para separación de clusters
- 10+ re-ejecuciones con Índice de Rand Ajustado ≥ 0.95 para estabilidad

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
- Dashboard interactivo con Plotly Dash con sistema de 6 vistas
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
# Preparar el ambiente (tarea ligera en login)
bash hpc/bootstrap_kabre.sh "$PWD"
mkdir -p outputs/slurm

# Enviar el cálculo a Slurm; no ejecutar el pipeline en login
EXPERIMENT_ID=kabre-carga-300 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_job_array.slurm
```

## Contribuciones

1. Crea una rama de funcionalidad (`git checkout -b feature/tu-funcionalidad`)
2. Realiza cambios siguiendo los principios SOLID
3. Agrega pruebas unitarias para la nueva funcionalidad
4. Ejecuta la suite completa de pruebas: `pytest`
5. Haz commits atómicos y descriptivos
6. Haz push y crea un pull request
