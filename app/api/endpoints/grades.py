from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from collections import defaultdict

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import StudentParent
from app.models.grade import Grade
from app.schemas.grade import Grade as GradeSchema, GradesByPeriod

router = APIRouter()


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
            detail="You don't have access to this student's grades"
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
