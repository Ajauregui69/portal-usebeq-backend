from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import requests

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import StudentParent
from app.schemas.report import BoletaResponse

router = APIRouter()


def _verify_student_access(db: Session, current_user: User, al_id: int) -> None:
    """Verify the student is linked to the current user via pp_alumnos."""
    link = db.query(StudentParent).filter(
        StudentParent.al_id == al_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

# Azure SCE API configuration
SCE_API_BASE_URL = "https://sce-usebeq-api.azurewebsites.net/api"
SCE_API_TOKEN = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImVkLnBlbmEuOTRAaG90bWFpbC5jb20iLCJuYW1lIjoiTGFsbyIsImdpdmVuX25hbWUiOiJFZHVhcmRvIFBlw7FhIE9tYcOxYSIsInJvbCI6IjEiLCJzdWJjYXRlZ29yaWEiOlsiMTAiLCIyIiwiMyIsIjQiLCI1IiwiNiIsIjciLCI4IiwiOSJdLCJjYXRlZ29yaWEiOiIxIiwibmJmIjoxNzAwNTk2ODMyLCJleHAiOjE3MDA2ODMyMzIsImlhdCI6MTcwMDU5NjgzMiwiaXNzIjoiU2lnYSIsImF1ZCI6IkF1ZGllbmNlIn0.q9dwtsirCDylcZThsXyVIluTil1JcPEg404bSN56Ojmf6oke-Aj1hhUWB0j2qq88Pu432uifqTX6FDNYfBOtIg"


@router.get("/boleta/{al_id}")
async def get_boleta_pdf(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    al_id: int
) -> Any:
    """
    Get boleta (report card) PDF from Azure SCE API

    Returns PDF directly or error message
    """
    # Verify student belongs to current user
    _verify_student_access(db, current_user, al_id)

    # Call Azure API
    api_url = f"{SCE_API_BASE_URL}/boletas/{al_id}"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {SCE_API_TOKEN}'
    }

    try:
        response = requests.get(
            api_url,
            headers=headers,
            verify=False,  # Ignore SSL verification (as in original PHP)
            timeout=30
        )

        # Check if response is PDF
        if response.status_code == 200 and response.content.startswith(b'%PDF-'):
            # Return PDF directly
            return Response(
                content=response.content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename=boleta_{al_id}.pdf"
                }
            )
        else:
            # Try to decode error message
            try:
                error_data = response.json()
                error_message = error_data.get('message', 'Error desconocido')
            except:
                error_message = "No es posible generar la boleta en este momento"

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_message
            )

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error de comunicacion con el servidor: {str(e)}"
        )


@router.get("/certificado-electronico/{al_id}")
async def get_certificado_electronico(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    al_id: int,
    ciclo: str = "2425"  # Default to current cycle
) -> Any:
    """
    Get electronic certificate PDF

    Returns redirect to certificate URL or error if not available
    """
    # Verify student belongs to current user
    _verify_student_access(db, current_user, al_id)

    # Check availability directly against the portal (no local SCE tables)
    certificate_url = f"https://portal.usebeq.edu.mx/certificados2/{ciclo}/{al_id}.pdf"

    try:
        check = requests.head(certificate_url, verify=False, timeout=15, allow_redirects=True)
        available = check.status_code == 200
    except requests.exceptions.RequestException:
        available = False

    if not available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado electronico no disponible para este estudiante"
        )

    return {
        "success": True,
        "message": "Certificado electronico disponible",
        "certificate_url": certificate_url
    }


@router.get("/reporte-componentes/{al_id}")
async def get_reporte_componentes(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    al_id: int,
    ciclo: str = "2223"  # Default to 2022-2023
) -> Any:
    """
    Get components curriculares report PDF

    Returns redirect to report URL
    """
    # Verify student belongs to current user
    _verify_student_access(db, current_user, al_id)

    # Generate report URL
    import base64
    encoded_id = base64.b64encode(str(al_id).encode()).decode()

    report_url = f"https://portal.usebeq.edu.mx/portal/ReporteE/ReporteCC_{ciclo}.php?al_id={encoded_id}"

    return {
        "success": True,
        "message": "Reporte de componentes curriculares disponible",
        "report_url": report_url
    }
