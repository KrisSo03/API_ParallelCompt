# Guía de ejecución en Kabré

El proyecto usa Slurm y Dask dentro de un único nodo. No ejecute el pipeline,
las pruebas ni los benchmarks directamente en los nodos `login`.

## 1. Preparar el código

Desde el nodo login se permiten tareas ligeras:

```bash
git clone https://github.com/KrisSo03/API_ParallelCompt.git
cd API_ParallelCompt
git checkout <commit-o-tag-del-experimento>
module avail python
module load <modulo-python-3.10-o-superior>
bash hpc/bootstrap_kabre.sh "$PWD"
mkdir -p outputs/slurm
```

Confirme con `sinfo` que `kura` está disponible. Si conviene otra partición,
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

El job array crea cuatro tareas independientes para 1, 2, 4 y 8 workers:

```bash
EXPERIMENT_ID=kabre-carga-300 POINTS=300 REPEATS=3 \
  sbatch hpc/kabre_job_array.slurm
```

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

Cada manifiesto registra estado, duración, configuración, checksum del grid,
commit, Python, hostname y job Slurm. Una configuración es estable si todas sus
repeticiones tienen `status=success`, el checksum coincide y Slurm no reporta
`OUT_OF_MEMORY`, `TIMEOUT` ni códigos de salida distintos de cero.

Comience con 8 puntos, continúe con 50 y finalmente pruebe 300 o más.
