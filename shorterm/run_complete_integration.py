#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar la integración completa: DeclarativeProcessSimulation + ongoing-bps-state
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

def run_ongoing_bps_state():
    """Ejecuta la funcionalidad de ongoing-bps-state"""
    print("\n🔄 Ejecutando ongoing-bps-state...")
    
    # Volver al directorio shorterm
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Ejecutar test_ongoing_only.py con el entorno de ongoing-bps-state
        result = subprocess.run([
            "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1-short-term/repos-short-term/ongoing-bps-state/venv/bin/python",
            "test_ongoing_only.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ ongoing-bps-state completado")
            return True
        else:
            print(f"❌ Error en ongoing-bps-state: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando ongoing-bps-state: {e}")
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
    """Genera un reporte de la integración completa"""
    print("\n📋 Generando reporte de integración...")
    
    # Verificar archivos generados
    base_path = "../data"
    
    # Verificar resultados de DeclarativeProcessSimulation
    declarative_results = [
        f"{base_path}/4.simulation_results/PurchasingExample/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_ASIS/PurchasingExample_prosimos_stats.csv",
        f"{base_path}/4.simulation_results/PurchasingExample/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_TOBE/PurchasingExample_prosimos_stats.csv"
    ]
    
    # Verificar resultados de ongoing-bps-state
    ongoing_results = [
        f"{base_path}/5.ongoing_state/PurchasingExample/process_state.json",
        f"{base_path}/5.ongoing_state/PurchasingExample/ongoing_simulation_log.csv",
        f"{base_path}/5.ongoing_state/PurchasingExample/ongoing_simulation_stats.csv"
    ]
    
    # Verificar resultados de comparación
    comparison_results = [
        f"{base_path}/4.simulation_results/PurchasingExample/comparison_stats/directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation_comparison.csv",
        f"{base_path}/4.simulation_results/PurchasingExample/comparison_stats/visualizations/comparison_report.html"
    ]
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "declarative_process_simulation": {
            "status": "completed" if all(os.path.exists(f) for f in declarative_results) else "failed",
            "files": declarative_results
        },
        "ongoing_bps_state": {
            "status": "completed" if all(os.path.exists(f) for f in ongoing_results) else "failed", 
            "files": ongoing_results
        },
        "comparison_visualization": {
            "status": "completed" if all(os.path.exists(f) for f in comparison_results) else "failed",
            "files": comparison_results
        }
    }
    
    # Guardar reporte
    report_file = f"{base_path}/integration_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Reporte guardado en: {report_file}")
    
    # Mostrar resumen
    print("\n📊 RESUMEN DE INTEGRACIÓN:")
    print(f"• DeclarativeProcessSimulation: {report['declarative_process_simulation']['status']}")
    print(f"• ongoing-bps-state: {report['ongoing_bps_state']['status']}")
    print(f"• Comparación y visualización: {report['comparison_visualization']['status']}")
    
    return report

def main():
    """Función principal"""
    print("🎯 EJECUTANDO INTEGRACIÓN COMPLETA: DeclarativeProcessSimulation + ongoing-bps-state")
    print("=" * 80)
    
    success_count = 0
    total_steps = 3
    
    # Paso 1: DeclarativeProcessSimulation
    if run_declarative_pipeline():
        success_count += 1
    else:
        print("❌ Falló DeclarativeProcessSimulation")
        return
    
    # Paso 2: ongoing-bps-state
    if run_ongoing_bps_state():
        success_count += 1
    else:
        print("⚠️ ongoing-bps-state falló, pero continuando...")
    
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
    print("• ongoing-bps-state: data/5.ongoing_state/")
    print("• Comparación: data/4.simulation_results/PurchasingExample/comparison_stats/")
    print("• Reporte: data/integration_report.json")

if __name__ == "__main__":
    main()
