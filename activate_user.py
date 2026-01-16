from sqlalchemy import create_engine, text
from datetime import datetime
import os

# Get database URL from environment or use default
db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://usebeq_user:usebeq_password_123@localhost/usebeq_portal?charset=utf8mb4')

# Create engine
engine = create_engine(db_url)

# Email to activate
email = 'alonso@email.com'

# Update user status
with engine.connect() as conn:
    # First, check if user exists
    result = conn.execute(
        text("SELECT u_id, u_correo, estatus FROM PP_usuarios WHERE u_correo = :email"),
        {"email": email}
    )
    user = result.fetchone()
    
    if user:
        print(f"Usuario encontrado: {user[1]}")
        print(f"Estatus actual: {user[2]}")
        
        # Update to VALIDADO
        conn.execute(
            text("""
                UPDATE PP_usuarios 
                SET estatus = 'VALIDADO', 
                    fecha_validacion = :fecha,
                    token_activacion = NULL
                WHERE u_correo = :email
            """),
            {"email": email, "fecha": datetime.now()}
        )
        conn.commit()
        
        print(f"✓ Usuario {email} activado exitosamente!")
        print(f"✓ Estatus cambiado a: VALIDADO")
        print(f"✓ Fecha de validacion: {datetime.now()}")
    else:
        print(f"✗ Usuario {email} no encontrado en la base de datos")
        print("Intenta registrarlo primero usando el endpoint /auth/register")

