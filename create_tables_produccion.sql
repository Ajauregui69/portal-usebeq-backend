-- =====================================================
-- Script de creacion de tablas para produccion
-- Portal USEBEQ - Base de datos MySQL
-- Fecha: 2026-02-13
-- =====================================================
-- INSTRUCCIONES:
-- 1. Hacer BACKUP de la base de datos antes de ejecutar
-- 2. Ejecutar en orden, cada bloque verifica si la tabla ya existe
-- 3. Si alguna tabla ya existe, el IF NOT EXISTS la omite sin error
-- =====================================================

-- =====================================================
-- 1. TABLA: tramite_revocaciong
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
-- 2. TABLA: tramites1
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
-- 3. TABLA: tramites_portal
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
-- 4. TABLA: tramite_baja
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
-- VERIFICACION: Confirmar que las tablas fueron creadas
-- =====================================================
SELECT 'tramite_revocaciong' AS tabla, COUNT(*) AS registros FROM tramite_revocaciong
UNION ALL
SELECT 'tramites1', COUNT(*) FROM tramites1
UNION ALL
SELECT 'tramites_portal', COUNT(*) FROM tramites_portal
UNION ALL
SELECT 'tramite_baja', COUNT(*) FROM tramite_baja
UNION ALL
SELECT 'pp_avisos', COUNT(*) FROM pp_avisos;
