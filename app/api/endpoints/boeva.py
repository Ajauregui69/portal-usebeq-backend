"""
BOEVA - Document Authenticity Verification
Verifies student documents by folio number, matching PHP portal's boeva.php
"""
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db

router = APIRouter()


class BoevaRequest(BaseModel):
    folio: str


class BoevaResponse(BaseModel):
    found: bool
    folio: Optional[str] = None
    nombre: Optional[str] = None
    curp: Optional[str] = None
    estatus: Optional[str] = None
    estatus_descripcion: Optional[str] = None
    message: Optional[str] = None


def get_estatus_descripcion(estatus: str) -> str:
    mapping = {
        'I': 'Inscrito',
        'B': 'Dado de Baja',
        'A': 'Inscrito con adeudo de materias',
        'E': 'Egresado',
    }
    return mapping.get(estatus.strip() if estatus else '', 'Desconocido')


@router.post("/verificar", response_model=BoevaResponse)
def verificar_documento(
    request: BoevaRequest,
    db: Session = Depends(get_db),
):
    """
    Verify document authenticity by folio number.
    Extracts student ID from folio and queries SCE004.
    """
    folio = request.folio.strip()

    if not folio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El folio es requerido"
        )

    # Extract student ID from folio (last 6-7 chars like PHP does)
    cad = folio[-7:]
    if cad[0] == '0':
        student_id = cad[-6:]
    else:
        student_id = cad

    try:
        student_id_int = int(student_id)
    except ValueError:
        return BoevaResponse(
            found=False,
            message="No se ha encontrado información con el folio ingresado, por favor revise la información proporcionada e intente nuevamente."
        )

    query = text("""
        SELECT al_appat, al_apmat, al_nombre, al_curp, al_estatus
        FROM SCE004
        WHERE al_id = :al_id
    """)

    result = db.execute(query, {"al_id": student_id_int}).fetchone()

    if not result:
        return BoevaResponse(
            found=False,
            message="No se ha encontrado información con el folio ingresado, por favor revise la información proporcionada e intente nuevamente."
        )

    nombre_completo = f"{result[2]} {result[0]} {result[1]}".strip()
    estatus = result[4].strip() if result[4] else ''

    generated_folio = f"BE22200{student_id_int}"

    return BoevaResponse(
        found=True,
        folio=generated_folio,
        nombre=nombre_completo,
        curp=result[3],
        estatus=estatus,
        estatus_descripcion=get_estatus_descripcion(estatus),
        message=f"La lectura del código vincula al educando {nombre_completo} con CURP {result[3]}, "
                f"como alumno(a) acreedor(a) del documento con folio: {generated_folio}."
    )


@router.get("/verificar/{encoded_id}")
def verificar_por_qr(
    encoded_id: str,
    db: Session = Depends(get_db),
):
    """
    Verify document by QR code (base64 encoded student ID).
    """
    try:
        decoded = base64.b64decode(encoded_id).decode('utf-8')
        student_id = int(decoded)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código QR inválido"
        )

    query = text("""
        SELECT al_appat, al_apmat, al_nombre, al_curp, al_estatus
        FROM SCE004
        WHERE al_id = :al_id
    """)

    result = db.execute(query, {"al_id": student_id}).fetchone()

    if not result:
        return BoevaResponse(
            found=False,
            message="No se encontró información para el código proporcionado."
        )

    nombre_completo = f"{result[2]} {result[0]} {result[1]}".strip()
    estatus = result[4].strip() if result[4] else ''
    generated_folio = f"BE22200{student_id}"

    return BoevaResponse(
        found=True,
        folio=generated_folio,
        nombre=nombre_completo,
        curp=result[3],
        estatus=estatus,
        estatus_descripcion=get_estatus_descripcion(estatus),
        message=f"La lectura del código QR vincula al educando {nombre_completo} con CURP {result[3]}, "
                f"como alumno(a) acreedor(a) del documento con folio: {generated_folio}."
    )
