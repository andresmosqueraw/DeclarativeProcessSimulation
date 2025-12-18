#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar la Simulación Neuro-Simbólica (Short-Term What-If).
Usa:
1. Estado Parcial (AS-IS)
2. Modelo BPMN (AS-IS)
3. Reglas Declarativas (LTL)
4. Modelo LSTM (Predictivo)

Para realizar una simulación donde las decisiones de ruta (XOR) son tomadas 
por el "Cerebro AI" (LSTM) validado por el "Monitor Lógico" (Reglas).
"""

import os
import sys
import json
import yaml
import glob
import argparse
from pathlib import Path
import datetime

# -----------------------------------------------------------------------------
# Configuración de Paths
# -----------------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(script_dir) == "src":
    base_dir = os.path.dirname(script_dir)
else:
    base_dir = script_dir

# Paths clave
declarative_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
ongoing_bps_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term"

# Agregar módulos al path
if ongoing_bps_path not in sys.path:
    sys.path.insert(0, ongoing_bps_path)

# Importar la función Neuro-Simbólica
from src.process_state_prosimos_run import run_whatif_short_term_simulation, parse_datetime

# -----------------------------------------------------------------------------
# Funciones de Ayuda
# -----------------------------------------------------------------------------
def load_config(config_path=None):
    if config_path is None:
        config_path = os.path.join(base_dir, "config.yaml")
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")
        return None

def get_log_name_from_path(log_path):
    return os.path.splitext(os.path.basename(log_path))[0]

def extract_cut_point_from_state(state_file_path, partial_state):
    # Intenta extraer fecha de corte del estado parcial
    if "last_case_arrival" in partial_state:
        try:
            return parse_datetime(partial_state["last_case_arrival"])
        except:
            pass
    return datetime.datetime.now(datetime.timezone.utc)

def filter_ongoing_cases_only(partial_state):
    """Filtra el estado para dejar solo casos activos (simplificado)."""
    if not partial_state or "cases" not in partial_state:
        return partial_state, 0
    
    filtered_cases = {}
    count = 0
    for cid, cdata in partial_state["cases"].items():
        # Criterio simple: tiene actividades en curso o tokens
        if (cdata.get("ongoing_activities") or 
            cdata.get("enabled_activities") or 
            cdata.get("control_flow_state", {}).get("flows")):
            filtered_cases[cid] = cdata
            count += 1
            
    partial_state["cases"] = filtered_cases
    return partial_state, count

def read_rules(rules_path):
    # Leer reglas en un diccionario simple o crudo
    # Por simplicidad, pasamos el path o leemos el contenido
    rules = {}
    if os.path.exists(rules_path):
        import configparser
        cp = configparser.ConfigParser()
        cp.read(rules_path)
        # Convertir a dict
        for sec in cp.sections():
            rules[sec] = dict(cp.items(sec))
    return rules

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
def main():
    print(f"\n{'='*80}")
    print(f"🧠 EJECUTANDO SIMULACIÓN NEURO-SIMBÓLICA (WHAT-IF SHORT-TERM)")
    print(f"{'='*80}")

    # 1. Cargar Configuración
    config = load_config()
    if not config:
        return
        
    log_config = config.get("log_config", {})
    log_path = log_config.get("log_path")
    if not log_path:
        print("❌ No log_path en config.")
        return
    if not os.path.isabs(log_path):
        log_path = os.path.join(base_dir, log_path)
    log_name = get_log_name_from_path(log_path)
    
    # 2. Localizar Recursos (AS-IS Model, Rules, LSTM, State)
    
    # a) Modelo AS-IS (Generado por Simod)
    simod_output_dir = os.path.join(base_dir, "data", "generado-simod")
    bpmn_path = os.path.join(simod_output_dir, f"{log_name}.bpmn")
    json_path = os.path.join(simod_output_dir, f"{log_name}.json")
    
    if not os.path.exists(bpmn_path) or not os.path.exists(json_path):
        print(f"❌ No se encontró modelo AS-IS en: {simod_output_dir}")
        return

    # b) Reglas Declarativas
    whatif_config = config.get("whatif_config", {})
    rules_path = whatif_config.get("rules_path")
    if not rules_path or not os.path.exists(rules_path):
         rules_path = os.path.join(base_dir, "data", "rules.ini")
    
    if not os.path.exists(rules_path):
        print(f"❌ No se encontraron reglas en: {rules_path}")
        return
    declarative_rules = read_rules(rules_path)
    print(f"✅ Reglas cargadas desde: {rules_path}")

    # c) Modelo LSTM
    # Asumimos estructura de DeclarativeProcessSimulation
    lstm_dir = os.path.join(declarative_dir, "data", "1.predicton_models", log_name)
    # Buscar el último output folder
    import glob
    subdirs = glob.glob(os.path.join(lstm_dir, "20*")) # Folders tipo fecha
    if not subdirs:
         print(f"❌ No se encontró modelo LSTM en: {lstm_dir}")
         # return # Opcional: continuar sin LSTM real para probar la arquitectura
         lstm_model_path = "DUMMY_PATH.h5"
    else:
        latest_lstm_dir = max(subdirs, key=os.path.getmtime)
        lstm_model_path = os.path.join(latest_lstm_dir, f"{log_name}.h5")
        print(f"✅ Modelo LSTM encontrado: {lstm_model_path}")

    # d) Estado Parcial
    state_output_dir = os.path.join(base_dir, "data", "generado-state")
    state_files = sorted(glob.glob(os.path.join(state_output_dir, f"{log_name}_process_state*.json")))
    
    if not state_files:
        print(f"❌ No se encontraron estados parciales en: {state_output_dir}")
        return

    # 3. Configurar Salida
    output_dir = os.path.join(base_dir, "data", "generado-neuro-symbolic")
    os.makedirs(output_dir, exist_ok=True)

    # 4. Ejecutar Simulación por cada Estado
    for state_file in state_files:
        print(f"\n👉 Procesando estado: {os.path.basename(state_file)}")
        
        # Cargar estado
        with open(state_file, 'r') as f:
            partial_state = json.load(f)
            
        # Filtrar casos (Solo Ongoing)
        filtered_state, ongoing_count = filter_ongoing_cases_only(partial_state)
        if ongoing_count == 0:
            print("   ⚠️  Sin casos activos. Saltando.")
            continue
            
        cut_point = extract_cut_point_from_state(state_file, filtered_state)
        
        # Definir Horizonte (ej. 7 días desde corte)
        horizon_dt = cut_point + datetime.timedelta(days=7)
        
        # Definir archivos de salida
        idx = os.path.splitext(os.path.basename(state_file))[0].split('_')[-1] # Extraer timestamp o indice
        stats_csv = os.path.join(output_dir, f"neuro_stats_{idx}.csv")
        log_csv = os.path.join(output_dir, f"neuro_log_{idx}.csv")
        
        try:
            # LLAMADA A LA FUNCIÓN NEURO-SIMBÓLICA
            # IMPORTANTE: Pasar objetos datetime, no strings, porque Prosimos hará cálculos con ellos
            duration = run_whatif_short_term_simulation(
                start_date=cut_point,  # Datetime object
                total_cases=ongoing_count, # Solo existentes
                bpmn_model=bpmn_path,
                json_sim_params=json_path,
                out_stats_csv_path=stats_csv,
                out_log_csv_path=log_csv,
                process_state=filtered_state,
                simulation_horizon=horizon_dt,  # Datetime object
                declarative_rules=declarative_rules,
                lstm_model_path=lstm_model_path
            )
            
            print(f"   ✅ Simulación completada en {duration:.2f}s")
            print(f"   📄 Log generado: {log_csv}")
            
        except Exception as e:
            print(f"   ❌ Error en simulación: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ Proceso finalizado. Resultados en {output_dir}")

if __name__ == "__main__":
    main()

