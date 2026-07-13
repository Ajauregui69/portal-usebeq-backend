from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import StudentParent
from app.schemas.student import (
    StudentWithEnrollment,
    StudentParentCreate,
    AddStudentRequest,
    AddStudentResponse,
)
from app.schemas.usebeq_api import EstudianteUSEBEQ
from app.services.usebeq_api_service import USEBEQAPIService

router = APIRouter()


def _student_payload(api_data: EstudianteUSEBEQ) -> dict:
    """Build the student response dict from live USEBEQ API data."""
    return {
        "al_id": api_data.IdAlumno,
        "al_curp": (api_data.CURP or "").strip(),
        "al_nombre": api_data.Nombre,
        "al_appat": api_data.ApellidoPaterno,
        "al_apmat": api_data.ApellidoMaterno,
        "al_estatus": (api_data.Estatus or "").strip() or None,
        "al_fecing": None,
        "al_fecnac": None,
        "current_enrollment": {
            "clavecct": (api_data.CCT or "").strip() or None,
            "nombrect": (api_data.NombreCT or "").strip() or None,
            "eg_grado": (api_data.Grado or "").strip() or None,
            "eg_grupo": (api_data.Grupo or "").strip() or None,
            "turno": (api_data.Turno or "").strip() or None,
            "al_id": api_data.IdAlumno,
        },
    }


@router.get("/my-students", response_model=List[StudentWithEnrollment])
async def get_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all students linked to current user.
    Student data is fetched live from the USEBEQ external API (never stored locally).
    """
    student_parents = db.query(StudentParent).filter(
        StudentParent.u_id == current_user.u_id
    ).all()

    usebeq_service = USEBEQAPIService(db)
    students_data = []

    for sp in student_parents:
        try:
            api_data = await usebeq_service.get_estudiante_by_id(sp.al_id)
        except Exception:
            # USEBEQ API unavailable or student not found; skip this record
            continue
        students_data.append(_student_payload(api_data))

    return students_data


async def _link_student_and_build_response(
    db: Session,
    current_user: User,
    usebeq_service: USEBEQAPIService,
    estudiante_data: EstudianteUSEBEQ,
    relacion: str,
) -> dict:
    """
    Create the parent-student link for a student already validated against the
    USEBEQ API, detect potential siblings, and build the response payload.
    Raises HTTPException on duplicate links or relacion conflicts.
    """
    student_id = estudiante_data.IdAlumno

    # Check if already linked to this user
    existing = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este estudiante ya está vinculado a tu cuenta"
        )

    # Check if same relacion already taken by another user
    existing_relacion = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.relacion == relacion
    ).first()

    if existing_relacion and existing_relacion.u_id != current_user.u_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El parentesco {relacion.upper()} ya ha sido vinculado al estudiante con otra cuenta. "
                   "Por favor intenta con un parentesco diferente. "
                   "En caso de necesitar apoyo puedes escribir a: epena@usebeq.edu.mx"
        )

    # Create link (the CURP captured at registration is kept, as in the
    # production PHP portal, to allow future linking by CURP alone)
    student_parent = StudentParent(
        al_id=student_id,
        al_curp=(estudiante_data.CURP or "").strip().upper() or None,
        u_id=current_user.u_id,
        relacion=relacion
    )
    db.add(student_parent)
    db.commit()

    # Detect potential siblings (same paternal and maternal last names)
    siblings_detected = []
    try:
        new_appat = (estudiante_data.ApellidoPaterno or "").strip()
        new_apmat = (estudiante_data.ApellidoMaterno or "").strip()
        if new_appat and new_apmat:
            all_linked = db.query(StudentParent).filter(
                StudentParent.u_id == current_user.u_id,
                StudentParent.al_id != student_id
            ).all()
            for sp in all_linked:
                try:
                    other = await usebeq_service.get_estudiante_by_id(sp.al_id)
                except Exception:
                    continue
                other_appat = (other.ApellidoPaterno or "").strip()
                other_apmat = (other.ApellidoMaterno or "").strip()
                if other_apmat and other_appat == new_appat and other_apmat == new_apmat:
                    already_confirmed = db.execute(text(
                        "SELECT h_id FROM pp_hermanos "
                        "WHERE (al_id = :id1 AND her_id = :id2) "
                        "OR (al_id = :id2 AND her_id = :id1)"
                    ), {"id1": student_id, "id2": other.IdAlumno}).fetchone()
                    if not already_confirmed:
                        siblings_detected.append({
                            "al_id": other.IdAlumno,
                            "nombre": f"{other.Nombre} {other.ApellidoPaterno}"
                        })
    except Exception:
        pass  # pp_hermanos may not exist yet

    return {
        "success": True,
        "message": "Student linked successfully",
        "student": {
            "al_id": estudiante_data.IdAlumno,
            "al_curp": estudiante_data.CURP,
            "al_nombre": estudiante_data.Nombre,
            "al_appat": estudiante_data.ApellidoPaterno,
            "al_apmat": estudiante_data.ApellidoMaterno,
            "cct": estudiante_data.CCT,
            "grado": estudiante_data.Grado,
            "grupo": estudiante_data.Grupo,
            "estatus": estudiante_data.Estatus
        },
        "siblings": siblings_detected if siblings_detected else None
    }


@router.post("/link-student", status_code=status.HTTP_201_CREATED)
async def link_student(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_in: StudentParentCreate,
) -> Any:
    """
    Link a student to current user account by CURP only, like the production
    PHP portal: the student is located through a link already registered by
    another parent (pp_alumnos keeps the CURP captured at registration).
    As a fallback, the CURP is tried against the CCTs of the students already
    linked to this account (siblings usually attend the same school).
    If not found either way, the CURP + CCT flow is required.
    """
    curp = student_in.al_curp.strip().upper()
    relacion = (student_in.relacion or "padre").strip().lower()

    if len(curp) != 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CURP must be 18 characters"
        )

    if relacion not in ['padre', 'madre', 'tutor']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La relacion debe ser: padre, madre o tutor"
        )

    usebeq_service = USEBEQAPIService(db)
    estudiante_data = None

    # 1. PHP-portal behavior: the student was already registered by another
    #    parent, so the CURP is known locally and gives us the al_id
    known_link = db.query(StudentParent).filter(
        StudentParent.al_curp == curp
    ).first()
    if known_link:
        try:
            estudiante_data = await usebeq_service.get_estudiante_by_id(known_link.al_id)
        except Exception:
            estudiante_data = None

    # 2. Fallback: try the CURP against the CCTs of this user's linked students
    if not estudiante_data:
        candidate_ccts: List[str] = []
        for sp in db.query(StudentParent).filter(
            StudentParent.u_id == current_user.u_id
        ).all():
            try:
                other = await usebeq_service.get_estudiante_by_id(sp.al_id)
            except Exception:
                continue
            cct = (other.CCT or "").strip()
            if cct and cct not in candidate_ccts:
                candidate_ccts.append(cct)

        for cct in candidate_ccts:
            try:
                estudiante_data = await usebeq_service.get_estudiante_by_curp_cct(curp, cct)
                break
            except Exception:
                continue

    if not estudiante_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estudiante no encontrado. Intenta vincular con CURP y CCT."
        )

    return await _link_student_and_build_response(
        db, current_user, usebeq_service, estudiante_data, relacion
    )


@router.post("/link-student-with-cct", status_code=status.HTTP_201_CREATED)
async def link_student_with_cct(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    curp: str,
    cct: str,
    relacion: str = "padre"
) -> Any:
    """
    Link a student to current user account by CURP and CCT.
    The student is validated against the USEBEQ external API; only the link
    (al_id + user + relacion) is stored locally.
    """
    curp = curp.strip().upper()
    cct = cct.strip().upper()
    relacion = relacion.lower()

    if len(curp) != 18:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CURP must be 18 characters"
        )

    if relacion not in ['padre', 'madre', 'tutor']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La relacion debe ser: padre, madre o tutor"
        )

    usebeq_service = USEBEQAPIService(db)

    try:
        try:
            estudiante_data = await usebeq_service.get_estudiante_by_curp_cct(curp, cct)
        except Exception as api_error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No fue posible consultar al estudiante en USEBEQ. Verifica CURP y CCT e intenta de nuevo. Error: {str(api_error)}"
            )

        return await _link_student_and_build_response(
            db, current_user, usebeq_service, estudiante_data, relacion
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error linking student: {str(e)}"
        )


@router.delete("/unlink-student/{student_id}")
def unlink_student(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_id: int,
) -> Any:
    """
    Unlink a student from current user account
    """
    student_parent = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not student_parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vinculacion de estudiante no encontrada"
        )

    db.delete(student_parent)
    db.commit()

    return {"message": "Student unlinked successfully"}


@router.get("/siblings-count")
def get_siblings_count(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Returns the number of confirmed sibling pairs for the current user's students.
    """
    student_ids = [
        sp.al_id for sp in db.query(StudentParent).filter(
            StudentParent.u_id == current_user.u_id
        ).all()
    ]
    if not student_ids:
        return {"count": 0}

    placeholders = ",".join(str(i) for i in student_ids)
    try:
        count = db.execute(text(
            f"SELECT COUNT(*) FROM pp_hermanos "
            f"WHERE al_id IN ({placeholders}) OR her_id IN ({placeholders})"
        )).scalar()
    except Exception:
        count = 0
    return {"count": count or 0}


@router.post("/confirm-sibling")
async def confirm_sibling(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    al_id: int,
    her_id: int
) -> Any:
    """
    Confirm sibling relationship between two students already linked to the user.
    Only the pair of USEBEQ student IDs is stored; student data stays in the API.
    """
    # Verify both students belong to this user
    s1_link = db.query(StudentParent).filter(
        StudentParent.al_id == al_id,
        StudentParent.u_id == current_user.u_id
    ).first()
    s2_link = db.query(StudentParent).filter(
        StudentParent.al_id == her_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not s1_link or not s2_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o ambos estudiantes no están vinculados a tu cuenta"
        )

    usebeq_service = USEBEQAPIService(db)
    try:
        s1 = await usebeq_service.get_estudiante_by_id(al_id)
        s2 = await usebeq_service.get_estudiante_by_id(her_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible consultar a los estudiantes en USEBEQ. Intenta más tarde."
        )

    # Determine order: older sibling (smaller birth year in CURP[4:6]) goes as al_id
    curp1 = (s1.CURP or "").strip()
    curp2 = (s2.CURP or "").strip()
    year_s1 = curp1[4:6] if len(curp1) >= 6 else "99"
    year_s2 = curp2[4:6] if len(curp2) >= 6 else "99"

    if year_s1 <= year_s2:
        older_id, younger_id = al_id, her_id
    else:
        older_id, younger_id = her_id, al_id

    # Check if relationship already exists
    existing = db.execute(text(
        "SELECT h_id FROM pp_hermanos WHERE al_id = :al_id AND her_id = :her_id"
    ), {"al_id": older_id, "her_id": younger_id}).fetchone()

    if existing:
        return {"success": True, "message": "La relación de hermandad ya estaba registrada"}

    db.execute(text(
        "INSERT INTO pp_hermanos (al_id, her_id) VALUES (:al_id, :her_id)"
    ), {"al_id": older_id, "her_id": younger_id})
    db.commit()

    return {"success": True, "message": "Relación de hermandad confirmada correctamente"}


@router.post("/add-student", response_model=AddStudentResponse)
async def add_student_to_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_data: AddStudentRequest
) -> Any:
    """
    Add student to parent account with full validation against the USEBEQ API.
    Only the link (al_id + user + relacion) is stored locally.
    """
    import unicodedata

    curp = student_data.curp.strip().upper()
    apellido = student_data.apellido.strip().upper()
    cct = student_data.cct.strip().upper()
    grupo = student_data.grupo.strip().upper()
    parentesco = student_data.parentesco.lower()

    def remove_accents(s):
        return ''.join(c for c in unicodedata.normalize('NFD', s)
                       if unicodedata.category(c) != 'Mn')

    apellido = remove_accents(apellido)

    if parentesco not in ['padre', 'madre', 'tutor']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parentesco debe ser PADRE, MADRE o TUTOR"
        )

    usebeq_service = USEBEQAPIService(db)
    try:
        estudiante = await usebeq_service.get_estudiante_by_curp_cct(curp, cct)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encuentra al estudiante. Intente nuevamente."
        )

    # Validate provided data against the API record
    api_apellido = remove_accents((estudiante.ApellidoPaterno or "").strip().upper())
    api_grupo = (estudiante.Grupo or "").strip().upper()
    if api_apellido != apellido or api_grupo != grupo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encuentra al estudiante. Intente nuevamente."
        )

    al_id = estudiante.IdAlumno

    # Check if student already linked to this user with same relacion
    existing_link = db.query(StudentParent).filter(
        StudentParent.al_id == al_id,
        StudentParent.u_id == current_user.u_id,
        StudentParent.relacion == parentesco
    ).first()
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este estudiante ya está vinculado a tu cuenta como {parentesco.upper()}"
        )

    # Check if relacion taken by another user
    other_link = db.query(StudentParent).filter(
        StudentParent.al_id == al_id,
        StudentParent.relacion == parentesco
    ).first()
    if other_link and other_link.u_id != current_user.u_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El parentesco {parentesco.upper()} ya ha sido vinculado al estudiante con otra cuenta. "
                   "En caso de necesitar apoyo puedes escribir a: epena@usebeq.edu.mx"
        )

    student_parent = StudentParent(
        al_id=al_id,
        al_curp=curp,
        u_id=current_user.u_id,
        relacion=parentesco
    )
    db.add(student_parent)
    db.commit()

    return AddStudentResponse(
        success=True,
        message="Estudiante agregado correctamente.",
        student={
            "al_id": al_id,
            "al_curp": estudiante.CURP,
            "al_nombre": estudiante.Nombre,
            "al_appat": estudiante.ApellidoPaterno,
            "al_apmat": estudiante.ApellidoMaterno,
            "grado": estudiante.Grado,
            "grupo": estudiante.Grupo,
            "cct": estudiante.CCT
        },
        siblings=None
    )


@router.get("/{student_id}/teachers")
async def get_student_teachers(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_id: int
) -> Any:
    """
    Get group information for a specific student from the USEBEQ API.
    Teacher rosters are not exposed by the USEBEQ API.
    """
    # Verify student belongs to current user
    link = db.query(StudentParent).filter(
        StudentParent.al_id == student_id,
        StudentParent.u_id == current_user.u_id
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

    usebeq_service = USEBEQAPIService(db)
    try:
        estudiante = await usebeq_service.get_estudiante_by_id(student_id)
    except Exception:
        return {
            "success": False,
            "message": "No se encontró información del grupo del estudiante",
            "teachers": []
        }

    return {
        "success": True,
        "student_id": student_id,
        "group": {
            "grado": (estudiante.Grado or "").strip(),
            "grupo": (estudiante.Grupo or "").strip(),
            "cct": (estudiante.CCT or "").strip(),
            "escuela": (estudiante.NombreCT or "").strip(),
            "turno": (estudiante.Turno or "").strip()
        },
        "teachers": [],
        "total": 0,
        "message": "La información de maestros no está disponible por el momento"
    }
