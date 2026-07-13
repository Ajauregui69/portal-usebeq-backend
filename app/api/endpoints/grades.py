from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import StudentParent
from app.schemas.grade import GradesByPeriod
from app.services.usebeq_api_service import USEBEQAPIService

router = APIRouter()


# --- Schemas for public consulta ---
class ConsultaRequest(BaseModel):
    curp: str

class ConsultaMateria(BaseModel):
    materia: str
    calif1: Optional[str] = None
    calif2: Optional[str] = None
    calif3: Optional[str] = None
    promedio: Optional[str] = None

class ConsultaComponente(BaseModel):
    campo: str
    nivel1: Optional[str] = None
    nivel2: Optional[str] = None
    nivel3: Optional[str] = None

class ConsultaResponse(BaseModel):
    curp: str
    nivel: Optional[str] = None
    grado: Optional[str] = None
    ciclo: str
    materias: List[ConsultaMateria]
    componentes: List[ConsultaComponente]
    observaciones: List[str]


def _scrape_consulta(curp: str) -> ConsultaResponse:
    """
    Consulta de calificaciones por CURP haciendo scraping del portal
    original de USEBEQ. No usa ninguna tabla local.
    """
    import httpx
    from bs4 import BeautifulSoup

    curp = curp.strip().upper()

    PORTAL_URL = "https://portal.usebeq.edu.mx/portal/portal/califica.php"

    try:
        response = httpx.post(
            PORTAL_URL,
            data={"curp": curp},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://portal.usebeq.edu.mx/portal/portal/consulta.php",
            },
            timeout=20,
            follow_redirects=True,
            verify=False,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"No se pudo conectar al portal: {e}")

    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="La consulta de calificaciones no está disponible en este momento")

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error al consultar el portal")

    soup = BeautifulSoup(response.text, "html.parser")

    # Verificar si el alumno existe (la página muestra el CURP si lo encontró)
    body_text = soup.get_text()
    if "No se encontró" in body_text or curp not in body_text:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró registro con la CURP proporcionada")

    # Extraer ciclo escolar del encabezado de la tabla
    ciclo = ""
    for h3 in soup.find_all("h3"):
        if "Ciclo escolar" in h3.get_text():
            # "Evaluaciones Ciclo escolar: 2025-2026"
            parts = h3.get_text().split(":")
            if len(parts) > 1:
                ciclo = parts[-1].strip()
            break

    # Extraer materias de la primera tabla (tabla oscura con calificaciones)
    materias: List[ConsultaMateria] = []
    tables = soup.find_all("table", class_="table-dark")

    if tables:
        rows = tables[0].find("tbody").find_all("tr")
        for row in rows:
            cols = row.find_all(["th", "td"])
            if len(cols) >= 5:
                nombre = cols[0].get_text(strip=True)
                calif1 = cols[1].get_text(strip=True) or None
                calif2 = cols[2].get_text(strip=True) or None
                calif3 = cols[3].get_text(strip=True) or None
                promedio = cols[4].get_text(strip=True) or None
                if nombre:
                    materias.append(ConsultaMateria(
                        materia=nombre,
                        calif1=calif1,
                        calif2=calif2,
                        calif3=calif3,
                        promedio=promedio,
                    ))

    # Extraer componentes curriculares de la segunda tabla
    componentes: List[ConsultaComponente] = []
    if len(tables) > 1:
        rows = tables[1].find("tbody").find_all("tr")
        for row in rows:
            cols = row.find_all(["th", "td"])
            if len(cols) >= 2:
                campo = cols[0].get_text(strip=True)
                nivel = cols[1].get_text(strip=True) or None
                obs = cols[2].get_text(strip=True) if len(cols) > 2 else None
                if campo:
                    componentes.append(ConsultaComponente(
                        campo=campo,
                        nivel1=nivel,
                        nivel2=obs,
                        nivel3=None,
                    ))

    # Extraer observaciones de la tercera tabla
    observaciones: List[str] = []
    if len(tables) > 2:
        rows = tables[2].find("tbody").find_all("tr")
        for row in rows:
            texto = row.get_text(strip=True)
            if texto:
                observaciones.append(texto)

    return ConsultaResponse(
        curp=curp,
        nivel=None,
        grado=None,
        ciclo=ciclo,
        materias=materias,
        componentes=componentes,
        observaciones=observaciones,
    )


@router.post("/consulta", response_model=ConsultaResponse)
def consulta_calificaciones(payload: ConsultaRequest) -> Any:
    """
    Consulta pública de calificaciones por CURP (sin autenticación).
    Hace scraping del portal original de USEBEQ.
    """
    return _scrape_consulta(payload.curp)


def _verify_student_access(db: Session, current_user: User, student_id: int) -> None:
    student_parent = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not student_parent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a las calificaciones de este estudiante"
        )


@router.get("/student/{student_id}", response_model=List[GradesByPeriod])
async def get_student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all grades for a specific student.
    The CURP is resolved through the USEBEQ API and grades are read from the
    official USEBEQ portal; no local grade tables are used.
    """
    _verify_student_access(db, current_user, student_id)

    usebeq_service = USEBEQAPIService(db)
    try:
        estudiante = await usebeq_service.get_estudiante_by_id(student_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar al estudiante en USEBEQ. Intenta más tarde."
        )

    try:
        consulta = _scrape_consulta(estudiante.CURP)
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND:
            return []
        raise

    grades_by_period: dict = {}
    for materia in consulta.materias:
        for idx, valor in enumerate([materia.calif1, materia.calif2, materia.calif3], start=1):
            if not valor:
                continue
            try:
                calificacion = float(valor.replace(",", "."))
            except ValueError:
                continue
            periodo = f"Evaluación {idx}"
            grades_by_period.setdefault(periodo, []).append({
                "al_id": student_id,
                "materia": materia.materia,
                "periodo": periodo,
                "calificacion": calificacion,
                "observaciones": None
            })

    return [
        {"periodo": periodo, "calificaciones": califs}
        for periodo, califs in sorted(grades_by_period.items())
    ]


@router.get("/student/{student_id}/pdf")
async def get_student_grades_pdf(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get the official report card (boleta) PDF from the USEBEQ API.
    """
    _verify_student_access(db, current_user, student_id)

    usebeq_service = USEBEQAPIService(db)
    try:
        pdf_content = await usebeq_service.get_boleta(student_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible obtener la boleta desde USEBEQ. Intenta más tarde."
        )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=boleta_{student_id}.pdf"}
    )
