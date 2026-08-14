"""
Script to create pp_token table in the database
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def create_token_table():
    """Create pp_token table if it doesn't exist"""
    engine = create_engine(settings.DATABASE_URL)

    sql = """
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
    """

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✓ Tabla pp_token creada exitosamente")

if __name__ == "__main__":
    create_token_table()
