#!/usr/bin/env python3
"""
API Service para generar archivos FIT de Garmin
Desplegado en Render.com
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar el wrapper de Java
from fit_java_wrapper import FitJavaWrapper

app = Flask(__name__)
CORS(app)  # Permitir CORS para llamadas desde WordPress

# Inicializar el wrapper de Java
try:
    fit_wrapper = FitJavaWrapper()
    logger.info("FitJavaWrapper inicializado correctamente")
except Exception as e:
    logger.error(f"Error inicializando FitJavaWrapper: {e}")
    fit_wrapper = None

@app.route('/', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud"""
    return jsonify({
        'status': 'ok',
        'message': 'API de generación FIT funcionando',
        'timestamp': datetime.now().isoformat(),
        'fit_wrapper_loaded': fit_wrapper is not None
    })

@app.route('/generate-fit', methods=['POST'])
def generate_fit():
    """Generar archivo FIT desde datos de rutina"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        # Validar datos requeridos
        required_fields = ['routine_name', 'steps']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo requerido: {field}'}), 400
        
        logger.info(f"Generando FIT para rutina: {data['routine_name']}")
        
        # Generar archivo FIT
        fit_file_path = generate_fit_file(data)
        
        if not fit_file_path or not os.path.exists(fit_file_path):
            return jsonify({'error': 'Error generando archivo FIT'}), 500
        
        # Enviar archivo
        return send_file(
            fit_file_path,
            as_attachment=True,
            download_name=f"{data['routine_name']}.fit",
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error en generate_fit: {str(e)}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

def generate_fit_file(routine_data):
    """Generar archivo FIT de workout usando el wrapper de Java"""
    try:
        if not fit_wrapper:
            raise Exception("FitJavaWrapper no está disponible")
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.fit')
        temp_file.close()
        
        # Usar el wrapper de Java para generar el archivo FIT
        result_path = fit_wrapper.create_workout_fit(routine_data, temp_file.name)
        
        if result_path and os.path.exists(result_path):
            return result_path
        else:
            raise Exception("El wrapper de Java no pudo generar el archivo FIT")
        
    except Exception as e:
        logger.error(f"Error generando FIT: {str(e)}")
        return None

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba para verificar la generación de archivos FIT"""
    try:
        test_data = {
            'routine_name': 'Test Workout',
            'steps': [
                {'type': 'warmup', 'time': '300'},
                {'type': 'run', 'time': '600'},
                {'type': 'cooldown', 'time': '300'}
            ]
        }
        
        fit_file = generate_fit_file(test_data)
        if fit_file:
            return jsonify({'status': 'success', 'message': 'Archivo FIT de prueba generado correctamente'})
        else:
            return jsonify({'status': 'error', 'message': 'Error generando archivo FIT de prueba'}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def parse_duration(duration_str):
    """Convertir duración de string a segundos"""
    try:
        return int(duration_str)
    except ValueError:
        return 60

def map_intensity(step_type):
    """Mapear tipo de paso a intensidad FIT"""
    intensity_map = {
        'warmup': 1,    # Warmup
        'cooldown': 2,  # Cooldown
        'run': 0,       # Active
        'rest': 3,      # Rest
    }
    return intensity_map.get(step_type.lower(), 0)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor Flask en puerto {port}")
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        raise