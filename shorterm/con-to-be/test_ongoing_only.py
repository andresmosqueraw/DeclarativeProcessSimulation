#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar solo la funcionalidad de ongoing-bps-state
"""

import os
import sys
import json
import datetime

# Agregar path de ongoing-bps-state
possible_paths = [
    "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term",
    "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1-short-term/repos-short-term/ongoing-bps-state",
]

ongoing_bps_path = None
for path in possible_paths:
    if os.path.exists(path) and os.path.isdir(path):
        ongoing_bps_path = path
        break

if ongoing_bps_path is None:
    print("❌ No se encontró ongoing-bps-state-short-term")
    sys.exit(1)

if ongoing_bps_path not in sys.path:
    sys.path.append(ongoing_bps_path)

# Agregar path de Prosimos (necesario para que ongoing-bps-state pueda importarlo)
prosimos_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/libraries-used/Prosimos"
if os.path.exists(prosimos_path) and prosimos_path not in sys.path:
    sys.path.insert(0, prosimos_path)
    # También agregar el directorio prosimos dentro de Prosimos
    prosimos_module_path = os.path.join(prosimos_path, "prosimos")
    if os.path.exists(prosimos_module_path) and prosimos_module_path not in sys.path:
        sys.path.insert(0, prosimos_module_path)

try:
    from src.runner import run_process_state_and_simulation
    print("✅ ongoing-bps-state disponible")
    ONGOING_AVAILABLE = True
except ImportError as e:
    print(f"❌ ongoing-bps-state no disponible: {e}")
    ONGOING_AVAILABLE = False
    sys.exit(1)

def test_ongoing_state():
    """Prueba la funcionalidad de ongoing-bps-state"""
    
    print("🔄 Probando funcionalidad de ongoing-bps-state...")
    
    # Configuración
    log_name = "PurchasingExample"
    # Obtener ruta absoluta desde el directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, "..", "..", "data")
    base_path = os.path.abspath(base_path)
    
    # Rutas de archivos
    event_log_path = os.path.join(base_path, "0.logs", log_name, f"{log_name}_ongoing.csv")
    # Buscar el directorio más reciente en 3.bps_tobe
    bpmn_base_dir = os.path.join(base_path, "3.bps_tobe", log_name)
    if not os.path.exists(bpmn_base_dir):
        print(f"❌ Directorio no encontrado: {bpmn_base_dir}")
        return False
    
    # Buscar el subdirectorio más reciente
    subdirs = [d for d in os.listdir(bpmn_base_dir) if os.path.isdir(os.path.join(bpmn_base_dir, d))]
    if not subdirs:
        print(f"❌ No se encontraron subdirectorios en: {bpmn_base_dir}")
        return False
    
    latest_subdir = sorted(subdirs)[-1]
    best_result_dir = os.path.join(bpmn_base_dir, latest_subdir, "best_result")
    
    bpmn_model_path = os.path.join(best_result_dir, f"{log_name}.bpmn")
    bpmn_params_path = os.path.join(best_result_dir, f"{log_name}_merged.json")
    
    # Verificar archivos
    for path in [event_log_path, bpmn_model_path, bpmn_params_path]:
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado: {path}")
            return False
        else:
            print(f"✅ Archivo encontrado: {os.path.basename(path)}")
    
    # Directorio de salida
    ongoing_output_dir = os.path.join(base_path, "5.ongoing_state", log_name)
    os.makedirs(ongoing_output_dir, exist_ok=True)
    
    try:
        print("📊 Calculando estado actual de procesos...")
        
        # Calcular estado
        result = run_process_state_and_simulation(
            event_log=event_log_path,
            bpmn_model=bpmn_model_path,
            bpmn_parameters=bpmn_params_path,
            simulate=False,  # Solo calcular estado
            total_cases=20
        )
        
        # Guardar estado
        state_file = os.path.join(ongoing_output_dir, "process_state.json")
        with open(state_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"✅ Estado calculado guardado en: {state_file}")
        
        # Ejecutar simulación a corto plazo
        print("🎯 Ejecutando simulación a corto plazo...")
        
        # Calcular horizonte (7 días desde ahora)
        now = datetime.datetime.now(datetime.timezone.utc)
        horizon = now + datetime.timedelta(days=7)
        simulation_horizon = horizon.isoformat()
        
        sim_result = run_process_state_and_simulation(
            event_log=event_log_path,
            bpmn_model=bpmn_model_path,
            bpmn_parameters=bpmn_params_path,
            simulate=True,
            simulation_horizon=simulation_horizon,
            total_cases=20,
            sim_stats_csv=os.path.join(ongoing_output_dir, "ongoing_simulation_stats.csv"),
            sim_log_csv=os.path.join(ongoing_output_dir, "ongoing_simulation_log.csv")
        )
        
        print(f"✅ Simulación completada")
        print(f"📁 Resultados guardados en: {ongoing_output_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if test_ongoing_state():
        print("\n🎉 ¡Prueba de ongoing-bps-state exitosa!")
        print("📁 La carpeta 5.ongoing_state ahora debería tener contenido")
    else:
        print("\n❌ La prueba de ongoing-bps-state falló")
