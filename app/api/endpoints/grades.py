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
    """Debug endpoint — exposes full traceback. Remove after debugging."""
    import traceback
    try:
        return consulta_calificaciones(payload, db)
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.post("/consulta", response_model=ConsultaResponse)
def consulta_calificaciones(payload: ConsultaRequest, db: Session = Depends(get_db)) -> Any:
    """
    Consulta pública de calificaciones por CURP (sin autenticación).
    Replica la funcionalidad de consulta.php / califica.php del portal anterior.
    """
    curp = payload.curp.strip().upper()

    # 1. Buscar alumno por CURP
    student = db.execute(
        text("SELECT al_id, al_nombre, al_appat, al_apmat FROM SCE004 WHERE al_curp = :curp"),
        {"curp": curp}
    ).fetchone()

    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró registro con la CURP proporcionada")

    al_id = student[0]

    # 2. Determinar ciclo escolar actual (meses 1-8 → año anterior, meses 9-12 → año actual)
    now = datetime.now()
    year = now.year if now.month >= 9 else now.year - 1
    ciclo = f"{year}-{year + 1}"

    # 3. Obtener la inscripción más reciente del ciclo actual (columnas reales de SCE005)
    enrollment = db.execute(
        text("""
            SELECT nivel, eg_grado, matricula_id
            FROM SCE005
            WHERE al_id = :al_id AND ciclo_escolar LIKE :ciclo
            ORDER BY matricula_id DESC
            LIMIT 1
        """),
        {"al_id": al_id, "ciclo": f"{year}%"}
    ).fetchone()

    nivel = enrollment[0].strip() if enrollment and enrollment[0] else None
    grado = str(enrollment[1]) if enrollment and enrollment[1] else None
    matricula_id = enrollment[2] if enrollment else None

    # 4. Obtener calificaciones del ciclo actual (filtrando por matricula_id si existe)
    if matricula_id:
        grades = db.query(Grade).filter(
            Grade.al_id == al_id,
            Grade.matricula_id == matricula_id
        ).all()
    else:
        grades = db.query(Grade).filter(Grade.al_id == al_id).all()

    # Construir materias agrupando periodos por nombre de materia
    materias_dict: dict = {}
    for g in grades:
        mat = g.materia or ""
        if mat not in materias_dict:
            materias_dict[mat] = {"materia": mat, "calif1": None, "calif2": None, "calif3": None, "promedio": None}
        periodo = (g.periodo or "").lower()
        calificacion = str(g.calificacion) if g.calificacion is not None else None
        if "1" in periodo or "primer" in periodo:
            materias_dict[mat]["calif1"] = calificacion
        elif "2" in periodo or "segund" in periodo:
            materias_dict[mat]["calif2"] = calificacion
        elif "3" in periodo or "tercer" in periodo:
            materias_dict[mat]["calif3"] = calificacion

    materias = [ConsultaMateria(**v) for v in materias_dict.values()]

    # 5. Obtener componentes curriculares (SCE044) — silencioso si la tabla no existe
    componentes_rows = []
    try:
        componentes_rows = db.execute(
            text("""
                SELECT cm_descrip, cc_nivel1, cc_nivel2, cc_nivel3
                FROM SCE044
                WHERE al_id = :al_id AND ciclo_escolar LIKE :ciclo
            """),
            {"al_id": al_id, "ciclo": f"{year}%"}
        ).fetchall()
    except Exception:
        pass

    componentes = [
        ConsultaComponente(
            campo=row[0] or "",
            nivel1=row[1].strip() if row[1] else None,
            nivel2=row[2].strip() if row[2] else None,
            nivel3=row[3].strip() if row[3] else None,
        )
        for row in componentes_rows
        if row[1] is not None
    ]

    # 6. Observaciones
    observaciones = []
    for m in materias:
        if m.calif1 in ("1", "-"):
            observaciones.append("- Información insuficiente, al registrar una comunicación y participación intermitente.")
            break
    for m in materias:
        if m.calif1 in ("2", "- -"):
            observaciones.append("- - Sin información, al registrar una comunicación prácticamente inexistente.")
            break

    return ConsultaResponse(
        curp=curp,
        nivel=nivel,
        grado=grado,
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
