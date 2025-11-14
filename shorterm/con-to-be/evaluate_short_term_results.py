#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de evaluación de resultados de short-term simulation
Usa los componentes de evaluación de ongoing-bps-state-short-term
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# Agregar path de ongoing-bps-state-short-term para acceder a los módulos de evaluación
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

# Agregar paths necesarios
test_path = os.path.join(ongoing_bps_path, "test")
if test_path not in sys.path:
    sys.path.insert(0, test_path)
if ongoing_bps_path not in sys.path:
    sys.path.insert(0, ongoing_bps_path)

try:
    import evaluation as ev
    from helper import read_event_log, split_into_subsets
    print("✅ Módulos de evaluación disponibles")
except ImportError as e:
    print(f"❌ Error importando módulos de evaluación: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def evaluate_short_term_simulation(
    reference_log_path: str,
    simulated_log_path: str,
    process_state_path: str,
    output_dir: str,
    cut_timestamp: pd.Timestamp = None,
    horizon_days: int = 7
) -> dict:
    """
    Evalúa los resultados de la simulación short-term comparando con el log de referencia.
    
    Args:
        reference_log_path: Ruta al log de referencia (original o generado)
        simulated_log_path: Ruta al log simulado (resultado de ongoing-bps-state)
        process_state_path: Ruta al archivo process_state.json
        output_dir: Directorio donde guardar los resultados de evaluación
        cut_timestamp: Timestamp del punto de corte (si None, se calcula desde process_state)
        horizon_days: Días del horizonte de simulación (default: 7)
    
    Returns:
        dict: Diccionario con las métricas de evaluación
    """
    print("\n📊 Iniciando evaluación de resultados short-term...")
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Leer logs
    print("📖 Leyendo logs...")
    
    # Leer log de referencia (puede tener diferentes formatos de columnas)
    try:
        reference_log = read_event_log(
            reference_log_path,
            rename={
                "CaseId": "case_id",
                "caseid": "case_id",
                "Activity": "activity",
                "task": "activity",
                "Resource": "resource",
                "user": "resource",
                "StartTime": "start_time",
                "start_timestamp": "start_time",
                "EndTime": "end_time",
                "end_timestamp": "end_time",
            },
            required=["case_id", "activity", "start_time", "end_time"]
        )
        # Si no tiene resource, agregar columna vacía
        if "resource" not in reference_log.columns:
            reference_log["resource"] = None
    except Exception as e:
        print(f"❌ Error leyendo log de referencia: {e}")
        raise
    
    # Leer log simulado (ya debería estar en formato correcto)
    try:
        simulated_log = read_event_log(
            simulated_log_path,
            rename={
                "CaseId": "case_id",
                "caseid": "case_id",
                "Activity": "activity",
                "task": "activity",
                "Resource": "resource",
                "user": "resource",
                "StartTime": "start_time",
                "start_timestamp": "start_time",
                "EndTime": "end_time",
                "end_timestamp": "end_time",
            },
            required=["case_id", "activity", "start_time", "end_time"]
        )
        # Si no tiene resource, agregar columna vacía
        if "resource" not in simulated_log.columns:
            simulated_log["resource"] = None
    except Exception as e:
        print(f"❌ Error leyendo log simulado: {e}")
        raise
    
    # 2. Determinar punto de corte y horizonte
    if cut_timestamp is None:
        # Leer process_state.json para obtener last_case_arrival
        try:
            with open(process_state_path, 'r') as f:
                process_state = json.load(f)
            
            # Verificar si process_state es válido (no null)
            if process_state and isinstance(process_state, dict):
                last_case_arrival_str = process_state.get("last_case_arrival")
                if last_case_arrival_str:
                    cut_timestamp = pd.to_datetime(last_case_arrival_str, utc=True)
                else:
                    # Fallback: usar el último timestamp del log de referencia
                    cut_timestamp = reference_log["start_time"].max()
                    print(f"⚠️  No se encontró last_case_arrival en process_state, usando último timestamp: {cut_timestamp}")
            else:
                # process_state es null o no es un dict
                cut_timestamp = reference_log["start_time"].max()
                print(f"⚠️  process_state.json está vacío o inválido, usando último timestamp del log: {cut_timestamp}")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # Fallback: usar el último timestamp del log de referencia
            cut_timestamp = reference_log["start_time"].max()
            print(f"⚠️  Error leyendo process_state.json ({e}), usando último timestamp: {cut_timestamp}")
    
    end_timestamp = cut_timestamp + pd.Timedelta(days=horizon_days)
    
    print(f"📅 Punto de corte: {cut_timestamp}")
    print(f"📅 Horizonte: {end_timestamp} ({horizon_days} días)")
    
    # 3. Dividir logs de referencia en subsets
    print("🔍 Dividiendo log de referencia en subsets...")
    A_event, A_ongoing, A_complete = split_into_subsets(
        reference_log, cut_timestamp, end_timestamp
    )
    
    # Guardar subsets de referencia
    ev._dump(A_event, output_dir, "A_event_filter.csv")
    ev._dump(A_ongoing, output_dir, "A_ongoing.csv")
    ev._dump(A_complete, output_dir, "A_complete.csv")
    
    # 4. Dividir log simulado en subsets
    print("🔍 Dividiendo log simulado en subsets...")
    G_event, G_ongoing, G_complete = split_into_subsets(
        simulated_log, cut_timestamp, end_timestamp
    )
    
    # Guardar subsets simulados
    ev._dump(G_event, output_dir, "G_event_filter.csv")
    ev._dump(G_ongoing, output_dir, "G_ongoing.csv")
    ev._dump(G_complete, output_dir, "G_complete.csv")
    
    # 5. Calcular métricas
    print("📊 Calculando métricas de evaluación...")
    metrics = ev._metrics(
        A_event, A_ongoing, A_complete,
        G_event, G_ongoing, G_complete,
        cut_timestamp
    )
    
    # 6. Guardar resultados
    results_file = os.path.join(output_dir, "evaluation_results.json")
    results = {
        "cut_timestamp": cut_timestamp.isoformat(),
        "end_timestamp": end_timestamp.isoformat(),
        "horizon_days": horizon_days,
        "metrics": metrics,
        "summary": {
            "reference_cases_ongoing": len(A_ongoing["case_id"].unique()),
            "simulated_cases_ongoing": len(G_ongoing["case_id"].unique()),
            "reference_cases_complete": len(A_complete["case_id"].unique()),
            "simulated_cases_complete": len(G_complete["case_id"].unique()),
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"✅ Resultados de evaluación guardados en: {results_file}")
    
    # 7. Mostrar resumen
    print("\n📊 RESUMEN DE EVALUACIÓN:")
    print(f"  • Casos en curso (referencia): {results['summary']['reference_cases_ongoing']}")
    print(f"  • Casos en curso (simulado): {results['summary']['simulated_cases_ongoing']}")
    print(f"  • Casos completados (referencia): {results['summary']['reference_cases_complete']}")
    print(f"  • Casos completados (simulado): {results['summary']['simulated_cases_complete']}")
    
    if metrics.get("event_filter"):
        print("\n📈 Métricas Event Filter:")
        for key, value in metrics["event_filter"].items():
            if value is not None:
                print(f"    • {key}: {value:.4f}")
    
    if metrics.get("ongoing_filter"):
        print("\n📈 Métricas Ongoing Filter:")
        for key, value in metrics["ongoing_filter"].items():
            if value is not None:
                print(f"    • {key}: {value:.4f}" if isinstance(value, float) else f"    • {key}: {value}")
    
    if metrics.get("complete_filter"):
        print("\n📈 Métricas Complete Filter:")
        for key, value in metrics["complete_filter"].items():
            if value is not None:
                print(f"    • {key}: {value:.4f}")
    
    return results


def main():
    """Función principal para ejecutar evaluación desde línea de comandos"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluar resultados de short-term simulation")
    parser.add_argument("--reference-log", required=True, help="Ruta al log de referencia")
    parser.add_argument("--simulated-log", required=True, help="Ruta al log simulado")
    parser.add_argument("--process-state", required=True, help="Ruta al process_state.json")
    parser.add_argument("--output-dir", required=True, help="Directorio de salida")
    parser.add_argument("--cut-timestamp", help="Timestamp del punto de corte (ISO format)")
    parser.add_argument("--horizon-days", type=int, default=7, help="Días del horizonte (default: 7)")
    
    args = parser.parse_args()
    
    cut_ts = None
    if args.cut_timestamp:
        cut_ts = pd.to_datetime(args.cut_timestamp, utc=True)
    
    evaluate_short_term_simulation(
        reference_log_path=args.reference_log,
        simulated_log_path=args.simulated_log,
        process_state_path=args.process_state,
        output_dir=args.output_dir,
        cut_timestamp=cut_ts,
        horizon_days=args.horizon_days
    )


if __name__ == "__main__":
    main()

