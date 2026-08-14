# Manual: Crear y Configurar Base de Datos SQL Server

Este manual explica cómo crear la base de datos SQL Server para el Portal USEBEQ, ya sea en Azure SQL Database o en un servidor propio. Reemplaza al manual anterior de MySQL.

---

## Opción A: Azure SQL Database

### Paso 1: Crear el Servidor SQL Server

1. Ir a [Azure Portal](https://portal.azure.com)
2. Click en **"Create a resource"**
3. Buscar **"SQL Database"**
4. Click en **"Create"**

### Configuración del Servidor

| Campo | Valor |
|-------|-------|
| Subscription | Tu suscripción |
| Resource group | `rg-portal-usebeq` |
| Database name | `portal_usebeq` |
| Server | Crear nuevo: `usebeq-sql-server` (debe ser único) |
| Region | `Mexico Central` (o la más cercana disponible) |
| Want to use SQL elastic pool | No |
| Compute + storage | **General Purpose - Serverless** o **Basic** (desarrollo) |

### Autenticación del servidor

| Campo | Valor |
|-------|-------|
| Authentication method | **Use SQL authentication** |
| Server admin login | `usebeq_admin` |
| Password | (crear password seguro, mínimo 8 caracteres, con mayúsculas/minúsculas/números/símbolos) |

5. Click en **"Review + create"**
6. Click en **"Create"**

### Paso 2: Configurar Firewall

1. Ir al servidor SQL creado (no a la base de datos, al **server**)
2. Click en **"Networking"** en el menú lateral
3. En **"Firewall rules"**:
   - Activar **"Allow Azure services and resources to access this server"** (necesario para que el Web App se conecte)
   - Click en **"+ Add current client IP address"** (para administrar desde tu máquina)
4. Click en **"Save"**

Azure SQL Database exige conexión cifrada (TLS) siempre; no hay opción de desactivarla.

---

## Opción B: SQL Server Local o Servidor Propio

### Instalar SQL Server (Ubuntu/Debian)

```bash
# Importar la llave y el repositorio de Microsoft
sudo apt update
sudo curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
sudo curl -fsSL https://packages.microsoft.com/config/ubuntu/22.04/mssql-server-2022.list | sudo tee /etc/apt/sources.list.d/mssql-server-2022.list

# Instalar SQL Server
sudo apt update
sudo apt install -y mssql-server
sudo /opt/mssql/bin/mssql-conf setup

# Iniciar el servicio
sudo systemctl start mssql-server
sudo systemctl enable mssql-server

# Instalar herramientas de línea de comandos (sqlcmd)
sudo apt install -y mssql-tools18 unixodbc-dev
```

### Instalar SQL Server (Windows)

1. Descargar SQL Server Developer/Express desde https://www.microsoft.com/sql-server/sql-server-downloads
2. Ejecutar el instalador
3. Seleccionar instalación **"Basic"** o **"Custom"**
4. Instalar también **SQL Server Management Studio (SSMS)** para administración

### Crear Base de Datos y Usuario

```sql
-- Conectar con sqlcmd o SSMS como administrador
sqlcmd -S localhost -U sa -P 'TuPasswordSA'

-- Crear base de datos
CREATE DATABASE portal_usebeq;
GO

-- Crear login y usuario
CREATE LOGIN usebeq_user WITH PASSWORD = 'tu_password_seguro';
GO
USE portal_usebeq;
GO
CREATE USER usebeq_user FOR LOGIN usebeq_user;
GO

-- Dar permisos
ALTER ROLE db_owner ADD MEMBER usebeq_user;
GO

-- Verificar
SELECT name FROM sys.databases;
GO
```

---

## Paso 4: Crear las Tablas

### Conectar a la Base de Datos

```bash
# Azure SQL Database
sqlcmd -S usebeq-sql-server.database.windows.net -d portal_usebeq -U usebeq_admin -P 'TuPassword'

# SQL Server Local
sqlcmd -S localhost -d portal_usebeq -U usebeq_user -P 'TuPassword'
```

### Script de Creación de Tablas

El script completo y actualizado vive en `create_tables_produccion.sql` (raíz del repo). Ejecutarlo con:

```bash
sqlcmd -S <host> -d portal_usebeq -U <usuario> -P '<password>' -i create_tables_produccion.sql
```

Resumen de lo que crea (ver el archivo para el detalle completo, incluyendo índices y constraints):

```sql
-- ============================================
-- Tabla: PP_usuarios (Usuarios/Padres de familia)
-- ============================================
CREATE TABLE PP_usuarios (
    u_id INT IDENTITY(1,1) PRIMARY KEY,
    u_correo VARCHAR(255) NOT NULL,
    u_pass VARCHAR(255) NULL,  -- NULL para usuarios de Google
    estatus VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
        CONSTRAINT ck_usuarios_estatus CHECK (estatus IN ('PENDIENTE', 'VALIDADO', 'INACTIVO')),
    u_nombre VARCHAR(100) NOT NULL,
    u_appat VARCHAR(100) NOT NULL,
    u_apmat VARCHAR(100) NULL,
    u_tel VARCHAR(20) NULL,
    domicilio VARCHAR(255) NULL,
    sexo VARCHAR(1) NULL,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE(),
    fecha_validacion DATETIME NULL,
    token_activacion VARCHAR(255) NULL,
    google_id VARCHAR(255) NULL,
    google_refresh_token VARCHAR(512) NULL,
    CONSTRAINT uk_correo UNIQUE (u_correo),
    CONSTRAINT uk_google_id UNIQUE (google_id)
);

-- ============================================
-- NOTA IMPORTANTE: Los datos de alumnos (nombre, CURP, matrícula,
-- calificaciones, certificados) viven en el sistema de USEBEQ y se
-- consultan en vivo a través de su API externa. NO se crean tablas
-- espejo SCE00x en esta base de datos; solo se guarda el IdAlumno
-- (al_id) como referencia en las tablas locales.
-- ============================================

-- ============================================
-- Tabla: pp_alumnos (Relación Padre-Alumno)
-- ============================================
CREATE TABLE pp_alumnos (
    id INT IDENTITY(1,1) PRIMARY KEY,
    al_id INT NOT NULL,  -- IdAlumno del API de USEBEQ
    al_curp VARCHAR(18) NULL,  -- CURP capturada por el padre al registrar
    u_id INT NOT NULL,
    relacion VARCHAR(20) NULL,  -- padre, madre, tutor
    CONSTRAINT fk_pp_alumnos_usuario FOREIGN KEY (u_id) REFERENCES PP_usuarios (u_id)
);

-- ============================================
-- Tabla: pp_token (Tokens de API externa USEBEQ)
-- ============================================
CREATE TABLE pp_token (
    id INT IDENTITY(1,1) PRIMARY KEY,
    token VARCHAR(2000) NOT NULL,
    refresh_token VARCHAR(2000) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT GETDATE()
);

-- ============================================
-- Verificar tablas creadas
-- ============================================
SELECT name FROM sys.tables;
```

---

## Paso 5: Configurar Conexión en el Backend

El backend usa el driver `pymssql` (paquete Python puro, no requiere instalar el ODBC Driver de Microsoft a nivel de sistema operativo, lo que simplifica el despliegue en Azure App Service Linux).

### Cadena de Conexión

**Formato:**
```
mssql+pymssql://usuario:password@host:puerto/base_de_datos
```

**Azure SQL Database:**
```
mssql+pymssql://usebeq_admin:TuPassword@usebeq-sql-server.database.windows.net:1433/portal_usebeq
```

**SQL Server Local:**
```
mssql+pymssql://usebeq_user:TuPassword@localhost:1433/portal_usebeq
```

### Configurar en .env (Desarrollo)

```env
DATABASE_URL=mssql+pymssql://usebeq_user:password123@localhost:1433/portal_usebeq
```

### Configurar en Azure (Producción)

En Azure Portal > Web App > Configuration > Application settings:

| Name | Value |
|------|-------|
| `DATABASE_URL` | `mssql+pymssql://usuario:password@host:1433/portal_usebeq` |

---

## Paso 6: Crear Tablas Automáticamente con SQLAlchemy

El backend puede crear las tablas automáticamente si no existen (útil para ambientes de prueba; en producción se recomienda ejecutar `create_tables_produccion.sql` directamente para tener control total del DDL).

### Script de inicialización

Crear archivo `init_db.py`:

```python
from app.core.database import engine, Base
from app.models import user, student, api_token

def init_database():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_database()
```

Ejecutar:
```bash
python init_db.py
```

---

## Diagrama de la Base de Datos

```
┌─────────────────────┐
│     PP_usuarios     │
├─────────────────────┤
│ u_id (PK)           │
│ u_correo            │
│ u_pass              │
│ estatus             │
│ u_nombre            │
│ u_appat             │
│ u_apmat             │
│ u_tel               │
│ domicilio           │
│ sexo                │
│ fecha_registro      │
│ fecha_validacion    │
│ token_activacion    │
│ google_id           │
│ google_refresh_token│
└─────────┬───────────┘
          │
          │ 1:N
          ▼
┌─────────────────────┐
│     pp_alumnos      │
├─────────────────────┤
│ id (PK)             │
│ al_id ──────────────┼──► IdAlumno en el API de USEBEQ
│ u_id (FK)           │    (datos del alumno consultados en vivo,
│ relacion            │     no se almacenan localmente)
└─────────────────────┘

┌─────────────────────┐
│     pp_token        │
├─────────────────────┤
│ id (PK)             │
│ token               │
│ refresh_token       │
│ fecha_registro      │
└─────────────────────┘
```

---

## Datos de Prueba

### Insertar Usuario de Prueba

```sql
INSERT INTO PP_usuarios (u_correo, u_pass, estatus, u_nombre, u_appat, u_apmat)
VALUES (
    'prueba@usebeq.edu.mx',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5k6YQvU3E5Ifi',  -- password: test123456
    'VALIDADO',
    'Usuario',
    'De Prueba',
    'Test'
);
```

### Vincular Alumno con Usuario

Los datos del alumno viven en el API de USEBEQ; solo se guarda el IdAlumno:

```sql
-- al_id debe ser un IdAlumno válido del API de USEBEQ
INSERT INTO pp_alumnos (al_id, u_id, relacion)
VALUES (863309, 1, 'padre');
```

---

## Solución de Problemas

### Error: "Login failed for user"

**Causa:** Usuario o contraseña incorrectos.

**Solución:**
```sql
-- Verificar logins existentes (ejecutar en la base master)
SELECT name FROM sys.sql_logins;

-- Recrear usuario si es necesario
DROP LOGIN usebeq_user;
CREATE LOGIN usebeq_user WITH PASSWORD = 'nuevo_password';
USE portal_usebeq;
CREATE USER usebeq_user FOR LOGIN usebeq_user;
ALTER ROLE db_owner ADD MEMBER usebeq_user;
```

### Error: "Cannot connect" / "Adaptive Server connection failed"

**Causas posibles:**
1. SQL Server no está corriendo
2. Firewall de Azure SQL bloqueando la IP de origen
3. Host o puerto incorrecto (Azure SQL siempre usa el puerto 1433)

**Soluciones:**
```bash
# Verificar que el servicio local está corriendo
sudo systemctl status mssql-server

# Verificar puerto
netstat -tlnp | grep 1433

# Para Azure SQL, revisar Networking > Firewall rules en el portal
# y confirmar que "Allow Azure services..." está activado si el
# Web App necesita conectarse
```

### Error: "Invalid column name 'google_id'"

**Causa:** La tabla existe pero le faltan las columnas nuevas.

**Solución:**
```sql
ALTER TABLE PP_usuarios ADD google_id VARCHAR(255) NULL;
ALTER TABLE PP_usuarios ADD google_refresh_token VARCHAR(512) NULL;
GO
ALTER TABLE PP_usuarios ADD CONSTRAINT uk_google_id UNIQUE (google_id);
GO
```

### Error: "Cannot insert the value NULL into column 'u_pass'"

**Causa:** La columna u_pass no permite NULL (necesario para usuarios de Google).

**Solución:**
```sql
ALTER TABLE PP_usuarios ALTER COLUMN u_pass VARCHAR(255) NULL;
```

---

## Backup y Restauración

### Crear Backup (Azure SQL Database)

Azure SQL Database hace backups automáticos (point-in-time restore) sin configuración adicional. Para un backup manual exportable:

1. Ir al recurso de la base de datos en Azure Portal
2. Click en **"Export"** en la barra superior
3. Guardar como archivo `.bacpac` en un Storage Account

### Restaurar Backup

1. Ir al servidor SQL en Azure Portal
2. Click en **"Import database"**
3. Seleccionar el archivo `.bacpac`

### Backup con sqlcmd/sqlpackage (servidor propio)

```bash
# Backup completo
sqlcmd -S host -U usuario -P 'password' -Q "BACKUP DATABASE portal_usebeq TO DISK = '/var/opt/mssql/backup/portal_usebeq.bak'"

# Restaurar
sqlcmd -S host -U usuario -P 'password' -Q "RESTORE DATABASE portal_usebeq FROM DISK = '/var/opt/mssql/backup/portal_usebeq.bak'"
```

---

## Costos Estimados (Azure SQL Database)

| Tier | Costo Aproximado | Recursos |
|------|------------------|----------|
| Serverless (General Purpose) | ~$5-15/mes (pausa cuando no hay uso) | Hasta 2 vCores, auto-pausa |
| Basic | ~$5/mes | 5 DTUs, 2GB storage |
| Standard S0 | ~$15/mes | 10 DTUs, 250GB storage |

**Nota:** Los precios pueden variar. Consultar [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/).
