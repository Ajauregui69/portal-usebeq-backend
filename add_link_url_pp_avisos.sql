-- Migracion para bases EXISTENTES: agrega link_url a pp_avisos
-- (las bases creadas desde cero con create_tables_produccion.sql ya la incluyen)
-- SQL Server (Azure SQL Database). Ejecutar UNA sola vez; el bloque
-- IF NOT EXISTS evita el error de columna duplicada si ya se aplico.
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('pp_avisos') AND name = 'link_url'
)
BEGIN
    ALTER TABLE pp_avisos
        ADD link_url VARCHAR(500) NULL; -- Destino al dar click en la imagen del aviso
END;
