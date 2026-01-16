from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class APIToken(Base):
    """
    Model to store external API tokens (USEBEQ API)
    """
    __tablename__ = "pp_token"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(2000), nullable=False)
    refresh_token = Column(String(2000), nullable=False)
    fecha_registro = Column(DateTime, nullable=False, server_default=func.now())
