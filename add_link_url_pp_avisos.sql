-- Migracion para bases EXISTENTES: agrega link_url a pp_avisos
-- (las bases creadas desde cero con create_tables_produccion.sql ya la incluyen)
-- Ejecutar UNA sola vez; si la columna ya existe, MySQL marcara
-- "Duplicate column name" y se puede ignorar.
ALTER TABLE pp_avisos
    ADD COLUMN link_url VARCHAR(500) NULL COMMENT 'Destino al dar click en la imagen del aviso' AFTER imagen_url;
