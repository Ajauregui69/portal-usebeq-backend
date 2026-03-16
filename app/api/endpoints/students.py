from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.models.student import Student, StudentParent, Enrollment
from app.schemas.student import (
    StudentWithEnrollment,
    StudentParentCreate,
    AddStudentRequest,
    AddStudentResponse,
)
from app.services.usebeq_api_service import USEBEQAPIService

router = APIRouter()


@router.get("/my-students", response_model=List[StudentWithEnrollment])
async def get_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all students linked to current user.
    At every call, validates and syncs student data against the USEBEQ external API.
    """
    student_parents = db.query(StudentParent).filter(
        StudentParent.u_id == current_user.u_id
    ).all()

    usebeq_service = USEBEQAPIService(db)
    students_data = []

    for sp in student_parents:
        student = db.query(Student).filter(Student.al_id == sp.al_id).first()
        if not student:
            continue

        # --- Sync with USEBEQ external API ---
        try:
            api_data = await usebeq_service.get_estudiante_by_id(student.al_id)

            # Sync SCE004 (student basic data)
            changes: dict = {}
            if api_data.Nombre and api_data.Nombre != student.al_nombre:
                changes["al_nombre"] = api_data.Nombre
            if api_data.ApellidoPaterno and api_data.ApellidoPaterno != student.al_appat:
                changes["al_appat"] = api_data.ApellidoPaterno
            if api_data.ApellidoMaterno is not None and api_data.ApellidoMaterno != student.al_apmat:
                changes["al_apmat"] = api_data.ApellidoMaterno

            api_estatus = (api_data.Estatus or "").strip()
            current_estatus = student.al_estatus.value if student.al_estatus else ""
            if api_estatus and api_estatus != current_estatus:
                try:
                    changes["al_estatus"] = StudentStatus(api_estatus)
                except ValueError:
                    pass

            if changes:
                for field, value in changes.items():
                    setattr(student, field, value)

                # Also update pp_alumnos name fields if they are stored there
                name_changes = {k: v for k, v in changes.items()
                                if k in ("al_nombre", "al_appat", "al_apmat")}
                if name_changes:
                    set_clause = ", ".join(f"{k} = :{k}" for k in name_changes)
                    try:
                        db.execute(
                            text(f"UPDATE pp_alumnos SET {set_clause} WHERE al_id = :al_id"),
                            {**name_changes, "al_id": student.al_id}
                        )
                    except Exception:
                        pass  # pp_alumnos may not have these columns in all environments

                db.commit()
                db.refresh(student)

            # Sync SCE005 (enrollment data: CCT, grado, grupo, turno)
            latest_enrollment = db.query(Enrollment).filter(
                Enrollment.al_id == student.al_id
            ).order_by(Enrollment.ciclo_escolar.desc()).first()

            if latest_enrollment:
                enrollment_changes = {}
                if api_data.CCT and api_data.CCT.strip() != (latest_enrollment.clavecct or "").strip():
                    enrollment_changes["clavecct"] = api_data.CCT.strip()
                if api_data.Grado and api_data.Grado.strip() != (latest_enrollment.eg_grado or "").strip():
                    enrollment_changes["eg_grado"] = api_data.Grado.strip()
                if api_data.Grupo and api_data.Grupo.strip() != (latest_enrollment.eg_grupo or "").strip():
                    enrollment_changes["eg_grupo"] = api_data.Grupo.strip()
                if api_data.Turno and api_data.Turno.strip() != (latest_enrollment.turno or "").strip():
                    enrollment_changes["turno"] = api_data.Turno.strip()

                if enrollment_changes:
                    for field, value in enrollment_changes.items():
                        setattr(latest_enrollment, field, value)
                    db.commit()
                    db.refresh(latest_enrollment)

        except Exception:
            # If the USEBEQ API is unavailable, proceed with existing local data
            pass
        # --- End sync ---

        enrollment = db.query(Enrollment).filter(
            Enrollment.al_id == student.al_id
        ).order_by(Enrollment.ciclo_escolar.desc()).first()

        students_data.append({
            "al_id": student.al_id,
            "al_curp": student.al_curp,
            "al_nombre": student.al_nombre,
            "al_appat": student.al_appat,
            "al_apmat": student.al_apmat,
            "al_estatus": student.al_estatus,
            "al_fecing": student.al_fecing,
            "al_fecnac": student.al_fecnac,
            "current_enrollment": enrollment
        })

    return students_data


@router.post("/link-student", status_code=status.HTTP_201_CREATED)
async def link_student(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_in: StudentParentCreate,
) -> Any:
    """
    Link a student to current user account by CURP
    Uses USEBEQ API to fetch student information and then links to parent account
    """
    # Initialize USEBEQ API service
    usebeq_service = USEBEQAPIService(db)

    # Extract CURP and get CCT if not provided
    curp = student_in.al_curp.strip().upper()

    # First, try to find student locally
    local_student = db.query(Student).filter(Student.al_curp == curp).first()

    if local_student:
        # Student exists locally, check if already linked
        existing = db.query(StudentParent).filter(
            StudentParent.al_id == local_student.al_id,
            StudentParent.u_id == current_user.u_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este estudiante ya esta vinculado a tu cuenta"
            )

        # Link existing student
        student_parent = StudentParent(
            al_id=local_student.al_id,
            u_id=current_user.u_id,
            relacion=student_in.relacion
        )
        db.add(student_parent)
        db.commit()

        return {
            "message": "Student linked successfully",
            "student": {
                "al_id": local_student.al_id,
                "al_curp": local_student.al_curp,
                "al_nombre": local_student.al_nombre,
                "al_appat": local_student.al_appat,
                "al_apmat": local_student.al_apmat,
                "al_estatus": local_student.al_estatus
            }
        }

    # Student not found locally, need CCT to query USEBEQ API
    # For now, return error asking for CCT
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Estudiante no encontrado. Intenta vincular con CURP y CCT."
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
    Link a student to current user account by CURP and CCT
    Fetches student information from USEBEQ API and creates local record

    Parameters:
    - curp: Student's CURP (18 characters)
    - cct: School's CCT code
    - relacion: Relationship (padre, madre, tutor)
    """
    # Validate inputs
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

    # Initialize USEBEQ API service
    usebeq_service = USEBEQAPIService(db)

    try:
        # Fetch student from USEBEQ API
        try:
            estudiante_data = await usebeq_service.get_estudiante_by_curp_cct(curp, cct)
        except Exception as api_error:
            # If API is down, try to find student in local database (SCE004)
            # This allows the system to work even when USEBEQ API is unavailable
            local_query = text("""
                SELECT al_id, al_curp, al_nombre, al_appat, al_apmat
                FROM SCE004
                WHERE al_curp = :curp
                LIMIT 1
            """)
            local_result = db.execute(local_query, {"curp": curp}).fetchone()

            if not local_result:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"API externa de USEBEQ no disponible y estudiante no encontrado en base local. Error: {str(api_error)}"
                )

            # Create mock estudiante_data from local database
            class MockEstudiante:
                def __init__(self, row):
                    self.IdAlumno = row[0]
                    self.CURP = row[1]
                    self.Nombre = row[2]
                    self.ApellidoPaterno = row[3]
                    self.ApellidoMaterno = row[4]
                    self.CCT = cct
                    self.Grado = "N/A"
                    self.Grupo = "N/A"
                    self.Estatus = "I"
                    self.NombreCT = "N/A"
                    self.Turno = "N/A"

            estudiante_data = MockEstudiante(local_result)

        # Check if student already exists in local DB (SCE004)
        local_student = db.query(Student).filter(Student.al_curp == curp).first()

        if local_student:
            student_id = local_student.al_id
        else:
            # Create new student record in SCE004 from USEBEQ data
            new_student = Student(
                al_id=estudiante_data.IdAlumno,
                al_curp=estudiante_data.CURP,
                al_nombre=estudiante_data.Nombre,
                al_appat=estudiante_data.ApellidoPaterno,
                al_apmat=estudiante_data.ApellidoMaterno,
                al_estatus=estudiante_data.Estatus.strip() if estudiante_data.Estatus else 'I'
            )
            db.add(new_student)
            db.flush()  # Get the ID without committing
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

        # Create link between parent and student
        student_parent = StudentParent(
            al_id=student_id,
            u_id=current_user.u_id,
            relacion=relacion
        )
        db.add(student_parent)
        db.commit()

        # Detect potential siblings — same non-empty al_appat + al_apmat, not already confirmed
        siblings_detected = []
        new_student_obj = db.query(Student).filter(Student.al_id == student_id).first()
        # Require BOTH last names to be non-empty before attempting sibling detection
        if (new_student_obj
                and new_student_obj.al_appat and new_student_obj.al_appat.strip()
                and new_student_obj.al_apmat and new_student_obj.al_apmat.strip()):
            all_linked = db.query(StudentParent).filter(
                StudentParent.u_id == current_user.u_id,
                StudentParent.al_id != student_id
            ).all()
            for sp in all_linked:
                other = db.query(Student).filter(Student.al_id == sp.al_id).first()
                # Both students must have non-empty last names that match exactly
                if (other
                        and other.al_apmat and other.al_apmat.strip()
                        and other.al_appat == new_student_obj.al_appat
                        and other.al_apmat == new_student_obj.al_apmat):
                    # Skip if sibling relationship already confirmed in pp_hermanos
                    already_confirmed = db.execute(text(
                        "SELECT h_id FROM pp_hermanos "
                        "WHERE (al_id = :id1 AND her_id = :id2) "
                        "OR (al_id = :id2 AND her_id = :id1)"
                    ), {"id1": student_id, "id2": other.al_id}).fetchone()
                    if not already_confirmed:
                        siblings_detected.append({
                            "al_id": other.al_id,
                            "nombre": f"{other.al_nombre} {other.al_appat}"
                        })

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
    count = db.execute(text(
        f"SELECT COUNT(*) FROM pp_hermanos "
        f"WHERE al_id IN ({placeholders}) OR her_id IN ({placeholders})"
    )).scalar()
    return {"count": count or 0}


@router.post("/confirm-sibling")
def confirm_sibling(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    al_id: int,
    her_id: int
) -> Any:
    """
    Confirm sibling relationship between two students already linked to the user.
    Inserts the relationship into pp_hermanos.
    """
    from sqlalchemy import text
    from datetime import datetime

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

    s1 = db.query(Student).filter(Student.al_id == al_id).first()
    s2 = db.query(Student).filter(Student.al_id == her_id).first()

    if not s1 or not s2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estudiante no encontrado")

    # Get current school year
    now = datetime.now()
    year = now.year if now.month > 7 else now.year - 1

    def get_enrollment(student_id):
        return db.execute(text("""
            SELECT dbo.SCE002.clavecct, dbo.SCE002.eg_grado, dbo.SCE002.eg_grupo
            FROM dbo.SCE002
            INNER JOIN dbo.SCE006 ON dbo.SCE002.eg_id = dbo.SCE006.eg_id
            WHERE dbo.SCE006.al_id = :al_id AND dbo.SCE002.ce_inicic = :year
        """), {"al_id": student_id, "year": str(year)}).fetchone()

    s1_info = get_enrollment(al_id)
    s2_info = get_enrollment(her_id)

    # Determine order: older sibling (smaller birth year in CURP[4:6]) goes as al_id
    year_s1 = s1.al_curp[4:6] if s1.al_curp and len(s1.al_curp) >= 6 else "99"
    year_s2 = s2.al_curp[4:6] if s2.al_curp and len(s2.al_curp) >= 6 else "99"

    if year_s1 <= year_s2:
        older, older_id, older_info = s1, al_id, s1_info
        younger, younger_id, younger_info = s2, her_id, s2_info
    else:
        older, older_id, older_info = s2, her_id, s2_info
        younger, younger_id, younger_info = s1, al_id, s1_info

    # Check if relationship already exists
    existing = db.execute(text(
        "SELECT h_id FROM pp_hermanos WHERE al_id = :al_id AND her_id = :her_id"
    ), {"al_id": older_id, "her_id": younger_id}).fetchone()

    if existing:
        return {"success": True, "message": "La relación de hermandad ya estaba registrada"}

    db.execute(text("""
        INSERT INTO pp_hermanos (
            al_id, al_curp, al_nombre, al_appat, al_apmat, al_cct, al_grado, al_grupo,
            her_id, her_curp, her_nombre, her_appat, her_apmat, her_cct, her_grado, her_grupo
        ) VALUES (
            :al_id, :al_curp, :al_nombre, :al_appat, :al_apmat, :al_cct, :al_grado, :al_grupo,
            :her_id, :her_curp, :her_nombre, :her_appat, :her_apmat, :her_cct, :her_grado, :her_grupo
        )
    """), {
        "al_id": older_id, "al_curp": older.al_curp, "al_nombre": older.al_nombre,
        "al_appat": older.al_appat, "al_apmat": older.al_apmat or "",
        "al_cct": older_info[0] if older_info else "", "al_grado": older_info[1] if older_info else "",
        "al_grupo": older_info[2] if older_info else "",
        "her_id": younger_id, "her_curp": younger.al_curp, "her_nombre": younger.al_nombre,
        "her_appat": younger.al_appat, "her_apmat": younger.al_apmat or "",
        "her_cct": younger_info[0] if younger_info else "", "her_grado": younger_info[1] if younger_info else "",
        "her_grupo": younger_info[2] if younger_info else ""
    })
    db.commit()

    return {"success": True, "message": "Relación de hermandad confirmada correctamente"}


@router.post("/add-student", response_model=AddStudentResponse)
def add_student_to_account(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_data: AddStudentRequest
) -> Any:
    """
    Add student to parent account with full validation

    This endpoint:
    - Validates student exists in SCE004
    - Validates apellido, CCT, and grupo match
    - Checks if student already linked to account
    - Automatically detects siblings
    - Links student to parent account
    """
    from sqlalchemy import text
    from datetime import datetime
    import unicodedata

    # Normalize input data
    curp = student_data.curp.strip().upper()
    apellido = student_data.apellido.strip().upper()
    cct = student_data.cct.strip().upper()
    grupo = student_data.grupo.strip().upper()
    parentesco = student_data.parentesco.upper()
    correo = current_user.u_correo

    # Remove accents from apellido
    def remove_accents(text):
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')

    apellido = remove_accents(apellido)

    # Validate parentesco
    if parentesco not in ['PADRE', 'MADRE', 'TUTOR']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parentesco debe ser PADRE, MADRE o TUTOR"
        )

    # Check if student already exists in pp_alumnos by CURP
    existing_query = text("SELECT al_id, padre, madre, tutor FROM pp_alumnos WHERE al_curp = :curp")
    existing_result = db.execute(existing_query, {"curp": curp}).fetchone()

    if existing_result:
        # Student already exists, update parentesco
        al_id = existing_result[0]
        padre = existing_result[1]
        madre = existing_result[2]
        tutor = existing_result[3]

        # Check if current user already linked with same parentesco
        if parentesco == 'PADRE' and padre == correo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este estudiante ya está vinculado a tu cuenta como PADRE"
            )
        if parentesco == 'MADRE' and madre == correo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este estudiante ya está vinculado a tu cuenta como MADRE"
            )
        if parentesco == 'TUTOR' and tutor == correo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este estudiante ya está vinculado a tu cuenta como TUTOR"
            )

        # Check if parentesco is already taken by ANOTHER user
        if parentesco == 'PADRE' and padre is not None and padre != correo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El parentesco PADRE ya ha sido vinculado al estudiante con otra cuenta. "
                       "Por favor verifica el vínculo que has seleccionado o intenta con un parentesco diferente. "
                       "En caso de necesitar apoyo puedes escribir a: epena@usebeq.edu.mx"
            )
        if parentesco == 'MADRE' and madre is not None and madre != correo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El parentesco MADRE ya ha sido vinculado al estudiante con otra cuenta. "
                       "Por favor verifica el vínculo que has seleccionado o intenta con un parentesco diferente. "
                       "En caso de necesitar apoyo puedes escribir a: epena@usebeq.edu.mx"
            )
        if parentesco == 'TUTOR' and tutor is not None and tutor != correo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El parentesco TUTOR ya ha sido vinculado al estudiante con otra cuenta. "
                       "Por favor verifica el vínculo que has seleccionado o intenta con un parentesco diferente. "
                       "En caso de necesitar apoyo puedes escribir a: epena@usebeq.edu.mx"
            )

        # Update parentesco
        update_field = parentesco.lower()
        update_query = text(f"UPDATE pp_alumnos SET {update_field} = :correo WHERE al_id = :al_id")
        db.execute(update_query, {"correo": correo, "al_id": al_id})
        db.commit()

        # Get student info
        student = db.query(Student).filter(Student.al_id == al_id).first()

        return AddStudentResponse(
            success=True,
            message="Estudiante agregado correctamente.",
            student={
                "al_id": student.al_id,
                "al_curp": student.al_curp,
                "al_nombre": student.al_nombre,
                "al_appat": student.al_appat,
                "al_apmat": student.al_apmat
            }
        )

    # Student doesn't exist in pp_alumnos, search in SCE004
    search_query = text("""
        SELECT dbo.SCE004.al_curp, dbo.SCE004.al_appat, dbo.SCE004.al_apmat,
               dbo.SCE004.al_nombre, dbo.SCE004.al_id, dbo.SCE002.eg_grado,
               dbo.SCE002.clavecct, dbo.SCE002.eg_grupo
        FROM dbo.SCE002
        INNER JOIN dbo.SCE006 ON dbo.SCE002.eg_id = dbo.SCE006.eg_id
        INNER JOIN dbo.SCE004 ON dbo.SCE006.al_id = dbo.SCE004.al_id
        WHERE dbo.SCE004.al_curp = :curp
        AND dbo.SCE004.al_appat = :apellido
        AND dbo.SCE002.clavecct = :cct
        AND dbo.SCE002.eg_grupo = :grupo
        AND dbo.SCE004.al_estatus IN ('I', 'A', 'E', 'B')
        GROUP BY dbo.SCE004.al_curp, dbo.SCE004.al_appat, dbo.SCE004.al_apmat,
                 dbo.SCE004.al_nombre, dbo.SCE004.al_id, dbo.SCE002.eg_grado,
                 dbo.SCE002.clavecct, dbo.SCE002.eg_grupo
    """)

    result = db.execute(search_query, {
        "curp": curp,
        "apellido": apellido,
        "cct": cct,
        "grupo": grupo
    }).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encuentra al estudiante. Intente nuevamente."
        )

    # Extract student info
    al_apmat = result[2]
    al_nombre = result[3]
    al_id = result[4]
    al_grado = result[5]
    al_cct = result[6]
    al_grupo = result[7]

    # Detect siblings automatically
    siblings_detected = []
    current_year = datetime.now().year
    month = datetime.now().month

    # Adjust year if in first half of year
    if month <= 7:
        current_year -= 1

    # Get all students already linked to this parent
    linked_students_query = text("""
        SELECT al_id, al_appat, al_apmat, al_nombre, al_curp
        FROM pp_alumnos
        WHERE padre = :correo OR madre = :correo OR tutor = :correo
    """)

    linked_students = db.execute(linked_students_query, {"correo": correo}).fetchall()

    for linked in linked_students:
        linked_al_id = linked[0]
        linked_appat = linked[1]
        linked_apmat = linked[2]
        linked_nombre = linked[3]
        linked_curp = linked[4]

        # Check if same apellidos (siblings)
        if apellido == linked_appat and al_apmat == linked_apmat:
            # Get linked student current info
            linked_info_query = text("""
                SELECT dbo.SCE004.al_curp, dbo.SCE002.eg_grado, dbo.SCE002.eg_grupo,
                       dbo.SCE002.clavecct
                FROM dbo.SCE002
                INNER JOIN dbo.SCE006 ON dbo.SCE002.eg_id = dbo.SCE006.eg_id
                INNER JOIN dbo.SCE004 ON dbo.SCE006.al_id = dbo.SCE004.al_id
                WHERE dbo.SCE004.al_id = :al_id
                AND dbo.SCE002.ce_inicic = :year
            """)

            linked_info = db.execute(linked_info_query, {
                "al_id": linked_al_id,
                "year": str(current_year)
            }).fetchone()

            if linked_info:
                # Potential sibling detected — do NOT auto-link; return for user confirmation
                siblings_detected.append({
                    "al_id": linked_al_id,
                    "nombre": f"{linked_nombre} {linked_appat}"
                })

    # Insert student into pp_alumnos
    fecha = datetime.now().strftime("%d-%m-%Y")

    insert_query = text(f"""
        INSERT INTO pp_alumnos (
            al_curp, al_appat, al_apmat, al_nombre, al_id,
            fecha_alta, estatus, {parentesco.lower()}
        ) VALUES (
            :al_curp, :al_appat, :al_apmat, :al_nombre, :al_id,
            :fecha_alta, :estatus, :correo
        )
    """)

    db.execute(insert_query, {
        "al_curp": curp,
        "al_appat": apellido,
        "al_apmat": al_apmat,
        "al_nombre": al_nombre,
        "al_id": al_id,
        "fecha_alta": fecha,
        "estatus": 'A',
        "correo": correo
    })

    db.commit()

    return AddStudentResponse(
        success=True,
        message="Estudiante agregado correctamente.",
        student={
            "al_id": al_id,
            "al_curp": curp,
            "al_nombre": al_nombre,
            "al_appat": apellido,
            "al_apmat": al_apmat,
            "grado": al_grado,
            "grupo": al_grupo,
            "cct": al_cct
        },
        siblings=siblings_detected if siblings_detected else None
    )


@router.get("/{student_id}/teachers")
def get_student_teachers(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    student_id: int
) -> Any:
    """
    Get list of teachers for a specific student

    Returns all teachers teaching the student's group
    """
    from sqlalchemy import text

    # Verify student belongs to current user
    verify_query = text("""
        SELECT al_id FROM pp_alumnos
        WHERE al_id = :student_id
        AND (padre = :correo OR madre = :correo OR tutor = :correo)
    """)

    result = db.execute(verify_query, {
        "student_id": student_id,
        "correo": current_user.u_correo
    }).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante"
        )

    # Get student's current group
    group_query = text("""
        SELECT dbo.SCE002.eg_id, dbo.SCE002.eg_grado, dbo.SCE002.eg_grupo,
               dbo.SCE002.clavecct, dbo.SCE002.nombrect, dbo.SCE002.turno
        FROM dbo.SCE002
        INNER JOIN dbo.SCE006 ON dbo.SCE002.eg_id = dbo.SCE006.eg_id
        WHERE dbo.SCE006.al_id = :student_id
    """)

    group_info = db.execute(group_query, {"student_id": student_id}).fetchone()

    if not group_info:
        return {
            "success": False,
            "message": "No se encontró información del grupo del estudiante",
            "teachers": []
        }

    eg_id = group_info[0]

    # Get teachers for this group
    teachers_query = text("""
        SELECT DISTINCT
            dbo.SCE034.ma_nombre,
            dbo.SCE034.ma_appat,
            dbo.SCE034.ma_apmat,
            dbo.SCE035.as_nombre as materia,
            dbo.SCE034.ma_correo
        FROM dbo.SCE023
        INNER JOIN dbo.SCE034 ON dbo.SCE023.ma_id = dbo.SCE034.ma_id
        INNER JOIN dbo.SCE035 ON dbo.SCE023.as_id = dbo.SCE035.as_id
        WHERE dbo.SCE023.eg_id = :eg_id
        ORDER BY dbo.SCE035.as_nombre
    """)

    teachers_result = db.execute(teachers_query, {"eg_id": eg_id}).fetchall()

    teachers = []
    for teacher in teachers_result:
        teachers.append({
            "nombre": f"{teacher[0]} {teacher[1]} {teacher[2] or ''}".strip(),
            "materia": teacher[3],
            "correo": teacher[4]
        })

    return {
        "success": True,
        "student_id": student_id,
        "group": {
            "grado": group_info[1],
            "grupo": group_info[2],
            "cct": group_info[3],
            "escuela": group_info[4],
            "turno": group_info[5]
        },
        "teachers": teachers,
        "total": len(teachers)
    }
