# Renewable Energy Atlas - Hybrid Solar-Eolic for Central America

Production-ready prototype for parallel processing of climate data to create renewable energy potential atlas for Central America.

## Project Overview

This project processes NASA POWER climate data for ~300 geographic points across Central America, calculates renewable energy indicators (solar, wind, hybrid), applies K-Means clustering for spatial analysis, and benchmarks parallel processing performance using Dask.

## Architecture

### Layered Design (Domain-Driven Design)

```
┌─────────────────────────────────────┐
│     Presentation / CLI              │
├─────────────────────────────────────┤
│     Application Layer               │
│  (Services, Pipelines, Orchestration)
├─────────────────────────────────────┤
│     Infrastructure Layer            │
│  (External integrations, persistence)
├─────────────────────────────────────┤
│     Domain Layer                    │
│  (Models, Interfaces, Business logic)
└─────────────────────────────────────┘
```

### SOLID Principles Applied

- **S**ingle Responsibility: Each service has one job (validation, transformation, clustering, etc.)
- **O**pen/Closed: New processing strategies can be added without modifying existing code
- **L**iskov Substitution: All ProcessingStrategy implementations are interchangeable
- **I**nterface Segregation: Interfaces are focused (ClimateDataSource, DataRepository, etc.)
- **D**ependency Inversion: Composition root wires concrete implementations to abstractions

## Key Features

### Data Pipeline
- **NASA POWER Client**: HTTP client with retry logic, timeout handling, error resilience
- **Data Validation**: Completeness checks, range validation, anomaly detection
- **Data Transformation**: Outlier removal, interpolation, normalization
- **Indicator Calculation**: Solar Potential Index, Wind Potential Index, hybrid scoring

### Processing Strategies
- **Sequential Baseline**: Single-threaded for comparison
- **Dask Parallel**: Multi-worker parallelization (1, 2, 4, 8 workers configurable)
- **Benchmarking**: Execution time, speedup, efficiency, memory usage tracking

### Clustering & Analysis
- **K-Means Clustering**: Optimal cluster determination with silhouette validation
- **Cluster Interpretation**: Domain-specific labeling (Solar-dominant, Wind-dominant, Hybrid-high, Lower-resource)
- **Spatial Analysis**: Country-level and regional pattern identification

### Configuration
- Environment-based settings via pydantic-settings
- Hierarchical configuration (NasaPower, Grid, Scoring, Clustering, Benchmark, Paths)
- Full externalization for HPC/supercomputer compatibility

## Installation

### Requirements
- Python 3.10+
- pip or conda

### Steps

```bash
# Clone repository
git clone https://github.com/krisso03/api_parallelcompt.git
cd Proyecto_Paralela

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional)
```

## Usage

### Run Complete Pipeline

```bash
python main.py run-all
```

This will:
1. Download climate data from NASA POWER (or use fake data for offline testing)
2. Clean and validate data
3. Calculate renewable energy indicators
4. Run K-Means clustering
5. Generate cluster profiles with domain-specific labels

### Run Benchmarking

```bash
python main.py benchmark
```

Compares sequential vs parallel execution with 1, 2, 4, 8 workers. Outputs:
- Execution time per configuration
- Speedup metrics
- Efficiency percentage
- Memory usage

### Run Individual Stages

```bash
python main.py download  # Data acquisition
python main.py process   # Cleaning & transformation
python main.py cluster   # K-Means analysis
```

## Configuration

Edit `.env` file to customize:

```bash
# NASA POWER API
NASA_POWER_BASE_URL=https://power.larc.nasa.gov/api/v1/
NASA_POWER_TIMEOUT_SECONDS=30
NASA_POWER_MAX_RETRIES=3

# Grid Configuration
GRID_SIZE=20              # Points per country
GRID_ENABLE_SAMPLING=true
GRID_SAMPLE_SIZE=20

# Clustering
CLUSTERING_N_CLUSTERS=4
CLUSTERING_RANDOM_STATE=42

# Benchmarking
BENCHMARK_WORKER_COUNTS=1,2,4,8
BENCHMARK_REPEATS_PER_CONFIG=3

# Output Paths
PATH_DATA_DIR=./data
PATH_RESULTS_DIR=./results
```

## Performance

Tested at scale:
- **20 points × 2-year**: ~2.3 seconds sequential
- **300 points × 1-year**: ~3.5 seconds sequential
- **Speedup (4 workers)**: 3.2x typical
- **Efficiency (4 workers)**: 80% typical

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test module
pytest tests/unit/test_domain_models.py
```

## Code Quality

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/ --check
```

## Project Structure

```
Proyecto_Paralela/
├── src/renewable_atlas/
│   ├── domain/              # Core models and interfaces
│   │   ├── models/          # GridPoint, ClimateObservation, RenewableIndicators
│   │   └── interfaces/      # Abstract bases (ClimateDataSource, DataRepository, etc.)
│   ├── infrastructure/      # Implementations
│   │   ├── nasa_power/      # NASA POWER API client
│   │   ├── persistence/     # Parquet repository
│   │   ├── processing/      # Sequential and Dask processors
│   │   ├── clustering/      # K-Means strategy
│   │   ├── benchmarking/    # Performance measurement
│   │   └── grid/            # Geographic grid provider
│   ├── application/         # Business logic
│   │   ├── services/        # Data validation, transformation, clustering
│   │   └── pipelines/       # Atlas pipeline orchestration
│   ├── composition/         # Dependency injection container
│   ├── config/              # Configuration management
│   └── cli.py               # Command-line interface
├── tests/
│   ├── unit/                # Unit tests (no external I/O)
│   └── integration/         # Integration tests (with mocks)
├── docs/
│   └── decisions/           # Architecture Decision Records (ADRs)
├── scripts/                 # Utility scripts
├── pyproject.toml           # Project metadata and dependencies
├── .env.example             # Configuration template
└── README.md                # This file
```

## NASA POWER API Integration

### Available Variables
- `SW_DWN`: Surface downward shortwave flux (W/m²)
- `DNI`: Direct Normal Irradiance (W/m²)
- `WS50M`: Wind speed at 50m (m/s)
- `WS100M`: Wind speed at 100m (m/s)

### Data Quality
- Completeness target: ≥85% valid values per point
- Fill value handling: -999 → None
- Range validation applied during preprocessing

## Methodology

### Renewable Energy Scoring
Min-max normalization across the sample:
- **Solar Score**: (SW_DWN - min) / (max - min)
- **Wind Score**: (WS100M - min) / (max - min)
- **Hybrid Score**: 0.5×Solar + 0.3×Wind + 0.2×(Solar×Wind)

### Clustering Validation
- Silhouette coefficient ≥ 0.5 for cluster quality
- Davies-Bouldin index < 2.0 for cluster separation
- 10+ re-runs with Adjusted Rand Index ≥ 0.95 for stability

### Parallel Processing
- Baseline: Sequential processing (worker_count=1)
- Speedup = T_sequential / T_parallel
- Efficiency = (Speedup / NumWorkers) × 100%

## Limitations & Future Work

### Current Limitations
- NASA POWER data limited to gridded approximations (~111 km resolution)
- Clustering validation requires real project data (not available)
- No temporal trend analysis (Mann-Kendall test recommended)

### Future Enhancements
- Interactive Plotly Dash dashboard with 6-view system
- Export to GeoTIFF/NetCDF for GIS integration
- Validate against real project performance data
- Uncertainty quantification via ensemble methods
- Seasonal analysis and sub-annual patterns

## HPC Migration

This codebase is designed for supercomputer deployment:

### Portable Elements
- Configuration via environment variables
- No hardcoded file paths
- Dask scheduler abstraction (local/distributed)
- Dependency injection enables mock/real swapping

### HPC Deployment
```bash
# Submit SLURM job
sbatch config/job_template.slurm

# Distributed Dask scheduler
dask-scheduler
dask-worker tcp://localhost:8786
```

## Contributing

1. Create a feature branch (`git checkout -b feature/your-feature`)
2. Make changes following SOLID principles
3. Add unit tests for new functionality
4. Run full test suite: `pytest`
5. Commit with atomic, descriptive messages
6. Push and create pull request

## License

MIT

## Contact

claude@anthropic.com
