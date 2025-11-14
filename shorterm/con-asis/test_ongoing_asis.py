#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la funcionalidad de ongoing-bps-state usando modelos AS-IS
Esta es una nueva integración que usa el BPMN AS-IS y JSON AS-IS generados por SIMOD
"""

import os
import sys
import json
import datetime

# Agregar path de ongoing-bps-state
# Intentar diferentes rutas posibles
possible_paths = [
    "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term",
    "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1-short-term/repos-short-term/ongoing-bps-state",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 
                 "repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term")
]

ongoing_bps_path = None
for path in possible_paths:
    if os.path.exists(path) and os.path.isdir(path):
        ongoing_bps_path = path
        break

if ongoing_bps_path is None:
    print("❌ No se encontró la carpeta ongoing-bps-state en ninguna de las rutas esperadas:")
    for path in possible_paths:
        print(f"   • {path}")
    ONGOING_AVAILABLE = False
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

if prosimos_found:
    print(f"✅ Prosimos encontrado en: {prosimos_found}")
else:
    print("⚠️  Prosimos no encontrado en las rutas esperadas, intentando continuar...")

# Función auxiliar para obtener el folder más reciente (sin depender de support_modules)
def get_latest_output_folder(output_path):
    """Obtiene el folder más reciente en output_path"""
    if not os.path.exists(output_path):
        return None
    folders = [os.path.join(output_path, f) for f in os.listdir(output_path)]
    folders = [f for f in folders if os.path.isdir(f)]
    if not folders:
        return None
    latest_folder = max(folders, key=os.path.getmtime)
    return os.path.basename(latest_folder)

try:
    from src.runner import run_process_state_and_simulation
    print("✅ ongoing-bps-state disponible")
    print(f"   📁 ongoing-bps-state: {ongoing_bps_path}")
    if prosimos_found:
        print(f"   📁 Prosimos: {prosimos_found}")
    ONGOING_AVAILABLE = True
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print(f"   📁 Ruta ongoing-bps-state: {ongoing_bps_path}")
    if prosimos_found:
        print(f"   📁 Ruta Prosimos: {prosimos_found}")
    else:
        print(f"   ⚠️  Prosimos no encontrado")
    print(f"   💡 Verifica que:")
    print(f"      • La ruta de ongoing-bps-state sea correcta")
    print(f"      • Prosimos esté en libraries-used/Prosimos")
    print(f"      • El venv tenga todas las dependencias instaladas")
    ONGOING_AVAILABLE = False
    sys.exit(1)

def test_ongoing_state_asis():
    """Prueba la funcionalidad de ongoing-bps-state usando modelos AS-IS"""
    
    print("🔄 Probando funcionalidad de ongoing-bps-state con modelos AS-IS...")
    
    # Configuración
    log_name = "PurchasingExample"
    base_path = "../data"
    
    # Obtener el folder más reciente de AS-IS
    asis_base_path = f"{base_path}/3.bps_asis/{log_name}"
    if not os.path.exists(asis_base_path):
        print(f"❌ No se encontró la carpeta AS-IS: {asis_base_path}")
        return False
    
    latest_folder = get_latest_output_folder(asis_base_path)
    if not latest_folder:
        print(f"❌ No se encontró ningún folder en: {asis_base_path}")
        return False
    
    print(f"✅ Usando folder AS-IS más reciente: {latest_folder}")
    
    # Rutas de archivos AS-IS
    bpmn_model_path = f"{asis_base_path}/{latest_folder}/best_result/{log_name}.bpmn"
    bpmn_params_path = f"{asis_base_path}/{latest_folder}/best_result/{log_name}.json"
    
    # Usar el log original para calcular el estado
    event_log_path = f"{base_path}/0.logs/{log_name}/{log_name}.csv"
    
    # Si existe un log específico para ongoing, usarlo; si no, usar el original
    ongoing_log_path = f"{base_path}/0.logs/{log_name}/{log_name}_ongoing.csv"
    if os.path.exists(ongoing_log_path):
        event_log_path = ongoing_log_path
        print(f"✅ Usando log específico para ongoing: {ongoing_log_path}")
    else:
        print(f"✅ Usando log original: {event_log_path}")
    
    # Verificar archivos
    files_to_check = {
        "Event Log": event_log_path,
        "BPMN Model (AS-IS)": bpmn_model_path,
        "JSON Parameters (AS-IS)": bpmn_params_path
    }
    
    for file_type, path in files_to_check.items():
        if not os.path.exists(path):
            print(f"❌ Archivo no encontrado ({file_type}): {path}")
            return False
        else:
            print(f"✅ Archivo encontrado ({file_type}): {path}")
    
    # Directorio de salida (nuevo para diferenciar de la integración anterior)
    ongoing_output_dir = f"{base_path}/5.ongoing_state_asis/{log_name}"
    os.makedirs(ongoing_output_dir, exist_ok=True)
    
    try:
        print("\n📊 Calculando estado actual de procesos desde modelo AS-IS...")
        
        # Calcular estado (sin simulación primero)
        result = run_process_state_and_simulation(
            event_log=event_log_path,
            bpmn_model=bpmn_model_path,
            bpmn_parameters=bpmn_params_path,
            simulate=False,  # Solo calcular estado
            total_cases=20
        )
        
        # Leer output.json que se creó en el directorio de ejecución
        # (run_process_state_and_simulation guarda el estado ahí)
        # Intentar múltiples rutas posibles
        possible_output_paths = [
            "output.json",  # Directorio actual
            os.path.join(os.path.dirname(__file__), "output.json"),  # Directorio del script
            os.path.join(os.getcwd(), "output.json"),  # Directorio de trabajo actual
        ]
        
        output_json_path = None
        for path in possible_output_paths:
            if os.path.exists(path):
                output_json_path = path
                break
        
        if output_json_path:
            with open(output_json_path, 'r') as f:
                result = json.load(f)
            print(f"✅ Estado leído desde: {output_json_path}")
        else:
            print(f"⚠️  No se encontró output.json en ninguna de las rutas esperadas")
            if result is None:
                print(f"❌ Error: result es None y no se encontró output.json")
                return False
        
        # Guardar estado en el directorio de salida
        state_file = os.path.join(ongoing_output_dir, "process_state_asis.json")
        with open(state_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"✅ Estado calculado guardado en: {state_file}")
        
        # Ejecutar simulación a corto plazo
        print("\n🎯 Ejecutando simulación a corto plazo desde estado AS-IS...")
        
        # Calcular horizonte (7 días desde ahora)
        now = datetime.datetime.now(datetime.timezone.utc)
        horizon = now + datetime.timedelta(days=7)
        simulation_horizon = horizon.isoformat()
        
        print(f"📅 Horizonte de simulación: {simulation_horizon}")
        
        sim_result = run_process_state_and_simulation(
            event_log=event_log_path,
            bpmn_model=bpmn_model_path,
            bpmn_parameters=bpmn_params_path,
            simulate=True,
            simulation_horizon=simulation_horizon,
            total_cases=20,
            sim_stats_csv=os.path.join(ongoing_output_dir, "ongoing_simulation_stats_asis.csv"),
            sim_log_csv=os.path.join(ongoing_output_dir, "ongoing_simulation_log_asis.csv")
        )
        
        print(f"✅ Simulación completada")
        print(f"📁 Resultados guardados en: {ongoing_output_dir}")
        print(f"   • Estado: process_state_asis.json")
        print(f"   • Estadísticas: ongoing_simulation_stats_asis.csv")
        print(f"   • Log de simulación: ongoing_simulation_log_asis.csv")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_ongoing_state_asis():
        print("\n🎉 ¡Prueba de ongoing-bps-state con AS-IS exitosa!")
        print("📁 La carpeta 5.ongoing_state_asis ahora debería tener contenido")
    else:
        print("\n❌ La prueba de ongoing-bps-state con AS-IS falló")

