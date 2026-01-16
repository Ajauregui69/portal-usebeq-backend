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
