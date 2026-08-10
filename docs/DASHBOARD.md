# Guía del dashboard del Atlas de Energía Renovable

## Propósito

El dashboard presenta resultados terminados del pipeline. No descarga datos, no ejecuta K-Means
y no inicia trabajos de Dask. Puede leer experimentos generados localmente o en Kabré con la misma
estructura de archivos.

```text
NASA POWER o fuente fake
        ↓
Pipeline local o trabajo Slurm en Kabré
        ↓
results/<experimento>/
        ↓
Dashboard Streamlit
```

## Preparación local

El entorno de referencia usa Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-kabre.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
```

Para abrir la aplicación:

```powershell
python -m streamlit run dashboard/app.py
```

La dirección local predeterminada es `http://localhost:8501`.

## Experimentos locales de validación

### Atlas con datos reales

Esta corrida valida NASA POWER, el mapa, los índices, perfiles y calidad. Con un solo worker no
permite evaluar escalabilidad.

```powershell
$env:DATE_RANGE_START_YEAR="2023"
$env:DATE_RANGE_END_YEAR="2023"

python main.py hpc-run `
  --experiment-id nasa-dashboard-current `
  --source nasa `
  --points 8 `
  --workers 1 `
  --repeats 1 `
  --results-dir results
```

### Dashboard y rendimiento

Esta corrida usa una entrada fake determinista y permite comparar configuraciones sin depender de
la red o latencia de NASA POWER.

```powershell
$env:DATE_RANGE_START_YEAR="2023"
$env:DATE_RANGE_END_YEAR="2023"

python main.py hpc-benchmark `
  --experiment-id dashboard-full-local `
  --source fake `
  --points 40 `
  --workers "1,2,4,8" `
  --repeats 2 `
  --results-dir results `
  --scheduler processes
```

Al terminar las pruebas:

```powershell
Remove-Item Env:DATE_RANGE_START_YEAR
Remove-Item Env:DATE_RANGE_END_YEAR
```

Los resultados locales no se agregan a Git.

## Contrato de resultados

```text
results/<experimento>/
├── summary.csv
├── workers-001/
│   └── run-01/
│       ├── indicators.parquet
│       ├── cluster_profiles.json
│       └── manifest.json
└── workers-008/
    └── run-03/...
```

- `indicators.parquet`: puntos, coordenadas, país, variables climáticas, índices y `cluster_id`.
- `cluster_profiles.json`: etiqueta e interpretación de cada cluster.
- `manifest.json`: fuente, estado, configuración, memoria y calidad del clustering.
- `summary.csv`: tiempos, memoria, baseline, speedup y eficiencia por repetición.

El dashboard rechaza corridas incompletas, fallidas, sin coordenadas válidas, con índices fuera de
`[0, 1]` o sin perfiles para los clusters encontrados.

## Uso de resultados en otra ruta

La carpeta `results/` es solamente el valor predeterminado. Para abrir resultados descargados de
Kabré sin copiarlos dentro del repositorio:

```powershell
$env:ATLAS_RESULTS_DIR="C:\ruta\a\resultados-kabre"
python -m streamlit run dashboard/app.py
```

En Linux:

```bash
export ATLAS_RESULTS_DIR="/ruta/a/resultados-kabre"
python -m streamlit run dashboard/app.py
```

La ruta configurada debe contener directamente los directorios de experimentos.

## Resultados de Kabré

La ejecución del pipeline debe realizarse mediante Slurm siguiendo [KABRE.md](KABRE.md). La opción
más sencilla para presentar el atlas es:

1. Ejecutar el benchmark oficial en Kabré.
2. Verificar Slurm, manifiestos y consistencia entre workers.
3. Descargar la carpeta completa `results/<experimento>` a la computadora de presentación.
4. Configurar `ATLAS_RESULTS_DIR` para apuntar a la carpeta descargada.
5. Ejecutar Streamlit localmente.

Servir Streamlit desde un nodo de Kabré y acceder mediante túnel SSH depende de las políticas de
red del centro. No debe asumirse como disponible sin confirmación administrativa.

## Vistas disponibles

### Resumen general

Presenta todos los puntos de la corrida, promedios de índices relativos, perfil más frecuente y
mejores ubicaciones observadas.

### Atlas interactivo

Permite filtrar por país y perfil energético. El color representa el perfil regional producido por
el pipeline. La tarjeta de cada punto muestra su fortaleza principal y los tres índices relativos.

### Comparación

Compara los promedios de dos o tres países. Los porcentajes son relativos al conjunto del
experimento, no estimaciones absolutas de producción energética.

### Calidad y metodología

Muestra el mejor K observado, Silhouette, Davies–Bouldin, estabilidad ARI cuando esté disponible y
el origen de cada resultado. El mejor K observado no necesariamente cumple todos los umbrales.

### Rendimiento

Agrupa las métricas generadas por el pipeline. Usa `baseline_seconds`, `speedup` y
`efficiency_percent` del `summary.csv`; Streamlit no cambia sus fórmulas.

## Interpretación correcta

- Un índice de 100 % significa que el punto alcanzó el máximo dentro del experimento.
- No significa un potencial energético absoluto de 100 %.
- Los clusters se calculan con variables climáticas estandarizadas.
- Los clusters matemáticos se interpretan posteriormente como perfiles solares, eólicos, híbridos
  o de bajo potencial.
- Más de un cluster puede compartir el mismo perfil energético.
- Workers y repeticiones deben producir el mismo atlas; sus diferencias corresponden al
  rendimiento computacional.

## Lista de validación

Antes de una demostración:

- [ ] El entorno usa Python 3.12 y `python -m pip check` termina correctamente.
- [ ] El experimento aparece en el selector lateral.
- [ ] El encabezado identifica correctamente fuente fake o NASA.
- [ ] Resumen general muestra la cantidad esperada de puntos y países.
- [ ] El mapa carga y permite filtrar por país y perfil.
- [ ] La tarjeta del mapa muestra perfil regional, fortaleza e índices relativos.
- [ ] Comparación permite seleccionar al menos dos países.
- [ ] Calidad muestra las métricas guardadas en el manifiesto.
- [ ] Rendimiento muestra 1, 2, 4 y 8 workers para el benchmark oficial.
- [ ] Los manifiestos tienen `status=success` y el mismo `input_checksum`.
- [ ] No se muestran rutas locales, trazas de error ni datos simulados como si fueran NASA.

Antes del pull request:

```powershell
python -m pytest -q
git diff --check
git status --short
```

## Limitaciones conocidas

- Los puntos solo incluyen país, coordenadas e identificador; no contienen ciudad o provincia.
- El mapa base de Carto necesita acceso a Internet para descargar sus teselas.
- La estabilidad ARI aparece como no evaluada cuando `stability_runs` es cero.
- Los resultados locales pequeños no permiten concluir cómo escalará el pipeline en Kabré.
- Los pesos declarados actualmente coinciden con los valores predeterminados del cálculo. Si el
  equipo decide cambiarlos, debe verificar primero su conexión con `ScoringService`.

