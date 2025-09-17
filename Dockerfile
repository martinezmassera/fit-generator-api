# Usar imagen base de Python con Java
FROM python:3.9-slim

# Instalar Java y herramientas necesarias
RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless procps && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establecer JAVA_HOME y PATH de forma más explícita
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# Crear enlaces simbólicos para asegurar que java esté disponible
RUN ln -sf $JAVA_HOME/bin/java /usr/local/bin/java
RUN ln -sf $JAVA_HOME/bin/javac /usr/local/bin/javac

# Verificar instalación de Java
RUN java -version && which java

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

# Comando para ejecutar la aplicación con verificación de Java
CMD echo "=== VERIFICACIÓN DE JAVA ===" && \
    echo "JAVA_HOME: $JAVA_HOME" && \
    echo "PATH: $PATH" && \
    which java && \
    java -version && \
    echo "=== INICIANDO APLICACIÓN ===" && \
    gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 api_service:app