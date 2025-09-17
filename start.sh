#!/bin/bash
# Script de inicio para Render.com
echo "Iniciando API de FIT Generator..."
echo "Puerto: $PORT"
echo "Directorio actual: $(pwd)"
echo "Archivos disponibles:"
ls -la

# Ejecutar Gunicorn con el módulo correcto
exec gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 api_service:app