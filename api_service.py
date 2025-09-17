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
    """Generar archivo FIT de workout compatible con Garmin"""
    try:
        # Crear archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.fit')
        temp_file.close()
        
        # Generar archivo FIT de workout usando estructura correcta
        return generate_workout_fit_file(routine_data, temp_file.name)
        
    except Exception as e:
        logger.error(f"Error generando FIT: {str(e)}")
        return None

def generate_workout_fit_file(routine_data, filename):
    """Generar archivo FIT de workout compatible con Garmin usando el SDK"""
    try:
        from garmin_fit_sdk import Decoder, Stream
        from garmin_fit_sdk.profile import Profile
        import struct
        from datetime import datetime
        
        # Crear estructura de archivo FIT de workout
        fit_data = bytearray()
        
        # 1. Header FIT (14 bytes)
        header_size = 14
        protocol_version = 0x20  # Versión 2.0
        profile_version = 2171   # Versión del perfil
        data_size = 0  # Se calculará después
        data_type = b'.FIT'
        
        header = bytearray(header_size)
        header[0] = header_size
        header[1] = protocol_version
        header[2:4] = profile_version.to_bytes(2, 'little')
        # data_size se escribirá después
        header[8:12] = data_type
        
        # 2. Mensajes FIT
        messages = bytearray()
        
        # File ID Message (requerido)
        file_id_msg = create_file_id_message()
        messages.extend(file_id_msg)
        
        # Workout Message
        workout_name = routine_data.get('routine_name', 'Rutina')
        workout_msg = create_workout_message(workout_name, len(routine_data.get('steps', [])))
        messages.extend(workout_msg)
        
        # Workout Step Messages
        step_index = 0
        for step in routine_data.get('steps', []):
            step_msg = create_workout_step_message(step_index, step)
            messages.extend(step_msg)
            step_index += 1
        
        # Calcular tamaño de datos
        data_size = len(messages)
        header[4:8] = data_size.to_bytes(4, 'little')
        
        # CRC del header
        header_crc = calculate_crc(header[:12])
        header[12:14] = header_crc.to_bytes(2, 'little')
        
        # Combinar header y mensajes
        fit_data.extend(header)
        fit_data.extend(messages)
        
        # CRC final del archivo
        file_crc = calculate_crc(fit_data)
        fit_data.extend(file_crc.to_bytes(2, 'little'))
        
        # Escribir archivo
        with open(filename, 'wb') as f:
            f.write(fit_data)
        
        logger.info(f"Archivo FIT de workout generado: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error generando FIT de workout: {str(e)}")
        return None

def create_file_id_message():
    """Crear mensaje File ID requerido"""
    # Definición del mensaje File ID (mesg_num = 0)
    msg_def = bytearray([
        0x40,  # Header: definition message, local message type 0
        0x00,  # Reserved
        0x00,  # Architecture (little endian)
        0x00, 0x00,  # Global message number (0 = File ID)
        0x05,  # Number of fields
        # Field definitions: field_def_num, size, base_type
        0x00, 0x01, 0x00,  # Type (1 byte, enum)
        0x01, 0x02, 0x84,  # Manufacturer (2 bytes, uint16)
        0x02, 0x02, 0x84,  # Product (2 bytes, uint16)
        0x03, 0x04, 0x86,  # Serial Number (4 bytes, uint32z)
        0x04, 0x04, 0x86,  # Time Created (4 bytes, uint32)
    ])
    
    # Datos del mensaje
    current_time = int(datetime.now().timestamp()) - 631065600  # FIT epoch
    msg_data = bytearray([
        0x00,  # Header: data message, local message type 0
        0x06,  # Type: workout file
        0xFF, 0xFF,  # Manufacturer: development
        0x00, 0x00,  # Product: 0
        0x12, 0x34, 0x56, 0x78,  # Serial number (ejemplo)
    ])
    msg_data.extend(current_time.to_bytes(4, 'little'))  # Time created
    
    result = bytearray()
    result.extend(msg_def)
    result.extend(msg_data)
    return result

def create_workout_message(name, num_steps):
    """Crear mensaje Workout"""
    # Definición del mensaje Workout (mesg_num = 26)
    msg_def = bytearray([
        0x41,  # Header: definition message, local message type 1
        0x00,  # Reserved
        0x00,  # Architecture (little endian)
        0x1A, 0x00,  # Global message number (26 = Workout)
        0x04,  # Number of fields
        # Field definitions
        0x04, 0x01, 0x00,  # Sport (1 byte, enum)
        0x05, 0x10, 0x07,  # Wkt Name (16 bytes, string)
        0x06, 0x02, 0x84,  # Num Valid Steps (2 bytes, uint16)
        0x08, 0x04, 0x86,  # Capabilities (4 bytes, uint32z)
    ])
    
    # Datos del mensaje
    msg_data = bytearray([
        0x01,  # Header: data message, local message type 1
        0x01,  # Sport: running
    ])
    
    # Nombre del workout (16 bytes, rellenado con nulls)
    name_bytes = name.encode('utf-8')[:15]  # Máximo 15 chars + null terminator
    name_padded = name_bytes + b'\x00' * (16 - len(name_bytes))
    msg_data.extend(name_padded)
    
    msg_data.extend(num_steps.to_bytes(2, 'little'))  # Num valid steps
    msg_data.extend((0x00000020).to_bytes(4, 'little'))  # Capabilities
    
    result = bytearray()
    result.extend(msg_def)
    result.extend(msg_data)
    return result

def create_workout_step_message(step_index, step_data):
    """Crear mensaje Workout Step"""
    # Definición del mensaje Workout Step (mesg_num = 27)
    msg_def = bytearray([
        0x42,  # Header: definition message, local message type 2
        0x00,  # Reserved
        0x00,  # Architecture (little endian)
        0x1B, 0x00,  # Global message number (27 = Workout Step)
        0x06,  # Number of fields
        # Field definitions
        0x00, 0x02, 0x84,  # Message Index (2 bytes, uint16)
        0x01, 0x10, 0x07,  # Wkt Step Name (16 bytes, string)
        0x02, 0x01, 0x00,  # Duration Type (1 byte, enum)
        0x03, 0x04, 0x86,  # Duration Value (4 bytes, uint32)
        0x04, 0x01, 0x00,  # Target Type (1 byte, enum)
        0x06, 0x01, 0x00,  # Intensity (1 byte, enum)
    ])
    
    # Mapear tipos de paso
    step_type = step_data.get('type', '')
    duration_type = 0  # Time
    duration_value = parse_duration(step_data.get('time', '60'))
    target_type = 0  # Speed
    intensity = map_intensity(step_type)
    
    # Datos del mensaje
    msg_data = bytearray([
        0x02,  # Header: data message, local message type 2
    ])
    msg_data.extend(step_index.to_bytes(2, 'little'))  # Message index
    
    # Nombre del paso (16 bytes)
    step_name = f"{step_type} {step_index + 1}"
    name_bytes = step_name.encode('utf-8')[:15]
    name_padded = name_bytes + b'\x00' * (16 - len(name_bytes))
    msg_data.extend(name_padded)
    
    msg_data.append(duration_type)  # Duration type
    msg_data.extend(duration_value.to_bytes(4, 'little'))  # Duration value
    msg_data.append(target_type)  # Target type
    msg_data.append(intensity)  # Intensity
    
    result = bytearray()
    result.extend(msg_def)
    result.extend(msg_data)
    return result

def parse_duration(duration_str):
    """Convertir duración de string a segundos"""
    try:
        if 'min' in duration_str:
            minutes = float(duration_str.replace('min', '').strip())
            return int(minutes * 60)
        elif ':' in duration_str:
            parts = duration_str.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1]) if len(parts) > 1 else 0
            return minutes * 60 + seconds
        else:
            return int(float(duration_str))
    except:
        return 60  # Default 1 minuto

def map_intensity(step_type):
    """Mapear tipo de paso a intensidad"""
    intensity_map = {
        'EEC': 1,      # Warmup
        'VAC': 1,      # Cooldown  
        'Pasada': 2,   # Active
        'Pausa': 0,    # Rest
        'Rodaje': 2,   # Active
        'Tempo': 2,    # Active
        'Fartlek': 2   # Active
    }
    return intensity_map.get(step_type, 2)  # Default: active

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