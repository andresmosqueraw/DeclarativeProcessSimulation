# Carpeta Nuevo - Scripts Paso a Paso

Esta carpeta contiene scripts que se ejecutan paso a paso según las instrucciones del usuario.

## 🐍 Entorno Virtual

Esta carpeta incluye un entorno virtual (`venv/`) con todas las dependencias necesarias para ejecutar los scripts.

### Activar el entorno virtual

**Opción 1: Usando el script de activación**
```bash
source activate_venv.sh
```

**Opción 2: Manualmente**
```bash
source venv/bin/activate
```

**Opción 3: Ejecutar scripts directamente con el venv**
```bash
venv/bin/python extract_bpmn_json.py
venv/bin/python run_ongoing_state.py
```

### Desactivar el entorno virtual

```bash
deactivate
```

### Instalar/Actualizar dependencias

Si necesitas reinstalar las dependencias:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Dependencias incluidas

- `ongoing-bps-state-short-term` y sus dependencias
- `Prosimos` (instalado desde el repositorio local)
- `pyyaml` para manejo de configuración
- Todas las dependencias necesarias (pandas, numpy, networkx, etc.)

## Script 1: extract_bpmn_json.py

Extrae modelos BPMN y JSON desde un log de eventos usando Simod.

### Requisitos

1. **Docker** instalado y funcionando
2. **Imagen de Simod**: `nokal/simod` (se descarga automáticamente si no existe)
3. **Entorno virtual activado** (ver sección "Entorno Virtual" arriba)

### Instalación de dependencias

Las dependencias ya están instaladas en el entorno virtual. Si necesitas reinstalarlas:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Configuración

El script lee la configuración desde `config.yaml` en la misma carpeta. Este archivo contiene:

- **log_config**: Mapeo de columnas del log (ajustar según el formato del log)
- **simod_config**: Parámetros de Simod (control-flow, resource model, etc.)
- **script_config**: Configuración del script (directorio de salida, Docker, etc.)

Si el archivo `config.yaml` no existe, el script usa valores por defecto.

### Uso

El script puede recibir la ruta del log de dos formas (el argumento tiene prioridad):

**Opción 1: Como argumento de línea de comandos**
```bash
python extract_bpmn_json.py <ruta_al_log.csv>
```

**Opción 2: En config.yaml**
Especificar `log_config.log_path` en `config.yaml` y ejecutar sin argumentos:
```bash
python extract_bpmn_json.py
```

### Ejemplos

```bash
# Desde la carpeta nuevo/
# Opción 1: Con argumento
python extract_bpmn_json.py ../../data/0.logs/PurchasingExample/PurchasingExample.csv

# Opción 2: Sin argumento (usa config.yaml)
# Primero editar config.yaml y poner:
# log_config:
#   log_path: "../../data/0.logs/PurchasingExample/PurchasingExample.csv"
python extract_bpmn_json.py
```

### Qué hace el script

1. **Carga la configuración** desde `config.yaml` (o usa valores por defecto)
2. **Comprime el log** a formato `.gz` (requerido por Simod)
3. **Crea un archivo de configuración** YAML para Simod usando los parámetros de `config.yaml`
4. **Ejecuta Simod** usando Docker para descubrir el modelo BPMN y extraer parámetros JSON
5. **Copia los resultados** (`.bpmn` y `.json`) a la carpeta `nuevo/` (o la especificada en `config.yaml`)
6. **Limpia** los archivos temporales

### Archivos generados

En la carpeta `data/generado-simod/` dentro de `nuevo/` (o la especificada en `script_config.output_dir`):
- `<log_name>.bpmn` - Modelo BPMN descubierto
- `<log_name>.json` - Parámetros estocásticos (recursos, tiempos, probabilidades)

### Personalización

Para ajustar el comportamiento del script, edita `config.yaml`:

- **Mapeo de columnas**: Si tu log usa nombres diferentes, modifica `log_config.column_mapping`
- **Parámetros de Simod**: Ajusta `simod_config` para cambiar el algoritmo de descubrimiento, iteraciones, etc.
- **Directorio de salida**: Cambia `script_config.output_dir` para guardar los archivos en otra ubicación (por defecto: `data/generado-simod/`)
- **Docker**: Modifica `script_config.docker` para usar otra imagen o configuración

---

## Script 2: run_ongoing_state.py

Calcula el estado parcial del proceso y opcionalmente ejecuta simulación de corto plazo usando `ongoing-bps-state-short-term`.

### Requisitos

1. **Entorno virtual activado** (ver sección "Entorno Virtual" arriba)
   - Todas las dependencias ya están instaladas en `venv/`

2. **Archivos necesarios** (deben estar en la carpeta `nuevo/`):
   - `<log_name>.csv` - Log de eventos
   - `<log_name>.bpmn` - Modelo BPMN (generado por `extract_bpmn_json.py`)
   - `<log_name>.json` - Parámetros JSON (generado por `extract_bpmn_json.py`)

3. **Módulo ongoing-bps-state-short-term**:
   - El script lo importa automáticamente desde la ruta configurada

### Configuración

El script lee la configuración desde `config.yaml` en la sección `ongoing_config`:

- **start_time**: Fecha/hora de corte (cut-off) en formato ISO. Si es `null`, usa el último evento del log.
- **column_mapping**: Mapeo de columnas (si es `null`, usa el de `log_config`).
- **simulate**: Si ejecutar simulación de corto plazo (`true`/`false`).
- **simulation_horizon**: Horizonte de simulación en formato ISO. Si es `null` y `simulate=true`, se calcula automáticamente.
- **horizon_days**: Días desde ahora para calcular el horizonte automáticamente (default: 7).
- **total_cases**: Número de casos a simular (default: 20).

### Uso

**Con entorno virtual activado:**
```bash
source venv/bin/activate
python run_ongoing_state.py
```

**O directamente con el venv:**
```bash
venv/bin/python run_ongoing_state.py
```

El script:
1. Lee la configuración desde `config.yaml`
2. Busca los archivos `<log_name>.csv`, `<log_name>.bpmn` y `<log_name>.json` en la carpeta `nuevo/`
3. Calcula el estado parcial del proceso
4. Opcionalmente ejecuta simulación de corto plazo (si `simulate: true`)

### Ejemplo

```bash
# Desde la carpeta nuevo/
# Asegúrate de tener:
# - PurchasingExample.csv
# - PurchasingExample.bpmn (generado por extract_bpmn_json.py)
# - PurchasingExample.json (generado por extract_bpmn_json.py)

python run_ongoing_state.py
```

### Qué hace el script

1. **Carga la configuración** desde `config.yaml`
2. **Verifica archivos** necesarios (log, BPMN, JSON)
3. **Calcula el estado parcial** del proceso usando `ongoing-bps-state-short-term`:
   - Procesa el log hasta el cut-off (`start_time` o último evento)
   - Identifica casos en curso
   - Calcula el estado de control-flow (tokens, actividades en curso, actividades habilitadas)
4. **Guarda el estado** en `<log_name>_process_state.json`
5. **Opcionalmente ejecuta simulación** de corto plazo:
   - Usa el estado parcial como punto de partida
   - Simula hasta el horizonte especificado
   - Genera log y estadísticas de simulación

### Archivos generados

En la carpeta `data/generado-ongoing/` dentro de `nuevo/` (o la especificada en `script_config.output_dir`):

- `<log_name>_process_state.json` - Estado parcial del proceso (siempre se genera)
- `<log_name>_simulation_stats.csv` - Estadísticas de simulación (solo si `simulate: true`)
- `<log_name>_simulation_log.csv` - Log de eventos simulados (solo si `simulate: true`)

### Personalización

Para ajustar el comportamiento del script, edita `config.yaml`:

- **Cut-off personalizado**: Especifica `ongoing_config.start_time` con una fecha/hora en formato ISO
- **Simulación**: Cambia `ongoing_config.simulate` a `true`/`false` para habilitar/deshabilitar simulación
- **Horizonte**: Especifica `ongoing_config.simulation_horizon` o ajusta `ongoing_config.horizon_days`
- **Número de casos**: Modifica `ongoing_config.total_cases` para cambiar cuántos casos simular

