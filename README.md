# Portal USEBEQ - Backend (FastAPI)

API REST para el Portal USEBEQ construida con FastAPI.

## Inicio Rápido

### 1. Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
nano .env
```

### 3. Base de Datos

Asegúrate de tener SQL Server configurado y las tablas creadas:

```sql
-- Tablas principales
PP_usuarios       -- Usuarios del portal
SCE004           -- Estudiantes
SCE005           -- Matrículas
pp_alumnos       -- Relación padre-alumno
SCE039           -- Certificados
```

### 4. Ejecutar

```bash
uvicorn app.main:app --reload
```

Accede a:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estructura

```
app/
├── api/
│   ├── dependencies/
│   │   └── auth.py           # Dependencias de autenticación
│   └── endpoints/
│       ├── auth.py           # Login, register
│       ├── users.py          # Perfil de usuario
│       └── students.py       # Gestión de alumnos
├── core/
│   ├── config.py             # Configuración
│   ├── database.py           # Conexión a BD
│   └── security.py           # JWT, passwords
├── models/
│   ├── user.py               # Modelo Usuario
│   ├── student.py            # Modelo Estudiante
│   └── certificate.py        # Modelo Certificado
├── schemas/
│   ├── user.py               # Schemas de usuario
│   └── student.py            # Schemas de estudiante
└── main.py                   # Aplicación principal
```

## Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión a BD | `mssql+pyodbc://...` |
| `SECRET_KEY` | Clave secreta JWT | `your-secret-key` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración token | `30` |
| `BACKEND_CORS_ORIGINS` | Orígenes permitidos | `["http://localhost:3000"]` |

## Endpoints Principales

### Autenticación

```bash
# Registrar usuario
POST /api/v1/auth/register
{
  "u_correo": "usuario@ejemplo.com",
  "u_pass": "password123",
  "u_nombre": "Juan",
  "u_appat": "Pérez",
  "u_apmat": "García"
}

# Login
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
username=usuario@ejemplo.com&password=password123

# Activar cuenta
POST /api/v1/auth/activate/{token}
```

### Usuarios

```bash
# Obtener perfil
GET /api/v1/users/me
Authorization: Bearer {token}

# Actualizar perfil
PUT /api/v1/users/me
Authorization: Bearer {token}
{
  "u_tel": "4421234567",
  "domicilio": "Calle Principal 123"
}
```

### Estudiantes

```bash
# Listar alumnos vinculados
GET /api/v1/students/my-students
Authorization: Bearer {token}

# Vincular alumno
POST /api/v1/students/link-student
Authorization: Bearer {token}
{
  "al_curp": "ABCD123456HDFGHI00",
  "relacion": "padre"
}

# Desvincular alumno
DELETE /api/v1/students/unlink-student/{student_id}
Authorization: Bearer {token}
```

## Seguridad

### Autenticación JWT

```python
from app.api.dependencies.auth import get_current_active_user

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hola {current_user.u_nombre}"}
```

### Passwords

- Hashing con bcrypt
- Mínimo 6 caracteres
- Validación en schemas Pydantic

## Testing

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio httpx

# Ejecutar tests
pytest

# Con cobertura
pytest --cov=app
```

## Migraciones (Alembic)

```bash
# Inicializar Alembic
alembic init alembic

# Crear migración
alembic revision --autogenerate -m "Descripción"

# Aplicar migraciones
alembic upgrade head

# Revertir
alembic downgrade -1
```

## Producción

### Con Gunicorn

```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Con Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Error de conexión a SQL Server

```bash
# Instalar driver ODBC
# Ubuntu/Debian
sudo apt-get install unixodbc-dev

# Verificar drivers disponibles
odbcinst -q -d
```

### Error de importación circular

Usa imports locales dentro de funciones si es necesario.

### Problemas con CORS

Verifica que `BACKEND_CORS_ORIGINS` incluya el origen del frontend.
