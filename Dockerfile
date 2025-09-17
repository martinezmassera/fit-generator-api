# Usar imagen base de Python con Java preinstalado
FROM openjdk:11-jre-slim

# Instalar Python y pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crear enlaces simbólicos para python
RUN ln -sf /usr/bin/python3 /usr/bin/python
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

# Verificar que Java y Python estén disponibles
RUN java -version && python --version

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Verificar que fit.jar esté presente
RUN ls -la fit.jar

# Exponer el puerto
EXPOSE 10000

# Comando para ejecutar la aplicación
CMD echo "=== VERIFICACIÓN DEL ENTORNO ===" && \
    echo "Java version:" && java -version && \
    echo "Python version:" && python --version && \
    echo "JAVA_HOME: $JAVA_HOME" && \
    echo "PATH: $PATH" && \
    echo "=== INICIANDO APLICACIÓN ===" && \
    gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 api_service:app