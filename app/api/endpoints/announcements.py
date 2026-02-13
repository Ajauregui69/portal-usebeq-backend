from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from pydantic import BaseModel

from app.core.database import get_db, Base
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

# Model
class Announcement(Base):
    __tablename__ = "pp_avisos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(255), nullable=False)
    contenido = Column(Text, nullable=False)
    tipo = Column(String(50), default="info")  # info, warning, urgent
    imagen_url = Column(String(500), nullable=True)
    activo = Column(Boolean, default=True)
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Schemas
class AnnouncementBase(BaseModel):
    titulo: str
    contenido: str
    tipo: str = "info"
    imagen_url: Optional[str] = None
    activo: bool = True
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementResponse(AnnouncementBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Endpoints
@router.get("/", response_model=List[AnnouncementResponse])
def get_announcements(db: Session = Depends(get_db)) -> Any:
    """Get all active announcements"""
    now = datetime.utcnow()
    announcements = db.query(Announcement).filter(
        Announcement.activo == True,
    ).order_by(Announcement.created_at.desc()).all()

    # Filter by date range in Python to avoid DB-specific date issues
    result = []
    for a in announcements:
        if a.fecha_fin and a.fecha_fin < now:
            continue
        result.append(a)

    return result

@router.get("/all", response_model=List[AnnouncementResponse])
def get_all_announcements(db: Session = Depends(get_db)) -> Any:
    """Get all announcements (including inactive) - for admin"""
    return db.query(Announcement).order_by(Announcement.created_at.desc()).all()

@router.post("/", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    announcement: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create a new announcement"""
    db_announcement = Announcement(
        titulo=announcement.titulo,
        contenido=announcement.contenido,
        tipo=announcement.tipo,
        imagen_url=announcement.imagen_url,
        activo=announcement.activo,
        fecha_inicio=announcement.fecha_inicio or datetime.utcnow(),
        fecha_fin=announcement.fecha_fin,
    )
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return db_announcement

@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    announcement: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Update an announcement"""
    db_announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not db_announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviso no encontrado")

    for key, value in announcement.model_dump().items():
        setattr(db_announcement, key, value)
    db_announcement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_announcement)
    return db_announcement

@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Delete an announcement"""
    db_announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not db_announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviso no encontrado")
    db.delete(db_announcement)
    db.commit()
    return {"message": "Aviso eliminado correctamente"}
