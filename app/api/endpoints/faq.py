from typing import Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FAQItem(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    video_url: Optional[str] = None
    link_text: Optional[str] = None
    link_url: Optional[str] = None

FAQ_ITEMS = [
    FAQItem(id=1, question="¿Qué es el Portal para Padres?", answer="Es una opción adicional a la escuela que permite a las madres, padres de familia o tutores conocer la información académica de los estudiantes que cursan Preescolar, Primaria y Secundaria en el estado de Querétaro.", category="General"),
    FAQItem(id=2, question="¿Por qué es necesario registrar una cuenta?", answer="Para tener acceso a la impresión de los documentos oficiales de acreditación.", category="General"),
    FAQItem(id=3, question="¿Qué pasa si no registro una cuenta?", answer="No será posible consultar la información específica del estudiante.", category="General"),
    FAQItem(id=4, question="¿Cómo registro mi cuenta?", answer="Ingresa a la opción \"Registra tu cuenta\", donde será necesario darse de alta con una dirección de correo electrónico vigente y definir una contraseña. Consulta el tutorial a continuación.", category="Registro", video_url="/videos/registro.webm"),
    FAQItem(id=5, question="¿Cómo visualizo la información del estudiante?", answer="Es necesario agregarlo a tu perfil de usuario. Consulta el tutorial a continuación.", category="Consultas", video_url="/videos/sesion.webm"),
    FAQItem(id=6, question="¿Puedo agregar varios estudiantes a mi perfil?", answer="Sí, siempre y cuando sea posible la vinculación a partir de los datos del estudiante con el padre, madre de familia o tutor.", category="Consultas"),
    FAQItem(id=7, question="¿Qué es la Vinculación de Hermanos?", answer="Es el procedimiento que permite identificar el parentesco consanguíneo o por afinidad entre estudiantes que cursan la educación básica en el estado de Querétaro.", category="Vinculación"),
    FAQItem(id=8, question="¿Qué función tiene el Buzón para Padres de Familia?", answer="Es el medio para hacer llegar la documentación necesaria sujeta a cotejo para aclaraciones o trámites.", category="Comunicación"),
    FAQItem(id=9, question="¿Qué es una Baja por Traslado?", answer="Es la asignación del estatus de baja a un estudiante que será transferido de una escuela a otra.", category="Trámites"),
    FAQItem(id=10, question="¿Qué es un duplicado de certificado y cuándo solicitarlo?", answer="La certificación o duplicado de certificado es la emisión del documento que acredita un nivel educativo a partir del antecedente académico del educando. Se solicita cuando el original fue extraviado o es necesario actualizar la emisión del mismo.", category="Trámites"),
    FAQItem(id=11, question="¿Qué son las solicitudes en línea?", answer="Son los trámites que se encuentran disponibles desde el Portal para Padres de Familia, algunos de los cuales pueden ser realizados en su totalidad a distancia.", category="Trámites"),
    FAQItem(id=12, question="¿Qué pasa si no he recibido el correo de verificación de la cuenta?", answer="Si no has recibido el correo de validación, para que se reenvíe el mensaje", category="Registro", link_text="haz clic aquí", link_url="/register"),
]

@router.get("/", response_model=List[FAQItem])
def get_faq() -> Any:
    """Get all FAQ items"""
    return FAQ_ITEMS

@router.get("/category/{category}", response_model=List[FAQItem])
def get_faq_by_category(category: str) -> Any:
    """Get FAQ items by category"""
    return [item for item in FAQ_ITEMS if item.category.lower() == category.lower()]
