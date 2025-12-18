#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para ejecutar análisis What-If con reglas declarativas usando el estado parcial.

REQUISITOS CRÍTICOS:
- REQUIERE que compute_state.py haya sido ejecutado previamente para generar el estado parcial
- Sin el estado parcial, este script NO puede funcionar
- La simulación SOLO cubre desde el punto de corte hacia adelante
- La simulación SOLO procesa casos en curso (no genera casos nuevos)

COMPORTAMIENTO:
1. Filtra el estado parcial para mantener SOLO casos en curso (con ongoing_activities, 
   enabled_activities, o tokens en el proceso)
2. Usa el punto de corte como inicio de la simulación
3. Simula SOLO los casos en curso desde el punto de corte hasta el horizonte
4. NO genera casos nuevos (total_cases = número de casos en curso)
"""

import os
import sys
import json
import yaml
import gzip
import shutil
import subprocess
import glob
from pathlib import Path

# Verificar si estamos en un entorno virtual
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(script_dir, "..", "venv", "bin", "python")
    if os.path.exists(venv_python):
        print("⚠️  No se detectó entorno virtual activo.")
        print(f"💡 Ejecuta: source {os.path.dirname(venv_python)}/activate")
        print()

# Agregar paths necesarios
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(script_dir) == "src":
    base_dir = os.path.dirname(script_dir)
else:
    base_dir = script_dir

# Paths a DeclarativeProcessSimulation
# Desde nuevo/ necesitamos subir 2 niveles: nuevo/ -> shorterm/ -> DeclarativeProcessSimulation/
declarative_dir = os.path.join(base_dir, "..", "..")
declarative_dir = os.path.abspath(declarative_dir)

# Verificar que el directorio existe y tiene support_modules
if not os.path.exists(declarative_dir):
    print(f"⚠️  Advertencia: No se encontró DeclarativeProcessSimulation en: {declarative_dir}")
elif not os.path.exists(os.path.join(declarative_dir, "support_modules")):
    print(f"⚠️  Advertencia: No se encontró support_modules en: {declarative_dir}")
    print(f"   Verificando estructura del directorio...")
else:
    # IMPORTANTE: Agregar DeclarativeProcessSimulation al INICIO del path
    # para que tenga prioridad sobre el paquete support_modules instalado desde pip
    # El paquete pip tiene 'readers' pero el local tiene 'predictor_adapter'
    if declarative_dir in sys.path:
        sys.path.remove(declarative_dir)  # Remover si ya está para reinsertarlo al inicio
    sys.path.insert(0, declarative_dir)  # Insertar al inicio para máxima prioridad
    
    # NO agregar GenerativeLSTM al path directamente porque tiene su propio support_modules
    # que entra en conflicto. En su lugar, los imports de GenerativeLSTM funcionarán
    # porque están dentro de DeclarativeProcessSimulation y pueden usar imports relativos
    # desde declarative_dir
    
    # Forzar recarga de módulos si ya fueron importados
    if 'support_modules' in sys.modules:
        # Si support_modules ya fue importado (del paquete pip), forzar recarga desde el path local
        import importlib
        if 'support_modules.predictor_adapter' in sys.modules:
            del sys.modules['support_modules.predictor_adapter']
        if 'support_modules' in sys.modules:
            # No eliminar support_modules completamente porque puede tener 'readers' del paquete pip
            pass

# Paths a ongoing-bps-state-short-term
ongoing_bps_path = "/home/andrew/Documents/asistencia-graduada-phd-oscar/paper1/repos-asis-online-predictivo/whats-coming-next-short-term-simulation-of-business-processes-from-current-state/ongoing-bps-state-short-term"

if not os.path.exists(ongoing_bps_path):
    print(f"❌ No se encontró la carpeta ongoing-bps-state-short-term en: {ongoing_bps_path}")
    sys.exit(1)

if ongoing_bps_path not in sys.path:
    sys.path.insert(0, ongoing_bps_path)

# Importar módulos de DeclarativeProcessSimulation
# IMPORTANTE: Asegurar que support_modules de DeclarativeProcessSimulation esté disponible
# antes de que GenerativeLSTM lo intente importar
try:
    # Primero, importar support_modules.traces_evaluation para que esté en sys.modules
    # Esto asegura que cuando GenerativeLSTM intente importar support_modules,
    # Python use el de DeclarativeProcessSimulation
    from support_modules import traces_evaluation as te
    
    # Ahora importar predictor_adapter (que importará GenerativeLSTM)
    import support_modules.predictor_adapter as pa
    
    # Importar dg_prediction
    from dg_prediction import extract_rules
        
except ImportError as e:
    print(f"❌ Error importando módulos de DeclarativeProcessSimulation: {e}")
    print(f"   DeclarativeProcessSimulation encontrado en: {declarative_dir}")
    generative_lstm_path = os.path.join(declarative_dir, "GenerativeLSTM") if 'declarative_dir' in locals() else 'N/A'
    print(f"   GenerativeLSTM encontrado en: {generative_lstm_path}")
    print(f"\n   Posibles soluciones:")
    print(f"   1. Instala las dependencias: pip install -r {os.path.join(declarative_dir, 'requirements.txt')}")
    print(f"   2. Activa el entorno virtual si existe")
    print(f"   3. Verifica que todos los módulos estén disponibles")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Importar módulos de ongoing-bps-state-short-term
from src.process_state_prosimos_run import run_short_term_simulation, parse_datetime

def load_config(config_path=None):
    """Carga la configuración desde el archivo YAML"""
    if config_path is None:
        if os.path.basename(script_dir) == "src":
            base_dir_config = os.path.dirname(script_dir)
        else:
            base_dir_config = script_dir
        config_path = os.path.join(base_dir_config, "config.yaml")
    
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

def find_state_files(base_dir, log_name, script_config=None):
    """Busca todos los archivos de estado parcial (REQUERIDO)"""
    if script_config:
        state_output_dir = script_config.get("state_output_dir")
        if state_output_dir:
            state_output_dir = os.path.abspath(state_output_dir)
        else:
            state_output_dir = os.path.join(base_dir, "data", "generado-state")
    else:
        state_output_dir = os.path.join(base_dir, "data", "generado-state")
    
    pattern = os.path.join(state_output_dir, f"{log_name}_process_state*.json")
    state_files = sorted(glob.glob(pattern))
    
    if not state_files:
        print(f"❌ ERROR CRÍTICO: No se encontraron archivos de estado parcial")
        print(f"   Buscado en: {state_output_dir}")
        print(f"   Patrón: {pattern}")
        print(f"\n   ⚠️  Este script REQUIERE el estado parcial calculado por compute_state.py")
        print(f"   Ejecuta primero: python src/compute_state.py")
        return []
    
    return state_files

def read_all_rules_from_ini(rules_ini_path):
    """
    Lee todas las reglas (activas y comentadas) del archivo rules.ini.
    Retorna lista de reglas con su información.
    """
    import configparser
    import re
    
    if not os.path.exists(rules_ini_path):
        return []
    
    rules = []
    
    with open(rules_ini_path, 'r') as f:
        lines = f.readlines()
    
    current_variation = None
    current_comment = None
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Ignorar líneas vacías
        if not line_stripped:
            continue
        
        # Capturar comentarios descriptivos (antes de una regla)
        if line_stripped.startswith('#') and not line_stripped.startswith('#path') and not line_stripped.startswith('#-'):
            comment = line_stripped[1:].strip()
            if comment and not comment.startswith('RULES') and not comment.startswith('%'):
                # Solo guardar comentarios que parezcan descriptivos (no muy cortos)
                if len(comment) > 5:
                    current_comment = comment
        
        # Capturar reglas comentadas o activas
        if 'path' in line_stripped.lower() and '=' in line_stripped:
            is_commented = line_stripped.startswith('#')
            path_match = re.search(r'path\s*=\s*(.+)', line_stripped, re.IGNORECASE)
            
            if path_match:
                path_value = path_match.group(1).strip()
                rule_info = {
                    "path": path_value,
                    "commented": is_commented,
                    "line_number": i + 1,
                    "comment": current_comment if current_comment else None,
                    "variation": None  # Se asignará después si se encuentra
                }
                rules.append(rule_info)
                current_comment = None  # Reset después de usar
        
        # Capturar variation (puede estar en la misma sección o después)
        if 'variation' in line_stripped.lower() and '=' in line_stripped and not line_stripped.startswith('#'):
            var_match = re.search(r'variation\s*=\s*(.+)', line_stripped, re.IGNORECASE)
            if var_match:
                current_variation = var_match.group(1).strip()
                # Asignar a la última regla si no tiene variation
                if rules and rules[-1].get("variation") is None:
                    rules[-1]["variation"] = current_variation
    
    return rules

def create_rules_ini_with_rule(rules_ini_path, selected_rule, output_path):
    """
    Crea un archivo rules.ini temporal con la regla seleccionada activa.
    
    Args:
        rules_ini_path: Ruta al archivo rules.ini original
        selected_rule: Diccionario con la regla seleccionada (de read_all_rules_from_ini)
        output_path: Ruta donde guardar el nuevo rules.ini
    """
    import configparser
    
    # Leer el archivo original para obtener variation por defecto
    config = configparser.ConfigParser()
    default_variation = "=1"
    try:
        config.read(rules_ini_path)
        if 'RULES' in config and 'variation' in config['RULES']:
            default_variation = config['RULES']['variation']
    except:
        pass
    
    # Crear nuevo archivo con la regla seleccionada
    with open(output_path, 'w') as f:
        f.write("# RULES SPECIFICATION\n")
        f.write("#- Directly folllows: A >> B\n")
        f.write("#- Eventually folllows: A >> * >> B\n")
        f.write("#- Task required: A\n")
        f.write("#- Task not allowed: ^A\n")
        f.write("\n")
        f.write("[RULES]\n")
        f.write(f"path = {selected_rule['path']}\n")
        
        # Usar variation de la regla seleccionada o el default
        variation = selected_rule.get("variation") or default_variation
        f.write(f"variation = {variation}\n")
    
    return output_path

def select_rules_interactive(rules_ini_path):
    """
    Permite al usuario seleccionar qué reglas aplicar de forma interactiva.
    """
    rules = read_all_rules_from_ini(rules_ini_path)
    
    if not rules:
        print(f"❌ No se encontraron reglas en: {rules_ini_path}")
        return []
    
    # Filtrar solo reglas activas (no comentadas)
    active_rules = [r for r in rules if not r.get("commented", True)]
    
    if not active_rules:
        print(f"⚠️  No hay reglas activas en: {rules_ini_path}")
        print(f"   Mostrando todas las reglas (incluyendo comentadas):\n")
        active_rules = rules
    
    print(f"\n📋 Reglas disponibles en {os.path.basename(rules_ini_path)}:\n")
    for i, rule in enumerate(active_rules, 1):
        status = "✅ ACTIVA" if not rule.get("commented", True) else "❌ COMENTADA"
        comment = f" ({rule['comment']})" if rule.get("comment") else ""
        print(f"  {i}. {status}")
        print(f"     Path: {rule['path']}")
        if rule.get("variation"):
            print(f"     Variation: {rule['variation']}")
        if comment:
            print(f"     {comment}")
        print()
    
    # Permitir seleccionar múltiples reglas
    print("Selecciona qué regla(s) aplicar:")
    print("  - Ingresa números separados por comas (ej: 1,2,3)")
    print("  - Ingresa 'all' para aplicar todas las reglas activas")
    print("  - Ingresa 'q' para cancelar")
    print()
    
    selection = input("Tu selección: ").strip().lower()
    
    if selection == 'q':
        return []
    
    if selection == 'all':
        return active_rules
    
    # Parsear selección
    try:
        indices = [int(x.strip()) - 1 for x in selection.split(',')]
        selected_rules = [active_rules[i] for i in indices if 0 <= i < len(active_rules)]
        return selected_rules
    except (ValueError, IndexError):
        print("❌ Selección inválida")
        return []

def compress_csv_to_gz(csv_path, output_folder):
    """Comprime un CSV a formato .gz"""
    os.makedirs(output_folder, exist_ok=True)
    csv_name = os.path.basename(csv_path)
    gz_path = os.path.join(output_folder, f"{csv_name}.gz")
    
    with open(csv_path, 'rb') as f_in:
        with gzip.open(gz_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return gz_path

def generate_tobe_with_rules(state_file_path, log_path, log_name, base_dir, config, 
                              rules_path, rule_name=None, cut_index=None):
    """
    Genera modelo TO-BE usando reglas declarativas.
    Requiere el estado parcial para saber desde dónde simular.
    """
    print(f"\n{'='*80}")
    print(f"🔮 GENERANDO MODELO TO-BE CON REGLAS DECLARATIVAS")
    print(f"{'='*80}")
    
    # Obtener declarative_dir para cambiar el directorio de trabajo
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == "src":
        base_dir_local = os.path.dirname(script_dir)
    else:
        base_dir_local = script_dir
    declarative_dir_local = os.path.abspath(os.path.join(base_dir_local, "..", ".."))
    
    # Directorios de trabajo
    whatif_output_dir = os.path.join(base_dir, "data", "generado-whatif-declarative")
    if rule_name:
        whatif_output_dir = os.path.join(whatif_output_dir, rule_name)
    if cut_index is not None:
        whatif_output_dir = os.path.join(whatif_output_dir, f"punto-corte-{cut_index}")
    os.makedirs(whatif_output_dir, exist_ok=True)
    
    # Directorios temporales para DeclarativeProcessSimulation
    hallucination_dir = os.path.join(whatif_output_dir, "hallucination_logs")
    input_logs_dir = os.path.join(whatif_output_dir, "input_logs")
    bps_tobe_dir = os.path.join(whatif_output_dir, "bps_tobe")
    os.makedirs(hallucination_dir, exist_ok=True)
    os.makedirs(input_logs_dir, exist_ok=True)
    os.makedirs(bps_tobe_dir, exist_ok=True)
    
    # Verificar que existe rules.ini
    if not os.path.exists(rules_path):
        print(f"❌ Error: No se encontró rules.ini en: {rules_path}")
        return None
    
    print(f"✅ Reglas declarativas encontradas: {rules_path}")
    
    # 1. Comprimir log original para Simod
    log_filename = os.path.basename(log_path)
    compress_csv_to_gz(log_path, input_logs_dir)
    
    # 2. Generar trazas sintéticas con reglas declarativas
    print(f"\n📝 Generando trazas sintéticas con reglas declarativas...")
    
    # Buscar modelo entrenado en DeclarativeProcessSimulation
    prediction_models_dir = os.path.join(declarative_dir_local, "data", "1.predicton_models", log_name)
    if not os.path.exists(prediction_models_dir):
        print(f"❌ Error: No se encontró modelo entrenado en: {prediction_models_dir}")
        print(f"   Ejecuta primero dg_training.py en DeclarativeProcessSimulation")
        return None
    
    # Parámetros para hallucinate
    # IMPORTANTE: one_timestamp debe estar en el nivel superior (no dentro de read_options)
    # porque model_predictor.py lo busca directamente en self.parms['one_timestamp']
    params = {
        'filename': log_filename,
        'activity': 'pred_log',
        'folder': pa.get_latest_output_folder(prediction_models_dir),
        'model_file': f"{log_name}.h5",
        'log_name': log_name,
        'is_single_exec': False,
        'variant': 'Rules Based Random Choice',
        'rep': 1,
        'one_timestamp': False,  # Debe estar en el nivel superior
        'include_org_log': False,  # No incluir el log original en las trazas generadas
        'read_options': {
            # Formato de fecha: usar formato con espacio como en dg_prediction.py
            # El log de entrenamiento tiene formato "2011-06-20 09:33:00" (con espacio, sin microsegundos)
            # Este formato funciona tanto para lectura (LogReader) como para escritura (strftime)
            # Si el log tiene microsegundos, pandas los ignorará con este formato
            'timeformat': '%Y-%m-%d %H:%M:%S',  # Formato con espacio (compatible con LogReader y strftime)
            'column_names': {
                'Case ID': 'caseid',
                'Activity': 'task',
                'lifecycle:transition': 'event_type',
                'Resource': 'user'
            },
            'one_timestamp': False,  # También puede estar aquí, pero el importante es el de arriba
            'filter_d_attrib': False
        }
    }
    
    # IMPORTANTE: ModelPredictor busca 'GenerativeLSTM/models_spec.ini' con ruta relativa
    # Necesitamos cambiar al directorio DeclarativeProcessSimulation antes de llamar a hallucinate
    original_cwd = os.getcwd()
    
    try:
        # Cambiar al directorio DeclarativeProcessSimulation para que las rutas relativas funcionen
        # Esto es necesario porque ModelPredictor.read_model_definition() busca 'GenerativeLSTM/models_spec.ini'
        os.chdir(declarative_dir_local)
        
        # Ajustar rutas para que sean relativas desde declarative_dir o absolutas
        # prediction_models_dir ya es absoluta, pero output_folder y rules_path también deben serlo
        abs_prediction_models_dir = os.path.abspath(prediction_models_dir) if not os.path.isabs(prediction_models_dir) else prediction_models_dir
        abs_hallucination_dir = os.path.abspath(hallucination_dir) if not os.path.isabs(hallucination_dir) else hallucination_dir
        abs_rules_path = os.path.abspath(rules_path) if not os.path.isabs(rules_path) else rules_path
        
        pa.hallucinate(
            parameters=params,
            input_folder=abs_prediction_models_dir,
            output_folder=abs_hallucination_dir,
            rules_path=abs_rules_path
        )
        print(f"✅ Trazas sintéticas generadas en: {hallucination_dir}")
    except Exception as e:
        print(f"❌ Error generando trazas sintéticas: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restaurar directorio original
        os.chdir(original_cwd)
    
    # 3. Comprimir log generado
    generated_log_path = os.path.join(hallucination_dir, log_filename)
    if not os.path.exists(generated_log_path):
        print(f"❌ Error: No se generó el log sintético: {generated_log_path}")
        return None
    
    compress_csv_to_gz(generated_log_path, hallucination_dir)
    
    # 4. Crear configuración para Simod (TO-BE)
    log_config = config.get("log_config", {})
    simod_config = config.get("simod_config", {})
    
    simod_yaml_config = {
        "version": simod_config.get("version", 5),
        "common": {
            "train_log_path": f"./{log_filename}.gz",
            "log_ids": {
                "case": log_config["column_mapping"]["case"],
                "activity": log_config["column_mapping"]["activity"],
                "resource": log_config["column_mapping"]["resource"],
                "start_time": log_config["column_mapping"]["start_time"],
                "end_time": log_config["column_mapping"]["end_time"]
            },
            "discover_data_attributes": simod_config.get("common", {}).get("discover_data_attributes", True)
        },
        "preprocessing": simod_config.get("preprocessing", {}),
        "control_flow": simod_config.get("control_flow", {}),
        "resource_model": simod_config.get("resource_model", {}),
        "extraneous_activity_delays": simod_config.get("extraneous_activity_delays", {})
    }
    
    config_path = os.path.join(hallucination_dir, "configuration_generated.yaml")
    with open(config_path, 'w') as f:
        yaml.dump(simod_yaml_config, f, default_flow_style=False, sort_keys=False)
    
    # 5. Descubrir modelo TO-BE con Simod
    print(f"\n🔍 Descubriendo modelo TO-BE con Simod...")
    
    temp_input_dir = os.path.join(hallucination_dir, ".simod_temp_input")
    temp_output_dir = os.path.join(hallucination_dir, ".simod_temp_output")
    os.makedirs(temp_input_dir, exist_ok=True)
    os.makedirs(temp_output_dir, exist_ok=True)
    
    # Copiar archivos necesarios a temp_input
    shutil.copy(os.path.join(hallucination_dir, f"{log_filename}.gz"), 
                os.path.join(temp_input_dir, f"{log_filename}.gz"))
    shutil.copy(config_path, os.path.join(temp_input_dir, "configuration_generated.yaml"))
    
    docker_config = config.get("script_config", {}).get("docker", {})
    user_id = docker_config.get("user_id") or os.getuid()
    group_id = docker_config.get("group_id") or os.getgid()
    docker_image = docker_config.get("image", "nokal/simod")
    
    docker_command = [
        "docker", "run", "--rm",
        "--user", f"{user_id}:{group_id}",
        "-v", f"{temp_input_dir}:/usr/src/Simod/resources",
        "-v", f"{temp_output_dir}:/usr/src/Simod/outputs",
        docker_image,
        "poetry", "run", "simod",
        "--configuration", "/usr/src/Simod/resources/configuration_generated.yaml"
    ]
    
    result = subprocess.run(docker_command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error ejecutando Simod para TO-BE: {result.stderr}")
        return None
    
    # 6. Copiar resultados TO-BE
    latest_subdir = pa.get_latest_output_folder(temp_output_dir)
    best_result_dir = os.path.join(temp_output_dir, latest_subdir, "best_result")
    
    tobe_bpmn_path = os.path.join(best_result_dir, f"{log_name}.bpmn")
    tobe_json_path = os.path.join(best_result_dir, f"{log_name}.json")
    
    if not os.path.exists(tobe_bpmn_path) or not os.path.exists(tobe_json_path):
        print(f"❌ Error: No se encontraron archivos TO-BE en: {best_result_dir}")
        return None
    
    # Copiar a bps_tobe_dir
    final_tobe_dir = os.path.join(bps_tobe_dir, latest_subdir, "best_result")
    os.makedirs(final_tobe_dir, exist_ok=True)
    shutil.copy(tobe_bpmn_path, os.path.join(final_tobe_dir, f"{log_name}.bpmn"))
    shutil.copy(tobe_json_path, os.path.join(final_tobe_dir, f"{log_name}.json"))
    
    print(f"✅ Modelo TO-BE generado en: {final_tobe_dir}")
    
    # 7. Fusionar recursos AS-IS → TO-BE
    print(f"\n🔗 Fusionando recursos AS-IS → TO-BE...")
    
    # Obtener modelo AS-IS
    simod_output_dir = os.path.join(base_dir, "data", "generado-simod")
    asis_bpmn_path = os.path.join(simod_output_dir, f"{log_name}.bpmn")
    asis_json_path = os.path.join(simod_output_dir, f"{log_name}.json")
    
    if not os.path.exists(asis_bpmn_path) or not os.path.exists(asis_json_path):
        print(f"❌ Error: No se encontraron archivos AS-IS en: {simod_output_dir}")
        print(f"   Ejecuta primero: python src/extract_bpmn_json.py")
        return None
    
    merged_json_path = os.path.join(final_tobe_dir, f"{log_name}_merged.json")
    
    try:
        pa.adapt_json(
            asis_bpmn_path=asis_bpmn_path,
            asis_json_path=asis_json_path,
            tobe_bpmn_path=os.path.join(final_tobe_dir, f"{log_name}.bpmn"),
            tobe_json_path=os.path.join(final_tobe_dir, f"{log_name}.json"),
            merged_json_path=merged_json_path
        )
        print(f"✅ Recursos fusionados: {merged_json_path}")
    except Exception as e:
        print(f"❌ Error fusionando recursos: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Limpiar temporales
    if os.path.exists(temp_input_dir):
        shutil.rmtree(temp_input_dir)
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir)
    
    return {
        "tobe_bpmn": os.path.join(final_tobe_dir, f"{log_name}.bpmn"),
        "tobe_json": merged_json_path,
        "state_file": state_file_path
    }

def filter_ongoing_cases_only(partial_state):
    """
    Filtra el estado parcial para mantener SOLO los casos en curso.
    Un caso está en curso si tiene:
    - ongoing_activities (actividades en ejecución), O
    - enabled_activities (actividades habilitadas), O
    - control_flow_state con flows o activities (tokens en el proceso)
    
    Args:
        partial_state: Estado parcial completo
        
    Returns:
        dict: Estado parcial filtrado con solo casos en curso
    """
    if not partial_state or "cases" not in partial_state:
        return partial_state
    
    filtered_cases = {}
    ongoing_count = 0
    
    for case_id, case_data in partial_state.get("cases", {}).items():
        # Verificar si el caso está realmente en curso
        has_ongoing = len(case_data.get("ongoing_activities", [])) > 0
        has_enabled = len(case_data.get("enabled_activities", [])) > 0
        has_flows = len(case_data.get("control_flow_state", {}).get("flows", [])) > 0
        has_activities = len(case_data.get("control_flow_state", {}).get("activities", [])) > 0
        
        # Un caso está en curso si tiene alguna de estas condiciones
        is_ongoing = has_ongoing or has_enabled or has_flows or has_activities
        
        if is_ongoing:
            filtered_cases[case_id] = case_data
            ongoing_count += 1
    
    # Crear nuevo estado parcial solo con casos en curso
    filtered_state = {
        "cases": filtered_cases
    }
    
    # Preservar otros campos importantes si existen
    if "last_case_arrival" in partial_state:
        filtered_state["last_case_arrival"] = partial_state["last_case_arrival"]
    if "resource_last_end_times" in partial_state:
        filtered_state["resource_last_end_times"] = partial_state["resource_last_end_times"]
    
    return filtered_state, ongoing_count

def extract_cut_point_from_state(state_file_path, partial_state):
    """
    Extrae el punto de corte (timestamp) del estado parcial.
    Intenta obtenerlo de:
    1. last_case_arrival en el estado parcial
    2. El timestamp más reciente de las actividades en curso
    3. El nombre del archivo (si contiene timestamp)
    
    Returns:
        datetime.datetime: Punto de corte o None si no se puede determinar
    """
    import datetime
    import re
    
    # 1. Intentar desde last_case_arrival
    if "last_case_arrival" in partial_state:
        try:
            cut_point = parse_datetime(partial_state["last_case_arrival"])
            print(f"✅ Punto de corte extraído de last_case_arrival: {cut_point.isoformat()}")
            return cut_point
        except:
            pass
    
    # 2. Intentar desde el timestamp más reciente de actividades en curso
    max_time = None
    for case_data in partial_state.get("cases", {}).values():
        # Revisar ongoing_activities
        for act in case_data.get("ongoing_activities", []):
            if "start_time" in act:
                try:
                    act_time = parse_datetime(act["start_time"]) if isinstance(act["start_time"], str) else act["start_time"]
                    if max_time is None or act_time > max_time:
                        max_time = act_time
                except:
                    pass
        # Revisar enabled_activities
        for act in case_data.get("enabled_activities", []):
            if "enabled_time" in act:
                try:
                    act_time = parse_datetime(act["enabled_time"]) if isinstance(act["enabled_time"], str) else act["enabled_time"]
                    if max_time is None or act_time > max_time:
                        max_time = act_time
                except:
                    pass
    
    if max_time:
        print(f"✅ Punto de corte extraído de actividades: {max_time.isoformat()}")
        return max_time
    
    # 3. Intentar desde el nombre del archivo (formato: *_process_state_YYYYMMDD_HHMMSS.json)
    filename = os.path.basename(state_file_path)
    match = re.search(r'_process_state_(\d{8})_(\d{6})', filename)
    if match:
        try:
            date_str = f"{match.group(1)}_{match.group(2)}"
            cut_point = datetime.datetime.strptime(date_str, "%Y%m%d_%H%M%S")
            cut_point = cut_point.replace(tzinfo=datetime.timezone.utc)
            print(f"✅ Punto de corte extraído del nombre del archivo: {cut_point.isoformat()}")
            return cut_point
        except:
            pass
    
    return None

def load_bpmn_elements(bpmn_path):
    """
    Carga un archivo BPMN y extrae:
    - activity_id_to_name: {id: nombre}
    - flow_id_to_pair: {id: (source_id, target_id)}
    - name_to_activity_id: {nombre: id} (asumiendo nombres únicos para tareas)
    - pair_to_flow_id: {(source_id, target_id): id}
    """
    import xml.etree.ElementTree as ET
    
    tree = ET.parse(bpmn_path)
    root = tree.getroot()
    
    # Namespaces
    ns = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'definitions': 'http://www.omg.org/spec/BPMN/20100524/MODEL'
    }
    
    # Encontrar proceso
    process = root.find('.//bpmn:process', ns)
    if process is None:
        # Intentar sin namespace si falla
        process = root.find('.//process')
        if process is None:
            return {}, {}, {}, {}
            
    activity_id_to_name = {}
    name_to_activity_id = {}
    flow_id_to_pair = {} # {flow_id: (source_ref, target_ref)}
    
    # Extraer tareas
    for task in process.findall('.//bpmn:task', ns) + process.findall('.//task'):
        tid = task.get('id')
        name = task.get('name')
        if tid and name:
            activity_id_to_name[tid] = name
            name_to_activity_id[name] = tid
            
    # Extraer eventos (startEvent, endEvent, intermediateCatchEvent, etc)
    # Los eventos a veces no tienen nombre, o tienen nombres genericos.
    # Para simplificar, nos centramos en tareas que son las que suelen estar en ongoing_activities.
    # Pero los flujos conectan eventos tambien.
    for event_tag in ['startEvent', 'endEvent', 'intermediateCatchEvent', 'intermediateThrowEvent']:
        for event in process.findall(f'.//bpmn:{event_tag}', ns) + process.findall(f'.//{event_tag}'):
            tid = event.get('id')
            name = event.get('name')
            if tid:
                activity_id_to_name[tid] = name or tid # Usar ID si no hay nombre
                if name:
                    name_to_activity_id[name] = tid
    
    # Extraer flujos
    for flow in process.findall('.//bpmn:sequenceFlow', ns) + process.findall('.//sequenceFlow'):
        fid = flow.get('id')
        source = flow.get('sourceRef')
        target = flow.get('targetRef')
        if fid and source and target:
            flow_id_to_pair[fid] = (source, target)
            
    return activity_id_to_name, flow_id_to_pair, name_to_activity_id

def map_partial_state_to_tobe(partial_state, asis_bpmn_path, tobe_bpmn_path):
    """
    Transforma el estado parcial del modelo AS-IS al modelo TO-BE.
    Mapea IDs de actividades por nombre y flujos por pares (origen, destino).
    """
    print(f"🔄 Mapeando estado parcial de AS-IS a TO-BE...")
    
    # Cargar elementos de ambos modelos
    asis_act_map, asis_flow_map, _, = load_bpmn_elements(asis_bpmn_path)
    _, tobe_flow_map, tobe_name_map = load_bpmn_elements(tobe_bpmn_path)
    
    # Crear mapa inverso de flujos TO-BE: {(source_name, target_name): flow_id}
    # Necesitamos resolver los nombres de las referencias en TO-BE
    tobe_act_map, _, _ = load_bpmn_elements(tobe_bpmn_path)
    tobe_pair_names_to_id = {}
    
    for fid, (src_ref, tgt_ref) in tobe_flow_map.items():
        src_name = tobe_act_map.get(src_ref)
        tgt_name = tobe_act_map.get(tgt_ref)
        if src_name and tgt_name:
            tobe_pair_names_to_id[(src_name, tgt_name)] = fid
            
    new_state = {"cases": {}}
    
    # Copiar metadatos globales
    for k, v in partial_state.items():
        if k != "cases":
            new_state[k] = v
            
    mapped_cases_count = 0
    
    for case_id, case_data in partial_state.get("cases", {}).items():
        new_case_data = {"case_id": case_id}
        # Copiar datos que no dependen del modelo
        for k, v in case_data.items():
            if k not in ["ongoing_activities", "enabled_activities", "control_flow_state"]:
                new_case_data[k] = v
                
        # Mapear ongoing_activities
        new_ongoing = []
        for act in case_data.get("ongoing_activities", []):
            asis_id = act.get("id") # Este es el ID de la actividad en el modelo, o es el nombre?
            # En prosimos process_state, ongoing_activities es una lista de dicts.
            # Depende de como se guardo. Normalmente tiene 'element_id' o similar.
            # Asumimos que el process_state generado por compute_state.py sigue el formato de Prosimos.
            # Si compute_state usa ongoing-bps-state, el formato puede variar.
            # Revisando process_state_prosimos_run.py parece que load_process_state no cambia estructura.
            
            # En output.json de ongoing-bps-state:
            # "ongoing_activities": [{"element_id": "Activity_...", "start_time": ...}]
            
            elem_id = act.get("element_id")
            if elem_id:
                name = asis_act_map.get(elem_id)
                if name and name in tobe_name_map:
                    new_act = act.copy()
                    new_act["element_id"] = tobe_name_map[name]
                    new_ongoing.append(new_act)
                else:
                    print(f"⚠️ No se pudo mapear actividad en curso: {elem_id} ({name})")
            else:
                # Si no tiene element_id, quizas es por nombre directo?
                new_ongoing.append(act)
                
        new_case_data["ongoing_activities"] = new_ongoing
        
        # Mapear enabled_activities (similar a ongoing)
        new_enabled = []
        for act in case_data.get("enabled_activities", []):
            elem_id = act.get("element_id")
            if elem_id:
                name = asis_act_map.get(elem_id)
                if name and name in tobe_name_map:
                    new_act = act.copy()
                    new_act["element_id"] = tobe_name_map[name]
                    new_enabled.append(new_act)
                else:
                    print(f"⚠️ No se pudo mapear actividad habilitada: {elem_id} ({name})")
            else:
                new_enabled.append(act)
        new_case_data["enabled_activities"] = new_enabled
        
        # Mapear control_flow_state (tokens)
        # "control_flow_state": {"flows": ["Flow_1", ...], "activities": ["Activity_1", ...]}
        new_cfs = {"flows": [], "activities": []}
        old_cfs = case_data.get("control_flow_state", {})
        
        # Mapear tokens en actividades
        for act_id in old_cfs.get("activities", []):
            name = asis_act_map.get(act_id)
            if name and name in tobe_name_map:
                new_cfs["activities"].append(tobe_name_map[name])
            else:
                print(f"⚠️ Token en actividad no mapeable: {act_id} ({name})")
                
        # Mapear tokens en flujos (Lo más crítico para el error ValueError)
        for flow_id in old_cfs.get("flows", []):
            pair = asis_flow_map.get(flow_id) # (source_id, target_id)
            if pair:
                src_id, tgt_id = pair
                src_name = asis_act_map.get(src_id)
                tgt_name = asis_act_map.get(tgt_id)
                
                if src_name and tgt_name:
                    # Buscar flujo equivalente en TO-BE
                    new_flow_id = tobe_pair_names_to_id.get((src_name, tgt_name))
                    if new_flow_id:
                        new_cfs["flows"].append(new_flow_id)
                    else:
                        # Si el flujo directo no existe, intentar heurística:
                        # Mover el token a la actividad de destino (asumir que llegó)
                        # Esto es arriesgado pero evita el crash.
                        print(f"⚠️ Flujo {src_name}->{tgt_name} no existe en TO-BE. Moviendo token a {tgt_name}.")
                        if tgt_name in tobe_name_map:
                            new_cfs["activities"].append(tobe_name_map[tgt_name])
                else:
                    print(f"⚠️ No se pudieron resolver nombres para flujo {flow_id}")
            else:
                print(f"⚠️ Flujo {flow_id} no encontrado en mapa AS-IS")
                
        new_case_data["control_flow_state"] = new_cfs
        new_state["cases"][case_id] = new_case_data
        mapped_cases_count += 1
        
    print(f"✅ Estado mapeado para {mapped_cases_count} casos")
    return new_state

def simulate_tobe_from_state(state_file_path, tobe_bpmn, tobe_json, log_name, 
                              base_dir, config, rule_name=None, cut_index=None, asis_bpmn_path=None):
    """
    Simula modelo TO-BE desde el estado parcial.
    
    REGLAS CRÍTICAS:
    1. La simulación SOLO ocurre desde el punto de corte hacia adelante
    2. La simulación SOLO procesa casos en curso (no genera casos nuevos)
    3. El estado parcial es OBLIGATORIO y define el punto de inicio de la simulación
    4. Solo se simulan casos que tienen actividades en curso, habilitadas, o tokens en el proceso
    """
    print(f"\n{'='*80}")
    print(f"🎯 SIMULANDO TO-BE DESDE ESTADO PARCIAL")
    print(f"{'='*80}")
    print(f"⚠️  La simulación SOLO cubre desde el punto de corte hacia adelante")
    print(f"{'='*80}")
    
    # VALIDACIÓN CRÍTICA: El estado parcial es obligatorio
    if not os.path.exists(state_file_path):
        print(f"❌ ERROR CRÍTICO: No se encontró el archivo de estado parcial: {state_file_path}")
        print(f"   El what-if REQUIERE el estado parcial para funcionar")
        return {"success": False, "error": "Estado parcial no encontrado"}
    
    # Cargar estado parcial
    try:
        with open(state_file_path, 'r') as f:
            partial_state = json.load(f)
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: No se pudo cargar el estado parcial: {e}")
        print(f"   El what-if REQUIERE el estado parcial para funcionar")
        return {"success": False, "error": f"Error cargando estado parcial: {e}"}
        
    # MAPEO DE ESTADO (AS-IS -> TO-BE)
    # Esto es crucial para evitar errores "Flow ID not found"
    if asis_bpmn_path and os.path.exists(asis_bpmn_path):
        try:
            partial_state = map_partial_state_to_tobe(partial_state, asis_bpmn_path, tobe_bpmn)
        except Exception as e:
            print(f"⚠️ Error al mapear estado AS-IS -> TO-BE: {e}")
            print("   Se intentará usar el estado original (puede fallar)")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️ No se proporcionó modelo AS-IS para mapeo de estado. Pueden ocurrir errores de IDs.")
    
    # Validar que el estado parcial tiene contenido
    if not partial_state or "cases" not in partial_state:
        print(f"❌ ERROR CRÍTICO: El estado parcial está vacío o es inválido")
        print(f"   El what-if REQUIERE un estado parcial válido para funcionar")
        return {"success": False, "error": "Estado parcial inválido"}
    
    # FILTRAR: Mantener SOLO casos en curso (what-if solo simula casos en curso)
    print(f"\n🔍 Filtrando casos en curso del estado parcial...")
    filtered_state, ongoing_count = filter_ongoing_cases_only(partial_state)
    
    if ongoing_count == 0:
        print(f"❌ ERROR CRÍTICO: No se encontraron casos en curso en el estado parcial")
        print(f"   El what-if SOLO puede simular casos que están en progreso")
        print(f"   Verifica que el punto de corte tenga casos activos")
        return {"success": False, "error": "No hay casos en curso"}
    
    total_cases_in_state = len(partial_state.get("cases", {}))
    print(f"✅ Casos en curso identificados: {ongoing_count}/{total_cases_in_state}")
    print(f"   La simulación what-if SOLO procesará estos {ongoing_count} casos en curso")
    
    # Usar el estado filtrado para la simulación
    partial_state = filtered_state
    
    # Extraer punto de corte del estado parcial
    cut_point_dt = extract_cut_point_from_state(state_file_path, partial_state)
    
    if cut_point_dt is None:
        print(f"❌ ERROR CRÍTICO: No se pudo determinar el punto de corte del estado parcial")
        print(f"   El what-if REQUIERE conocer el punto de corte para simular solo hacia adelante")
        return {"success": False, "error": "No se pudo determinar punto de corte"}
    
    print(f"📅 Punto de corte identificado: {cut_point_dt.isoformat()}")
    print(f"   La simulación comenzará desde este punto y solo hacia adelante")
    
    # Directorio de salida
    script_config = config.get("script_config", {})
    output_dir = script_config.get("simulation_output_dir")
    if output_dir is None:
        output_dir = os.path.join(base_dir, "data", "generado-short-term-simulation")
    else:
        output_dir = os.path.abspath(output_dir)
    
    # Organizar por regla y punto de corte
    if rule_name:
        output_dir = os.path.join(output_dir, f"whatif-{rule_name}")
    if cut_index is not None:
        cut_folder = os.path.join(output_dir, f"punto-corte-{cut_index}")
        os.makedirs(cut_folder, exist_ok=True)
        output_dir = cut_folder
    
    # Calcular horizonte de simulación DESDE EL PUNTO DE CORTE (no desde "ahora")
    ongoing_config = config.get("ongoing_config", {})
    horizon_days = ongoing_config.get("horizon_days", 7)
    simulation_horizon = ongoing_config.get("simulation_horizon")
    
    if not simulation_horizon:
        import datetime
        # IMPORTANTE: El horizonte se calcula desde el punto de corte, no desde "ahora"
        horizon = cut_point_dt + datetime.timedelta(days=horizon_days)
        simulation_horizon = horizon.isoformat()
        print(f"📅 Horizonte calculado desde punto de corte: {horizon_days} días hacia adelante")
    else:
        # Si se especifica un horizonte absoluto, validar que sea después del punto de corte
        horizon_dt = parse_datetime(simulation_horizon)
        if horizon_dt <= cut_point_dt:
            print(f"⚠️  ADVERTENCIA: El horizonte especificado ({horizon_dt.isoformat()})")
            print(f"   es anterior o igual al punto de corte ({cut_point_dt.isoformat()})")
            print(f"   Se ajustará el horizonte a {horizon_days} días desde el punto de corte")
            import datetime
            horizon_dt = cut_point_dt + datetime.timedelta(days=horizon_days)
            simulation_horizon = horizon_dt.isoformat()
    
    print(f"📅 Horizonte de simulación: {simulation_horizon}")
    print(f"   Simulación desde: {cut_point_dt.isoformat()}")
    print(f"   Simulación hasta: {simulation_horizon}")
    
    # Rutas de salida
    sim_stats_csv = os.path.join(output_dir, f"{log_name}_tobe_simulation_stats.csv")
    sim_log_csv = os.path.join(output_dir, f"{log_name}_tobe_simulation_log.csv")
    
    original_cwd = os.getcwd()
    os.chdir(output_dir)
    
    try:
        # Convertir horizonte a datetime
        horizon_dt = parse_datetime(simulation_horizon)
        
        # VALIDACIÓN FINAL: Asegurar que el estado parcial se está usando
        if not partial_state:
            raise ValueError("El estado parcial no puede estar vacío")
        
        # Ejecutar simulación TO-BE desde estado parcial
        # IMPORTANTE: 
        # - start_date debe ser el punto de corte para que la simulación comience desde ese momento
        # - total_cases debe ser igual al número de casos en curso (no generar casos nuevos)
        # - process_state contiene SOLO los casos en curso
        print(f"\n🚀 Iniciando simulación TO-BE desde punto de corte...")
        print(f"   Casos a simular: {ongoing_count} (solo casos en curso, sin casos nuevos)")
        
        # IMPORTANTE: total_cases debe ser igual al número de casos en curso
        # Esto asegura que NO se generen casos nuevos, solo se simulen los casos en curso
        total_cases_to_simulate = ongoing_count
        
        # Convertir fecha de corte a string ISO para evitar error en prosimos
        # parse_datetime en prosimos espera string, si recibe datetime falla con TypeError
        start_date_str = cut_point_dt.isoformat()
        
        sim_time = run_short_term_simulation(
            start_date=start_date_str,  # USAR EL PUNTO DE CORTE COMO INICIO (String ISO)
            total_cases=total_cases_to_simulate,  # SOLO casos en curso, NO generar casos nuevos
            bpmn_model=tobe_bpmn,
            json_sim_params=tobe_json,
            out_stats_csv_path=sim_stats_csv,
            out_log_csv_path=sim_log_csv,
            process_state=partial_state,  # ESTADO PARCIAL CON SOLO CASOS EN CURSO
            simulation_horizon=horizon_dt
        )
        
        print(f"✅ Simulación TO-BE completada en {sim_time:.2f} segundos")
        print(f"📁 Resultados guardados en: {output_dir}")
        
        return {
            "success": True,
            "sim_time": sim_time,
            "stats_csv": sim_stats_csv,
            "log_csv": sim_log_csv
        }
        
    except Exception as e:
        print(f"❌ Error en simulación TO-BE: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        os.chdir(original_cwd)

def run_whatif_declarative(config=None, state_file_path=None, rules_path=None, cut_index=None):
    """
    Ejecuta análisis What-If con reglas declarativas usando el estado parcial.
    
    Args:
        config: Diccionario de configuración
        state_file_path: Ruta al archivo de estado parcial (si None, busca todos)
        rules_path: Ruta al archivo rules.ini
        cut_index: Índice del punto de corte (para organizar resultados)
    
    Returns:
        bool: True si fue exitoso, False en caso contrario
    """
    print("=" * 80)
    print("🔮 WHAT-IF CON REGLAS DECLARATIVAS")
    print("=" * 80)
    print("\n⚠️  REQUIERE estado parcial calculado por compute_state.py")
    print("⚠️  La simulación SOLO cubre desde el punto de corte hacia adelante")
    print("⚠️  La simulación SOLO procesa casos en curso (no genera casos nuevos)")
    print("⚠️  Sin estado parcial, este script NO puede funcionar")
    print("=" * 80)
    
    # Cargar configuración
    if config is None:
        config = load_config()
        if config is None:
            return False
    
    log_config = config.get("log_config", {})
    ongoing_config = config.get("ongoing_config", {})
    script_config = config.get("script_config", {})
    whatif_config = config.get("whatif_config", {})
    
    # Obtener rutas
    if os.path.basename(script_dir) == "src":
        base_dir_local = os.path.dirname(script_dir)
    else:
        base_dir_local = script_dir
    
    # Obtener ruta del log
    log_path = log_config.get("log_path")
    if not log_path:
        print("❌ Error: No se especificó log_path en config.yaml")
        return False
    
    if not os.path.isabs(log_path):
        log_path = os.path.join(base_dir_local, log_path)
    
    log_name = get_log_name_from_path(log_path)
    
    # Buscar archivo(s) de estado parcial (REQUERIDO - SIN ESTO NO FUNCIONA)
    if state_file_path is None:
        state_files = find_state_files(base_dir_local, log_name, script_config)
        if not state_files:
            print(f"\n❌ ERROR CRÍTICO: No se encontraron archivos de estado parcial")
            print(f"   El what-if SOLO puede funcionar con estado parcial")
            print(f"   Ejecuta primero: python src/compute_state.py")
            return False
    else:
        if isinstance(state_file_path, str):
            state_files = [state_file_path]
        elif isinstance(state_file_path, list):
            state_files = state_file_path
        else:
            state_files = []
    
    # Obtener ruta de rules.ini
    if rules_path is None:
        rules_path = whatif_config.get("rules_path")
        if rules_path:
            # Si se especificó una ruta, resolverla (puede ser relativa o absoluta)
            if not os.path.isabs(rules_path):
                # Ruta relativa: resolver desde base_dir_local
                rules_path = os.path.join(base_dir_local, rules_path)
        else:
            # Buscar en ubicaciones comunes
            possible_paths = [
                os.path.join(base_dir_local, "data", "rules.ini"),  # data/rules.ini en nuevo/
                os.path.join(base_dir_local, "data", f"{log_name}", "rules.ini"),
                os.path.join(declarative_dir, "data", "0.logs", log_name, "rules.ini"),
                os.path.join(declarative_dir, "GenerativeLSTM", "rules.ini"),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    rules_path = path
                    break
    
    if not rules_path or not os.path.exists(rules_path):
        print(f"❌ Error: No se encontró rules.ini")
        print(f"   Buscado en:")
        possible_paths = [
            os.path.join(base_dir_local, "data", "rules.ini"),  # data/rules.ini en nuevo/
            os.path.join(base_dir_local, "data", f"{log_name}", "rules.ini"),
            os.path.join(declarative_dir, "data", "0.logs", log_name, "rules.ini"),
            os.path.join(declarative_dir, "GenerativeLSTM", "rules.ini"),
        ]
        for path in possible_paths:
            print(f"     - {path}")
        print(f"   Especifica 'whatif_config.rules_path' en config.yaml")
        print(f"   Ejemplo: rules_path: data/rules.ini")
        return False
    
    print(f"✅ Archivo de reglas encontrado: {rules_path}")
    
    # Leer todas las reglas disponibles
    all_rules = read_all_rules_from_ini(rules_path)
    
    if not all_rules:
        print(f"❌ No se encontraron reglas en: {rules_path}")
        return False
    
    # Seleccionar reglas a aplicar
    selected_rules = whatif_config.get("selected_rules")
    
    if selected_rules is None:
        # Modo interactivo: preguntar al usuario
        print(f"\n📋 Seleccionando reglas declarativas a aplicar...")
        selected_rules_list = select_rules_interactive(rules_path)
    elif isinstance(selected_rules, list):
        # Lista de índices desde config
        active_rules = [r for r in all_rules if not r.get("commented", True)]
        try:
            selected_rules_list = [active_rules[i-1] for i in selected_rules if 1 <= i <= len(active_rules)]
        except (IndexError, TypeError):
            print(f"⚠️  Índices inválidos en whatif_config.selected_rules, usando modo interactivo")
            selected_rules_list = select_rules_interactive(rules_path)
    elif isinstance(selected_rules, int):
        # Un solo índice
        active_rules = [r for r in all_rules if not r.get("commented", True)]
        if 1 <= selected_rules <= len(active_rules):
            selected_rules_list = [active_rules[selected_rules - 1]]
        else:
            print(f"⚠️  Índice inválido, usando modo interactivo")
            selected_rules_list = select_rules_interactive(rules_path)
    else:
        selected_rules_list = select_rules_interactive(rules_path)
    
    if not selected_rules_list:
        print("❌ No se seleccionaron reglas")
        return False
    
    print(f"\n✅ Reglas seleccionadas: {len(selected_rules_list)}")
    for i, rule in enumerate(selected_rules_list, 1):
        print(f"   {i}. {rule['path']} (variation: {rule.get('variation', '=1')})")
    
    # Procesar cada regla y cada estado parcial
    all_results = []
    
    for rule_idx, selected_rule in enumerate(selected_rules_list, 1):
        # Crear nombre de regla para organizar resultados
        rule_name = f"rule_{rule_idx}"
        rule_path_clean = selected_rule['path'].replace('>>', '_').replace('*', 'eventually').replace('^', 'not_').replace(' ', '_')
        rule_name = rule_path_clean[:50]  # Limitar longitud
        
        print(f"\n{'='*80}")
        print(f"🔮 REGLA {rule_idx}/{len(selected_rules_list)}: {selected_rule['path']}")
        print(f"{'='*80}")
        
        # Crear rules.ini temporal con esta regla
        temp_rules_dir = os.path.join(base_dir_local, "data", ".temp_rules")
        os.makedirs(temp_rules_dir, exist_ok=True)
        temp_rules_path = os.path.join(temp_rules_dir, f"rules_{rule_name}.ini")
        create_rules_ini_with_rule(rules_path, selected_rule, temp_rules_path)
        
        # Procesar cada estado parcial con esta regla
        for state_idx, state_file in enumerate(state_files, 1):
            current_cut_index = cut_index if cut_index is not None else state_idx
            
            print(f"\n{'='*80}")
            print(f"📅 Punto de corte {current_cut_index}/{len(state_files)}: {os.path.basename(state_file)}")
            print(f"{'='*80}")
            
            # 1. Generar modelo TO-BE con esta regla
            tobe_result = generate_tobe_with_rules(
                state_file_path=state_file,
                log_path=log_path,
                log_name=log_name,
                base_dir=base_dir_local,
                config=config,
                rules_path=temp_rules_path,
                rule_name=rule_name,
                cut_index=current_cut_index
            )
            
            if not tobe_result:
                print(f"❌ Error generando modelo TO-BE para regla {rule_idx}, punto de corte {current_cut_index}")
                all_results.append({
                    "success": False,
                    "rule": rule_name,
                    "rule_path": selected_rule['path'],
                    "cut_index": current_cut_index
                })
                continue
            
            # 2. Simular TO-BE desde estado parcial
            # Calcular ruta del AS-IS para el mapeo
            simod_output_dir = os.path.join(base_dir_local, "data", "generado-simod")
            asis_bpmn_path = os.path.join(simod_output_dir, f"{log_name}.bpmn")
            
            sim_result = simulate_tobe_from_state(
                state_file_path=state_file,
                tobe_bpmn=tobe_result["tobe_bpmn"],
                tobe_json=tobe_result["tobe_json"],
                log_name=log_name,
                base_dir=base_dir_local,
                config=config,
                rule_name=rule_name,
                cut_index=current_cut_index,
                asis_bpmn_path=asis_bpmn_path
            )
            
            if sim_result and sim_result.get("success"):
                all_results.append({
                    "success": True,
                    "rule": rule_name,
                    "rule_path": selected_rule['path'],
                    "cut_index": current_cut_index,
                    "tobe_result": tobe_result,
                    "sim_result": sim_result
                })
            else:
                all_results.append({
                    "success": False,
                    "rule": rule_name,
                    "rule_path": selected_rule['path'],
                    "cut_index": current_cut_index
                })
        
        # Limpiar archivo temporal
        if os.path.exists(temp_rules_path):
            os.remove(temp_rules_path)
    
    # Resumen final
    successful = sum(1 for r in all_results if r.get("success"))
    total_combinations = len(selected_rules_list) * len(state_files)
    
    print(f"\n{'='*80}")
    print(f"✅ Proceso completado: {successful}/{total_combinations} análisis what-if exitosos")
    print(f"{'='*80}")
    print(f"\n📊 Resumen por regla:")
    for rule in selected_rules_list:
        rule_results = [r for r in all_results if r.get("rule_path") == rule['path']]
        rule_success = sum(1 for r in rule_results if r.get("success"))
        print(f"   • {rule['path']}: {rule_success}/{len(rule_results)} exitosos")
    
    return successful == total_combinations

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="What-If con reglas declarativas usando estado parcial")
    parser.add_argument("--state-file", help="Ruta específica al archivo de estado parcial")
    parser.add_argument("--rules-path", help="Ruta al archivo rules.ini")
    parser.add_argument("--cut-index", type=int, help="Índice del punto de corte")
    
    args = parser.parse_args()
    
    if run_whatif_declarative(
        state_file_path=args.state_file,
        rules_path=args.rules_path,
        cut_index=args.cut_index
    ):
        print("\n🎉 ¡Análisis What-If completado exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ El análisis What-If falló")
        sys.exit(1)

if __name__ == "__main__":
    main()

