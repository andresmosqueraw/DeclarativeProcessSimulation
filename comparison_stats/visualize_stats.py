#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para visualizar estadísticas de comparación AS-IS vs TO-BE
Genera gráficos y reportes HTML más legibles
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

# Configurar estilo
plt.style.use('default')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

def format_time(seconds):
    """Convierte segundos a formato legible (días, horas, minutos, segundos)"""
    if seconds < 0:
        return "0s"
    
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

def format_large_time(seconds):
    """Formato más compacto para tiempos muy grandes"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"

def load_comparison_data(comparison_file):
    """Carga los datos de comparación desde el archivo CSV"""
    try:
        df = pd.read_csv(comparison_file)
        return df
    except Exception as e:
        print(f"Error loading {comparison_file}: {e}")
        return None

def create_performance_chart(df, output_dir):
    """Crea gráfico de barras comparando métricas principales"""
    
    # Preparar datos para el gráfico
    metrics = ['cycle_time', 'processing_time', 'waiting_time', 'idle_time']
    asis_values = []
    tobe_values = []
    
    for metric in metrics:
        row = df[df['KPI'] == metric]
        if not row.empty:
            asis_values.append(row.iloc[0]['AS-IS_Average'])
            tobe_values.append(row.iloc[0]['TO-BE_Average'])
        else:
            asis_values.append(0)
            tobe_values.append(0)
    
    # Crear gráfico
    fig, ax = plt.subplots(figsize=(12, 8))
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, asis_values, width, label='AS-IS', alpha=0.8, color='#ff7f0e')
    bars2 = ax.bar(x + width/2, tobe_values, width, label='TO-BE', alpha=0.8, color='#2ca02c')
    
    ax.set_xlabel('Métricas de Rendimiento')
    ax.set_ylabel('Tiempo')
    ax.set_title('Comparación de Rendimiento: AS-IS vs TO-BE')
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics], rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Formatear eje Y con tiempos legibles
    y_ticks = ax.get_yticks()
    y_labels = [format_large_time(tick) for tick in y_ticks]
    ax.set_yticklabels(y_labels)
    
    # Agregar valores en las barras con formato de tiempo
    def add_value_labels(bars, values):
        for bar, value in zip(bars, values):
            height = bar.get_height()
            formatted_time = format_large_time(value)
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   formatted_time, ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    add_value_labels(bars1, asis_values)
    add_value_labels(bars2, tobe_values)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/performance_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ Gráfico de rendimiento guardado: performance_comparison.png")

def create_change_chart(df, output_dir):
    """Crea gráfico de cambios porcentuales"""
    
    # Preparar datos
    kpis = df['KPI'].tolist()
    changes = df['Change'].tolist()
    
    # Colores: verde para mejoras, rojo para empeoramientos
    colors = ['#2ca02c' if change < 0 else '#d62728' for change in changes]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bars = ax.barh(kpis, changes, color=colors, alpha=0.7)
    
    ax.set_xlabel('Cambio Porcentual (%)')
    ax.set_title('Impacto de las Reglas Declarativas\n(Cambios en TO-BE vs AS-IS)')
    ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    ax.grid(True, alpha=0.3)
    
    # Agregar valores en las barras
    for i, (bar, change) in enumerate(zip(bars, changes)):
        width = bar.get_width()
        ax.text(width + (5 if width > 0 else -5), bar.get_y() + bar.get_height()/2,
               f'{change:.1f}%', ha='left' if width > 0 else 'right', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/change_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ Gráfico de cambios guardado: change_analysis.png")

def create_radar_chart(df, output_dir):
    """Crea gráfico radar para comparación multidimensional"""
    
    # Normalizar datos para el radar chart
    metrics = ['cycle_time', 'processing_time', 'waiting_time', 'idle_time']
    
    asis_normalized = []
    tobe_normalized = []
    
    for metric in metrics:
        row = df[df['KPI'] == metric]
        if not row.empty:
            # Normalizar por el valor máximo entre AS-IS y TO-BE
            max_val = max(row.iloc[0]['AS-IS_Average'], row.iloc[0]['TO-BE_Average'])
            asis_normalized.append(row.iloc[0]['AS-IS_Average'] / max_val * 100)
            tobe_normalized.append(row.iloc[0]['TO-BE_Average'] / max_val * 100)
        else:
            asis_normalized.append(0)
            tobe_normalized.append(0)
    
    # Crear gráfico radar
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]  # Cerrar el círculo
    
    asis_normalized += asis_normalized[:1]
    tobe_normalized += tobe_normalized[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    ax.plot(angles, asis_normalized, 'o-', linewidth=2, label='AS-IS', color='#ff7f0e')
    ax.fill(angles, asis_normalized, alpha=0.25, color='#ff7f0e')
    
    ax.plot(angles, tobe_normalized, 'o-', linewidth=2, label='TO-BE', color='#2ca02c')
    ax.fill(angles, tobe_normalized, alpha=0.25, color='#2ca02c')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics])
    ax.set_ylim(0, 100)
    ax.set_title('Comparación Multidimensional AS-IS vs TO-BE', size=16, pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    ax.grid(True)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/radar_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✅ Gráfico radar guardado: radar_comparison.png")

def encode_image_to_base64(image_path):
    """Convierte una imagen a base64 para incrustarla en HTML"""
    import base64
    
    try:
        with open(image_path, 'rb') as img_file:
            img_data = img_file.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def create_summary_table(df, output_dir):
    """Crea tabla resumen con formato HTML"""
    
    # Preparar datos para la tabla
    summary_data = []
    
    for _, row in df.iterrows():
        kpi = row['KPI']
        asis_avg = row['AS-IS_Average']
        tobe_avg = row['TO-BE_Average']
        change = row['Change']
        
        # Interpretación del cambio
        if 'time' in kpi.lower():
            interpretation = "✅ Mejor" if change < 0 else "❌ Peor"
        else:
            interpretation = "✅ Mejor" if change > 0 else "❌ Peor"
        
        summary_data.append({
            'KPI': kpi.replace('_', ' ').title(),
            'AS-IS': format_time(asis_avg),
            'TO-BE': format_time(tobe_avg),
            'Cambio': f"{change:+.1f}%",
            'Interpretación': interpretation
        })
    
    # Codificar imágenes a base64
    performance_img = encode_image_to_base64(f'{output_dir}/performance_comparison.png')
    change_img = encode_image_to_base64(f'{output_dir}/change_analysis.png')
    radar_img = encode_image_to_base64(f'{output_dir}/radar_comparison.png')
    
    # Crear HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comparación AS-IS vs TO-BE</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; }}
            h3 {{ color: #495057; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            .improvement {{ background-color: #d4edda; }}
            .degradation {{ background-color: #f8d7da; }}
            .summary {{ background-color: #e9ecef; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>📊 Reporte de Comparación: AS-IS vs TO-BE</h1>
        
        <div class="summary">
            <h2>📈 Resumen Ejecutivo</h2>
            <p><strong>Regla Aplicada:</strong> Send Request for Quotation to Supplier >> Analyze Request for Quotation</p>
            <p><strong>Fecha de Análisis:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <h2>📋 Métricas Detalladas</h2>
        <table>
            <tr>
                <th>KPI</th>
                <th>AS-IS (Promedio)</th>
                <th>TO-BE (Promedio)</th>
                <th>Cambio %</th>
                <th>Interpretación</th>
            </tr>
    """
    
    for row in summary_data:
        row_class = "improvement" if "✅" in row['Interpretación'] else "degradation"
        html_content += f"""
            <tr class="{row_class}">
                <td>{row['KPI']}</td>
                <td>{row['AS-IS']}</td>
                <td>{row['TO-BE']}</td>
                <td>{row['Cambio']}</td>
                <td>{row['Interpretación']}</td>
            </tr>
        """
    
    # Agregar sección de visualizaciones
    html_content += f"""
        </table>
        
        <h2>📊 Visualizaciones</h2>
        <p>Las siguientes gráficas muestran la comparación visual:</p>
        
        <h3>📈 Comparación de Rendimiento</h3>
        <p>Gráfico de barras comparando las métricas principales entre AS-IS y TO-BE:</p>
        <img src="{performance_img}" alt="Comparación de Rendimiento">
        
        <h3>📊 Análisis de Cambios</h3>
        <p>Gráfico horizontal mostrando los cambios porcentuales (verde = mejora, rojo = empeoramiento):</p>
        <img src="{change_img}" alt="Análisis de Cambios">
        
        <h3>🎯 Comparación Multidimensional</h3>
        <p>Gráfico radar mostrando el perfil completo de ambos modelos:</p>
        <img src="{radar_img}" alt="Comparación Multidimensional">
        
        <h2>🎯 Conclusiones</h2>
        <p>Este análisis muestra el impacto de aplicar reglas declarativas específicas en el proceso de negocio.</p>
    </body>
    </html>
    """
    
    # Guardar HTML
    with open(f'{output_dir}/comparison_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Reporte HTML guardado: comparison_report.html")

def main():
    """Función principal"""
    
    # Configuración de rutas (desde comparison_stats)
    base_path = "../data/4.simulation_results/PurchasingExample"
    rules_name = "directly__Send_Request_for_Quotation_to_Supplier__Analyze_Request_for_Quotation"
    comparison_file = f"{base_path}/comparison_stats/{rules_name}_comparison.csv"
    output_dir = f"{base_path}/comparison_stats/visualizations"
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Cargar datos
    df = load_comparison_data(comparison_file)
    if df is None:
        print("❌ Error: No se pudieron cargar los datos de comparación")
        return
    
    print("🎨 Generando visualizaciones...")
    
    # Crear gráficos
    create_performance_chart(df, output_dir)
    create_change_chart(df, output_dir)
    create_radar_chart(df, output_dir)
    create_summary_table(df, output_dir)
    
    print(f"\n✅ Todas las visualizaciones guardadas en: {output_dir}/")
    print("\n📁 Archivos generados:")
    print("  • performance_comparison.png - Gráfico de barras comparativo")
    print("  • change_analysis.png - Análisis de cambios porcentuales")
    print("  • radar_comparison.png - Comparación multidimensional")
    print("  • comparison_report.html - Reporte HTML completo")

if __name__ == "__main__":
    main()
