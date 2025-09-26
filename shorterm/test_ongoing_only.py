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
ongoing_bps_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1-short-term/repos-short-term/ongoing-bps-state"
if ongoing_bps_path not in sys.path:
    sys.path.append(ongoing_bps_path)

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
    base_path = "../data"
    
    # Rutas de archivos
    event_log_path = f"{base_path}/0.logs/{log_name}/{log_name}_ongoing.csv"
    bpmn_model_path = f"{base_path}/3.bps_tobe/{log_name}/20250926_181023_70FFA5C6_19A5_43EB_9E54_2347C1A341E4/best_result/{log_name}.bpmn"
    bpmn_params_path = f"{base_path}/3.bps_tobe/{log_name}/20250926_181023_70FFA5C6_19A5_43EB_9E54_2347C1A341E4/best_result/{log_name}_merged.json"
    
    # Verificar archivos
    for path in [event_log_path, bpmn_model_path, bpmn_params_path]:
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado: {path}")
            return False
        else:
            print(f"✅ Archivo encontrado: {path}")
    
    # Directorio de salida
    ongoing_output_dir = f"{base_path}/5.ongoing_state/{log_name}"
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
