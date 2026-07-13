from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.services.usebeq_api_service import USEBEQAPIService

router = APIRouter()

# ========== SCHEMAS ==========

class TramiteRequest(BaseModel):
    curp: str
    nombre_alumno: str
    a_paterno: str
    a_materno: Optional[str] = None
    cct: str
    nombre_escuela: str
    grado: str
    grupo: str
    turno: str
    ciclo_escolar: str
    tipo_tramite: str
    descripcion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

class TramiteResponse(BaseModel):
    success: bool
    message: str
    folio: Optional[str] = None
    data: Optional[dict] = None

class TramiteStatusResponse(BaseModel):
    folio: str
    curp: str
    nombre: Optional[str] = None
    tipo_tramite: str
    estatus: str
    comentarios: Optional[str] = None
    fecha_solicitud: Optional[str] = None

class RevocacionRequest(BaseModel):
    curp: str
    nombre_alumno: str
    a_paterno: str
    a_materno: Optional[str] = None
    cct: str
    nombre_escuela: str
    grado: str
    grupo: str
    turno: str
    ciclo_escolar: str
    motivo: str
    nombre_padre: str
    telefono: str
    email: str

class RevocacionStatusResponse(BaseModel):
    folio: str
    curp: str
    nombre: Optional[str] = None
    estatus: str
    comentarios: Optional[str] = None
    fecha_solicitud: Optional[str] = None

# ========== SOLUCIONES EN LINEA ==========

@router.post("/solicitud", response_model=TramiteResponse)
async def crear_solicitud(
    solicitud: TramiteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create a new online request (solicitud en linea)"""
    # Generate folio
    year = datetime.now().year
    query_count = text("SELECT COUNT(*) FROM PP_tramites WHERE YEAR(fecha_solicitud) = :year")
    result = db.execute(query_count, {"year": year}).fetchone()
    count = (result[0] if result else 0) + 1
    folio = f"SOL-{year}-{count:05d}"

    # Resolve the student ID through the USEBEQ API (no local student tables)
    al_id = None
    try:
        estudiante = await USEBEQAPIService(db).get_estudiante_by_curp_cct(
            solicitud.curp.strip().upper(), solicitud.cct.strip().upper()
        )
        al_id = estudiante.IdAlumno
    except Exception:
        al_id = None

    # Insert into PP_tramites
    insert_query = text("""
        INSERT INTO PP_tramites (al_id, u_id, tipo_tramite, folio, fecha_solicitud, estatus, descripcion)
        VALUES (:al_id, :u_id, :tipo_tramite, :folio, :fecha, :estatus, :descripcion)
    """)

    a_materno = solicitud.a_materno or ""
    desc_detalle = solicitud.descripcion or "N/A"
    tel_val = solicitud.telefono or "N/A"
    email_val = solicitud.email or "N/A"
    descripcion_full = (
        f"Alumno: {solicitud.nombre_alumno} {solicitud.a_paterno} {a_materno} "
        f"| CCT: {solicitud.cct} | Grado: {solicitud.grado} "
        f"| Grupo: {solicitud.grupo} | Turno: {solicitud.turno} "
        f"| Ciclo: {solicitud.ciclo_escolar} | Detalle: {desc_detalle} "
        f"| Tel: {tel_val} | Email: {email_val}"
    )

    try:
        db.execute(insert_query, {
            "al_id": al_id,
            "u_id": current_user.u_id,
            "tipo_tramite": solicitud.tipo_tramite,
            "folio": folio,
            "fecha": datetime.now(),
            "estatus": "SOLICITADO",
            "descripcion": descripcion_full
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear solicitud: {str(e)}")

    return TramiteResponse(
        success=True,
        message="Solicitud registrada exitosamente. Consulta el estatus con tu folio.",
        folio=folio,
        data={"tipo_tramite": solicitud.tipo_tramite, "nombre": f"{solicitud.nombre_alumno} {solicitud.a_paterno}"}
    )

async def _student_curp_nombre(db: Session, al_id: Optional[int]) -> tuple:
    """Resolve CURP and full name from the USEBEQ API; empty values on failure."""
    if not al_id:
        return "", None
    try:
        estudiante = await USEBEQAPIService(db).get_estudiante_by_id(al_id)
        nombre = f"{estudiante.Nombre} {estudiante.ApellidoPaterno} {estudiante.ApellidoMaterno or ''}".strip()
        return estudiante.CURP or "", nombre
    except Exception:
        return "", None

@router.get("/solicitud/estatus/{folio}", response_model=TramiteStatusResponse)
async def consultar_estatus_solicitud(
    folio: str,
    db: Session = Depends(get_db),
) -> Any:
    """Check the status of an online request"""
    query = text("""
        SELECT t.folio, t.tipo_tramite, t.estatus, t.descripcion, t.fecha_solicitud, t.al_id
        FROM PP_tramites t
        WHERE t.folio = :folio
    """)
    result = db.execute(query, {"folio": folio.upper()}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="No se encontró solicitud con este folio")

    curp, nombre = await _student_curp_nombre(db, result[5])

    return TramiteStatusResponse(
        folio=result[0],
        curp=curp,
        nombre=nombre,
        tipo_tramite=result[1] or "",
        estatus=result[2] or "",
        comentarios=result[3],
        fecha_solicitud=str(result[4]) if result[4] else None
    )

@router.get("/solicitudes/mis-tramites", response_model=List[TramiteStatusResponse])
async def mis_tramites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get all requests for current user"""
    query = text("""
        SELECT t.folio, t.tipo_tramite, t.estatus, t.descripcion, t.fecha_solicitud, t.al_id
        FROM PP_tramites t
        WHERE t.u_id = :u_id
        ORDER BY t.fecha_solicitud DESC
    """)
    results = db.execute(query, {"u_id": current_user.u_id}).fetchall()

    tramites = []
    for r in results:
        curp, nombre = await _student_curp_nombre(db, r[5])
        tramites.append(TramiteStatusResponse(
            folio=r[0], curp=curp, nombre=nombre,
            tipo_tramite=r[1] or "", estatus=r[2] or "",
            comentarios=r[3], fecha_solicitud=str(r[4]) if r[4] else None
        ))
    return tramites

# ========== REVOCACION DE GRADO ==========

@router.post("/revocacion", response_model=TramiteResponse)
def solicitar_revocacion(
    solicitud: RevocacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Request grade revocation (revocacion de grado)"""
    curp = solicitud.curp.strip().upper()

    # Generate folio
    year = datetime.now().year
    folio = f"RE{str(year)[2:]}-{curp[:4]}-{datetime.now().strftime('%H%M%S')}"

    # Check for existing request
    check_query = text("""
        SELECT folio, estatus FROM tramite_revocaciong
        WHERE al_curp = :curp AND ciclo_escolar = :ciclo AND estatus = 'SOLICITADO'
    """)
    existing = db.execute(check_query, {"curp": curp, "ciclo": solicitud.ciclo_escolar}).fetchone()

    if existing:
        return TramiteResponse(
            success=False,
            message=f"Ya existe una solicitud de revocación en proceso con folio: {existing[0]}",
            folio=existing[0]
        )

    # Insert revocation request
    insert_query = text("""
        INSERT INTO tramite_revocaciong
        (folio, al_curp, al_nombreComp, clavecct, nombre_cct, al_grado, al_grupo, turno,
         ciclo_escolar, motivo, nombre_padre, telefono, email, estatus, fecha_solicitud, usuario)
        VALUES (:folio, :curp, :nombre, :cct, :nombre_esc, :grado, :grupo, :turno,
                :ciclo, :motivo, :nombre_padre, :tel, :email, 'SOLICITADO', :fecha, :usuario)
    """)

    nombre_completo = f"{solicitud.nombre_alumno} {solicitud.a_paterno} {solicitud.a_materno or ''}".strip()

    try:
        db.execute(insert_query, {
            "folio": folio,
            "curp": curp,
            "nombre": nombre_completo,
            "cct": solicitud.cct,
            "nombre_esc": solicitud.nombre_escuela,
            "grado": solicitud.grado,
            "grupo": solicitud.grupo,
            "turno": solicitud.turno,
            "ciclo": solicitud.ciclo_escolar,
            "motivo": solicitud.motivo,
            "nombre_padre": solicitud.nombre_padre,
            "tel": solicitud.telefono,
            "email": solicitud.email,
            "fecha": datetime.now(),
            "usuario": current_user.u_correo
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar solicitud: {str(e)}")

    return TramiteResponse(
        success=True,
        message="Solicitud de revocación registrada exitosamente. Consulta el estatus con tu folio. NOTA: La revocación de grado es un proceso irreversible.",
        folio=folio,
        data={"nombre": f"{solicitud.nombre_alumno} {solicitud.a_paterno}", "grado": solicitud.grado}
    )

@router.get("/revocacion/estatus/{folio}", response_model=RevocacionStatusResponse)
def consultar_estatus_revocacion(folio: str, db: Session = Depends(get_db)) -> Any:
    """Check the status of a grade revocation request"""
    query = text("""
        SELECT folio, al_curp, al_nombreComp, estatus, comentarios, fecha_solicitud
        FROM tramite_revocaciong
        WHERE folio = :folio
    """)
    result = db.execute(query, {"folio": folio}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="No se encontró solicitud con este folio")

    return RevocacionStatusResponse(
        folio=result[0], curp=result[1], nombre=result[2],
        estatus=result[3] or "", comentarios=result[4],
        fecha_solicitud=str(result[5]) if result[5] else None
    )

@router.get("/revocacion/mis-solicitudes", response_model=List[RevocacionStatusResponse])
def mis_revocaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get all revocation requests for current user"""
    query = text("""
        SELECT folio, al_curp, al_nombreComp, estatus, comentarios, fecha_solicitud
        FROM tramite_revocaciong
        WHERE usuario = :usuario
        ORDER BY fecha_solicitud DESC
    """)
    results = db.execute(query, {"usuario": current_user.u_correo}).fetchall()

    return [
        RevocacionStatusResponse(
            folio=r[0], curp=r[1], nombre=r[2],
            estatus=r[3] or "", comentarios=r[4],
            fecha_solicitud=str(r[5]) if r[5] else None
        ) for r in results
    ]

# ========== TYPES CATALOG ==========

@router.get("/tipos-tramite")
def get_tipos_tramite() -> Any:
    """Get available request types"""
    return [
        {"id": "CORRECCION_DATOS", "nombre": "Corrección de datos", "descripcion": "Solicitud de corrección de datos personales del alumno"},
        {"id": "CAMBIO_TURNO", "nombre": "Cambio de turno", "descripcion": "Solicitud de cambio de turno escolar"},
        {"id": "CONSTANCIA_ESTUDIOS", "nombre": "Constancia de estudios", "descripcion": "Solicitud de constancia de estudios vigente"},
        {"id": "CAMBIO_GRUPO", "nombre": "Cambio de grupo", "descripcion": "Solicitud de cambio de grupo"},
        {"id": "OTRO", "nombre": "Otro trámite", "descripcion": "Otro tipo de solicitud o trámite administrativo"},
    ]
