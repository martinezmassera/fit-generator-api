# API Generador FIT - Render.com

Este es el servicio API Python para generar archivos FIT de Garmin, diseñado para desplegarse en Render.com.

## 🚀 Despliegue en Render.com

### Paso 1: Preparar Repositorio Git

1. **Crear repositorio en GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - FIT Generator API"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/fit-generator-api.git
   git push -u origin main
   ```

### Paso 2: Configurar en Render.com

1. **Crear cuenta** en [render.com](https://render.com)
2. **Conectar GitHub** y seleccionar el repositorio
3. **Configurar Web Service:**
   - **Name:** `fit-generator-api`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn -c gunicorn.conf.py api_service:app`
   - **Plan:** Free (para empezar)

### Paso 3: Variables de Entorno (Opcional)

En Render.com, puedes configurar:
- `PYTHON_VERSION=3.9.18`
- `FLASK_ENV=production`

## 📋 Estructura de Archivos

```
render_deploy/
├── api_service.py          # Servicio Flask principal
├── requirements.txt        # Dependencias Python
├── render.yaml            # Configuración Render
├── gunicorn.conf.py       # Configuración Gunicorn
├── Procfile               # Comando de inicio alternativo
├── garmin_fit_sdk/        # SDK de Garmin FIT
└── README.md              # Este archivo
```

## 🔗 Endpoints del API

Una vez desplegado, el API tendrá estos endpoints:

- `GET /` - Health check
- `POST /generate-fit` - Generar archivo FIT
- `GET /test` - Endpoint de prueba

## 📝 Ejemplo de Uso

```bash
# Health check
curl https://tu-app.onrender.com/

# Generar archivo FIT
curl -X POST https://tu-app.onrender.com/generate-fit \
  -H "Content-Type: application/json" \
  -d '{
    "routine_name": "Mi Rutina",
    "steps": [
      {"type": "EEC", "duration": 300},
      {"type": "Pasada", "duration": 120},
      {"type": "Pausa", "duration": 60},
      {"type": "VAC", "duration": 300}
    ]
  }' \
  --output mi_rutina.fit
```

## 🔧 Configuración WordPress

Una vez desplegado, actualiza la URL del API en tu plugin WordPress:

```php
// En meta-running-rutinas-api.php
private $api_base_url = 'https://tu-app.onrender.com';
```

## 🆘 Solución de Problemas

### Error "No module named 'app'"
✅ **SOLUCIONADO** - Ahora usa `gunicorn.conf.py` y `Procfile`

### Comandos de inicio alternativos:
1. `gunicorn -c gunicorn.conf.py api_service:app` (Recomendado)
2. `gunicorn --bind 0.0.0.0:$PORT api_service:app` (Básico)
3. `python api_service.py` (Solo para desarrollo)

### Error de Build
```bash
# Verificar requirements.txt
pip install -r requirements.txt
```

### Error de Start
```bash
# Probar localmente
gunicorn -c gunicorn.conf.py api_service:app
```

### Error de SDK
El API incluye un fallback básico si el SDK de Garmin no se carga correctamente.

## 📊 Monitoreo

Render.com proporciona:
- ✅ Logs en tiempo real
- ✅ Métricas de rendimiento
- ✅ SSL automático
- ✅ Reinicio automático

## 💰 Costos

- **Plan Free:** Gratis con limitaciones
- **Plan Starter:** $7/mes - Recomendado para producción
- **Plan Pro:** $25/mes - Para mayor tráfico