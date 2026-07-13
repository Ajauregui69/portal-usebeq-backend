# Manual: Crear y Configurar Base de Datos MySQL

Este manual explica cómo crear la base de datos MySQL para el Portal USEBEQ, ya sea en Azure o en un servidor propio.

---

## Opción A: Azure Database for MySQL

### Paso 1: Crear el Servidor MySQL

1. Ir a [Azure Portal](https://portal.azure.com)
2. Click en **"Create a resource"**
3. Buscar **"Azure Database for MySQL"**
4. Seleccionar **"Flexible Server"** (recomendado)
5. Click en **"Create"**

### Configuración del Servidor

| Campo | Valor |
|-------|-------|
| Subscription | Tu suscripción |
| Resource group | `rg-portal-usebeq` |
| Server name | `usebeq-mysql-server` (debe ser único) |
| Region | `Mexico Central` |
| MySQL version | **8.0** |
| Workload type | **Development** (o Production según necesidad) |
| Compute + storage | **Burstable, B1ms** (desarrollo) |

### Autenticación

| Campo | Valor |
|-------|-------|
| Authentication method | **MySQL authentication only** |
| Admin username | `usebeq_admin` |
| Password | (crear password seguro, mínimo 8 caracteres) |

6. Click en **"Review + create"**
7. Click en **"Create"**

### Paso 2: Configurar Firewall

1. Ir al servidor MySQL creado
2. Click en **"Networking"** en el menú lateral
3. En **"Firewall rules"**:
   - Activar **"Allow public access from any Azure service"**
   - Click en **"+ Add current client IP address"** (para desarrollo)
4. Click en **"Save"**

### Paso 3: Crear la Base de Datos

1. En el servidor MySQL, click en **"Databases"**
2. Click en **"+ Add"**
3. Database name: `portal_usebeq`
4. Character set: `utf8mb4`
5. Collation: `utf8mb4_unicode_ci`
6. Click en **"Save"**

---

## Opción B: MySQL Local o Servidor Propio

### Instalar MySQL (Ubuntu/Debian)

```bash
# Instalar MySQL Server
sudo apt update
sudo apt install mysql-server

# Iniciar el servicio
sudo systemctl start mysql
sudo systemctl enable mysql

# Configurar seguridad
sudo mysql_secure_installation
```

### Instalar MySQL (Windows)

1. Descargar MySQL Installer desde https://dev.mysql.com/downloads/installer/
2. Ejecutar el instalador
3. Seleccionar "MySQL Server" y "MySQL Workbench"
4. Seguir el asistente de configuración

### Crear Base de Datos y Usuario

```sql
-- Conectar como root
mysql -u root -p

-- Crear base de datos
CREATE DATABASE portal_usebeq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario
CREATE USER 'usebeq_user'@'%' IDENTIFIED BY 'tu_password_seguro';

-- Dar permisos
GRANT ALL PRIVILEGES ON portal_usebeq.* TO 'usebeq_user'@'%';
FLUSH PRIVILEGES;

-- Verificar
SHOW DATABASES;
```

---

## Paso 4: Crear las Tablas

### Conectar a la Base de Datos

```bash
# Azure MySQL
mysql -h usebeq-mysql-server.mysql.database.azure.com -u usebeq_admin -p portal_usebeq

# MySQL Local
mysql -u usebeq_user -p portal_usebeq
```

### Script de Creación de Tablas

```sql
-- ============================================
-- PORTAL USEBEQ - Script de Base de Datos
-- ============================================

-- Usar la base de datos
USE portal_usebeq;

-- ============================================
-- Tabla: PP_usuarios (Usuarios/Padres de familia)
-- ============================================
CREATE TABLE IF NOT EXISTS PP_usuarios (
    u_id INT AUTO_INCREMENT PRIMARY KEY,
    u_correo VARCHAR(255) NOT NULL UNIQUE,
    u_pass VARCHAR(255) NULL,  -- NULL para usuarios de Google
    estatus ENUM('PENDIENTE', 'VALIDADO', 'INACTIVO') DEFAULT 'PENDIENTE',
    u_nombre VARCHAR(100) NOT NULL,
    u_appat VARCHAR(100) NOT NULL,
    u_apmat VARCHAR(100) NULL,
    u_tel VARCHAR(20) NULL,
    domicilio VARCHAR(255) NULL,
    sexo CHAR(1) NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_validacion DATETIME NULL,
    token_activacion VARCHAR(255) NULL,
    google_id VARCHAR(255) NULL UNIQUE,
    google_refresh_token TEXT NULL,

    INDEX idx_correo (u_correo),
    INDEX idx_google_id (google_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
CREATE TABLE IF NOT EXISTS pp_alumnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    al_id INT NOT NULL,  -- IdAlumno del API de USEBEQ
    al_curp VARCHAR(18) NULL,  -- CURP capturada por el padre al registrar (permite vincular por CURP sola)
    u_id INT NOT NULL,
    relacion VARCHAR(20) NULL,  -- padre, madre, tutor

    FOREIGN KEY (u_id) REFERENCES PP_usuarios(u_id) ON DELETE CASCADE,
    INDEX idx_al_curp (al_curp),
    INDEX idx_alumno (al_id),
    INDEX idx_usuario (u_id),
    UNIQUE KEY uk_alumno_usuario (al_id, u_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Tabla: pp_token (Tokens de API externa USEBEQ)
-- ============================================
CREATE TABLE IF NOT EXISTS pp_token (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- Verificar tablas creadas
-- ============================================
SHOW TABLES;
```

### Guardar Script

Guardar el script como `database_setup.sql` y ejecutarlo:

```bash
mysql -h host -u usuario -p nombre_bd < database_setup.sql
```

---

## Paso 5: Configurar Conexión en el Backend

### Cadena de Conexión

**Formato:**
```
mysql+pymysql://usuario:password@host:puerto/base_de_datos?charset=utf8mb4
```

**Azure MySQL:**
```
mysql+pymysql://usebeq_admin:TuPassword@usebeq-mysql-server.mysql.database.azure.com:3306/portal_usebeq?charset=utf8mb4
```

**MySQL Local:**
```
mysql+pymysql://usebeq_user:TuPassword@localhost:3306/portal_usebeq?charset=utf8mb4
```

### Configurar en .env (Desarrollo)

```env
DATABASE_URL=mysql+pymysql://usebeq_user:password123@localhost:3306/portal_usebeq?charset=utf8mb4
```

### Configurar en Azure (Producción)

En Azure Portal > Web App > Configuration:

| Name | Value |
|------|-------|
| `DATABASE_URL` | `mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4` |

---

## Paso 6: Crear Tablas Automáticamente con SQLAlchemy

El backend puede crear las tablas automáticamente si no existen.

### Opción 1: Crear al iniciar la app

Agregar en `app/main.py`:

```python
from app.core.database import engine, Base
from app.models import user, student, api_token  # Importar todos los modelos

# Crear tablas al iniciar (solo si no existen)
Base.metadata.create_all(bind=engine)
```

### Opción 2: Script de inicialización

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

### Error: "Access denied for user"

**Causa:** Usuario o contraseña incorrectos.

**Solución:**
```sql
-- Verificar usuarios
SELECT user, host FROM mysql.user;

-- Recrear usuario si es necesario
DROP USER 'usebeq_user'@'%';
CREATE USER 'usebeq_user'@'%' IDENTIFIED BY 'nuevo_password';
GRANT ALL PRIVILEGES ON portal_usebeq.* TO 'usebeq_user'@'%';
FLUSH PRIVILEGES;
```

### Error: "Can't connect to MySQL server"

**Causas posibles:**
1. MySQL no está corriendo
2. Firewall bloqueando conexión
3. Host incorrecto

**Soluciones:**
```bash
# Verificar que MySQL está corriendo
sudo systemctl status mysql

# Verificar puerto
netstat -tlnp | grep 3306

# Para Azure, verificar firewall en el portal
```

### Error: "Unknown column 'google_id'"

**Causa:** La tabla existe pero le faltan las columnas nuevas.

**Solución:**
```sql
ALTER TABLE PP_usuarios ADD COLUMN google_id VARCHAR(255) NULL UNIQUE;
ALTER TABLE PP_usuarios ADD COLUMN google_refresh_token TEXT NULL;
```

### Error: "Column 'u_pass' cannot be null"

**Causa:** La columna u_pass no permite NULL (necesario para usuarios de Google).

**Solución:**
```sql
ALTER TABLE PP_usuarios MODIFY COLUMN u_pass VARCHAR(255) NULL;
```

---

## Backup y Restauración

### Crear Backup

```bash
# Backup completo
mysqldump -h host -u usuario -p portal_usebeq > backup_portal_usebeq.sql

# Backup con fecha
mysqldump -h host -u usuario -p portal_usebeq > backup_$(date +%Y%m%d).sql
```

### Restaurar Backup

```bash
mysql -h host -u usuario -p portal_usebeq < backup_portal_usebeq.sql
```

---

## Costos Estimados (Azure)

| Tier | Costo Aproximado | Recursos |
|------|------------------|----------|
| Burstable B1ms | ~$12/mes | 1 vCore, 2GB RAM, 20GB storage |
| Burstable B2s | ~$25/mes | 2 vCores, 4GB RAM, 32GB storage |
| General Purpose | ~$50+/mes | Más recursos, alta disponibilidad |

**Nota:** Los precios pueden variar. Consultar [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/).
