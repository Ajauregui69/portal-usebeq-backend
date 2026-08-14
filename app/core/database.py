from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.core.config import settings


def get_clean_database_url(url: str) -> tuple[str, dict]:
    """
    Clean DATABASE_URL for the active driver and return connect_args.

    - MySQL (legacy, kept for local/dev fallback): Azure Database for MySQL
      adds ssl_mode to the URL, which pymysql doesn't accept as a URL
      parameter, so it's stripped out and turned into connect_args instead.
    - SQL Server (mssql+pymssql, Azure SQL Database): no cleanup needed.
      pymssql/FreeTDS negotiate TLS automatically with Azure SQL, so the
      URL is passed through as-is.
    """
    parsed = urlparse(url)

    if not parsed.scheme.startswith("mysql"):
        return url, {}

    query_params = parse_qs(parsed.query)

    # Check if ssl_mode is in the URL
    ssl_mode = query_params.pop('ssl_mode', [None])[0]

    # Rebuild URL without ssl_mode
    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    # Configure SSL for pymysql if needed
    connect_args = {}
    if ssl_mode and ssl_mode.lower() in ('require', 'required', 'verify-ca', 'verify-full'):
        connect_args['ssl'] = {'ssl': True}

    return clean_url, connect_args


# Get clean URL and SSL config
database_url, connect_args = get_clean_database_url(settings.DATABASE_URL)

# Create database engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=connect_args
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
