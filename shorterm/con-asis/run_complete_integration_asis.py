#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar la integración completa: DeclarativeProcessSimulation + ongoing-bps-state (con AS-IS)
Esta es una nueva integración que usa el BPMN AS-IS y JSON AS-IS generados por SIMOD
"""

import os
import sys
import subprocess
import json
import datetime

def run_declarative_pipeline():
    """Ejecuta el pipeline de DeclarativeProcessSimulation"""
    print("🚀 Ejecutando pipeline DeclarativeProcessSimulation...")
    
    # Cambiar al directorio padre
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(parent_dir)
    
    try:
        # Ejecutar dg_prediction.py
        result = subprocess.run([
            "/home/andrew/miniconda3/envs/deep_generator/bin/python", 
            "dg_prediction.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Pipeline DeclarativeProcessSimulation completado")
            return True
        else:
            print(f"❌ Error en pipeline: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando pipeline: {e}")
        return False

def run_ongoing_bps_state_asis():
    """Ejecuta la funcionalidad de ongoing-bps-state usando modelos AS-IS"""
    print("\n🔄 Ejecutando ongoing-bps-state con modelos AS-IS...")
    
    # Volver al directorio shorterm
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Buscar la ruta correcta del venv de ongoing-bps-state
        possible_venv_paths = [
            "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term/venv/bin/python",
            "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1-short-term/repos-short-term/ongoing-bps-state/venv/bin/python"
        ]
        
        venv_python = None
        for venv_path in possible_venv_paths:
            if os.path.exists(venv_path):
                venv_python = venv_path
                break
        
        if venv_python is None:
            print("❌ No se encontró el venv de ongoing-bps-state")
            print("   Intentando usar el Python del sistema...")
            venv_python = "python3"
        
        # Ejecutar test_ongoing_asis.py con el entorno de ongoing-bps-state
        result = subprocess.run([
            venv_python,
            "test_ongoing_asis.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ongoing-bps-state con AS-IS completado")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Error en ongoing-bps-state con AS-IS: {result.stderr}")
            if result.stdout:
                print("STDOUT:", result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando ongoing-bps-state con AS-IS: {e}")
        return False

def run_comparison_and_visualization():
    """Ejecuta la comparación y visualización"""
    print("\n📊 Ejecutando comparación y visualización...")
    
    # Cambiar al directorio comparison_stats
    comparison_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "comparison_stats")
    os.chdir(comparison_dir)
    
    try:
        # Ejecutar compare_stats.py
        result1 = subprocess.run([
            "/home/andrew/miniconda3/envs/deep_generator/bin/python",
            "compare_stats.py"
        ], capture_output=True, text=True)
        
        if result1.returncode != 0:
            print(f"❌ Error en compare_stats: {result1.stderr}")
            return False
        
        # Ejecutar visualize_stats.py
        result2 = subprocess.run([
            "/home/andrew/miniconda3/envs/deep_generator/bin/python",
            "visualize_stats.py"
        ], capture_output=True, text=True)
        
        if result2.returncode == 0:
            print("✅ Comparación y visualización completada")
            return True
        else:
            print(f"❌ Error en visualize_stats: {result2.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando comparación: {e}")
        return False

def generate_integration_report():
    """Genera un reporte de la integración completa con AS-IS"""
    print("\n📋 Generando reporte de integración (AS-IS)...")
    
    # Verificar archivos generados
    base_path = "../data"
    log_name = "PurchasingExample"
    
    # Verificar resultados de DeclarativeProcessSimulation
    declarative_results = [
        f"{base_path}/4.simulation_results/{log_name}/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_ASIS/{log_name}_prosimos_stats.csv",
        f"{base_path}/4.simulation_results/{log_name}/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_TOBE/{log_name}_prosimos_stats.csv"
    ]
    
    # Verificar resultados de ongoing-bps-state con AS-IS
    ongoing_results = [
        f"{base_path}/5.ongoing_state_asis/{log_name}/process_state_asis.json",
        f"{base_path}/5.ongoing_state_asis/{log_name}/ongoing_simulation_log_asis.csv",
        f"{base_path}/5.ongoing_state_asis/{log_name}/ongoing_simulation_stats_asis.csv"
    ]
    
    # Verificar resultados de comparación
    comparison_results = [
        f"{base_path}/4.simulation_results/{log_name}/comparison_stats/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_comparison.csv",
        f"{base_path}/4.simulation_results/{log_name}/comparison_stats/visualizations/comparison_report.html"
    ]
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "integration_type": "AS-IS",
        "description": "Integración usando modelos BPMN AS-IS y JSON AS-IS generados por SIMOD",
        "declarative_process_simulation": {
            "status": "completed" if all(os.path.exists(f) for f in declarative_results) else "failed",
            "files": declarative_results
        },
        "ongoing_bps_state_asis": {
            "status": "completed" if all(os.path.exists(f) for f in ongoing_results) else "failed", 
            "files": ongoing_results,
            "model_type": "AS-IS",
            "bpmn_source": f"{base_path}/3.bps_asis/{log_name}",
            "json_source": f"{base_path}/3.bps_asis/{log_name}"
        },
        "comparison_visualization": {
            "status": "completed" if all(os.path.exists(f) for f in comparison_results) else "failed",
            "files": comparison_results
        }
    }
    
    # Guardar reporte
    report_file = f"{base_path}/integration_report_asis.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Reporte guardado en: {report_file}")
    
    # Mostrar resumen
    print("\n📊 RESUMEN DE INTEGRACIÓN (AS-IS):")
    print(f"• DeclarativeProcessSimulation: {report['declarative_process_simulation']['status']}")
    print(f"• ongoing-bps-state (AS-IS): {report['ongoing_bps_state_asis']['status']}")
    print(f"• Comparación y visualización: {report['comparison_visualization']['status']}")
    
    return report

def main():
    """Función principal"""
    print("🎯 EJECUTANDO INTEGRACIÓN COMPLETA: DeclarativeProcessSimulation + ongoing-bps-state (AS-IS)")
    print("=" * 80)
    print("📌 Esta integración usa modelos BPMN AS-IS y JSON AS-IS generados por SIMOD")
    print("=" * 80)
    
    success_count = 0
    total_steps = 3
    
    # Paso 1: DeclarativeProcessSimulation
    if run_declarative_pipeline():
        success_count += 1
    else:
        print("❌ Falló DeclarativeProcessSimulation")
        return
    
    # Paso 2: ongoing-bps-state con AS-IS
    if run_ongoing_bps_state_asis():
        success_count += 1
    else:
        print("⚠️ ongoing-bps-state con AS-IS falló, pero continuando...")
    
    # Paso 3: Comparación y visualización
    if run_comparison_and_visualization():
        success_count += 1
    else:
        print("❌ Falló comparación y visualización")
        return
    
    # Generar reporte
    report = generate_integration_report()
    
    print("\n" + "=" * 80)
    print(f"🎉 INTEGRACIÓN COMPLETADA: {success_count}/{total_steps} pasos exitosos")
    
    if success_count == total_steps:
        print("✅ ¡Toda la integración funcionó correctamente!")
    else:
        print("⚠️ Algunos componentes fallaron, pero la integración principal está funcionando")
    
    print("\n📁 Archivos generados:")
    print("• DeclarativeProcessSimulation: data/4.simulation_results/")
    print("• ongoing-bps-state (AS-IS): data/5.ongoing_state_asis/")
    print("• Comparación: data/4.simulation_results/PurchasingExample/comparison_stats/")
    print("• Reporte: data/integration_report_asis.json")
    
    print("\n📊 Diferencias con la integración anterior:")
    print("• Esta integración usa modelos AS-IS (BPMN y JSON originales)")
    print("• La integración anterior usa modelos TO-BE (BPMN generado) y JSON merged")
    print("• Los resultados se guardan en 5.ongoing_state_asis/ (nueva carpeta)")

if __name__ == "__main__":
    main()

