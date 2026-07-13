"""
BOEVA - Document Authenticity Verification
Verifies student documents by folio number, matching PHP portal's boeva.php.
Student data is fetched live from the USEBEQ external API.
"""
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.services.usebeq_api_service import USEBEQAPIService

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


async def _verify_student(db: Session, student_id: int, not_found_message: str, via_qr: bool = False) -> BoevaResponse:
    usebeq_service = USEBEQAPIService(db)
    try:
        estudiante = await usebeq_service.get_estudiante_by_id(student_id)
    except Exception:
        return BoevaResponse(found=False, message=not_found_message)

    nombre_completo = f"{estudiante.Nombre} {estudiante.ApellidoPaterno} {estudiante.ApellidoMaterno or ''}".strip()
    estatus = (estudiante.Estatus or '').strip()
    generated_folio = f"BE22200{student_id}"
    codigo = "código QR" if via_qr else "código"

    return BoevaResponse(
        found=True,
        folio=generated_folio,
        nombre=nombre_completo,
        curp=estudiante.CURP,
        estatus=estatus,
        estatus_descripcion=get_estatus_descripcion(estatus),
        message=f"La lectura del {codigo} vincula al educando {nombre_completo} con CURP {estudiante.CURP}, "
                f"como alumno(a) acreedor(a) del documento con folio: {generated_folio}."
    )


@router.post("/verificar", response_model=BoevaResponse)
async def verificar_documento(
    request: BoevaRequest,
    db: Session = Depends(get_db),
):
    """
    Verify document authenticity by folio number.
    Extracts student ID from folio and queries the USEBEQ API.
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

    not_found = ("No se ha encontrado información con el folio ingresado, "
                 "por favor revise la información proporcionada e intente nuevamente.")

    try:
        student_id_int = int(student_id)
    except ValueError:
        return BoevaResponse(found=False, message=not_found)

    return await _verify_student(db, student_id_int, not_found)


@router.get("/verificar/{encoded_id}")
async def verificar_por_qr(
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

    return await _verify_student(
        db,
        student_id,
        "No se encontró información para el código proporcionado.",
        via_qr=True,
    )
