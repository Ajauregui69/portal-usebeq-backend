from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.services.usebeq_api_service import USEBEQAPIService
from app.schemas.usebeq_api import (
    EstudianteUSEBEQ,
    SolicitudBajaRequest,
    SolicitudBajaResponse,
    TipoBaja,
    SIGALoginRequest,
    SIGALoginResponse,
    SIGATokenStatus
)

router = APIRouter()


def get_api_service(db: Session = Depends(get_db)) -> USEBEQAPIService:
    """
    Dependency to get USEBEQ API service
    """
    return USEBEQAPIService(db)


@router.get("/estudiante/{curp}/{cct}", response_model=EstudianteUSEBEQ)
async def get_estudiante_by_curp_cct(
    curp: str,
    cct: str,
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get student information by CURP and CCT from external USEBEQ API

    Example:
    - CURP: AAPR160106HQTLRNA6
    - CCT: 22DPR0200G
    """
    try:
        estudiante = await api_service.get_estudiante_by_curp_cct(curp, cct)
        return estudiante
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar estudiante: {str(e)}"
        )


@router.get("/estudiante/{id_alumno}", response_model=EstudianteUSEBEQ)
async def get_estudiante_by_id(
    id_alumno: int,
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get student information by student ID from external USEBEQ API

    Example:
    - id_alumno: 863309
    """
    try:
        estudiante = await api_service.get_estudiante_by_id(id_alumno)
        return estudiante
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar estudiante: {str(e)}"
        )


@router.get("/boleta/{id_alumno}")
async def get_boleta(
    id_alumno: int,
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get student report card (boleta) as PDF

    Returns a PDF stream with the student's current report card.

    Example:
    - id_alumno: 863309
    """
    try:
        pdf_content = await api_service.get_boleta(id_alumno)

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=boleta_{id_alumno}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener boleta: {str(e)}"
        )


@router.get("/boleta-historica/{id_alumno}/{anio_inicio}")
async def get_boleta_historica(
    id_alumno: int,
    anio_inicio: int,
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get historical student report card (boleta) as PDF

    Returns a PDF stream with the student's historical report card for a specific year.

    Example:
    - id_alumno: 863309
    - anio_inicio: 2023
    """
    try:
        pdf_content = await api_service.get_boleta_historica(id_alumno, anio_inicio)

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=boleta_historica_{id_alumno}_{anio_inicio}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener boleta histórica: {str(e)}"
        )


@router.post("/baja/", response_model=SolicitudBajaResponse)
async def solicitar_baja(
    solicitud: SolicitudBajaRequest,
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Request student withdrawal (baja)

    Submit a withdrawal request for a student.

    Example request body:
    ```json
    {
        "idAlumno": 863309,
        "idMotivoBaja": 1
    }
    ```

    Example response:
    ```json
    {
        "mensaje": "La solicitud de baja de 863309 se ha procesado correctamente"
    }
    ```
    """
    try:
        response = await api_service.solicitar_baja(
            solicitud.idAlumno,
            solicitud.idMotivoBaja
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar solicitud de baja: {str(e)}"
        )


@router.get("/catalogo/tipos-de-baja", response_model=List[TipoBaja])
async def get_tipos_baja(
    current_user: User = Depends(get_current_active_user),
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get catalog of withdrawal types (tipos de baja)

    Returns a list of available withdrawal types that can be used when requesting
    a student withdrawal.

    Example response:
    ```json
    [
        {
            "Id": 1,
            "Descripcion": "CAMBIO DE ESCUELA"
        },
        {
            "Id": 2,
            "Descripcion": "CAMBIO DE ENTIDAD/PAÍS"
        },
        ...
    ]
    ```
    """
    try:
        tipos = await api_service.get_tipos_baja()
        return tipos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener catálogo de tipos de baja: {str(e)}"
        )


@router.post("/auth/login", response_model=SIGALoginResponse)
async def siga_login(
    credentials: SIGALoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate with SIGA external API and get tokens.

    This endpoint authenticates with the external SIGA API using the provided
    credentials and returns the access and refresh tokens.

    The tokens are also stored in the database for subsequent API calls.

    Example request:
    ```json
    {
        "correo": "usuario@ejemplo.com",
        "contrasenia": "password123"
    }
    ```

    Example response:
    ```json
    {
        "AccessToken": "eyJhbGciOiJIUzUxMiIs...",
        "RefreshToken": "f4735654b362..."
    }
    ```
    """
    import httpx
    from datetime import datetime
    from sqlalchemy import text
    from app.core.config import settings

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{settings.USEBEQ_AUTH_API_URL}/simple",
                json={
                    "correo": credentials.correo,
                    "contrasenia": credentials.contrasenia
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                error_data = response.json()
                detail = error_data.get("detail", "Credenciales inválidas")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=detail
                )

            data = response.json()
            access_token = data.get("AccessToken") or data.get("accessToken")
            refresh_token = data.get("RefreshToken") or data.get("refreshToken")

            # Store tokens in database
            query = text("""
                INSERT INTO pp_token (token, refresh_token, fecha_registro)
                VALUES (:token, :refresh_token, :fecha_registro)
            """)
            db.execute(query, {
                "token": access_token,
                "refresh_token": refresh_token,
                "fecha_registro": datetime.now()
            })
            db.commit()

            return SIGALoginResponse(
                AccessToken=access_token,
                RefreshToken=refresh_token
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al autenticar con SIGA: {str(e)}"
        )


@router.get("/auth/token-status", response_model=SIGATokenStatus)
async def get_token_status(
    api_service: USEBEQAPIService = Depends(get_api_service)
):
    """
    Get the current SIGA token status.

    Returns information about the currently stored token and whether it's still valid.

    Example response:
    ```json
    {
        "token_valid": true,
        "token_preview": "eyJhbGciOiJIUzUxMiIs...abc123",
        "fecha_registro": "2024-01-15 10:30:00",
        "message": "Token válido"
    }
    ```
    """
    try:
        from sqlalchemy import text
        from datetime import datetime, timedelta

        query = text("""
            SELECT TOP 1 token, fecha_registro FROM pp_token
            ORDER BY fecha_registro DESC
        """)
        result = api_service.db.execute(query).fetchone()

        if not result:
            return SIGATokenStatus(
                token_valid=False,
                message="No hay token almacenado"
            )

        token, fecha_registro = result
        time_diff = datetime.now() - fecha_registro
        is_valid = time_diff < timedelta(hours=24)

        # Show only first 30 and last 10 characters of token
        token_preview = f"{token[:30]}...{token[-10:]}" if len(token) > 40 else token

        return SIGATokenStatus(
            token_valid=is_valid,
            token_preview=token_preview,
            fecha_registro=fecha_registro.strftime("%Y-%m-%d %H:%M:%S"),
            message="Token válido" if is_valid else "Token expirado (más de 24 horas)"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar token: {str(e)}"
        )


@router.get("/auth/scheduler-status")
async def get_scheduler_status(
    db: Session = Depends(get_db)
):
    """
    Get the status of the automatic token refresh scheduler.

    Returns information about the scheduler and the next scheduled refresh.

    Example response:
    ```json
    {
        "scheduler_running": true,
        "next_refresh": "2024-01-16 09:30:00",
        "refresh_interval_hours": 23,
        "current_token_age_hours": 5.5,
        "message": "Scheduler activo - próximo refresh en 17.5 horas"
    }
    ```
    """
    from datetime import datetime, timedelta
    from sqlalchemy import text
    from app.services.token_scheduler import token_scheduler

    try:
        scheduler = token_scheduler._scheduler
        is_running = scheduler.running if scheduler else False

        # Get current token age
        query = text("""
            SELECT TOP 1 fecha_registro FROM pp_token
            ORDER BY fecha_registro DESC
        """)
        result = db.execute(query).fetchone()

        current_token_age_hours = None
        if result:
            fecha_registro = result[0]
            time_diff = datetime.now() - fecha_registro
            current_token_age_hours = round(time_diff.total_seconds() / 3600, 2)

        # Get next scheduled run
        next_refresh = None
        if is_running:
            job = scheduler.get_job("refresh_usebeq_token")
            if job and job.next_run_time:
                next_refresh = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

        message = "Scheduler activo" if is_running else "Scheduler no está corriendo"
        if current_token_age_hours is not None:
            hours_until_expiry = 24 - current_token_age_hours
            message += f" - Token tiene {current_token_age_hours}h de antigüedad, expira en {hours_until_expiry:.1f}h"

        return {
            "scheduler_running": is_running,
            "next_refresh": next_refresh,
            "refresh_interval_hours": 23,
            "current_token_age_hours": current_token_age_hours,
            "message": message
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar scheduler: {str(e)}"
        )


@router.post("/auth/force-refresh")
async def force_token_refresh(
    db: Session = Depends(get_db)
):
    """
    Force an immediate refresh of the USEBEQ API token.

    This endpoint manually triggers the token refresh process, regardless of
    whether the current token is expired or not.

    Useful for:
    - Testing the refresh mechanism
    - Recovering from a corrupted token
    - Manual intervention when needed

    Example response:
    ```json
    {
        "success": true,
        "message": "Token refrescado exitosamente",
        "new_token_preview": "eyJhbGciOiJIUzUxMiIs...xyz789"
    }
    ```
    """
    from app.services.token_scheduler import token_scheduler
    from sqlalchemy import text

    try:
        # Force token refresh
        await token_scheduler.refresh_usebeq_token()

        # Get the new token to confirm
        query = text("""
            SELECT TOP 1 token, fecha_registro FROM pp_token
            ORDER BY fecha_registro DESC
        """)
        result = db.execute(query).fetchone()

        if result:
            token, fecha_registro = result
            token_preview = f"{token[:30]}...{token[-10:]}" if len(token) > 40 else token

            return {
                "success": True,
                "message": "Token refrescado exitosamente",
                "new_token_preview": token_preview,
                "fecha_registro": fecha_registro.strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            return {
                "success": False,
                "message": "No se pudo obtener el token después del refresh"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al refrescar token: {str(e)}"
        )
