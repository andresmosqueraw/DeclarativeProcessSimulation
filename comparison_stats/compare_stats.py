#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para comparar estadísticas entre modelos AS-IS y TO-BE
"""

import pandas as pd
import os
import sys
from pathlib import Path

def load_prosimos_stats(stats_file):
    """Carga las estadísticas de Prosimos desde el archivo CSV"""
    try:
        # Leer el archivo línea por línea para encontrar las secciones
        with open(stats_file, 'r') as f:
            lines = f.readlines()
        
        # Buscar la sección "Overall Scenario Statistics"
        overall_start = None
        for i, line in enumerate(lines):
            if 'Overall Scenario Statistics' in line:
                overall_start = i
                break
        
        if overall_start is None:
            print(f"No se encontró sección 'Overall Scenario Statistics' en {stats_file}")
            return None
        
        # Leer desde la línea de inicio hasta encontrar una línea vacía
        overall_lines = []
        for i in range(overall_start, len(lines)):
            line = lines[i].strip()
            if line == '':
                break
            overall_lines.append(line)
        
        # Convertir a DataFrame
        if len(overall_lines) > 2:  # Header + KPI header + data
            # La primera línea es "Overall Scenario Statistics"
            # La segunda línea es el header: "KPI,Min,Max,Average,Accumulated Value,Trace Ocurrences"
            # Las siguientes líneas son los datos
            data_lines = overall_lines[2:]  # Saltar las dos primeras líneas
            
            data = []
            for line in data_lines:
                if ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 6:  # Asegurar que tenemos todas las columnas
                        kpi = parts[0].strip()
                        min_val = parts[1].strip()
                        max_val = parts[2].strip()
                        avg_val = parts[3].strip()
                        acc_val = parts[4].strip()
                        trace_occ = parts[5].strip()
                        
                        data.append({
                            'KPI': kpi,
                            'Min': min_val,
                            'Max': max_val,
                            'Average': avg_val,
                            'Accumulated': acc_val,
                            'Trace_Occurrences': trace_occ
                        })
            
            if data:
                df = pd.DataFrame(data)
                return df
        
        return None
        
    except Exception as e:
        print(f"Error loading {stats_file}: {e}")
        return None

def compare_overall_stats(asis_stats_file, tobe_stats_file, output_file=None):
    """
    Compara las estadísticas overall entre AS-IS y TO-BE
    
    Args:
        asis_stats_file: Ruta al archivo de stats AS-IS
        tobe_stats_file: Ruta al archivo de stats TO-BE  
        output_file: Archivo de salida para el reporte (opcional)
    """
    
    print("=== COMPARACIÓN DE ESTADÍSTICAS AS-IS vs TO-BE ===\n")
    
    # Cargar estadísticas
    asis_df = load_prosimos_stats(asis_stats_file)
    tobe_df = load_prosimos_stats(tobe_stats_file)
    
    if asis_df is None or tobe_df is None:
        print("❌ Error: No se pudieron cargar las estadísticas")
        return
    
    # Encontrar la sección de estadísticas overall
    asis_overall = find_overall_section(asis_df)
    tobe_overall = find_overall_section(tobe_df)
    
    if asis_overall is None or tobe_overall is None:
        print("❌ Error: No se encontraron estadísticas overall")
        return
    
    # Crear comparación
    comparison = create_comparison_table(asis_overall, tobe_overall)
    
    # Mostrar resultados
    print_comparison(comparison)
    
    # Guardar si se especifica archivo de salida
    if output_file:
        save_comparison(comparison, output_file)
        print(f"\n📊 Reporte guardado en: {output_file}")

def find_overall_section(df):
    """Encuentra la sección de estadísticas overall en el DataFrame"""
    # Si ya tenemos el DataFrame con las métricas, lo devolvemos
    if df is not None and 'KPI' in df.columns:
        return df
    return None

def create_comparison_table(asis_overall, tobe_overall):
    """Crea tabla de comparación entre AS-IS y TO-BE"""
    
    comparison = []
    
    # Comparar cada KPI
    for _, asis_row in asis_overall.iterrows():
        kpi = asis_row['KPI']
        
        # Buscar el mismo KPI en TO-BE
        tobe_row = tobe_overall[tobe_overall['KPI'] == kpi]
        
        if not tobe_row.empty:
            asis_avg = float(asis_row['Average'])
            tobe_avg = float(tobe_row.iloc[0]['Average'])
            
            change = calculate_change(asis_avg, tobe_avg)
            
            comparison.append({
                'KPI': kpi,
                'AS-IS_Average': asis_avg,
                'TO-BE_Average': tobe_avg,
                'Change': change,
                'Change %': f"{change:.2f}%",
                'AS-IS_Min': float(asis_row['Min']),
                'TO-BE_Min': float(tobe_row.iloc[0]['Min']),
                'AS-IS_Max': float(asis_row['Max']),
                'TO-BE_Max': float(tobe_row.iloc[0]['Max'])
            })
    
    return pd.DataFrame(comparison)

def extract_metric_value(df, metric_name):
    """Extrae el valor de una métrica específica del DataFrame"""
    try:
        # Buscar la métrica en la columna 'Metric'
        for idx, row in df.iterrows():
            if metric_name.lower() in str(row['Metric']).lower():
                # El valor está en la columna 'Value'
                value_str = str(row['Value']).replace(',', '').strip()
                # Intentar convertir a float
                try:
                    return float(value_str)
                except:
                    return None
    except:
        pass
    return None

def calculate_change(asis_val, tobe_val):
    """Calcula el cambio porcentual entre AS-IS y TO-BE"""
    if asis_val == 0:
        return 0
    return ((tobe_val - asis_val) / asis_val) * 100

def print_comparison(comparison_df):
    """Imprime la tabla de comparación"""
    print("📊 COMPARACIÓN DE KPIs AS-IS vs TO-BE")
    print("=" * 100)
    print(f"{'KPI':<20} {'AS-IS Avg':<12} {'TO-BE Avg':<12} {'Cambio %':<12} {'AS-IS Min':<12} {'TO-BE Min':<12} {'AS-IS Max':<12} {'TO-BE Max':<12}")
    print("-" * 100)
    
    for _, row in comparison_df.iterrows():
        print(f"{row['KPI']:<20} {row['AS-IS_Average']:<12.2f} {row['TO-BE_Average']:<12.2f} {row['Change %']:<12} {row['AS-IS_Min']:<12.2f} {row['TO-BE_Min']:<12.2f} {row['AS-IS_Max']:<12.2f} {row['TO-BE_Max']:<12.2f}")
    
    print("\n📈 INTERPRETACIÓN:")
    print("• Cambio positivo (+) = TO-BE es mayor que AS-IS")
    print("• Cambio negativo (-) = TO-BE es menor que AS-IS")
    print("• Para cycle_time: negativo es mejor (más rápido)")
    print("• Para processing_time: negativo es mejor (más eficiente)")
    print("• Para waiting_time: negativo es mejor (menos espera)")
    print("• Para idle_time: negativo es mejor (menos tiempo inactivo)")

def save_comparison(comparison_df, output_file):
    """Guarda la comparación en un archivo CSV"""
    comparison_df.to_csv(output_file, index=False)
    print(f"✅ Comparación guardada en: {output_file}")

def main():
    """Función principal"""
    
    # Configuración de rutas (desde comparison_stats)
    base_path = "../data/4.simulation_results/PurchasingExample"
    rules_name = "directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation"
    
    asis_stats = f"{base_path}/{rules_name}_ASIS/PurchasingExample_prosimos_stats.csv"
    tobe_stats = f"{base_path}/{rules_name}_TOBE/PurchasingExample_prosimos_stats.csv"
    os.makedirs(f"{base_path}/comparison_stats", exist_ok=True)
    output_file = f"{base_path}/comparison_stats/{rules_name}_comparison.csv"
    
    # Verificar que los archivos existen
    if not os.path.exists(asis_stats):
        print(f"❌ Error: No se encontró {asis_stats}")
        return
    
    if not os.path.exists(tobe_stats):
        print(f"❌ Error: No se encontró {tobe_stats}")
        return
    
    # Ejecutar comparación
    compare_overall_stats(asis_stats, tobe_stats, output_file)

if __name__ == "__main__":
    main()
