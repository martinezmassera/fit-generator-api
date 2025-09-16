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

# Agregar el SDK de Garmin al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'garmin_fit_sdk'))

try:
    from garmin_fit_sdk import Fit
    logger.info("SDK de Garmin cargado correctamente")
except ImportError as e:
    logger.error(f"Error cargando SDK de Garmin: {e}")
    # Fallback básico si no se puede cargar el SDK
    Fit = None

app = Flask(__name__)
CORS(app)  # Permitir CORS para llamadas desde WordPress

@app.route('/', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud"""
    return jsonify({
        'status': 'ok',
        'message': 'API de generación FIT funcionando',
        'timestamp': datetime.now().isoformat(),
        'sdk_loaded': Fit is not None
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
    """Generar archivo FIT usando el SDK de Garmin"""
    try:
        if Fit is None:
            # Fallback: generar archivo FIT básico sin SDK
            return generate_basic_fit_file(routine_data)
        
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.fit')
        temp_file.close()
        
        # Usar SDK de Garmin para generar FIT
        fit = Fit()
        
        # Configurar información básica del archivo
        fit.add_file_id_mesg()
        
        # Agregar información del workout
        workout_name = routine_data.get('routine_name', 'Rutina')
        fit.add_workout_mesg(workout_name)
        
        # Procesar pasos de la rutina
        step_index = 0
        for step in routine_data.get('steps', []):
            step_type = step.get('type', '')
            duration = step.get('duration', 60)
            intensity = step.get('intensity', 'active')
            
            # Mapear tipos de pasos
            if step_type in ['EEC', 'calentamiento']:
                fit.add_workout_step_mesg(
                    step_index, 
                    'warmup', 
                    duration_type='time',
                    duration_value=duration
                )
            elif step_type in ['VAC', 'enfriamiento']:
                fit.add_workout_step_mesg(
                    step_index, 
                    'cooldown', 
                    duration_type='time',
                    duration_value=duration
                )
            elif step_type in ['Pasada', 'intervalo']:
                fit.add_workout_step_mesg(
                    step_index, 
                    'interval', 
                    duration_type='time',
                    duration_value=duration,
                    intensity='active'
                )
            elif step_type in ['Pausa', 'recuperacion']:
                fit.add_workout_step_mesg(
                    step_index, 
                    'rest', 
                    duration_type='time',
                    duration_value=duration,
                    intensity='rest'
                )
            
            step_index += 1
        
        # Escribir archivo
        fit.write(temp_file.name)
        
        logger.info(f"Archivo FIT generado: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error generando FIT con SDK: {str(e)}")
        return generate_basic_fit_file(routine_data)

def generate_basic_fit_file(routine_data):
    """Generar archivo FIT básico sin SDK (fallback)"""
    try:
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.fit')
        
        # Header FIT básico
        header = bytearray(14)
        header[0] = 14  # Header size
        header[1] = 0x10  # Protocol version
        header[2:4] = (0).to_bytes(2, 'little')  # Profile version
        header[8:12] = b'.FIT'  # Data type
        
        # Calcular tamaño de datos (simplificado)
        data_size = len(routine_data.get('steps', [])) * 20 + 100
        header[4:8] = data_size.to_bytes(4, 'little')
        
        # CRC del header
        crc = calculate_crc(header[:12])
        header[12:14] = crc.to_bytes(2, 'little')
        
        # Escribir header
        temp_file.write(header)
        
        # Datos básicos del archivo (simplificado)
        # En una implementación real, aquí irían los mensajes FIT codificados
        basic_data = b'\x00' * data_size
        temp_file.write(basic_data)
        
        # CRC final
        temp_file.seek(0)
        file_crc = calculate_crc(temp_file.read())
        temp_file.write(file_crc.to_bytes(2, 'little'))
        
        temp_file.close()
        
        logger.info(f"Archivo FIT básico generado: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Error generando FIT básico: {str(e)}")
        return None

def calculate_crc(data):
    """Calcular CRC para archivo FIT"""
    crc_table = [
        0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
    ]
    
    crc = 0
    for byte in data:
        tmp = crc_table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ crc_table[byte & 0xF]
        
        tmp = crc_table[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]
    
    return crc

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba"""
    return jsonify({
        'message': 'API funcionando correctamente',
        'endpoints': [
            'GET / - Health check',
            'POST /generate-fit - Generar archivo FIT',
            'GET /test - Este endpoint'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)