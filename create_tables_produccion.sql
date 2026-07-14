-- =====================================================
-- Script de creacion de tablas para produccion
-- Portal USEBEQ - Base de datos MySQL
-- Fecha: 2026-07-14
-- =====================================================
-- INSTRUCCIONES:
-- Este script crea la base de datos DESDE CERO: incluye todas las
-- tablas que usa el portal, en orden de dependencias (PP_usuarios
-- primero porque pp_alumnos y PP_tramites la referencian).
-- 1. Hacer BACKUP si la base ya tiene datos
-- 2. Ejecutar el script completo de una sola vez
-- 3. Cada bloque usa IF NOT EXISTS: si una tabla ya existe se omite
--    sin error (no modifica tablas existentes)
-- NOTA: Los datos de alumnos (nombre, CCT, grado, calificaciones)
-- NO se guardan localmente; se consultan en vivo al API de USEBEQ.
-- Solo se guardan referencias (al_id / IdAlumno).
-- =====================================================

-- =====================================================
-- 1. TABLA: PP_usuarios
-- Uso: Cuentas de padres de familia del portal
-- Endpoint: POST /api/v1/auth/register, /api/v1/auth/login
-- =====================================================
CREATE TABLE IF NOT EXISTS PP_usuarios (
    u_id INT AUTO_INCREMENT PRIMARY KEY,
    u_correo VARCHAR(255) NOT NULL,
    u_pass VARCHAR(255) NULL COMMENT 'NULL para usuarios de Google',
    estatus ENUM('PENDIENTE', 'VALIDADO', 'INACTIVO') DEFAULT 'PENDIENTE',
    u_nombre VARCHAR(100) NOT NULL,
    u_appat VARCHAR(100) NOT NULL,
    u_apmat VARCHAR(100),
    u_tel VARCHAR(20),
    domicilio VARCHAR(255),
    sexo VARCHAR(1),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_validacion DATETIME NULL,
    token_activacion VARCHAR(255) NULL,
    google_id VARCHAR(255) NULL,
    google_refresh_token VARCHAR(512) NULL,
    UNIQUE KEY uk_correo (u_correo),
    UNIQUE KEY uk_google_id (google_id),
    INDEX idx_correo (u_correo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 2. TABLA: pp_alumnos
-- Uso: Vinculo padre-alumno (solo referencia al IdAlumno de USEBEQ)
-- Endpoint: POST /api/v1/students/link-student
-- =====================================================
-- NOTA: al_curp es la CURP capturada por el padre al registrar
-- (dato del usuario, no del API); permite vincular por CURP sola
-- cuando el alumno ya fue registrado por otro padre.
CREATE TABLE IF NOT EXISTS pp_alumnos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    al_id INT NOT NULL COMMENT 'IdAlumno del API de USEBEQ',
    al_curp VARCHAR(18) NULL COMMENT 'CURP capturada por el padre al registrar',
    u_id INT NOT NULL,
    relacion VARCHAR(20) COMMENT 'padre, madre, tutor',
    INDEX idx_al_id (al_id),
    INDEX idx_al_curp (al_curp),
    INDEX idx_u_id (u_id),
    CONSTRAINT fk_pp_alumnos_usuario FOREIGN KEY (u_id) REFERENCES PP_usuarios (u_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. TABLA: pp_hermanos
-- Uso: Relaciones de hermandad entre estudiantes confirmadas por el padre
-- Endpoint: POST /api/v1/students/confirm-sibling
-- =====================================================
CREATE TABLE IF NOT EXISTS pp_hermanos (
    h_id INT AUTO_INCREMENT PRIMARY KEY,
    al_id INT NOT NULL COMMENT 'ID del hermano mayor (IdAlumno USEBEQ)',
    her_id INT NOT NULL COMMENT 'ID del hermano menor (IdAlumno USEBEQ)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_al_id (al_id),
    INDEX idx_her_id (her_id),
    UNIQUE KEY uk_hermanos (al_id, her_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 4. TABLA: pp_token
-- Uso: Tokens de autenticacion del API externa de USEBEQ
-- =====================================================
CREATE TABLE IF NOT EXISTS pp_token (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(2000) NOT NULL,
    refresh_token VARCHAR(2000) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fecha_registro (fecha_registro DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 5. TABLA: pp_avisos
-- Uso: Avisos importantes para padres de familia
-- Endpoint: GET /api/v1/announcements/
-- =====================================================
CREATE TABLE IF NOT EXISTS pp_avisos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    contenido TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'info',
    imagen_url VARCHAR(500),
    activo TINYINT(1) DEFAULT 1,
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_fin DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 6. TABLA: PP_tramites
-- Uso: Tramites administrativos del padre (bajas, revocaciones, etc.)
-- =====================================================
CREATE TABLE IF NOT EXISTS PP_tramites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    al_id INT NULL COMMENT 'IdAlumno del API de USEBEQ',
    u_id INT NOT NULL,
    tipo_tramite VARCHAR(50) COMMENT 'BAJA, REVOCACION, DUPLICADO',
    folio VARCHAR(50),
    fecha_solicitud DATE,
    estatus VARCHAR(20) COMMENT 'PENDIENTE, EN_PROCESO, COMPLETADO',
    descripcion TEXT,
    documentos_adjuntos TEXT COMMENT 'JSON con URLs de documentos',
    UNIQUE KEY uk_folio (folio),
    INDEX idx_al_id (al_id),
    INDEX idx_folio (folio),
    CONSTRAINT fk_pp_tramites_usuario FOREIGN KEY (u_id) REFERENCES PP_usuarios (u_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 7. TABLA: tramites1
-- Uso: Solicitudes de duplicado de certificado
-- Endpoint: POST /api/v1/certificates/request
-- =====================================================
CREATE TABLE IF NOT EXISTS tramites1 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    folio VARCHAR(50) NOT NULL,
    nombre_alumno VARCHAR(100) NOT NULL,
    a_paterno VARCHAR(100) NOT NULL,
    a_materno VARCHAR(100),
    telefono VARCHAR(20),
    email VARCHAR(255),
    curp VARCHAR(18) NOT NULL,
    cct VARCHAR(20) NOT NULL,
    nombre_esc VARCHAR(255),
    dom_esc VARCHAR(255),
    turno VARCHAR(50),
    ciclo_terminacion VARCHAR(20) NOT NULL,
    tipo_tramite VARCHAR(50) NOT NULL,
    usuario VARCHAR(100),
    foto VARCHAR(255),
    zona VARCHAR(50),
    sector VARCHAR(50),
    fecha VARCHAR(20),
    fecha_elaborado DATE,
    status VARCHAR(50) DEFAULT 'SOLICITADO',
    entregado VARCHAR(20) DEFAULT 'PENDIENTE',
    region VARCHAR(10),
    correccion VARCHAR(5),
    core VARCHAR(255),
    tipo_escuela VARCHAR(50),
    grado VARCHAR(10),
    reprobo_materias VARCHAR(255),
    presento_extras_en VARCHAR(255),
    year_extras VARCHAR(10),
    estudio_siempre VARCHAR(255),
    nom_esc_ant VARCHAR(255),
    sexo VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_folio (folio),
    INDEX idx_curp (curp),
    INDEX idx_folio (folio),
    INDEX idx_status (status),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 8. TABLA: tramites_portal
-- Uso: Soluciones en linea (revalidacion, legalizacion, evaluacion)
-- Endpoint: POST /api/v1/tramites/solicitud
-- =====================================================
CREATE TABLE IF NOT EXISTS tramites_portal (
    id INT AUTO_INCREMENT PRIMARY KEY,
    folio VARCHAR(50) NOT NULL,
    nombre VARCHAR(100),
    a_paterno VARCHAR(100),
    a_materno VARCHAR(100),
    domicilio VARCHAR(255),
    nacionalidad VARCHAR(100),
    pais_estado VARCHAR(100),
    sexo VARCHAR(20),
    clave_deseo VARCHAR(20),
    revalida_nivel VARCHAR(100),
    correo VARCHAR(255),
    tel VARCHAR(20),
    solicitante VARCHAR(255),
    tipo_tramite VARCHAR(100),
    responsable VARCHAR(255),
    estatus VARCHAR(50) DEFAULT 'SOLICITADO',
    fecha VARCHAR(20),
    ruta_doc VARCHAR(255),
    core VARCHAR(255),
    curp VARCHAR(18),
    grado_cursado VARCHAR(50),
    doc_legaliza VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_folio (folio),
    INDEX idx_folio (folio),
    INDEX idx_estatus (estatus)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 9. TABLA: tramite_revocaciong
-- Uso: Solicitudes de revocacion de grado
-- Endpoint: POST /api/v1/tramites/revocacion
-- =====================================================
CREATE TABLE IF NOT EXISTS tramite_revocaciong (
    id INT AUTO_INCREMENT PRIMARY KEY,
    folio VARCHAR(50) NOT NULL,
    al_curp VARCHAR(18) NOT NULL,
    al_nombreComp VARCHAR(255),
    clavecct VARCHAR(20),
    nombre_cct VARCHAR(255),
    al_grado VARCHAR(10),
    al_grupo VARCHAR(10),
    turno VARCHAR(50),
    ciclo_escolar VARCHAR(20),
    motivo TEXT,
    nombre_padre VARCHAR(255),
    telefono VARCHAR(20),
    email VARCHAR(255),
    estatus VARCHAR(50) DEFAULT 'SOLICITADO',
    comentarios TEXT,
    fecha_solicitud DATETIME,
    usuario VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_folio (folio),
    INDEX idx_curp (al_curp),
    INDEX idx_folio (folio),
    INDEX idx_estatus (estatus)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 10. TABLA: tramite_baja
-- Uso: Solicitudes de baja por traslado
-- Endpoint: POST /api/v1/tramites/baja (futuro)
-- =====================================================
CREATE TABLE IF NOT EXISTS tramite_baja (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curp VARCHAR(18) NOT NULL,
    nombre VARCHAR(255),
    cct VARCHAR(20),
    nombre_cct VARCHAR(255),
    grado VARCHAR(10),
    grupo VARCHAR(10),
    dom_cct VARCHAR(255),
    nivel VARCHAR(50),
    correo VARCHAR(255),
    motivo TEXT,
    realiza VARCHAR(255),
    identi VARCHAR(255),
    acta VARCHAR(255),
    curpf VARCHAR(255),
    fecha_sol VARCHAR(20),
    estatus VARCHAR(50) DEFAULT 'SOLICITADO',
    usuario VARCHAR(255),
    tel VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_curp (curp),
    INDEX idx_estatus (estatus)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
SELECT 'PP_tramites', COUNT(*) FROM PP_tramites
UNION ALL
SELECT 'tramites1', COUNT(*) FROM tramites1
UNION ALL
SELECT 'tramites_portal', COUNT(*) FROM tramites_portal
UNION ALL
SELECT 'tramite_revocaciong', COUNT(*) FROM tramite_revocaciong
UNION ALL
SELECT 'tramite_baja', COUNT(*) FROM tramite_baja;
