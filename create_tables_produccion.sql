-- =====================================================
-- Script de creacion de tablas para produccion
-- Portal USEBEQ - Base de datos SQL Server (Azure SQL Database)
-- Fecha: 2026-08-14
-- =====================================================
-- INSTRUCCIONES:
-- Este script crea la base de datos DESDE CERO: incluye todas las
-- tablas que usa el portal, en orden de dependencias (PP_usuarios
-- primero porque pp_alumnos y PP_tramites la referencian).
-- 1. Hacer BACKUP si la base ya tiene datos
-- 2. Ejecutar el script completo de una sola vez
-- 3. Cada bloque valida si la tabla ya existe (IF NOT EXISTS via
--    sys.tables); si ya existe se omite sin error (no modifica
--    tablas existentes)
-- NOTA: Los datos de alumnos (nombre, CCT, grado, calificaciones)
-- NO se guardan localmente; se consultan en vivo al API de USEBEQ.
-- Solo se guardan referencias (al_id / IdAlumno).
-- =====================================================

-- =====================================================
-- 1. TABLA: PP_usuarios
-- Uso: Cuentas de padres de familia del portal
-- Endpoint: POST /api/v1/auth/register, /api/v1/auth/login
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PP_usuarios')
BEGIN
    CREATE TABLE PP_usuarios (
        u_id INT IDENTITY(1,1) PRIMARY KEY,
        u_correo VARCHAR(255) NOT NULL,
        u_pass VARCHAR(255) NULL, -- NULL para usuarios de Google
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
    CREATE INDEX idx_correo ON PP_usuarios (u_correo);
END;

-- =====================================================
-- 2. TABLA: pp_alumnos
-- Uso: Vinculo padre-alumno (solo referencia al IdAlumno de USEBEQ)
-- Endpoint: POST /api/v1/students/link-student
-- =====================================================
-- NOTA: al_curp es la CURP capturada por el padre al registrar
-- (dato del usuario, no del API); permite vincular por CURP sola
-- cuando el alumno ya fue registrado por otro padre.
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pp_alumnos')
BEGIN
    CREATE TABLE pp_alumnos (
        id INT IDENTITY(1,1) PRIMARY KEY,
        al_id INT NOT NULL, -- IdAlumno del API de USEBEQ
        al_curp VARCHAR(18) NULL, -- CURP capturada por el padre al registrar
        u_id INT NOT NULL,
        relacion VARCHAR(20) NULL, -- padre, madre, tutor
        CONSTRAINT fk_pp_alumnos_usuario FOREIGN KEY (u_id) REFERENCES PP_usuarios (u_id)
    );
    CREATE INDEX idx_al_id ON pp_alumnos (al_id);
    CREATE INDEX idx_al_curp ON pp_alumnos (al_curp);
    CREATE INDEX idx_u_id ON pp_alumnos (u_id);
END;

-- =====================================================
-- 3. TABLA: pp_hermanos
-- Uso: Relaciones de hermandad entre estudiantes confirmadas por el padre
-- Endpoint: POST /api/v1/students/confirm-sibling
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pp_hermanos')
BEGIN
    CREATE TABLE pp_hermanos (
        h_id INT IDENTITY(1,1) PRIMARY KEY,
        al_id INT NOT NULL, -- ID del hermano mayor (IdAlumno USEBEQ)
        her_id INT NOT NULL, -- ID del hermano menor (IdAlumno USEBEQ)
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT uk_hermanos UNIQUE (al_id, her_id)
    );
    CREATE INDEX idx_al_id_hermanos ON pp_hermanos (al_id);
    CREATE INDEX idx_her_id ON pp_hermanos (her_id);
END;

-- =====================================================
-- 4. TABLA: pp_token
-- Uso: Tokens de autenticacion del API externa de USEBEQ
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pp_token')
BEGIN
    CREATE TABLE pp_token (
        id INT IDENTITY(1,1) PRIMARY KEY,
        token VARCHAR(2000) NOT NULL,
        refresh_token VARCHAR(2000) NOT NULL,
        fecha_registro DATETIME NOT NULL DEFAULT GETDATE()
    );
    CREATE INDEX idx_fecha_registro ON pp_token (fecha_registro DESC);
END;

-- =====================================================
-- 5. TABLA: pp_avisos
-- Uso: Avisos importantes para padres de familia
-- Endpoint: GET /api/v1/announcements/
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pp_avisos')
BEGIN
    CREATE TABLE pp_avisos (
        id INT IDENTITY(1,1) PRIMARY KEY,
        titulo VARCHAR(255) NOT NULL,
        contenido VARCHAR(MAX) NOT NULL,
        tipo VARCHAR(50) NOT NULL DEFAULT 'info',
        imagen_url VARCHAR(500) NULL,
        link_url VARCHAR(500) NULL, -- Destino al dar click en la imagen del aviso
        activo BIT NOT NULL DEFAULT 1,
        fecha_inicio DATETIME NOT NULL DEFAULT GETDATE(),
        fecha_fin DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME NOT NULL DEFAULT GETDATE()
    );
END;
GO

-- Trigger para simular ON UPDATE CURRENT_TIMESTAMP de MySQL en updated_at
IF NOT EXISTS (SELECT * FROM sys.triggers WHERE name = 'trg_pp_avisos_updated_at')
BEGIN
    EXEC('
        CREATE TRIGGER trg_pp_avisos_updated_at ON pp_avisos
        AFTER UPDATE AS
        BEGIN
            SET NOCOUNT ON;
            UPDATE pp_avisos
            SET updated_at = GETDATE()
            FROM pp_avisos a
            INNER JOIN inserted i ON a.id = i.id;
        END
    ');
END;
GO

-- =====================================================
-- 6. TABLA: PP_tramites
-- Uso: Tramites administrativos del padre (bajas, revocaciones, etc.)
-- =====================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PP_tramites')
BEGIN
    CREATE TABLE PP_tramites (
        id INT IDENTITY(1,1) PRIMARY KEY,
        al_id INT NULL, -- IdAlumno del API de USEBEQ
        u_id INT NOT NULL,
        tipo_tramite VARCHAR(50) NULL, -- BAJA, REVOCACION, DUPLICADO
        folio VARCHAR(50) NULL,
        fecha_solicitud DATE NULL,
        estatus VARCHAR(20) NULL, -- PENDIENTE, EN_PROCESO, COMPLETADO
        descripcion VARCHAR(MAX) NULL,
        documentos_adjuntos VARCHAR(MAX) NULL, -- JSON con URLs de documentos
        CONSTRAINT uk_folio UNIQUE (folio),
        CONSTRAINT fk_pp_tramites_usuario FOREIGN KEY (u_id) REFERENCES PP_usuarios (u_id)
    );
    CREATE INDEX idx_al_id_tramites ON PP_tramites (al_id);
    CREATE INDEX idx_folio ON PP_tramites (folio);
END;
GO

-- =====================================================
-- VERIFICACION: Confirmar que las tablas fueron creadas
-- =====================================================
SELECT 'PP_usuarios' AS tabla, COUNT(*) AS registros FROM PP_usuarios
UNION ALL
SELECT 'pp_alumnos', COUNT(*) FROM pp_alumnos
UNION ALL
SELECT 'pp_hermanos', COUNT(*) FROM pp_hermanos
UNION ALL
SELECT 'pp_token', COUNT(*) FROM pp_token
UNION ALL
SELECT 'pp_avisos', COUNT(*) FROM pp_avisos
UNION ALL
SELECT 'PP_tramites', COUNT(*) FROM PP_tramites;
