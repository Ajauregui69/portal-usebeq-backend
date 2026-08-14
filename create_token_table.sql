-- Tabla para almacenar tokens de autenticación de la API externa de USEBEQ
-- SQL Server (Azure SQL Database)
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
