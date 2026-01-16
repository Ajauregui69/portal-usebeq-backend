-- Tabla para almacenar tokens de autenticación de la API externa de USEBEQ
CREATE TABLE IF NOT EXISTS pp_token (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(2000) NOT NULL,
    refresh_token VARCHAR(2000) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fecha_registro (fecha_registro DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
