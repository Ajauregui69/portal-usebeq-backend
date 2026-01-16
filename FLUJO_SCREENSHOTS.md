# Flujo para Screenshots de Endpoints USEBEQ

Este documento describe el flujo paso a paso para tomar screenshots de todos los endpoints implementados.

## Preparación

### 1. Iniciar el servidor
```bash
cd /home/alonso/projects/portal-usebeq-modernized/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verificar que el servidor esté corriendo
Abre tu navegador y ve a: http://localhost:8000/api/v1/docs

---

## PASO 1: Autenticación (Obtener Token)

### Screenshot 1: Swagger UI - Vista General
- **URL**: http://localhost:8000/api/v1/docs
- **Qué capturar**: Vista general de Swagger mostrando todas las secciones, especialmente la sección **"usebeq-external"** expandida

### Screenshot 2: Login para obtener token
1. En Swagger, busca la sección **"authentication"**
2. Expande el endpoint **POST /api/v1/auth/login**
3. Click en "Try it out"
4. Ingresa las credenciales:
```json
{
  "username": "tu_usuario",
  "password": "tu_password"
}
```
5. Click en "Execute"
6. **Captura**: La respuesta mostrando el `access_token`

### Screenshot 3: Autorizar en Swagger
1. Click en el botón **"Authorize"** (candado) en la parte superior derecha
2. En el campo "Value", ingresa: `Bearer {tu_token_aqui}`
   - Ejemplo: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. Click en "Authorize"
4. **Captura**: El modal de autorización con el token ingresado

---

## PASO 2: Endpoints de Consulta de Estudiantes

### Screenshot 4: GET /api/v1/usebeq/estudiante/{curp}/{cct}
1. Busca la sección **"usebeq-external"**
2. Expande **GET /api/v1/usebeq/estudiante/{curp}/{cct}**
3. Click en "Try it out"
4. Ingresa los parámetros:
   - `curp`: AAPR160106HQTLRNA6
   - `cct`: 22DPR0200G
5. Click en "Execute"
6. **Captura**: La respuesta exitosa mostrando los datos del estudiante

**Respuesta esperada**:
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

### Screenshot 5: GET /api/v1/usebeq/estudiante/{id_alumno}
1. Expande **GET /api/v1/usebeq/estudiante/{id_alumno}**
2. Click en "Try it out"
3. Ingresa el parámetro:
   - `id_alumno`: 863309
4. Click en "Execute"
5. **Captura**: La respuesta exitosa (misma estructura que el anterior)

---

## PASO 3: Endpoint de Catálogo de Bajas

### Screenshot 6: GET /api/v1/usebeq/catalogo/tipos-de-baja
1. Expande **GET /api/v1/usebeq/catalogo/tipos-de-baja**
2. Click en "Try it out"
3. Click en "Execute"
4. **Captura**: La respuesta mostrando el catálogo completo

**Respuesta esperada**:
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

## PASO 4: Endpoint de Solicitud de Baja

### Screenshot 7: POST /api/v1/usebeq/baja/
1. Expande **POST /api/v1/usebeq/baja/**
2. Click en "Try it out"
3. Modifica el Request body:
```json
{
  "idAlumno": 863309,
  "idMotivoBaja": 1
}
```
4. Click en "Execute"
5. **Captura**: La respuesta exitosa

**Respuesta esperada**:
```json
{
  "mensaje": "La solicitud de baja de 863309 se ha procesado correctamente"
}
```

**⚠️ NOTA**: Este endpoint realmente procesa la baja. Si no quieres dar de baja al estudiante, NO ejecutes este paso o usa un ID de prueba.

---

## PASO 5: Endpoints de Boletas (PDF)

### Screenshot 8: GET /api/v1/usebeq/boleta/{id_alumno}
1. Expande **GET /api/v1/usebeq/boleta/{id_alumno}**
2. Click en "Try it out"
3. Ingresa el parámetro:
   - `id_alumno`: 863309
4. Click en "Execute"
5. **Captura 8a**: La respuesta mostrando "Download file" o el enlace de descarga
6. Click en "Download file"
7. **Captura 8b**: El PDF descargado abierto mostrando la boleta

### Screenshot 9: GET /api/v1/usebeq/boleta-historica/{id_alumno}/{anio_inicio}
1. Expande **GET /api/v1/usebeq/boleta-historica/{id_alumno}/{anio_inicio}**
2. Click en "Try it out"
3. Ingresa los parámetros:
   - `id_alumno`: 863309
   - `anio_inicio`: 2023 (o el año que corresponda)
4. Click en "Execute"
5. **Captura 9a**: La respuesta mostrando "Download file"
6. Click en "Download file"
7. **Captura 9b**: El PDF descargado abierto mostrando la boleta histórica

---

## PASO 6: Verificar Tokens en Base de Datos (Opcional)

### Screenshot 10: Tabla pp_token
Ejecuta esta consulta SQL para mostrar que los tokens se están guardando:

```bash
mysql -u usebeq_user -p usebeq_portal -e "SELECT id, LEFT(token, 50) as token_preview, LEFT(refresh_token, 50) as refresh_preview, fecha_registro FROM pp_token ORDER BY fecha_registro DESC LIMIT 5;"
```

O desde Python:
```bash
python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; engine = create_engine(settings.DATABASE_URL); conn = engine.connect(); result = conn.execute(text('SELECT id, LEFT(token, 50) as token_preview, fecha_registro FROM pp_token ORDER BY fecha_registro DESC LIMIT 5')); print('\n'.join([str(row) for row in result]))"
```

**Captura**: La salida mostrando los tokens almacenados

---

## PASO 7: Prueba con cURL (Terminal)

### Screenshot 11: Prueba desde terminal con cURL

Primero obtén el token:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"tu_usuario","password":"tu_password"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Luego prueba un endpoint:
```bash
curl -X GET "http://localhost:8000/api/v1/usebeq/estudiante/AAPR160106HQTLRNA6/22DPR0200G" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Captura**: La terminal mostrando el comando y la respuesta JSON formateada

---

## Resumen de Screenshots

| # | Descripción | Endpoint |
|---|-------------|----------|
| 1 | Vista general de Swagger UI | `/docs` |
| 2 | Login y obtención de token | `POST /auth/login` |
| 3 | Autorización en Swagger | Modal Authorize |
| 4 | Consulta estudiante por CURP/CCT | `GET /usebeq/estudiante/{curp}/{cct}` |
| 5 | Consulta estudiante por ID | `GET /usebeq/estudiante/{id}` |
| 6 | Catálogo de tipos de baja | `GET /usebeq/catalogo/tipos-de-baja` |
| 7 | Solicitud de baja | `POST /usebeq/baja/` |
| 8a | Descarga de boleta - Swagger | `GET /usebeq/boleta/{id}` |
| 8b | PDF de boleta abierto | - |
| 9a | Descarga boleta histórica - Swagger | `GET /usebeq/boleta-historica/{id}/{año}` |
| 9b | PDF de boleta histórica abierto | - |
| 10 | Tokens en base de datos | SQL query |
| 11 | Prueba con cURL en terminal | Terminal |

---

## Tips para Screenshots

1. **Usa modo claro** en el navegador para mejor contraste
2. **Zoom apropiado**: 100% o 90% para ver todo el contenido
3. **Resalta información importante** con flechas o cuadros rojos
4. **Minimiza información sensible**: Oculta tokens completos si es necesario
5. **Captura el código de respuesta**: Asegúrate de que se vea el "200 OK"
6. **Nombra los archivos**: Usa nombres descriptivos como:
   - `01-swagger-overview.png`
   - `02-login-response.png`
   - `03-authorize-modal.png`
   - etc.

---

## Orden Recomendado

1. ✅ Verificar servidor corriendo
2. ✅ Screenshot de Swagger UI completo
3. ✅ Login y obtener token
4. ✅ Autorizar en Swagger
5. ✅ Catálogo de tipos de baja (no requiere datos específicos)
6. ✅ Consultar estudiante por CURP/CCT
7. ✅ Consultar estudiante por ID
8. ✅ Descargar boleta actual
9. ✅ Descargar boleta histórica
10. ⚠️ Solicitud de baja (último, porque modifica datos)
11. ✅ Verificar tokens en DB
12. ✅ Prueba con cURL

---

## Credenciales de Prueba

**Usuario de prueba del portal** (necesitarás uno válido):
- Usuario: [tu_usuario]
- Password: [tu_password]

**Datos de estudiante de prueba** (según la API externa):
- CURP: AAPR160106HQTLRNA6
- CCT: 22DPR0200G
- ID Alumno: 863309

**API Externa USEBEQ**:
- Email: portalpadres@usebeq.edu.mx
- Password: pp4NUudeCQFo2
- (Estas credenciales se usan automáticamente por el backend)
