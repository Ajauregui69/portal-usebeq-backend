"""
Create all tables defined in the models directory.
"""
from app.core.database import engine, Base
from app.models import api_token, certificate, grade, student, user

def create_all_tables():
    """Create all tables"""
    print("Creating all tables...")
    # The magic happens here. SQLAlchemy looks at all classes that inherit
    # from Base and creates tables for them.
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully (if they didn't exist).")

if __name__ == "__main__":
    create_all_tables()
