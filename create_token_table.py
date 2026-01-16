"""
Script to create pp_token table in the database
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def create_token_table():
    """Create pp_token table if it doesn't exist"""
    engine = create_engine(settings.DATABASE_URL)

    sql = """
    CREATE TABLE IF NOT EXISTS pp_token (
        id INT AUTO_INCREMENT PRIMARY KEY,
        token VARCHAR(2000) NOT NULL,
        refresh_token VARCHAR(2000) NOT NULL,
        fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_fecha_registro (fecha_registro DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✓ Tabla pp_token creada exitosamente")

if __name__ == "__main__":
    create_token_table()
