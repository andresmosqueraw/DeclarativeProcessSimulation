#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar simulación de corto plazo usando el estado parcial calculado.
Requiere que compute_state.py haya sido ejecutado previamente para generar el estado parcial.
"""

import os
import sys
import json
import datetime
import yaml

# Verificar si estamos en un entorno virtual
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    if os.path.exists(venv_python):
        print("⚠️  No se detectó entorno virtual activo.")
        print(f"💡 Ejecuta: source {script_dir}/venv/bin/activate")
        print("   O ejecuta el script con: venv/bin/python run_simulation.py")
        print()

# Agregar path de ongoing-bps-state
ongoing_bps_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term"

if not os.path.exists(ongoing_bps_path):
    print(f"❌ No se encontró la carpeta ongoing-bps-state-short-term en: {ongoing_bps_path}")
    sys.exit(1)

if ongoing_bps_path not in sys.path:
    sys.path.insert(0, ongoing_bps_path)

# Agregar path de Prosimos (requerido por ongoing-bps-state)
prosimos_paths = [
    os.path.join(ongoing_bps_path, "..", "libraries-used", "Prosimos"),
    os.path.join(os.path.dirname(ongoing_bps_path), "libraries-used", "Prosimos"),
]

prosimos_found = None
for prosimos_path in prosimos_paths:
    abs_prosimos_path = os.path.abspath(prosimos_path)
    if os.path.exists(abs_prosimos_path) and os.path.isdir(abs_prosimos_path):
        prosimos_found = abs_prosimos_path
        if abs_prosimos_path not in sys.path:
            sys.path.insert(0, abs_prosimos_path)
        break

if prosimos_found is None:
    print("⚠️  Advertencia: No se encontró Prosimos, puede haber errores al simular")

# Importar después de agregar paths
from src.process_state_prosimos_run import run_short_term_simulation, parse_datetime

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

def find_state_file(base_dir, log_name, script_config=None):
    """Busca el archivo de estado parcial generado"""
    # Buscar en el directorio de estado parcial
    if script_config:
        state_output_dir = script_config.get("state_output_dir")
        if state_output_dir:
            state_output_dir = os.path.abspath(state_output_dir)
        else:
            state_output_dir = os.path.join(base_dir, "data", "generado-state")
    else:
        state_output_dir = os.path.join(base_dir, "data", "generado-state")
    
    state_file = os.path.join(state_output_dir, f"{log_name}_process_state.json")
    
    if os.path.exists(state_file):
        return state_file
    
    # Intentar con output.json como fallback
    output_json = os.path.join(state_output_dir, "output.json")
    if os.path.exists(output_json):
        return output_json
    
    return None

def run_simulation(config=None, state_file_path=None):
    """
    Ejecuta simulación de corto plazo usando el estado parcial.
    
    Args:
        config: Diccionario de configuración (si es None, se carga desde config.yaml)
        state_file_path: Ruta al archivo de estado parcial (si es None, se busca automáticamente)
    
    Returns:
        bool: True si la simulación fue exitosa, False en caso contrario
    """
    print("=" * 80)
    print("🎯 SIMULACIÓN DE CORTO PLAZO")
    print("=" * 80)
    
    # Cargar configuración
    if config is None:
        config = load_config()
        if config is None:
            return False
    
    # Obtener configuración
    ongoing_config = config.get("ongoing_config", {})
    log_config = config.get("log_config", {})
    script_config = config.get("script_config", {})
    
    # Verificar que la simulación esté habilitada
    if not ongoing_config.get("simulate", False):
        print("ℹ️  Simulación deshabilitada (simulate: false en config.yaml)")
        print("   Para habilitar, establece simulate: true en ongoing_config")
        return False
    
    # Obtener rutas de archivos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == "src":
        base_dir = os.path.dirname(script_dir)
    else:
        base_dir = script_dir
    
    # Directorio de salida para simulación
    output_dir = script_config.get("simulation_output_dir")
    if output_dir is None:
        output_dir = os.path.join(base_dir, "data", "generado-short-term-simulation")
    else:
        output_dir = os.path.abspath(output_dir)
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener ruta del log
    log_path = log_config.get("log_path")
    if not log_path:
        print("❌ Error: No se especificó log_path en config.yaml")
        return False
    
    # Si es una ruta relativa, hacerla relativa al directorio base (nuevo/)
    if not os.path.isabs(log_path):
        log_path = os.path.join(base_dir, log_path)
    
    # Obtener nombre del log
    log_name = get_log_name_from_path(log_path)
    
    # Buscar archivo de estado parcial
    if state_file_path is None:
        state_file_path = find_state_file(base_dir, log_name, script_config)
    
    if not state_file_path or not os.path.exists(state_file_path):
        print(f"❌ Error: No se encontró el archivo de estado parcial")
        state_dir = script_config.get("state_output_dir") if script_config else None
        if not state_dir:
            state_dir = os.path.join(base_dir, "data", "generado-state")
        print(f"   Buscado en: {os.path.join(state_dir, f'{log_name}_process_state.json')}")
        print(f"   Ejecuta primero: python src/compute_state.py")
        return False
    
    print(f"✅ Archivo de estado encontrado: {state_file_path}")
    
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
    
    # Verificar archivos necesarios
    files_to_check = {
        "Event Log": log_path,
        "BPMN Model": bpmn_path,
        "JSON Parameters": json_path,
        "Process State": state_file_path
    }
    
    print("\n📋 Verificando archivos necesarios...")
    for file_type, path in files_to_check.items():
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado ({file_type}): {path}")
            return False
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
    
    # Calcular horizonte de simulación
    simulation_horizon = ongoing_config.get("simulation_horizon")
    if not simulation_horizon:
        # Calcular horizonte automáticamente (días desde ahora)
        horizon_days = ongoing_config.get("horizon_days", 7)
        now = datetime.datetime.now(datetime.timezone.utc)
        horizon = now + datetime.timedelta(days=horizon_days)
        simulation_horizon = horizon.isoformat()
    
    print(f"\n📅 Horizonte de simulación: {simulation_horizon}")
    
    # Rutas de salida para simulación
    sim_stats_csv = os.path.join(output_dir, f"{log_name}_simulation_stats.csv")
    sim_log_csv = os.path.join(output_dir, f"{log_name}_simulation_log.csv")
    
    # Cambiar al directorio de salida
    original_cwd = os.getcwd()
    os.chdir(output_dir)
    
    try:
        print("\n🎯 Ejecutando simulación de corto plazo...")
        
        # Cargar el estado parcial desde el archivo
        with open(state_file_path, 'r') as f:
            partial_state = json.load(f)
        
        # Convertir start_time y simulation_horizon a datetime si son strings
        start_dt = None
        if start_time:
            start_dt = parse_datetime(start_time)
        
        horizon_dt = parse_datetime(simulation_horizon)
        
        # Ejecutar simulación usando el estado parcial directamente
        sim_time = run_short_term_simulation(
            start_date=start_dt,
            total_cases=ongoing_config.get("total_cases", 20),
            bpmn_model=bpmn_path,
            json_sim_params=json_path,
            out_stats_csv_path=sim_stats_csv,
            out_log_csv_path=sim_log_csv,
            process_state=partial_state,
            simulation_horizon=horizon_dt
        )
        
        print(f"✅ Simulación completada en {sim_time:.2f} segundos")
        print(f"📁 Resultados guardados en: {output_dir}")
        print(f"   • Estado: {os.path.basename(state_file_path)}")
        print(f"   • Estadísticas: {os.path.basename(sim_stats_csv)}")
        print(f"   • Log de simulación: {os.path.basename(sim_log_csv)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)

def main():
    """Función principal para ejecutar desde línea de comandos"""
    if run_simulation():
        print("\n🎉 ¡Simulación completada exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ La simulación falló")
        sys.exit(1)

if __name__ == "__main__":
    main()

