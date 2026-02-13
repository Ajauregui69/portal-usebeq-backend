# Manual: Crear y Desplegar Web App en Azure (Python + FastAPI)

## Requisitos Previos
- Cuenta de Azure activa
- Repositorio en GitHub con el código del backend
- Python 3.11+ instalado localmente
- Base de datos MySQL (Azure Database for MySQL o externa)

---

## Paso 1: Crear Web App en Azure Portal

1. Ir a [Azure Portal](https://portal.azure.com)
2. Click en **"Create a resource"** (+ Crear un recurso)
3. Buscar **"Web App"**
4. Click en **"Create"**

### Configuración Básica

| Campo | Valor |
|-------|-------|
| Subscription | Tu suscripción de Azure |
| Resource Group | Crear nuevo o usar existente (ej: `rg-portal-usebeq`) |
| Name | `portal-usebeq-backend-app` (debe ser único) |
| Publish | **Code** |
| Runtime stack | **Python 3.11** |
| Operating System | **Linux** |
| Region | `Mexico Central` o la más cercana |

### Plan de App Service

| Campo | Valor |
|-------|-------|
| Linux Plan | Crear nuevo o usar existente |
| Pricing plan | **Basic B1** (desarrollo) o **Standard S1** (producción) |

5. Click en **"Review + create"**
6. Click en **"Create"**

---

## Paso 2: Configurar Variables de Entorno

1. En Azure Portal, ir a tu Web App
2. Click en **"Configuration"** en el menú lateral
3. En la pestaña **"Application settings"**, agregar:

| Name | Value |
|------|-------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@host/dbname?charset=utf8mb4` |
| `SECRET_KEY` | `tu-clave-secreta-muy-larga-y-segura` |
| `BACKEND_CORS_ORIGINS` | `["https://tu-frontend.azurestaticapps.net"]` |
| `GOOGLE_CLIENT_ID` | `tu-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | `tu-client-secret` |
| `GOOGLE_REDIRECT_URI` | `https://tu-backend.azurewebsites.net/api/v1/auth/google/callback` |
| `FRONTEND_URL` | `https://tu-frontend.azurestaticapps.net` |
| `MAIL_USERNAME` | `noreply@usebeq.edu.mx` |
| `MAIL_PASSWORD` | `tu-password-de-email` |
| `MAIL_FROM` | `noreply@usebeq.edu.mx` |
| `MAIL_SERVER` | `smtp.gmail.com` |
| `MAIL_PORT` | `587` |

4. Click en **"Save"**

---

## Paso 3: Configurar Comando de Inicio

1. En Azure Portal, ir a tu Web App
2. Click en **"Configuration"** > pestaña **"General settings"**
3. En **"Startup Command"**, ingresar:

```
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120
```

4. Click en **"Save"**

---

## Paso 4: Configurar Despliegue Automático con GitHub Actions

### 4.1 Descargar Publish Profile

1. En Azure Portal, ir a tu Web App
2. Click en **"Download publish profile"** (en la página Overview)
3. Guardar el archivo `.PublishSettings`

### 4.2 Agregar Secret en GitHub

1. Ir a tu repositorio en GitHub
2. Settings > Secrets and variables > Actions
3. Click en **"New repository secret"**
4. Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
5. Value: Pegar TODO el contenido del archivo `.PublishSettings`

### 4.3 Crear Workflow de GitHub Actions

Crear archivo `.github/workflows/azure-webapp.yml`:

```yaml
name: Deploy Python Backend to Azure Web App

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: 'portal-usebeq-backend-app'
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

---

## Paso 5: Archivos Necesarios en el Proyecto

### `requirements.txt`
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
sqlalchemy==2.0.23
pymysql==1.1.0
python-dotenv==1.0.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-api-python-client==2.111.0
itsdangerous==2.1.2
starlette==0.27.0
```

### `startup.txt` (en la raíz del proyecto)
```
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 120
```

---

## Estructura del Proyecto Python/FastAPI

```
backend/
├── .github/
│   └── workflows/
│       └── azure-webapp.yml    # CI/CD automático
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── users.py
│   ├── core/
│   │   ├── config.py           # Configuración con Pydantic
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   ├── services/
│   │   └── email_service.py
│   └── main.py                 # Punto de entrada
├── .env                        # Variables locales (NO subir)
├── .env.example
├── requirements.txt
└── startup.txt
```

---

## Paso 6: Configurar Base de Datos

### Opción A: Azure Database for MySQL

1. En Azure Portal, crear **"Azure Database for MySQL"**
2. Configurar:
   - Server name: `usebeq-mysql-server`
   - Admin username: `usebeq_admin`
   - Password: (crear password seguro)
3. En **"Connection security"**:
   - Permitir acceso desde Azure services
   - Agregar tu IP para desarrollo
4. Crear la base de datos:
   ```sql
   CREATE DATABASE portal_usebeq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### Opción B: Base de datos externa

Si usas una base de datos externa (como la de USEBEQ), asegúrate de que:
- El firewall permita conexiones desde Azure
- La cadena de conexión sea correcta

---

## Variables de Entorno

### Desarrollo Local (`.env`)
```env
DATABASE_URL=mysql+pymysql://user:pass@localhost/usebeq_portal?charset=utf8mb4
SECRET_KEY=dev-secret-key-change-in-production
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000
OAUTHLIB_INSECURE_TRANSPORT=1
```

### Producción (Azure Configuration)
```
DATABASE_URL=mysql+pymysql://user:pass@host/dbname?charset=utf8mb4
SECRET_KEY=clave-super-segura-de-produccion
BACKEND_CORS_ORIGINS=["https://tu-frontend.azurestaticapps.net"]
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
GOOGLE_REDIRECT_URI=https://tu-backend.azurewebsites.net/api/v1/auth/google/callback
FRONTEND_URL=https://tu-frontend.azurestaticapps.net
```

**NOTA**: NO incluir `OAUTHLIB_INSECURE_TRANSPORT` en producción (solo es para desarrollo local con HTTP).

---

## Comandos Útiles

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Desarrollo local
uvicorn app.main:app --reload --port 8000

# Ver documentación API
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

---

## Solución de Problemas

### Error 500 en producción
1. Ir a Azure Portal > Web App > **"Log stream"**
2. Revisar los logs en tiempo real
3. O ir a **"Diagnose and solve problems"**

### La base de datos no conecta
- Verificar que la IP de Azure esté permitida en el firewall
- Verificar la cadena de conexión
- Probar conexión desde Azure Cloud Shell

### Las variables de entorno no se cargan
- Reiniciar la Web App después de cambiar variables
- Verificar que no haya espacios extras en los valores
- Usar Azure Portal > Configuration para verificar

### Error de CORS
- Verificar que `BACKEND_CORS_ORIGINS` incluya la URL del frontend
- El formato debe ser JSON array: `["https://url1.com", "https://url2.com"]`

---

## Costos Estimados

| Plan | Costo | Recursos |
|------|-------|----------|
| Free F1 | $0 | 60 min/día, muy limitado |
| Basic B1 | ~$13/mes | 1.75GB RAM, 1 CPU |
| Standard S1 | ~$70/mes | 1.75GB RAM, 1 CPU, auto-scale |
| Premium P1V2 | ~$80/mes | 3.5GB RAM, 1 CPU, más rendimiento |
