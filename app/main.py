import os
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Allow OAuth over HTTP in development (from .env: OAUTHLIB_INSECURE_TRANSPORT=1)
# This must be set BEFORE importing google oauth libraries
if os.getenv("OAUTHLIB_INSECURE_TRANSPORT") == "1":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api.endpoints import api_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add session middleware
# The secret key is used to sign the session cookie
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """
    Root endpoint
    """
    return {
        "message": "Portal USEBEQ API",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}


@app.get("/debug/config")
def debug_config():
    """
    Debug endpoint to check if environment variables are loaded correctly.
    Remove this in production after debugging!
    """
    import os
    return {
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "database_url_starts_with": os.getenv("DATABASE_URL", "NOT_SET")[:20] + "..." if os.getenv("DATABASE_URL") else "NOT_SET",
        "secret_key_set": bool(os.getenv("SECRET_KEY")),
        "mail_username_set": bool(os.getenv("MAIL_USERNAME")),
        "mail_server_set": bool(os.getenv("MAIL_SERVER")),
        "cors_origins": os.getenv("BACKEND_CORS_ORIGINS", "NOT_SET"),
        "settings_loaded": {
            "project_name": settings.PROJECT_NAME,
            "api_v1_str": settings.API_V1_STR,
            "database_url_loaded": bool(settings.DATABASE_URL) if hasattr(settings, 'DATABASE_URL') else False,
        },
        "all_env_vars_starting_with_db": [k for k in os.environ.keys() if "DB" in k.upper() or "DATABASE" in k.upper()],
    }


@app.get("/debug/db")
def debug_db():
    """
    Debug endpoint to test database connection.
    Remove this in production after debugging!
    """
    from app.core.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return {"status": "connected", "test_query": "SELECT 1 OK"}
    except Exception as e:
        return {"status": "error", "error": str(e), "error_type": type(e).__name__}


@app.post("/debug/register")
def debug_register():
    """
    Debug endpoint to test registration.
    Remove this in production after debugging!
    """
    from app.core.database import SessionLocal
    from app.models.user import User, UserStatus
    from app.core.security import get_password_hash
    import secrets
    import traceback

    db = SessionLocal()
    try:
        # Check if test user exists
        existing = db.query(User).filter(User.u_correo == "debug@test.com").first()
        if existing:
            db.delete(existing)
            db.commit()

        # Create test user
        user = User(
            u_correo="debug@test.com",
            u_pass=get_password_hash("test123456"),
            u_nombre="Debug",
            u_appat="User",
            u_apmat="Test",
            estatus=UserStatus.PENDIENTE,
            token_activacion=secrets.token_urlsafe(32)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "status": "success",
            "user_id": user.u_id,
            "email": user.u_correo,
            "estatus": user.estatus.value if user.estatus else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
    finally:
        db.close()
