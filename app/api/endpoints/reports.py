from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import requests

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.report import BoletaResponse

router = APIRouter()

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
    from sqlalchemy import text

    # Verify student belongs to current user
    verify_query = text("""
        SELECT al_id FROM pp_alumnos
        WHERE al_id = :al_id
        AND (padre = :correo OR madre = :correo OR tutor = :correo)
    """)

    result = db.execute(verify_query, {
        "al_id": al_id,
        "correo": current_user.u_correo
    }).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

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
    from sqlalchemy import text

    # Verify student belongs to current user
    verify_query = text("""
        SELECT al_id FROM pp_alumnos
        WHERE al_id = :al_id
        AND (padre = :correo OR madre = :correo OR tutor = :correo)
    """)

    result = db.execute(verify_query, {
        "al_id": al_id,
        "correo": current_user.u_correo
    }).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

    # Check if certificate exists (IdEstatus = 4 means signed/ready)
    cert_query = text("""
        SELECT IdEstatus
        FROM SCE039
        WHERE al_id = :al_id
    """)

    cert_result = db.execute(cert_query, {"al_id": al_id}).fetchone()

    if not cert_result or cert_result[0] != 4:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado electronico no disponible para este estudiante"
        )

    # Return certificate URL
    certificate_url = f"https://portal.usebeq.edu.mx/certificados2/{ciclo}/{al_id}.pdf"

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
    from sqlalchemy import text

    # Verify student belongs to current user
    verify_query = text("""
        SELECT al_id FROM pp_alumnos
        WHERE al_id = :al_id
        AND (padre = :correo OR madre = :correo OR tutor = :correo)
    """)

    result = db.execute(verify_query, {
        "al_id": al_id,
        "correo": current_user.u_correo
    }).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

    # Generate report URL
    import base64
    encoded_id = base64.b64encode(str(al_id).encode()).decode()

    report_url = f"https://portal.usebeq.edu.mx/portal/ReporteE/ReporteCC_{ciclo}.php?al_id={encoded_id}"

    return {
        "success": True,
        "message": "Reporte de componentes curriculares disponible",
        "report_url": report_url
    }
