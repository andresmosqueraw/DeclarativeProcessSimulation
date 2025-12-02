# Paso a Paso Detallado: shorterm/con-to-be

## 📋 Descripción General

El módulo `shorterm/con-to-be` es una **integración completa** que combina:
1. **DeclarativeProcessSimulation**: Genera modelos TO-BE con reglas declarativas aplicadas
2. **ongoing-bps-state-short-term**: Calcula estados parciales y simula a corto plazo usando modelos TO-BE
3. **Evaluación de resultados**: Compara simulaciones short-term con logs de referencia
4. **Comparación y visualización**: Genera estadísticas comparativas y reportes visuales

**Objetivo**: Evaluar el impacto de reglas declarativas en simulaciones de corto plazo desde el estado actual del proceso.

---

## 🏗️ Arquitectura de la Integración

```
[DeclarativeProcessSimulation Pipeline]
    ↓
[Modelos TO-BE: BPMN + JSON merged]
    ↓
[ongoing-bps-state: Estado Parcial + Simulación Short-Term]
    ↓
[Evaluación: Comparación con Log de Referencia]
    ↓
[Comparación y Visualización: Estadísticas AS-IS vs TO-BE]
```

---

## 📁 Estructura de Archivos

```
shorterm/con-to-be/
├── run_complete_integration.py    # Orquestador principal (4 pasos)
├── test_ongoing_only.py            # Prueba standalone de ongoing-bps-state
├── evaluate_short_term_results.py  # Evaluación de resultados short-term
└── output.json                     # Estado parcial generado (ejemplo)
```

---

## 🔄 FLUJO COMPLETO PASO A PASO

### FASE 1: PIPELINE DECLARATIVEPROCESSSIMULATION

#### Paso 1.1: Ejecutar `dg_prediction.py`
- **Función**: `run_declarative_pipeline()`
- **Ubicación**: `run_complete_integration.py` (líneas 13-38)
- **Proceso**:
  1. **Cambiar directorio**:
     - Desde `shorterm/con-to-be/` sube 2 niveles
     - Va a `DeclarativeProcessSimulation/`
  2. **Ejecutar pipeline**:
     - Comando: `python dg_prediction.py`
     - Usa entorno: `/home/andrew/miniconda3/envs/deep_generator/bin/python`
  3. **Pipeline completo** (ver `PASO_A_PASO_DETALLADO.md` de DeclarativeProcessSimulation):
     - Genera trazas sintéticas con reglas declarativas
     - Descubre modelo BPMN TO-BE desde trazas generadas
     - Descubre modelo BPMN AS-IS desde log original
     - Fusiona recursos (AS-IS → TO-BE)
     - Simula ambos modelos (AS-IS y TO-BE)
  4. **Resultados generados**:
     - `data/3.bps_tobe/<log_name>/<run_id>/best_result/`:
       - `<log_name>.bpmn`: Modelo BPMN TO-BE
       - `<log_name>_merged.json`: Parámetros con recursos AS-IS y estructura TO-BE
     - `data/4.simulation_results/<log_name>/<rule_name>_ASIS/`: Estadísticas AS-IS
     - `data/4.simulation_results/<log_name>/<rule_name>_TOBE/`: Estadísticas TO-BE
  5. **Validación**:
     - Si `returncode == 0`: ✅ Éxito
     - Si falla: ❌ Detiene la integración

#### Paso 1.2: Preparar Log para Estado Parcial
- **Requisito**: Necesita un log con eventos hasta un punto de corte
- **Ubicación esperada**: `data/0.logs/<log_name>/<log_name>_ongoing.csv`
- **Formato**: CSV con columnas estándar (CaseId, Activity, Resource, StartTime, EndTime)
- **Nota**: Si no existe `_ongoing.csv`, se puede usar el log original

---

### FASE 2: CÁLCULO DE ESTADO PARCIAL Y SIMULACIÓN SHORT-TERM

#### Paso 2.1: Localizar Modelos TO-BE
- **Función**: `run_ongoing_bps_state()` → `test_ongoing_state()`
- **Ubicación**: `test_ongoing_only.py` (líneas 49-138)
- **Proceso**:
  1. **Buscar directorio más reciente**:
     - Base: `data/3.bps_tobe/<log_name>/`
     - Lista subdirectorios (tienen timestamps como nombres)
     - Selecciona el más reciente: `sorted(subdirs)[-1]`
  2. **Construir rutas**:
     - BPMN: `<latest_subdir>/best_result/<log_name>.bpmn`
     - JSON: `<latest_subdir>/best_result/<log_name>_merged.json`
  3. **Validar existencia**:
     - Verifica que ambos archivos existan
     - Si falta alguno: ❌ Error y detiene

#### Paso 2.2: Calcular Estado Parcial
- **Función**: `run_process_state_and_simulation(simulate=False)`
- **Proceso** (ver `PASO_A_PASO_DETALLADO.md` de ongoing-bps-state):
  1. **Leer entradas**:
     - Log: `data/0.logs/<log_name>/<log_name>_ongoing.csv`
     - BPMN: Modelo TO-BE encontrado
     - JSON: Parámetros merged (TO-BE structure + AS-IS resources)
  2. **Procesar log**:
     - Filtra casos en curso
     - Calcula `enabled_time` usando Concurrency Oracle
  3. **Construir N-Gram Index**:
     - Divide tareas en +START/+COMPLETE
     - Construye Reachability Graph
     - Indexa secuencias de actividades
  4. **Calcular estado de cada caso**:
     - Identifica actividades en curso
     - Determina estado de control de flujo (tokens en flows/activities)
     - Calcula actividades/gateways/eventos habilitados
  5. **Generar `output.json`**:
     - Estructura con `last_case_arrival` y `cases`
     - Cada caso tiene: `control_flow_state`, `ongoing_activities`, `enabled_activities`, etc.

#### Paso 2.3: Guardar Estado Parcial
- **Ubicación**: `data/5.ongoing_state/<log_name>/process_state.json`
- **Proceso**:
  - Lee `output.json` generado por ongoing-bps-state
  - Lo copia a la ubicación final
  - Formato: JSON con estructura completa del estado parcial

#### Paso 2.4: Ejecutar Simulación Short-Term
- **Función**: `run_process_state_and_simulation(simulate=True)`
- **Parámetros**:
  - `simulation_horizon`: 7 días desde ahora (calculado dinámicamente)
  - `total_cases`: 20 (fallback si no hay horizonte)
  - `sim_stats_csv`: `data/5.ongoing_state/<log_name>/ongoing_simulation_stats.csv`
  - `sim_log_csv`: `data/5.ongoing_state/<log_name>/ongoing_simulation_log.csv`
- **Proceso**:
  1. **Cargar estado parcial**:
     - Lee `process_state.json`
     - Convierte timestamps de strings a `datetime`
  2. **Inicializar Prosimos con estado parcial**:
     - Restaura casos en curso con sus recursos y tiempos
     - Restaura tokens en sequence flows y actividades
     - Marca actividades habilitadas
  3. **Simular hasta horizonte**:
     - Continúa desde el estado parcial
     - Genera nuevos casos según `arrival_time_distribution`
     - Simula hasta `simulation_horizon` (7 días)
  4. **Generar salidas**:
     - `ongoing_simulation_log.csv`: Eventos simulados desde estado parcial
     - `ongoing_simulation_stats.csv`: Estadísticas de simulación

#### Paso 2.5: Validar Resultados
- **Verificación**:
  - `process_state.json` existe
  - `ongoing_simulation_log.csv` existe
  - `ongoing_simulation_stats.csv` existe
- **Si falla**: ⚠️ Muestra advertencia pero continúa

---

### FASE 3: EVALUACIÓN DE RESULTADOS SHORT-TERM

#### Paso 3.1: Preparar Entradas para Evaluación
- **Función**: `run_short_term_evaluation()`
- **Ubicación**: `run_complete_integration.py` (líneas 65-127)
- **Rutas configuradas**:
  - `reference_log_path`: `data/0.logs/<log_name>/<log_name>_ongoing.csv` (o `.csv` original)
  - `simulated_log_path`: `data/5.ongoing_state/<log_name>/ongoing_simulation_log.csv`
  - `process_state_path`: `data/5.ongoing_state/<log_name>/process_state.json`
  - `evaluation_output_dir`: `data/5.ongoing_state/<log_name>/evaluation/`

#### Paso 3.2: Ejecutar Evaluación
- **Script**: `evaluate_short_term_results.py`
- **Función principal**: `evaluate_short_term_simulation()`
- **Proceso**:
  1. **Leer logs**:
     - **Log de referencia**:
       - Lee CSV con mapeo flexible de columnas
       - Renombra: `CaseId/caseid → case_id`, `Activity/task → activity`, etc.
       - Valida columnas requeridas: `case_id`, `activity`, `start_time`, `end_time`
       - Si falta `resource`, añade columna vacía
     - **Log simulado**:
       - Mismo proceso de lectura y mapeo
       - Ya debería estar en formato correcto (de Prosimos)
  2. **Determinar punto de corte y horizonte**:
     - Si no se proporciona `cut_timestamp`:
       - Lee `process_state.json`
       - Extrae `last_case_arrival`
       - Convierte a `pd.Timestamp`
       - Si falla: usa `max(start_time)` del log de referencia
     - **Horizonte**: `cut_timestamp + horizon_days` (default: 7 días)
  3. **Dividir logs en subsets** (usando `helper.split_into_subsets()`):
     - **A_event**: Eventos del log de referencia entre `cut_timestamp` y `end_timestamp`
     - **A_ongoing**: Casos en curso del log de referencia (con eventos antes de `cut_timestamp`)
     - **A_complete**: Casos completados del log de referencia (entre `cut_timestamp` y `end_timestamp`)
     - **G_event**: Eventos del log simulado entre `cut_timestamp` y `end_timestamp`
     - **G_ongoing**: Casos en curso del log simulado
     - **G_complete**: Casos completados del log simulado (entre `cut_timestamp` y `end_timestamp`)
  4. **Guardar subsets**:
     - `A_event_filter.csv`, `A_ongoing.csv`, `A_complete.csv` (referencia)
     - `G_event_filter.csv`, `G_ongoing.csv`, `G_complete.csv` (simulado)
  5. **Calcular métricas** (usando `evaluation._metrics()`):
     - **Event Filter Metrics**:
       - Compara `A_event` vs `G_event`
       - Métricas: precision, recall, F1, etc. (usando log-distance-measures)
     - **Ongoing Filter Metrics**:
       - Compara `A_ongoing` vs `G_ongoing`
       - Métricas de casos en curso
     - **Complete Filter Metrics**:
       - Compara `A_complete` vs `G_complete`
       - Métricas de casos completados
  6. **Guardar resultados**:
     - `evaluation_results.json`:
       ```json
       {
           "cut_timestamp": "...",
           "end_timestamp": "...",
           "horizon_days": 7,
           "metrics": {
               "event_filter": {...},
               "ongoing_filter": {...},
               "complete_filter": {...}
           },
           "summary": {
               "reference_cases_ongoing": N,
               "simulated_cases_ongoing": M,
               "reference_cases_complete": X,
               "simulated_cases_complete": Y
           }
       }
       ```
  7. **Mostrar resumen**:
     - Imprime métricas calculadas
     - Muestra conteos de casos

#### Paso 3.3: Validar Resultados de Evaluación
- **Archivos esperados**:
  - `evaluation/evaluation_results.json`
  - `evaluation/A_event_filter.csv`
  - `evaluation/G_event_filter.csv`
  - (y otros subsets)
- **Si falla**: ⚠️ Muestra advertencia pero continúa

---

### FASE 4: COMPARACIÓN Y VISUALIZACIÓN

#### Paso 4.1: Ejecutar Comparación de Estadísticas
- **Función**: `run_comparison_and_visualization()`
- **Ubicación**: `run_complete_integration.py` (líneas 129-165)
- **Proceso**:
  1. **Cambiar directorio**:
     - Va a `DeclarativeProcessSimulation/comparison_stats/`
  2. **Ejecutar `compare_stats.py`**:
     - Lee estadísticas AS-IS: `data/4.simulation_results/<log_name>/<rule_name>_ASIS/*_prosimos_stats.csv`
     - Lee estadísticas TO-BE: `data/4.simulation_results/<log_name>/<rule_name>_TOBE/*_prosimos_stats.csv`
     - Extrae sección "Overall Scenario Statistics"
     - Calcula cambio porcentual: `((TOBE - ASIS) / ASIS) * 100`
     - Genera tabla comparativa con KPIs
     - Guarda: `data/4.simulation_results/<log_name>/comparison_stats/<rule_name>_comparison.csv`
  3. **Ejecutar `visualize_stats.py`**:
     - Lee CSV de comparación
     - Genera gráficos:
       - `performance_comparison.png`: Gráfico de barras comparativo
       - `change_analysis.png`: Gráfico de cambios porcentuales
       - `radar_comparison.png`: Gráfico radar multidimensional
     - Genera reporte HTML: `comparison_report.html`
     - Guarda en: `data/4.simulation_results/<log_name>/comparison_stats/visualizations/`

#### Paso 4.2: Validar Resultados
- **Archivos esperados**:
  - `comparison_stats/<rule_name>_comparison.csv`
  - `comparison_stats/visualizations/comparison_report.html`
  - `comparison_stats/visualizations/*.png`
- **Si falla**: ❌ Detiene la integración

---

### FASE 5: GENERACIÓN DE REPORTE DE INTEGRACIÓN

#### Paso 5.1: Verificar Archivos Generados
- **Función**: `generate_integration_report()`
- **Ubicación**: `run_complete_integration.py` (líneas 167-234)
- **Verificaciones**:
  1. **DeclarativeProcessSimulation**:
     - `data/4.simulation_results/<log_name>/<rule_name>_ASIS/*_prosimos_stats.csv`
     - `data/4.simulation_results/<log_name>/<rule_name>_TOBE/*_prosimos_stats.csv`
  2. **ongoing-bps-state**:
     - `data/5.ongoing_state/<log_name>/process_state.json`
     - `data/5.ongoing_state/<log_name>/ongoing_simulation_log.csv`
     - `data/5.ongoing_state/<log_name>/ongoing_simulation_stats.csv`
  3. **Evaluación short-term**:
     - `data/5.ongoing_state/<log_name>/evaluation/evaluation_results.json`
     - `data/5.ongoing_state/<log_name>/evaluation/A_event_filter.csv`
     - `data/5.ongoing_state/<log_name>/evaluation/G_event_filter.csv`
  4. **Comparación y visualización**:
     - `data/4.simulation_results/<log_name>/comparison_stats/<rule_name>_comparison.csv`
     - `data/4.simulation_results/<log_name>/comparison_stats/visualizations/comparison_report.html`

#### Paso 5.2: Generar Reporte JSON
- **Estructura del reporte**:
  ```json
  {
      "timestamp": "2025-01-20T10:00:00",
      "declarative_process_simulation": {
          "status": "completed" | "failed",
          "files": [...]
      },
      "ongoing_bps_state": {
          "status": "completed" | "failed",
          "files": [...]
      },
      "short_term_evaluation": {
          "status": "completed" | "failed",
          "files": [...]
      },
      "comparison_visualization": {
          "status": "completed" | "failed",
          "files": [...]
      }
  }
  ```
- **Guardado**: `data/integration_report.json`

#### Paso 5.3: Mostrar Resumen
- **Imprime**:
  - Estado de cada componente (completed/failed)
  - Contador de pasos exitosos: `{success_count}/{total_steps}`
  - Ubicación de archivos generados

---

## 📊 ESTRUCTURA DE DATOS GENERADOS

### Directorio `data/5.ongoing_state/<log_name>/`

```
5.ongoing_state/
└── PurchasingExample/
    ├── process_state.json              # Estado parcial calculado
    ├── ongoing_simulation_log.csv      # Log simulado desde estado parcial
    ├── ongoing_simulation_stats.csv    # Estadísticas de simulación
    └── evaluation/
        ├── evaluation_results.json     # Métricas de evaluación
        ├── A_event_filter.csv         # Eventos de referencia (horizonte)
        ├── A_ongoing.csv              # Casos en curso (referencia)
        ├── A_complete.csv             # Casos completados (referencia)
        ├── G_event_filter.csv         # Eventos simulados (horizonte)
        ├── G_ongoing.csv              # Casos en curso (simulado)
        └── G_complete.csv             # Casos completados (simulado)
```

### Directorio `data/4.simulation_results/<log_name>/`

```
4.simulation_results/
└── PurchasingExample/
    ├── <rule_name>_ASIS/
    │   ├── PurchasingExample_prosimos_log.csv
    │   └── PurchasingExample_prosimos_stats.csv
    ├── <rule_name>_TOBE/
    │   ├── PurchasingExample_prosimos_log.csv
    │   └── PurchasingExample_prosimos_stats.csv
    └── comparison_stats/
        ├── <rule_name>_comparison.csv
        └── visualizations/
            ├── comparison_report.html
            ├── performance_comparison.png
            ├── change_analysis.png
            └── radar_comparison.png
```

---

## 🔧 MÓDULOS DETALLADOS

### `run_complete_integration.py`
- **`run_declarative_pipeline()`**: Ejecuta `dg_prediction.py` del pipeline principal
- **`run_ongoing_bps_state()`**: Ejecuta `test_ongoing_only.py` para calcular estado y simular
- **`run_short_term_evaluation()`**: Ejecuta `evaluate_short_term_results.py` para evaluar
- **`run_comparison_and_visualization()`**: Ejecuta `compare_stats.py` y `visualize_stats.py`
- **`generate_integration_report()`**: Verifica archivos y genera reporte JSON
- **`main()`**: Orquesta los 4 pasos principales

### `test_ongoing_only.py`
- **`test_ongoing_state()`**: Función principal
  - Localiza modelos TO-BE más recientes
  - Calcula estado parcial (sin simulación)
  - Guarda `process_state.json`
  - Ejecuta simulación short-term (7 días)
  - Guarda logs y estadísticas simuladas

### `evaluate_short_term_results.py`
- **`evaluate_short_term_simulation()`**: Función principal
  - Lee logs de referencia y simulado
  - Determina punto de corte y horizonte
  - Divide logs en subsets (event, ongoing, complete)
  - Calcula métricas usando `evaluation._metrics()`
  - Guarda resultados en JSON y CSVs
- **`main()`**: CLI para ejecutar evaluación desde línea de comandos

---

## 🚀 USO DEL SISTEMA

### Ejecutar Integración Completa

```bash
cd DeclarativeProcessSimulation/shorterm/con-to-be
python run_complete_integration.py
```

### Ejecutar Solo Estado Parcial y Simulación

```bash
cd DeclarativeProcessSimulation/shorterm/con-to-be
python test_ongoing_only.py
```

### Ejecutar Solo Evaluación

```bash
cd DeclarativeProcessSimulation/shorterm/con-to-be
python evaluate_short_term_results.py \
    --reference-log ../../data/0.logs/PurchasingExample/PurchasingExample_ongoing.csv \
    --simulated-log ../../data/5.ongoing_state/PurchasingExample/ongoing_simulation_log.csv \
    --process-state ../../data/5.ongoing_state/PurchasingExample/process_state.json \
    --output-dir ../../data/5.ongoing_state/PurchasingExample/evaluation \
    --horizon-days 7
```

---

## 🔍 CONCEPTOS CLAVE

### Estado Parcial (Partial State)
- **Definición**: Estado del proceso en un momento específico (punto de corte)
- **Contiene**:
  - Tokens en sequence flows
  - Actividades en curso (con recursos y tiempos)
  - Actividades/gateways/eventos habilitados
- **Uso**: Punto de partida para simulación short-term

### Simulación Short-Term
- **Propósito**: Predecir comportamiento futuro desde el estado actual
- **Características**:
  - Usa estado parcial como punto de partida
  - Simula hasta un horizonte temporal (7 días)
  - Restaura casos en curso con recursos y tiempos reales
  - Genera nuevos casos según distribución de llegada

### Evaluación Short-Term
- **Propósito**: Comparar simulación con realidad
- **Métodos**:
  - **Event Filter**: Compara eventos en el horizonte
  - **Ongoing Filter**: Compara casos en curso
  - **Complete Filter**: Compara casos completados
- **Métricas**: Precision, recall, F1, etc. (usando log-distance-measures)

### Modelos TO-BE
- **Origen**: Generados por DeclarativeProcessSimulation
- **Características**:
  - BPMN con estructura modificada por reglas declarativas
  - JSON merged con recursos AS-IS pero estructura TO-BE
- **Uso**: Base para calcular estado parcial y simular

---

## 📝 FLUJO DE DATOS COMPLETO

```
[Log Original] → [DeclarativeProcessSimulation]
                        ↓
[Reglas Declarativas] → [Trazas Sintéticas]
                        ↓
[Simod] → [BPMN TO-BE + JSON merged]
                        ↓
[Log _ongoing.csv] → [ongoing-bps-state]
                        ↓
[Estado Parcial] → [Prosimos Short-Term]
                        ↓
[Log Simulado] → [Evaluación]
                        ↓
[Métricas] → [Comparación AS-IS vs TO-BE]
                        ↓
[Reporte Final]
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Dependencias de orden**:
   - Paso 1 (DeclarativeProcessSimulation) debe completarse antes del Paso 2
   - Paso 2 puede fallar sin detener la integración (solo advertencia)
   - Paso 3 puede fallar sin detener la integración (solo advertencia)
   - Paso 4 debe completarse (detiene si falla)

2. **Rutas hardcodeadas**:
   - Entornos Python: `/home/andrew/miniconda3/envs/deep_generator/bin/python`
   - Entorno ongoing-bps-state: Ruta absoluta al venv
   - Ajustar según instalación

3. **Log _ongoing.csv**:
   - Debe contener eventos hasta el punto de corte deseado
   - Si no existe, se usa el log original
   - Debe tener formato estándar (CaseId, Activity, Resource, StartTime, EndTime)

4. **Horizonte de simulación**:
   - Por defecto: 7 días desde ahora
   - Se calcula dinámicamente en `test_ongoing_only.py`
   - Configurable en `evaluate_short_term_results.py` con `--horizon-days`

5. **Modelos TO-BE**:
   - Se busca el directorio más reciente en `3.bps_tobe/<log_name>/`
   - Debe contener `best_result/` con `.bpmn` y `_merged.json`

---

## 🎯 CASOS DE USO

1. **Evaluar Impacto de Reglas Declarativas en Corto Plazo**:
   - Genera modelos TO-BE con reglas
   - Simula desde estado actual
   - Compara con simulación AS-IS

2. **Predicción de Comportamiento Futuro**:
   - Calcula estado parcial actual
   - Simula próximos 7 días
   - Evalúa precisión de predicción

3. **Análisis Comparativo**:
   - Compara estadísticas AS-IS vs TO-BE
   - Visualiza diferencias
   - Genera reportes HTML

4. **Validación de Modelos**:
   - Evalúa calidad de simulaciones short-term
   - Compara con logs reales
   - Calcula métricas de precisión

---

## 📈 MÉTRICAS DE EVALUACIÓN

### Event Filter Metrics
- **Precision**: Proporción de eventos simulados que están en referencia
- **Recall**: Proporción de eventos de referencia que están en simulación
- **F1**: Media armónica de precision y recall

### Ongoing Filter Metrics
- **Casos en curso**: Compara casos en curso entre referencia y simulación
- **Actividades en curso**: Compara actividades activas

### Complete Filter Metrics
- **Casos completados**: Compara casos completados en el horizonte
- **Tiempos de ciclo**: Compara tiempos de ciclo de casos completados

---

Este documento describe el funcionamiento completo del módulo `shorterm/con-to-be` que integra DeclarativeProcessSimulation con ongoing-bps-state para evaluar simulaciones short-term con modelos TO-BE.

