import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import api_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

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
