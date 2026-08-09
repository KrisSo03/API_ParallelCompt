# Guía de ejecución en Kabré

El proyecto usa Slurm y Dask dentro de un único nodo. No ejecute el pipeline,
las pruebas ni los benchmarks directamente en los nodos `login`.

## 1. Preparar el código y el ambiente

En el nodo login limite las acciones a conexión y Slurm. Solicite una sesión
interactiva y prepare el repositorio dentro del nodo de cómputo asignado:

```bash
srun --partition=kura-debug --time=00:30:00 --cpus-per-task=2 --mem=4G --pty bash
hostname  # debe mostrar kura-..., nunca login-...
git clone https://github.com/KrisSo03/API_ParallelCompt.git
cd API_ParallelCompt
git checkout <commit-o-tag-del-experimento>
module purge
module load mamba/python-3.12.11
bash hpc/bootstrap_kabre.sh "$PWD"
mkdir -p outputs/slurm
exit
```

Ya en login, confirme con `sinfo` que `kura` está disponible. Si conviene otra partición,
puede sobrescribirla al enviar el trabajo con `sbatch --partition=<nombre>`.

## 2. Prueba mínima en una partición debug

```bash
EXPERIMENT_ID=smoke-kabre POINTS=8 REPEATS=1 WORKERS=1,2 \
  sbatch --partition=kura-debug --time=00:15:00 hpc/kabre_benchmark.slurm
```

Monitoree sin ejecutar carga en login:

```bash
squeue -u "$USER"
sacct -j <job-id> --format=JobID,State,Elapsed,MaxRSS,AllocCPUS,ExitCode
```

El resultado correcto es `COMPLETED` con `ExitCode=0:0`.

## 3. Prueba de carga reproducible

Para calcular métricas comparables con una sola entrada, ejecute la matriz
completa dentro de un job:

```bash
EXPERIMENT_ID=kabre-carga-300 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_benchmark.slurm
```

El job array queda disponible para probar estabilidad o configuraciones
independientes, pero sus archivos separados no comparten baseline. Para el
informe de speedup y eficiencia use `kabre_benchmark.slurm`.

La fuente sintética es determinista y sirve para medir estabilidad sin depender
de internet. Para NASA POWER use un solo benchmark, que descarga una vez:

```bash
EXPERIMENT_ID=kabre-nasa-20 POINTS=20 REPEATS=3 SOURCE=nasa \
  sbatch hpc/kabre_benchmark.slurm
```

Confirme primero que los nodos de cómputo pueden usar HTTPS. NASA POWER puede
bloquear solicitudes repetidas sobre las mismas celdas; no lance cargas masivas
contra la API sin autorización.

## 4. Resultados

```text
results/<experimento>/
├── summary.csv
├── workers-001/run-01/
│   ├── indicators.parquet
│   ├── cluster_profiles.json
│   └── manifest.json
└── workers-008/run-03/...
```

Cada manifiesto registra estado, duración, memoria RSS pico del árbol de
procesos, K recomendado y métricas de calidad, configuración, checksum del grid,
commit, Python, hostname y job Slurm. `summary.csv` añade el baseline promedio,
speedup y eficiencia por repetición. Una configuración es estable si todas sus
repeticiones tienen `status=success`, el checksum coincide y Slurm no reporta
`OUT_OF_MEMORY`, `TIMEOUT` ni códigos de salida distintos de cero.

Comience con 8 puntos, continúe con 50 y finalmente pruebe 300 o más.

Para documentar la evidencia final:

```bash
cat results/kabre-carga-300/summary.csv
sacct -j <job-id> --format=JobID,State,Elapsed,MaxRSS,AllocCPUS,ExitCode
python hpc/compare_worker_consistency.py results/kabre-carga-300
```
