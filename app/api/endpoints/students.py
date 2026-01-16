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
def get_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all students linked to current user
    """
    # Get student-parent relationships
    student_parents = db.query(StudentParent).filter(
        StudentParent.u_id == current_user.u_id
    ).all()

    students_data = []
    for sp in student_parents:
        student = db.query(Student).filter(Student.al_id == sp.al_id).first()
        if student:
            # Get latest enrollment
            enrollment = db.query(Enrollment).filter(
                Enrollment.al_id == student.al_id
            ).order_by(Enrollment.ciclo_escolar.desc()).first()

            student_dict = {
                "al_id": student.al_id,
                "al_curp": student.al_curp,
                "al_nombre": student.al_nombre,
                "al_appat": student.al_appat,
                "al_apmat": student.al_apmat,
                "al_estatus": student.al_estatus,
                "al_fecing": student.al_fecing,
                "al_fecnac": student.al_fecnac,
                "current_enrollment": enrollment
            }
            students_data.append(student_dict)

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
                detail="Student already linked to your account"
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
        detail="Student not found. Please use /link-student-with-cct endpoint and provide CCT"
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
            detail="Relacion must be: padre, madre, or tutor"
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
                detail="Student already linked to your account"
            )

        # Create link between parent and student
        student_parent = StudentParent(
            al_id=student_id,
            u_id=current_user.u_id,
            relacion=relacion
        )
        db.add(student_parent)
        db.commit()

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
            }
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
            detail="Student link not found"
        )

    db.delete(student_parent)
    db.commit()

    return {"message": "Student unlinked successfully"}


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

        # Check if current user already linked
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
                linked_al_cct = linked_info[3]
                linked_al_grado = linked_info[1]
                linked_al_grupo = linked_info[2]

                # Determine order by birth year in CURP (positions 4-5)
                year_new = curp[4:6]
                year_linked = linked_curp[4:6]

                # Insert sibling relationship in correct order
                if year_new < year_linked:
                    # New student is older
                    check_sibling = text("""
                        SELECT h_id FROM pp_hermanos
                        WHERE al_id = :al_id AND her_id = :her_id
                    """)
                    exists = db.execute(check_sibling, {
                        "al_id": al_id,
                        "her_id": linked_al_id
                    }).fetchone()

                    if not exists:
                        insert_sibling = text("""
                            INSERT INTO pp_hermanos (
                                al_id, al_curp, al_nombre, al_appat, al_apmat,
                                al_cct, al_grado, al_grupo,
                                her_id, her_curp, her_nombre, her_appat, her_apmat,
                                her_cct, her_grado, her_grupo
                            ) VALUES (
                                :al_id, :al_curp, :al_nombre, :al_appat, :al_apmat,
                                :al_cct, :al_grado, :al_grupo,
                                :her_id, :her_curp, :her_nombre, :her_appat, :her_apmat,
                                :her_cct, :her_grado, :her_grupo
                            )
                        """)
                        db.execute(insert_sibling, {
                            "al_id": al_id, "al_curp": curp, "al_nombre": al_nombre,
                            "al_appat": apellido, "al_apmat": al_apmat,
                            "al_cct": al_cct, "al_grado": al_grado, "al_grupo": al_grupo,
                            "her_id": linked_al_id, "her_curp": linked_curp,
                            "her_nombre": linked_nombre, "her_appat": linked_appat,
                            "her_apmat": linked_apmat, "her_cct": linked_al_cct,
                            "her_grado": linked_al_grado, "her_grupo": linked_al_grupo
                        })
                        siblings_detected.append(linked_nombre + " " + linked_appat)

                else:
                    # Linked student is older
                    check_sibling = text("""
                        SELECT h_id FROM pp_hermanos
                        WHERE al_id = :al_id AND her_id = :her_id
                    """)
                    exists = db.execute(check_sibling, {
                        "al_id": linked_al_id,
                        "her_id": al_id
                    }).fetchone()

                    if not exists:
                        insert_sibling = text("""
                            INSERT INTO pp_hermanos (
                                al_id, al_curp, al_nombre, al_appat, al_apmat,
                                al_cct, al_grado, al_grupo,
                                her_id, her_curp, her_nombre, her_appat, her_apmat,
                                her_cct, her_grado, her_grupo
                            ) VALUES (
                                :al_id, :al_curp, :al_nombre, :al_appat, :al_apmat,
                                :al_cct, :al_grado, :al_grupo,
                                :her_id, :her_curp, :her_nombre, :her_appat, :her_apmat,
                                :her_cct, :her_grado, :her_grupo
                            )
                        """)
                        db.execute(insert_sibling, {
                            "al_id": linked_al_id, "al_curp": linked_curp,
                            "al_nombre": linked_nombre, "al_appat": linked_appat,
                            "al_apmat": linked_apmat, "al_cct": linked_al_cct,
                            "al_grado": linked_al_grado, "al_grupo": linked_al_grupo,
                            "her_id": al_id, "her_curp": curp,
                            "her_nombre": al_nombre, "her_appat": apellido,
                            "her_apmat": al_apmat, "her_cct": al_cct,
                            "her_grado": al_grado, "her_grupo": al_grupo
                        })
                        siblings_detected.append(linked_nombre + " " + linked_appat)

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
