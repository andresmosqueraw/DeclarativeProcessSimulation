# Paso a Paso Detallado del Proyecto DeclarativeProcessSimulation

## 📋 Descripción General

Este proyecto automatiza la generación de escenarios de simulación de procesos de negocio basados en cambios declarativos de flujo de control usando modelos de deep learning (LSTM/GRU). El sistema entrena modelos, genera trazas sintéticas aplicando reglas declarativas, descubre modelos BPMN, y simula su ejecución para comparar escenarios AS-IS vs TO-BE.

---

## 🏗️ Arquitectura del Sistema

El proyecto sigue un pipeline modular con las siguientes etapas:

1. **Entrenamiento de Modelos** (`dg_training.py`)
2. **Predicción y Generación** (`dg_prediction.py`)
3. **Comparación de Estadísticas** (`comparison_stats/`)

---

## 📁 Estructura de Carpetas de Datos

```
data/
├── 0.logs/                        # Logs de eventos originales y reglas
│   └── <log_name>/
│       ├── <log_name>.csv         # Log de eventos en CSV
│       ├── rules.ini              # Reglas declarativas
│       └── embedded_matrix/       # Matrices embebidas generadas
├── 1.predicton_models/            # Modelos entrenados
│   └── <log_name>/
│       └── <model_folder>/
│           ├── parameters/
│           │   ├── traces_generated/  # Trazas generadas durante entrenamiento
│           │   └── <log_name>_ASIS.csv
│           └── <model_name>.h5        # Modelo guardado
├── 2.hallucination_logs/          # Trazas sintéticas generadas
│   └── <log_name>/
│       ├── <log_name>.csv         # Log generado
│       ├── <log_name>.csv.gz      # Versión comprimida
│       └── configuration_generated.yaml
├── 2.input_logs/                  # Logs preprocesados de entrada
│   └── <log_name>/
│       ├── <log_name>.csv.gz      # Log original comprimido
│       └── configuration_original.yaml
├── 3.bps_asis/                    # Modelos BPMN descubiertos (AS-IS)
│   └── <log_name>/
│       └── <run_id>/
│           └── best_result/
│               ├── <log_name>.bpmn
│               └── <log_name>.json
├── 3.bps_tobe/                    # Modelos BPMN simulados (TO-BE)
│   └── <log_name>/
│       └── <run_id>/
│           └── best_result/
│               ├── <log_name>.bpmn
│               ├── <log_name>.json
│               └── <log_name>_merged.json
└── 4.simulation_results/          # Resultados de simulación
    └── <log_name>/
        └── <rule_name>_ASIS/      # Resultados AS-IS
        └── <rule_name>_TOBE/      # Resultados TO-BE
        └── comparison_stats/      # Comparaciones
```

---

## 🔄 FLUJO COMPLETO PASO A PASO

### FASE 1: PREPARACIÓN Y CONFIGURACIÓN

#### Paso 1.1: Preparar el Log de Eventos
- **Ubicación**: `data/0.logs/<log_name>/<log_name>.csv`
- **Formato requerido**: CSV con columnas:
  - `Case ID` o `caseid`: Identificador del caso
  - `Activity` o `task`: Nombre de la actividad
  - `lifecycle:transition` o `event_type`: Tipo de evento (start/complete)
  - `Resource` o `user`: Recurso que ejecuta la actividad
  - `start_timestamp`: Timestamp de inicio
  - `end_timestamp`: Timestamp de fin
- **Acción**: Colocar el archivo CSV en la carpeta correspondiente

#### Paso 1.2: Definir Reglas Declarativas
- **Ubicación**: `data/0.logs/<log_name>/rules.ini`
- **Formato**:
  ```ini
  [RULES]
  path = TaskA >> TaskB
  variation = =1
  ```
- **Tipos de reglas soportadas**:
  - `directly`: `TaskA >> TaskB` - TaskB debe seguir directamente a TaskA
  - `eventually`: `TaskA * TaskB` - TaskB debe ocurrir eventualmente después de TaskA
  - `not_allowed`: `^TaskA` - TaskA no está permitido
  - `required`: `TaskA` - TaskA es requerido
- **Variaciones**:
  - `=1`: Exactamente 1 vez
  - `+1`: Aumentar en 1
  - `-1`: Disminuir en 1
- **Acción**: Crear/editar el archivo `rules.ini` con las reglas deseadas

#### Paso 1.3: Configurar Archivos YAML
- **Ubicación**: 
  - `data/2.input_logs/<log_name>/configuration_original.yaml`
  - `data/2.hallucination_logs/<log_name>/configuration_generated.yaml`
- **Contenido**: Configuración para Simod (herramienta de descubrimiento de procesos)
- **Acción**: Copiar desde `docs/example/configuration.yaml` y ajustar según necesidad

---

### FASE 2: ENTRENAMIENTO DEL MODELO (`dg_training.py`)

#### Paso 2.1: Configurar Parámetros de Entrenamiento
- **Archivo**: `dg_training.py` (línea ~40)
- **Parámetros principales**:
  ```python
  FILENAME = 'PurchasingExample.csv'  # Nombre del log
  NAME = FILENAME.split('.')[0]
  
  parameters = {
      'read_options': {
          'timeformat': '%Y-%m-%dT%H:%M:%S.%f',
          'column_names': {
              'Case ID': 'caseid',
              'Activity': 'task',
              'lifecycle:transition': 'event_type',
              'Resource': 'user'
          },
          'one_timestamp': False
      },
      'file_name': FILENAME,
      'opt_method': 'bayesian',      # Método de optimización
      'max_eval': 10,                # Máximo de evaluaciones
      'model_type': ['shared_cat', 'concatenated'],  # Tipos de modelo
      'epochs': 1,                   # Épocas de entrenamiento
      'n_size': [5, 10, 15],         # Tamaños de n-gram
      'l_size': [50, 100],           # Tamaños de capa LSTM
      # ... más parámetros
  }
  ```

#### Paso 2.2: Ejecutar Entrenamiento
- **Comando**: `python dg_training.py`
- **Proceso interno**:
  1. **Lectura del log**: 
     - Lee el CSV desde `data/0.logs/<log_name>/<log_name>.csv`
     - Parsea timestamps y normaliza columnas
  2. **Preprocesamiento**:
     - Crea matrices embebidas (embedding) de actividades y recursos
     - Genera secuencias de n-gramas para entrenamiento
     - Normaliza timestamps
     - Guarda matrices en `data/0.logs/<log_name>/embedded_matrix/`
  3. **Entrenamiento del modelo**:
     - Usa `GenerativeLSTM.model_training.model_trainer.ModelTrainer`
     - Prueba diferentes arquitecturas (LSTM, GRU, con/sin contexto)
     - Optimiza hiperparámetros usando Bayesian Optimization
     - Entrena múltiples variantes del modelo
  4. **Guardado**:
     - Modelo guardado en `data/1.predicton_models/<log_name>/<timestamp_folder>/`
     - Incluye:
       - `*.h5`: Modelo entrenado (Keras/TensorFlow)
       - `parameters/`: Parámetros del modelo, índices de actividades, escaladores
       - `parameters/<log_name>_ASIS.csv`: Copia del log original para referencia

#### Paso 2.3: Verificar Resultados
- **Ubicación**: `data/1.predicton_models/<log_name>/`
- **Verificar**: 
  - Carpeta con timestamp más reciente contiene el modelo
  - Archivo `.h5` del modelo
  - Carpeta `parameters/` con metadatos

---

### FASE 3: PREDICCIÓN Y GENERACIÓN (`dg_prediction.py`)

#### Paso 3.1: Configurar Parámetros de Predicción
- **Archivo**: `dg_prediction.py` (línea ~159)
- **Configuración**:
  ```python
  FILENAME = "PurchasingExample.csv"
  NAME = FILENAME.split('.')[0]
  rules_path = f"data/0.logs/{NAME}/rules.ini"
  path_prediction_models = f"data/1.predicton_models/{NAME}"
  ```

#### Paso 3.2: Generar Trazas Sintéticas (Hallucinación)
- **Función**: `call_predict()` → `predictor_adapter.hallucinate()`
- **Proceso**:
  1. **Carga del modelo**:
     - Encuentra la carpeta más reciente en `data/1.predicton_models/<log_name>/`
     - Carga el modelo `.h5` entrenado
     - Carga índices de actividades, escaladores, y parámetros
  2. **Lectura de reglas**:
     - Lee `rules.ini` usando `traces_evaluation.extract_rules()`
     - Parsea el tipo de regla (directly, eventually, not_allowed, required)
     - Extrae el path de actividades y la variación
  3. **Generación de trazas**:
     - Usa `GenerativeLSTM.model_prediction.model_predictor.ModelPredictor`
     - Para cada caso a generar:
       - Inicializa con n-grama de ceros
       - Predice siguiente actividad usando el modelo LSTM/GRU
       - Aplica reglas declarativas para filtrar/forzar actividades
       - Predice timestamps (start/end) para cada actividad
       - Continúa hasta que el modelo predice "End" o se alcanza longitud máxima
     - **Aplicación de reglas**:
       - `directly`: Verifica que TaskB siga directamente a TaskA
       - `eventually`: Verifica que existe un camino de TaskA a TaskB
       - `not_allowed`: Rechaza trazas que contengan la actividad prohibida
       - `required`: Asegura que la actividad esté presente
     - **Variaciones**: Ajusta la frecuencia de aparición según `variation`
  4. **Filtrado**:
     - Elimina actividades "Start" y "End" del log generado
     - Guarda en `data/2.hallucination_logs/<log_name>/<log_name>.csv`

#### Paso 3.3: Comprimir Logs
- **Función**: `compress_csv_to_gz()`
- **Proceso**:
  1. Comprime el log original: `data/0.logs/<log_name>/<log_name>.csv` → `data/2.input_logs/<log_name>/<log_name>.csv.gz`
  2. Comprime el log generado: `data/2.hallucination_logs/<log_name>/<log_name>.csv` → `data/2.hallucination_logs/<log_name>/<log_name>.csv.gz`
- **Razón**: Simod requiere logs comprimidos en formato `.gz`

#### Paso 3.4: Descubrir Modelo BPMN AS-IS
- **Función**: `generate_bps_model()` → `predictor_adapter.run_simod_docker()`
- **Proceso**:
  1. **Ejecución de Simod**:
     - Ejecuta contenedor Docker `nokal/simod`
     - Monta `data/2.input_logs/<log_name>/` como volumen
     - Usa `configuration_original.yaml` como configuración
     - Simod realiza:
       - Descubrimiento de proceso usando Split Miner 3
       - Extracción de parámetros estocásticos (distribuciones de tiempo, recursos)
       - Generación de modelo BPMN con anotaciones de simulación
  2. **Resultados**:
     - Guardados en `data/3.bps_asis/<log_name>/<run_id>/best_result/`
     - Archivos generados:
       - `<log_name>.bpmn`: Modelo BPMN descubierto
       - `<log_name>.json`: Parámetros estocásticos (recursos, tiempos, probabilidades)

#### Paso 3.5: Descubrir Modelo BPMN TO-BE
- **Función**: `generate_bps_model()` (mismo proceso que AS-IS)
- **Diferencia**: 
  - Usa `data/2.hallucination_logs/<log_name>/` como entrada
  - Usa `configuration_generated.yaml` como configuración
  - Guarda en `data/3.bps_tobe/<log_name>/<run_id>/best_result/`
- **Resultado**: Modelo BPMN que refleja el comportamiento con las reglas declarativas aplicadas

#### Paso 3.6: Fusionar Recursos (AS-IS → TO-BE)
- **Función**: `adapt_resources()` → `predictor_adapter.adapt_json()`
- **Problema**: 
  - El modelo TO-BE tiene nueva estructura de flujo (por las reglas)
  - Pero los recursos y tiempos deben venir del modelo AS-IS (datos reales)
- **Proceso**:
  1. **Mapeo de tareas**:
     - Lee ambos archivos BPMN (AS-IS y TO-BE)
     - Extrae tareas usando `extract_tasks()` (busca task, userTask, serviceTask, etc.)
     - Crea mapeo por nombre de tarea (case-insensitive): `{task_name: (id_asis, id_tobe)}`
  2. **Adaptación de JSON**:
     - Lee `ASIS.json` y `TOBE.json`
     - Usa `remap_ids_and_transfer_fields()`:
       - Copia `arrival_time_calendar`, `arrival_time_distribution`, `resource_calendars` de AS-IS
       - Remapea `assignedTasks` en `resource_profiles`: cambia IDs de AS-IS a IDs de TO-BE
       - Remapea `task_id` en `task_resource_distribution`: cambia IDs de AS-IS a IDs de TO-BE
  3. **Guardado**:
     - Guarda JSON fusionado en `data/3.bps_tobe/<log_name>/<run_id>/best_result/<log_name>_merged.json`
- **Resultado**: JSON con estructura de flujo TO-BE pero parámetros de recursos AS-IS

---

### FASE 4: SIMULACIÓN DE MODELOS

#### Paso 4.1: Simular Modelo TO-BE con Prosimos
- **Función**: `simulate_model()` → `predictor_adapter.run_prosimos_docker()`
- **Proceso**:
  1. **Ejecución de Prosimos**:
     - Ejecuta contenedor Docker `nokal/simod` (que incluye Prosimos)
     - Monta carpeta del modelo TO-BE como volumen
     - Usa:
       - BPMN: `<log_name>.bpmn` (estructura TO-BE)
       - JSON: `<log_name>_merged.json` (recursos AS-IS, estructura TO-BE)
     - Simula 20 casos (configurable)
  2. **Resultados**:
     - Guardados en `data/4.simulation_results/<log_name>/<rule_name>_TOBE/`
     - Archivos:
       - `<log_name>_prosimos_log.csv`: Log de eventos simulados
       - `<log_name>_prosimos_stats.csv`: Estadísticas de simulación

#### Paso 4.2: Simular Modelo TO-BE con BIMP
- **Función**: `simulate_bimp()` → `bimp_parser.embed_qbp_simulation()` + `predictor_adapter.run_bimp_docker()`
- **Proceso**:
  1. **Embedding QBP**:
     - Lee BPMN TO-BE y JSON merged
     - Usa `bimp_parser.embed_qbp_simulation()`:
       - Crea sección `<qbp:processSimulationInfo>` en el BPMN
       - Embebe:
         - `arrivalRateDistribution`: Distribución de llegada de casos
         - `timetables`: Calendarios de recursos
         - `resources`: Recursos con costos y disponibilidad
         - `elements`: Tareas con duraciones y recursos asignados
         - `sequenceFlows`: Probabilidades de ramificación
     - Guarda como `<log_name>_bimp_version.bpmn`
  2. **Simulación BIMP**:
     - Ejecuta contenedor Docker `java8-xvfb`
     - Ejecuta JAR de BIMP: `qbp-simulator-engine_with_csv_statistics.jar`
     - Simula usando el BPMN con QBP embebido
  3. **Resultados**:
     - Guardados en `data/4.simulation_results/<log_name>/<rule_name>_TOBE/`
     - Archivo: `<log_name>_bimp_log.csv`

#### Paso 4.3: Simular Modelo AS-IS (Para Comparación)
- **Proceso**: Similar a TO-BE pero usando:
  - BPMN: `data/3.bps_asis/<log_name>/<run_id>/best_result/<log_name>.bpmn`
  - JSON: `data/3.bps_asis/<log_name>/<run_id>/best_result/<log_name>.json`
- **Resultados**: Guardados en `data/4.simulation_results/<log_name>/<rule_name>_ASIS/`

---

### FASE 5: COMPARACIÓN Y ANÁLISIS

#### Paso 5.1: Comparar Estadísticas
- **Script**: `comparison_stats/compare_stats.py`
- **Proceso**:
  1. **Carga de estadísticas**:
     - Lee `*_prosimos_stats.csv` de AS-IS y TO-BE
     - Extrae sección "Overall Scenario Statistics"
     - Parsea KPIs: cycle_time, processing_time, waiting_time, idle_time, etc.
  2. **Comparación**:
     - Calcula cambio porcentual: `((TOBE - ASIS) / ASIS) * 100`
     - Crea tabla comparativa con:
       - KPI
       - AS-IS: Min, Max, Average, Accumulated
       - TO-BE: Min, Max, Average, Accumulated
       - Cambio porcentual
  3. **Guardado**:
     - Guarda CSV en `data/4.simulation_results/<log_name>/comparison_stats/<rule_name>_comparison.csv`

#### Paso 5.2: Visualizar Resultados
- **Script**: `comparison_stats/visualize_stats.py`
- **Proceso**:
  1. **Gráficos generados**:
     - `performance_comparison.png`: Gráfico de barras comparando métricas principales
     - `change_analysis.png`: Gráfico horizontal de cambios porcentuales (verde=mejora, rojo=empeoramiento)
     - `radar_comparison.png`: Gráfico radar multidimensional
  2. **Reporte HTML**:
     - Genera `comparison_report.html` con:
       - Tabla resumen de métricas
       - Gráficos embebidos
       - Interpretación de resultados
  3. **Guardado**:
     - Todo en `data/4.simulation_results/<log_name>/comparison_stats/visualizations/`

---

## 🔧 MÓDULOS DE SOPORTE DETALLADOS

### `support_modules/predictor_adapter.py`
- **`get_latest_output_folder()`**: Encuentra la carpeta más reciente por timestamp
- **`run_simod_docker()`**: Ejecuta Simod en Docker para descubrir modelos BPMN
- **`run_prosimos_docker()`**: Ejecuta Prosimos en Docker para simular procesos
- **`run_bimp_docker()`**: Ejecuta BIMP en Docker para simulación alternativa
- **`extract_tasks()`**: Extrae tareas de un archivo BPMN
- **`join_tasks_by_name()`**: Mapea tareas entre dos BPMN por nombre
- **`remap_ids_and_transfer_fields()`**: Adapta IDs de recursos de AS-IS a TO-BE
- **`adapt_json()`**: Función principal para fusionar recursos
- **`hallucinate()`**: Wrapper para generar trazas usando el modelo

### `support_modules/traces_evaluation.py`
- **`extract_rules()`**: Parsea `rules.ini` y determina tipo de regla
- **`evaluate_condition()`**: Evalúa si una traza cumple una regla declarativa
- **`evaluate_condition_list()`**: Versión para listas de actividades
- **`GenerateStats`**: Clase para calcular estadísticas de cumplimiento de reglas

### `support_modules/bimp_parser.py`
- **`embed_qbp_simulation()`**: Embebe información de simulación QBP en BPMN
  - Convierte JSON de recursos a XML QBP
  - Añade secciones: arrivalRateDistribution, timetables, resources, elements, sequenceFlows

### `support_modules/models_merger.py`
- **`MergeModels`**: Clase para fusionar modelos BPMN (usado en versión anterior)
- Actualmente la fusión se hace en `predictor_adapter.adapt_json()`

### `support_modules/xes_writer.py`
- Convierte logs CSV a formato XES (si es necesario)

### `support_modules/stochastic_model.py`
- Maneja modelos estocásticos de procesos

### `support_modules/log_replayer_stochastic.py`
- Replay de logs en modelos estocásticos

### `support_modules/bimp_generator.py`
- Genera archivos para BIMP

---

## 📊 FORMATOS DE ARCHIVOS

### Log CSV
```csv
Case ID,Activity,lifecycle:transition,Resource,start_timestamp,end_timestamp
case1,TaskA,start,User1,2024-01-01T10:00:00,2024-01-01T10:00:00
case1,TaskA,complete,User1,2024-01-01T10:00:00,2024-01-01T10:05:00
case1,TaskB,start,User2,2024-01-01T10:05:00,2024-01-01T10:05:00
```

### rules.ini
```ini
[RULES]
path = TaskA >> TaskB
variation = =1
```

### JSON de Recursos (Simod/Prosimos)
```json
{
  "arrival_time_distribution": {
    "distribution_name": "exponential",
    "distribution_params": [...]
  },
  "arrival_time_calendar": [...],
  "resource_profiles": [
    {
      "resource_list": [
        {
          "id": "resource1",
          "name": "User1",
          "cost_per_hour": 20,
          "amount": 1,
          "assignedTasks": ["task_id_1", "task_id_2"]
        }
      ]
    }
  ],
  "task_resource_distribution": [
    {
      "task_id": "task_id_1",
      "resources": [...]
    }
  ],
  "gateway_branching_probabilities": [...]
}
```

---

## 🎯 FLUJO DE DATOS COMPLETO

```
[Log Original CSV]
    ↓
[dg_training.py]
    ↓
[Modelo LSTM/GRU entrenado (.h5)]
    ↓
[dg_prediction.py + rules.ini]
    ↓
[Log Sintético Generado (CSV)]
    ↓
[Simod] → [BPMN AS-IS + JSON AS-IS]
    ↓
[Simod] → [BPMN TO-BE + JSON TO-BE]
    ↓
[adapt_json()] → [JSON Merged (TO-BE structure + AS-IS resources)]
    ↓
[Prosimos] → [Log Simulado TO-BE + Stats TO-BE]
    ↓
[BIMP] → [Log Simulado TO-BE (alternativo)]
    ↓
[compare_stats.py] → [Comparación AS-IS vs TO-BE]
    ↓
[visualize_stats.py] → [Gráficos y Reporte HTML]
```

---

## ⚙️ CONFIGURACIONES IMPORTANTES

### Docker
- **Simod**: `nokal/simod` - Para descubrimiento y simulación
- **Java8-XVFB**: `java8-xvfb` - Para ejecutar BIMP

### Parámetros Clave
- **Modelos**: LSTM, GRU, con/sin contexto inter-caso
- **Optimización**: Bayesian Optimization para hiperparámetros
- **Reglas**: 4 tipos (directly, eventually, not_allowed, required)
- **Simuladores**: Prosimos (moderno) y BIMP (legacy)

---

## 🔍 PUNTOS DE EXTENSIÓN

1. **Nuevos tipos de reglas**: Modificar `traces_evaluation.py`
2. **Nuevos modelos**: Añadir en `GenerativeLSTM/model_training/models/`
3. **Nuevos simuladores**: Añadir funciones en `predictor_adapter.py`
4. **Nuevas métricas**: Extender `compare_stats.py`

---

## 📝 NOTAS FINALES

- El proyecto usa Docker para herramientas externas (Simod, BIMP)
- Los modelos se guardan con timestamps para versionado
- Las reglas declarativas se aplican durante la generación, no después
- La fusión de recursos asegura que TO-BE use datos reales de recursos
- La comparación permite evaluar el impacto de cambios declarativos

