# Documentación de Endpoints USEBEQ API Externa

Esta documentación describe los nuevos endpoints implementados para integrar la API externa de USEBEQ.

## Configuración Inicial

### 1. Instalar dependencias
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Crear tabla de tokens
Ejecutar el script SQL para crear la tabla `pp_token`:
```bash
mysql -u [usuario] -p [base_de_datos] < create_token_table.sql
```

### 3. Configuración en .env
Las credenciales de la API externa ya están configuradas en `app/core/config.py`:
- **Email**: portalpadres@usebeq.edu.mx
- **Password**: pp4NUudeCQFo2
- **API Base URL**: https://sce-usebeq-api-test-v2.azurewebsites.net/api/portal-padres
- **Auth URL**: https://siga-usebeq-api.azurewebsites.net/api/authentication

## Endpoints Disponibles

Todos los endpoints están bajo el prefijo `/api/v1/usebeq` y requieren autenticación (Bearer token).

### 1. Consultar Estudiante por CURP y CCT

**Endpoint**: `GET /api/v1/usebeq/estudiante/{curp}/{cct}`

**Descripción**: Obtiene la información de un estudiante por su CURP y CCT.

**Parámetros**:
- `curp` (string): CURP del estudiante
- `cct` (string): Clave del Centro de Trabajo

**Ejemplo**:
```bash
GET /api/v1/usebeq/estudiante/AAPR160106HQTLRNA6/22DPR0200G
```

**Respuesta**:
```json
{
  "IdAlumno": 863309,
  "CURP": "AAPR160106HQTLRNA6",
  "ApellidoPaterno": "ALVAREZ",
  "ApellidoMaterno": "PEREZ",
  "Nombre": "RENE",
  "CCT": "22DPR0200G",
  "NombreCT": "JUVENTINO ROSAS",
  "Turno": "MAT",
  "Grado": "4",
  "Grupo": "A",
  "Estatus": "I "
}
```

---

### 2. Consultar Estudiante por ID

**Endpoint**: `GET /api/v1/usebeq/estudiante/{id_alumno}`

**Descripción**: Obtiene la información de un estudiante por su ID.

**Parámetros**:
- `id_alumno` (int): ID del alumno

**Ejemplo**:
```bash
GET /api/v1/usebeq/estudiante/863309
```

**Respuesta**: Igual que el endpoint anterior.

---

### 3. Descargar Boleta Actual

**Endpoint**: `GET /api/v1/usebeq/boleta/{id_alumno}`

**Descripción**: Descarga la boleta de calificaciones actual del estudiante en formato PDF.

**Parámetros**:
- `id_alumno` (int): ID del alumno

**Ejemplo**:
```bash
GET /api/v1/usebeq/boleta/863309
```

**Respuesta**: Stream de datos PDF (application/pdf)

---

### 4. Descargar Boleta Histórica

**Endpoint**: `GET /api/v1/usebeq/boleta-historica/{id_alumno}/{anio_inicio}`

**Descripción**: Descarga la boleta de calificaciones histórica del estudiante para un año específico.

**Parámetros**:
- `id_alumno` (int): ID del alumno
- `anio_inicio` (int): Año de inicio del ciclo escolar (ej: 2023)

**Ejemplo**:
```bash
GET /api/v1/usebeq/boleta-historica/863309/2023
```

**Respuesta**: Stream de datos PDF (application/pdf)

---

### 5. Solicitar Baja de Estudiante

**Endpoint**: `POST /api/v1/usebeq/baja/`

**Descripción**: Solicita la baja de un estudiante.

**Request Body**:
```json
{
  "idAlumno": 863309,
  "idMotivoBaja": 1
}
```

**Parámetros**:
- `idAlumno` (int): ID del alumno
- `idMotivoBaja` (int): ID del motivo de baja (ver catálogo)

**Ejemplo**:
```bash
POST /api/v1/usebeq/baja/
Content-Type: application/json

{
  "idAlumno": 863309,
  "idMotivoBaja": 1
}
```

**Respuesta**:
```json
{
  "mensaje": "La solicitud de baja de 863309 se ha procesado correctamente"
}
```

---

### 6. Obtener Catálogo de Tipos de Baja

**Endpoint**: `GET /api/v1/usebeq/catalogo/tipos-de-baja`

**Descripción**: Obtiene el catálogo de tipos de baja disponibles.

**Ejemplo**:
```bash
GET /api/v1/usebeq/catalogo/tipos-de-baja
```

**Respuesta**:
```json
[
  {
    "Id": 1,
    "Descripcion": "CAMBIO DE ESCUELA"
  },
  {
    "Id": 2,
    "Descripcion": "CAMBIO DE ENTIDAD/PAÍS"
  },
  {
    "Id": 3,
    "Descripcion": "BAJA POR DEFUNCIÓN (BD)"
  },
  {
    "Id": 4,
    "Descripcion": "BLOQUEAR ESTUDIANTE"
  },
  {
    "Id": 7,
    "Descripcion": "BAJA ADMINISTRATIVA"
  }
]
```

---

## Autenticación con la API Externa

El servicio `USEBEQAPIService` maneja automáticamente la autenticación con la API externa:

1. **Primer uso**: Se autentica con email y contraseña, obtiene tokens y los almacena en la base de datos.
2. **Usos siguientes**: Usa el token almacenado si es válido (menos de 24 horas).
3. **Token expirado**: Intenta refrescar el token automáticamente.
4. **Refresh fallido**: Obtiene nuevos tokens autenticándose nuevamente.

### Flujo de Autenticación

```
┌─────────────────────────────────────────┐
│  Request a endpoint USEBEQ              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  ¿Existe token en DB?                   │
└──────────────┬──────────────────────────┘
               │
         ┌─────┴─────┐
         │           │
        Sí          No
         │           │
         ▼           ▼
┌────────────┐  ┌──────────────┐
│¿Es válido? │  │ Autenticar   │
│(<24 horas) │  │ (nuevo token)│
└─────┬──────┘  └──────┬───────┘
      │                │
   ┌──┴──┐            │
   │     │            │
  Sí    No            │
   │     │            │
   │     ▼            │
   │ ┌──────────┐    │
   │ │ Refresh  │    │
   │ │  Token   │    │
   │ └────┬─────┘    │
   │      │          │
   │   ┌──┴──┐       │
   │   │     │       │
   │  OK   Fallo     │
   │   │     │       │
   │   │     ▼       │
   │   │  ┌────────┐ │
   │   │  │Autent. │ │
   │   │  │(nuevo) │ │
   │   │  └───┬────┘ │
   │   │      │      │
   └───┴──────┴──────┘
         │
         ▼
┌──────────────────────┐
│  Hacer request con   │
│  token válido        │
└──────────────────────┘
```

## Archivos Creados/Modificados

### Archivos Nuevos:
1. `backend/app/models/api_token.py` - Modelo para almacenar tokens
2. `backend/app/schemas/usebeq_api.py` - Schemas para las respuestas de la API
3. `backend/app/services/usebeq_api_service.py` - Servicio para manejar la API externa
4. `backend/app/api/endpoints/usebeq_external.py` - Endpoints de la API
5. `backend/create_token_table.sql` - Script SQL para crear la tabla

### Archivos Modificados:
1. `backend/requirements.txt` - Agregado httpx==0.26.0
2. `backend/app/core/config.py` - Agregada configuración de API externa
3. `backend/app/api/endpoints/__init__.py` - Registrado nuevo router

## Pruebas

### Probar con curl:

1. **Primero obtener token de autenticación**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "tu_usuario", "password": "tu_password"}'
```

2. **Consultar estudiante**:
```bash
curl -X GET "http://localhost:8000/api/v1/usebeq/estudiante/AAPR160106HQTLRNA6/22DPR0200G" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

3. **Obtener catálogo de bajas**:
```bash
curl -X GET "http://localhost:8000/api/v1/usebeq/catalogo/tipos-de-baja" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

4. **Descargar boleta**:
```bash
curl -X GET "http://localhost:8000/api/v1/usebeq/boleta/863309" \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -o boleta.pdf
```

## Notas Importantes

1. **Seguridad SSL**: El servicio desactiva la verificación SSL (`verify=False`) para las llamadas a la API externa. Esto es necesario porque la API puede usar certificados autofirmados en ambiente de pruebas.

2. **Tokens**: Los tokens tienen una vida útil de 24 horas. El servicio los maneja automáticamente.

3. **Autenticación de usuario**: Todos los endpoints requieren que el usuario esté autenticado en el portal.

4. **Manejo de errores**: Los endpoints devuelven errores HTTP 500 con detalles del error cuando falla la comunicación con la API externa.

## Swagger Documentation

Una vez que el servidor esté corriendo, puedes acceder a la documentación interactiva en:
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

Busca la sección "usebeq-external" para ver todos los endpoints disponibles.
