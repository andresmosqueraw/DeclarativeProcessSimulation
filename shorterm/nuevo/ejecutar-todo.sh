#!/bin/bash
# Script para ejecutar todo el pipeline: extract_bpmn_json.py y run_ongoing_state.py

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
SRC_DIR="$SCRIPT_DIR/src"

# Verificar que existe el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ No se encontró el entorno virtual en: $VENV_DIR"
    echo "   Ejecuta primero: python3 -m venv venv"
    exit 1
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"
echo "✅ Entorno virtual activado: $VENV_DIR"
echo "   Python: $(which python)"
echo "   Versión: $(python --version)"
echo ""

# Cambiar al directorio del script
cd "$SCRIPT_DIR"

# Función para manejar errores
handle_error() {
    echo ""
    echo "❌ Error en: $1"
    echo "   El proceso se detuvo"
    deactivate
    exit 1
}

# Paso 1: Ejecutar extract_bpmn_json.py
echo "=================================================================================="
echo "📋 PASO 1: Extrayendo BPMN y JSON con Simod"
echo "=================================================================================="
echo ""

if [ -f "$SRC_DIR/extract_bpmn_json.py" ]; then
    python "$SRC_DIR/extract_bpmn_json.py" || handle_error "extract_bpmn_json.py"
else
    echo "❌ No se encontró: $SRC_DIR/extract_bpmn_json.py"
    deactivate
    exit 1
fi

echo ""
echo "=================================================================================="
echo "✅ PASO 1 COMPLETADO"
echo "=================================================================================="
echo ""

# Paso 2: Ejecutar compute_state.py
echo "=================================================================================="
echo "📋 PASO 2: Calculando estado parcial del proceso"
echo "=================================================================================="
echo ""

if [ -f "$SRC_DIR/compute_state.py" ]; then
    python "$SRC_DIR/compute_state.py" || handle_error "compute_state.py"
else
    echo "❌ No se encontró: $SRC_DIR/compute_state.py"
    deactivate
    exit 1
fi

echo ""
echo "=================================================================================="
echo "✅ PASO 2 COMPLETADO"
echo "=================================================================================="
echo ""

# Paso 3: Ejecutar run_simulation.py (si está habilitado)
echo "=================================================================================="
echo "📋 PASO 3: Ejecutando simulación de corto plazo (si está habilitada)"
echo "=================================================================================="
echo ""

if [ -f "$SRC_DIR/run_simulation.py" ]; then
    python "$SRC_DIR/run_simulation.py" || handle_error "run_simulation.py"
else
    echo "❌ No se encontró: $SRC_DIR/run_simulation.py"
    deactivate
    exit 1
fi

echo ""
echo "=================================================================================="
echo "✅ PASO 3 COMPLETADO"
echo "=================================================================================="
echo ""

# Paso 4: Ejecutar what-if declarativo (si está habilitado)
echo "=================================================================================="
echo "📋 PASO 4: Análisis What-If con reglas declarativas (opcional)"
echo "=================================================================================="
echo ""

# Verificar si what-if está habilitado en config.yaml
WHATIF_ENABLED=$(python3 -c "
import yaml
import sys
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    whatif_config = config.get('whatif_config', {})
    enabled = whatif_config.get('enabled', False)
    print('true' if enabled else 'false')
except:
    print('false')
" 2>/dev/null)

if [ "$WHATIF_ENABLED" = "true" ]; then
    echo "✅ What-If declarativo está habilitado en config.yaml"
    echo ""
    
    if [ -f "$SRC_DIR/run_whatif_declarative.py" ]; then
        python "$SRC_DIR/run_whatif_declarative.py" || {
            echo "⚠️  What-If declarativo falló, pero el pipeline continúa"
        }
    else
        echo "⚠️  No se encontró: $SRC_DIR/run_whatif_declarative.py"
        echo "   Saltando paso de What-If"
    fi
else
    echo "ℹ️  What-If declarativo está deshabilitado (whatif_config.enabled: false)"
    echo "   Para habilitarlo, edita config.yaml y establece whatif_config.enabled: true"
fi

echo ""
echo "=================================================================================="
echo "✅ PASO 4 COMPLETADO"
echo "=================================================================================="
echo ""

# Desactivar entorno virtual
deactivate

echo ""
echo "🎉 ¡Pipeline completado exitosamente!"
echo ""
echo "📁 Archivos generados:"
echo "   • BPMN y JSON: data/generado-simod/"
echo "   • Estado parcial: data/generado-state/"
echo "   • Simulación: data/generado-short-term-simulation/"
if [ "$WHATIF_ENABLED" = "true" ]; then
    echo "   • What-If declarativo: data/generado-whatif-declarative/"
fi
