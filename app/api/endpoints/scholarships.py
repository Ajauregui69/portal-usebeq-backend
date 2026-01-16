# -*- coding: utf-8 -*-
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/info")
def get_scholarships_info(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get information about available scholarships
    """
    return {
        "success": True,
        "message": "Informacion sobre becas disponibles",
        "scholarships": [
            {
                "nombre": "Beca de Apoyo a la Educacion Basica",
                "descripcion": "Apoyo economico para estudiantes de educacion basica en situacion vulnerable",
                "requisitos": [
                    "Estar inscrito en una escuela publica del estado de Queretaro",
                    "Presentar situacion economica vulnerable",
                    "Mantener promedio minimo de 8.0"
                ],
                "contacto": "becas@usebeq.edu.mx"
            },
            {
                "nombre": "Beca de Excelencia Academica",
                "descripcion": "Reconocimiento a estudiantes con alto rendimiento academico",
                "requisitos": [
                    "Promedio general minimo de 9.5",
                    "No haber reprobado ninguna materia"
                ],
                "contacto": "excelencia@usebeq.edu.mx"
            }
        ],
        "enlaces": [
            {
                "nombre": "Portal de Becas USEBEQ",
                "url": "https://www.usebeq.edu.mx/becas"
            }
        ]
    }
