#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para calcular el estado parcial del proceso usando ongoing-bps-state-short-term.
Genera el archivo JSON con el estado parcial del proceso en un punto de corte temporal.
"""

import os
import sys
import json
import yaml

# Verificar si estamos en un entorno virtual
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    if os.path.exists(venv_python):
        print("⚠️  No se detectó entorno virtual activo.")
        print(f"💡 Ejecuta: source {script_dir}/venv/bin/activate")
        print("   O ejecuta el script con: venv/bin/python compute_state.py")
        print()

# Agregar path de ongoing-bps-state
ongoing_bps_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term"

if not os.path.exists(ongoing_bps_path):
    print(f"❌ No se encontró la carpeta ongoing-bps-state-short-term en: {ongoing_bps_path}")
    sys.exit(1)

if ongoing_bps_path not in sys.path:
    sys.path.insert(0, ongoing_bps_path)

# Importar después de agregar paths
from src.runner import run_process_state_and_simulation

def load_config(config_path=None):
    """Carga la configuración desde el archivo YAML"""
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(script_dir) == "src":
            base_dir = os.path.dirname(script_dir)
        else:
            base_dir = script_dir
        config_path = os.path.join(base_dir, "config.yaml")
    
    if not os.path.exists(config_path):
        print(f"❌ No se encontró archivo de configuración: {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")
        return None

def get_log_name_from_path(log_path):
    """Extrae el nombre del log desde la ruta"""
    return os.path.splitext(os.path.basename(log_path))[0]

def compute_state(config=None):
    """
    Calcula el estado parcial del proceso.
    
    Args:
        config: Diccionario de configuración (si es None, se carga desde config.yaml)
    
    Returns:
        str: Ruta al archivo de estado generado, o None si falló
    """
    print("=" * 80)
    print("🔧 CÁLCULO DE ESTADO PARCIAL DEL PROCESO")
    print("=" * 80)
    
    # Cargar configuración
    if config is None:
        config = load_config()
        if config is None:
            return None
    
    # Obtener configuración
    ongoing_config = config.get("ongoing_config", {})
    log_config = config.get("log_config", {})
    script_config = config.get("script_config", {})
    
    # Obtener rutas de archivos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == "src":
        base_dir = os.path.dirname(script_dir)
    else:
        base_dir = script_dir
    
    # Directorio de salida para estado parcial
    output_dir = script_config.get("state_output_dir")
    if output_dir is None:
        output_dir = os.path.join(base_dir, "data", "generado-state")
    else:
        output_dir = os.path.abspath(output_dir)
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener ruta del log
    log_path = log_config.get("log_path")
    if not log_path:
        print("❌ Error: No se especificó log_path en config.yaml")
        return None
    
    # Si es una ruta relativa, hacerla relativa al directorio base (nuevo/)
    if not os.path.isabs(log_path):
        log_path = os.path.join(base_dir, log_path)
    
    # Obtener nombre del log
    log_name = get_log_name_from_path(log_path)
    
    # Rutas de BPMN y JSON
    simod_output_dir = os.path.join(base_dir, "data", "generado-simod")
    bpmn_path_simod = os.path.join(simod_output_dir, f"{log_name}.bpmn")
    json_path_simod = os.path.join(simod_output_dir, f"{log_name}.json")
    
    if os.path.exists(bpmn_path_simod) and os.path.exists(json_path_simod):
        bpmn_path = bpmn_path_simod
        json_path = json_path_simod
    else:
        bpmn_path = os.path.join(base_dir, f"{log_name}.bpmn")
        json_path = os.path.join(base_dir, f"{log_name}.json")
    
    # Verificar que todos los archivos existan
    files_to_check = {
        "Event Log": log_path,
        "BPMN Model": bpmn_path,
        "JSON Parameters": json_path
    }
    
    print("\n📋 Verificando archivos necesarios...")
    for file_type, path in files_to_check.items():
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado ({file_type}): {path}")
            return None
        else:
            print(f"✅ {file_type}: {path}")
    
    # Obtener parámetros de configuración
    start_time = ongoing_config.get("start_time")  # None = usar último evento
    column_mapping = ongoing_config.get("column_mapping")
    
    # Si column_mapping es null en ongoing_config, usar el de log_config
    if column_mapping is None:
        column_mapping = log_config.get("column_mapping")
    
    # Convertir column_mapping a JSON string si es un dict
    if column_mapping and isinstance(column_mapping, dict):
        csv_to_standard = {
            column_mapping.get("case", "caseid"): "CaseId",
            column_mapping.get("activity", "task"): "Activity",
            column_mapping.get("resource", "user"): "Resource",
            column_mapping.get("start_time", "start_timestamp"): "StartTime",
            column_mapping.get("end_time", "end_timestamp"): "EndTime"
        }
        column_mapping = json.dumps(csv_to_standard)
    elif column_mapping is None:
        column_mapping = None
    
    # Cambiar al directorio de salida para que output.json se guarde ahí
    original_cwd = os.getcwd()
    os.chdir(output_dir)
    
    try:
        print("\n📊 Calculando estado parcial del proceso...")
        
        # Calcular estado (sin simulación)
        result = run_process_state_and_simulation(
            event_log=log_path,
            bpmn_model=bpmn_path,
            bpmn_parameters=json_path,
            start_time=start_time,
            column_mapping=column_mapping,
            simulate=False,  # Solo calcular estado
            total_cases=ongoing_config.get("total_cases", 20)
        )
        
        # Leer output.json que se creó en el directorio de salida
        output_json_path = os.path.join(output_dir, "output.json")
        
        if os.path.exists(output_json_path):
            with open(output_json_path, 'r') as f:
                result = json.load(f)
            print(f"✅ Estado calculado y guardado en: {output_json_path}")
        else:
            print(f"⚠️  No se encontró output.json en: {output_json_path}")
            if result is None:
                print(f"❌ Error: result es None y no se encontró output.json")
                return None
        
        # Renombrar output.json a un nombre más descriptivo
        state_file = os.path.join(output_dir, f"{log_name}_process_state.json")
        if os.path.exists(output_json_path):
            os.rename(output_json_path, state_file)
            print(f"✅ Estado renombrado a: {state_file}")
        
        print(f"\n📁 Estado parcial guardado en: {state_file}")
        return state_file
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)

def main():
    """Función principal para ejecutar desde línea de comandos"""
    state_file = compute_state()
    if state_file:
        print("\n🎉 ¡Estado parcial calculado exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ El cálculo del estado falló")
        sys.exit(1)

if __name__ == "__main__":
    main()

