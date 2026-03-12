from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from collections import defaultdict
from pydantic import BaseModel

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import StudentParent
from app.models.grade import Grade
from app.schemas.grade import Grade as GradeSchema, GradesByPeriod

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


@router.post("/consulta-debug")
def consulta_debug(payload: ConsultaRequest, db: Session = Depends(get_db)) -> Any:
    """Debug endpoint — tests DB queries for consulta. Remove after debugging."""
    from datetime import datetime as dt
    curp = payload.curp.strip().upper()
    now = dt.now()
    year = now.year if now.month >= 9 else now.year - 1

    result = {}

    # Test 1: SCE004 lookup
    try:
        student = db.execute(text("SELECT al_id, al_nombre FROM SCE004 WHERE al_curp = :curp"), {"curp": curp}).fetchone()
        result["sce004"] = {"al_id": student[0], "nombre": student[1]} if student else None
    except Exception as e:
        result["sce004_error"] = str(e)

    if not result.get("sce004"):
        return result

    al_id = result["sce004"]["al_id"]

    # Test 2: SCE005 — all rows for this student (show columns and any data)
    try:
        rows = db.execute(text("SELECT * FROM SCE005 WHERE al_id = :al_id ORDER BY matricula_id DESC LIMIT 5"), {"al_id": al_id}).fetchall()
        if rows:
            result["sce005_rows"] = [dict(zip(r._mapping.keys(), r)) for r in rows]
        else:
            result["sce005_rows"] = []
        # Also get column names
        col_rows = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'SCE005' ORDER BY ordinal_position")).fetchall()
        result["sce005_columns"] = [r[0] for r in col_rows]
    except Exception as e:
        result["sce005_error"] = str(e)

    # Test 3: SCE006 — all rows for this student
    try:
        rows = db.execute(text("SELECT * FROM SCE006 WHERE al_id = :al_id LIMIT 5"), {"al_id": al_id}).fetchall()
        if rows:
            result["sce006_rows"] = [dict(zip(r._mapping.keys(), r)) for r in rows]
        else:
            result["sce006_rows"] = []
        col_rows = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'SCE006' ORDER BY ordinal_position")).fetchall()
        result["sce006_columns"] = [r[0] for r in col_rows]
    except Exception as e:
        result["sce006_error"] = str(e)

    # Test 4: Grade ORM model
    try:
        from app.models.grade import Grade
        grades = db.query(Grade).filter(Grade.al_id == al_id).limit(5).all()
        result["grade_model_rows"] = len(grades)
        result["grade_model_sample"] = [{"id": g.id, "materia": g.materia, "periodo": g.periodo, "calificacion": str(g.calificacion)} for g in grades]
    except Exception as e:
        result["grade_model_error"] = str(e)

    # Test 5: MySQL CALL syntax for stored procedure (if it exists as MySQL SP)
    try:
        rows = db.execute(text("CALL spr_GetCalificaciones(:al_id, :year)"), {"al_id": al_id, "year": year}).fetchall()
        result["mysql_sp"] = [dict(zip(r._mapping.keys(), r)) for r in rows[:3]] if rows else []
    except Exception as e:
        result["mysql_sp_error"] = str(e)

    return result


@router.post("/consulta", response_model=ConsultaResponse)
def consulta_calificaciones(payload: ConsultaRequest) -> Any:
    """
    Consulta pública de calificaciones por CURP (sin autenticación).
    Hace scraping del portal original de USEBEQ.
    """
    import httpx
    from bs4 import BeautifulSoup

    curp = payload.curp.strip().upper()

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


@router.get("/student/{student_id}", response_model=List[GradesByPeriod])
def get_student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all grades for a specific student
    """
    # Verify that the student is linked to the current user
    student_parent = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not student_parent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a las calificaciones de este estudiante"
        )

    # Get all grades for the student
    grades = db.query(Grade).filter(Grade.al_id == student_id).all()

    if not grades:
        return []

    # Group grades by period
    grades_by_period = defaultdict(list)
    for grade in grades:
        grade_dict = {
            "id": grade.id,
            "al_id": grade.al_id,
            "matricula_id": grade.matricula_id,
            "materia": grade.materia,
            "periodo": grade.periodo,
            "calificacion": float(grade.calificacion),
            "observaciones": grade.observaciones
        }
        grades_by_period[grade.periodo].append(grade_dict)

    # Convert to list of GradesByPeriod
    result = [
        {
            "periodo": periodo,
            "calificaciones": califs
        }
        for periodo, califs in grades_by_period.items()
    ]

    return result


@router.get("/student/{student_id}/pdf")
def get_student_grades_pdf(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get student grades as a PDF report
    """
    from fastapi.responses import Response

    # Verify access
    student_parent = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()
    if not student_parent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a las calificaciones de este estudiante")

    # Get student info
    from sqlalchemy import text
    student_query = text("SELECT al_nombre, al_appat, al_apmat, al_curp FROM SCE004 WHERE al_id = :al_id")
    student_info = db.execute(student_query, {"al_id": student_id}).fetchone()

    enrollment_query = text("SELECT clavecct, nivel, eg_grado, eg_grupo, turno, ciclo_escolar FROM SCE005 WHERE al_id = :al_id ORDER BY ciclo_escolar DESC LIMIT 1")
    enrollment = db.execute(enrollment_query, {"al_id": student_id}).fetchone()

    # Get grades
    grades = db.query(Grade).filter(Grade.al_id == student_id).all()

    # Generate PDF
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=16, spaceAfter=6)
    elements.append(Paragraph("USEBEQ - Reporte de Calificaciones", title_style))
    elements.append(Spacer(1, 12))

    # Student info
    if student_info:
        nombre = f"{student_info[0]} {student_info[1]} {student_info[2] or ''}"
        elements.append(Paragraph(f"<b>Alumno:</b> {nombre}", styles['Normal']))
        elements.append(Paragraph(f"<b>CURP:</b> {student_info[3]}", styles['Normal']))
    if enrollment:
        elements.append(Paragraph(f"<b>Escuela (CCT):</b> {enrollment[0]} | <b>Nivel:</b> {enrollment[1]} | <b>Grado:</b> {enrollment[2]} | <b>Grupo:</b> {enrollment[3]}", styles['Normal']))
        elements.append(Paragraph(f"<b>Ciclo Escolar:</b> {enrollment[5]}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Group grades by period
    grades_by_period = defaultdict(list)
    for grade in grades:
        grades_by_period[grade.periodo].append(grade)

    for periodo, period_grades in sorted(grades_by_period.items()):
        elements.append(Paragraph(f"<b>{periodo}</b>", styles['Heading3']))

        data = [["Materia", "Calificaci\u00f3n", "Observaciones"]]
        for g in period_grades:
            data.append([g.materia, str(g.calificacion), g.observaciones or ""])

        # Calculate average
        avg = sum(float(g.calificacion) for g in period_grades) / len(period_grades) if period_grades else 0
        data.append(["PROMEDIO", f"{avg:.1f}", ""])

        table = Table(data, colWidths=[3*inch, 1.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 15))

    # Footer
    elements.append(Spacer(1, 20))
    from datetime import datetime
    elements.append(Paragraph(f"<i>Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    student_name = f"{student_info[0]}_{student_info[1]}" if student_info else str(student_id)

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=calificaciones_{student_name}.pdf"}
    )
