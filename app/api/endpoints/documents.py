from typing import Any, List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class NormativeDocument(BaseModel):
    id: int
    title: str
    description: str
    category: str
    url: str
    file_type: str = "pdf"

NORMATIVE_DOCUMENTS = [
    NormativeDocument(
        id=1,
        title="ACUERDO 10/09/23",
        description="Normas generales para la evaluación del aprendizaje, acreditación, promoción, regularización y certificación de los educandos de la educación básica",
        category="Acuerdos",
        url="/documents/ACUERDO100923.pdf",
        file_type="pdf"
    ),
    NormativeDocument(
        id=2,
        title="Normas Específicas de Control Escolar",
        description="Normas Específicas de Control Escolar relativas a la Inscripción, Reinscripción, Acreditación, Promoción, Regularización y Certificación en la Educación Básica 2019",
        category="Normas",
        url="/documents/normas_29042019.pdf",
        file_type="pdf"
    ),
    NormativeDocument(
        id=3,
        title="Anexos",
        description="Anexos de las Normas Específicas de Control Escolar",
        category="Anexos",
        url="/documents/Anexo_02052019.pdf",
        file_type="pdf"
    ),
    NormativeDocument(
        id=4,
        title="Lineamientos para la Promoción Anticipada",
        description="Lineamientos para la acreditación, promoción y certificación anticipada de alumnos con aptitudes sobresalientes en Educación Básica",
        category="Lineamientos",
        url="/documents/linemientos_29042019.pdf",
        file_type="pdf"
    ),
    NormativeDocument(
        id=5,
        title="Anexo 8",
        description="Anexo 8 - Documentación complementaria de Control Escolar",
        category="Anexos",
        url="/documents/Anexo_8.pdf",
        file_type="pdf"
    ),
]

@router.get("/", response_model=List[NormativeDocument])
def get_normative_documents() -> Any:
    """Get all normative documents"""
    return NORMATIVE_DOCUMENTS

@router.get("/{document_id}", response_model=NormativeDocument)
def get_document(document_id: int) -> Any:
    """Get a specific normative document by ID"""
    from fastapi import HTTPException, status
    doc = next((d for d in NORMATIVE_DOCUMENTS if d.id == document_id), None)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return doc
