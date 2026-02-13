from typing import Any, List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FAQItem(BaseModel):
    id: int
    question: str
    answer: str
    category: str

FAQ_ITEMS = [
    FAQItem(id=1, question="\u00bfQu\u00e9 es el Portal para Padres?", answer="Es una plataforma digital de la USEBEQ que permite a los padres de familia, madres y tutores acceder a la informaci\u00f3n acad\u00e9mica de sus hijos, realizar tr\u00e1mites en l\u00ednea y mantenerse informados sobre avisos importantes de la instituci\u00f3n educativa.", category="General"),
    FAQItem(id=2, question="\u00bfPor qu\u00e9 registrar una cuenta?", answer="Al registrar una cuenta podr\u00e1s vincular a tus hijos estudiantes, consultar sus calificaciones, descargar boletas, realizar tr\u00e1mites como bajas por traslado, solicitar duplicados de certificados y recibir avisos importantes de la escuela.", category="General"),
    FAQItem(id=3, question="\u00bfQu\u00e9 pasa si no me registro?", answer="Sin una cuenta registrada no podr\u00e1s acceder a la informaci\u00f3n acad\u00e9mica de tus hijos ni realizar tr\u00e1mites en l\u00ednea. Tendr\u00edas que acudir personalmente a la escuela o las oficinas de la USEBEQ para realizar cualquier consulta o tr\u00e1mite.", category="General"),
    FAQItem(id=4, question="\u00bfC\u00f3mo me registro?", answer="Haz clic en el bot\u00f3n 'Registrarse' en la p\u00e1gina de inicio. Completa el formulario con tus datos personales (nombre, correo electr\u00f3nico, tel\u00e9fono, direcci\u00f3n) y crea una contrase\u00f1a. Recibir\u00e1s un correo de verificaci\u00f3n para activar tu cuenta.", category="Registro"),
    FAQItem(id=5, question="\u00bfC\u00f3mo consulto la informaci\u00f3n de mi hijo?", answer="Una vez que hayas iniciado sesi\u00f3n, ve al panel principal y haz clic en 'Vincular Estudiante'. Ingresa el CURP de tu hijo y la Clave del Centro de Trabajo (CCT) de su escuela. Una vez vinculado, podr\u00e1s ver toda su informaci\u00f3n acad\u00e9mica.", category="Consultas"),
    FAQItem(id=6, question="\u00bfPuedo agregar m\u00e1s de un estudiante?", answer="S\u00ed, puedes vincular m\u00faltiples estudiantes a tu cuenta. Solo necesitas el CURP y la CCT de cada estudiante. Esto es \u00fatil si tienes varios hijos en diferentes escuelas.", category="Consultas"),
    FAQItem(id=7, question="\u00bfQu\u00e9 es la Vinculaci\u00f3n de Hermanos?", answer="Es un proceso autom\u00e1tico que detecta si los estudiantes que vinculas a tu cuenta son hermanos (comparten apellidos). El sistema los vincula autom\u00e1ticamente para facilitar la gesti\u00f3n de la informaci\u00f3n familiar.", category="Vinculaci\u00f3n"),
    FAQItem(id=8, question="\u00bfQu\u00e9 es el Buz\u00f3n para Padres?", answer="Es un medio de comunicaci\u00f3n digital donde puedes enviar y recibir documentos relacionados con la educaci\u00f3n de tus hijos. Permite mantener una comunicaci\u00f3n directa con la instituci\u00f3n educativa.", category="Comunicaci\u00f3n"),
    FAQItem(id=9, question="\u00bfQu\u00e9 es una Baja por Traslado?", answer="Es el tr\u00e1mite que se realiza cuando un estudiante necesita cambiar de escuela, ya sea dentro del mismo estado o a otra entidad. A trav\u00e9s del portal puedes solicitar la baja, dar seguimiento al proceso y descargar la documentaci\u00f3n necesaria.", category="Tr\u00e1mites"),
    FAQItem(id=10, question="\u00bfQu\u00e9 es el duplicado de certificado?", answer="Es la reimpresi\u00f3n de un certificado de estudios (preescolar, primaria o secundaria) que ya fue emitido anteriormente. Se puede solicitar en caso de extrav\u00edo o deterioro del documento original.", category="Tr\u00e1mites"),
    FAQItem(id=11, question="\u00bfQu\u00e9 son las solicitudes en l\u00ednea?", answer="Son tr\u00e1mites administrativos que puedes realizar de forma digital sin necesidad de acudir a las oficinas. Incluyen diversos procedimientos como correcciones de datos, cambios administrativos y otras gestiones escolares.", category="Tr\u00e1mites"),
    FAQItem(id=12, question="\u00bfQu\u00e9 hago si no recib\u00ed el correo de verificaci\u00f3n?", answer="Verifica tu carpeta de correo no deseado o spam. Si no lo encuentras, puedes solicitar el reenv\u00edo del correo de verificaci\u00f3n desde la p\u00e1gina de inicio de sesi\u00f3n haciendo clic en 'Reenviar correo de verificaci\u00f3n'.", category="Registro"),
]

@router.get("/", response_model=List[FAQItem])
def get_faq() -> Any:
    """Get all FAQ items"""
    return FAQ_ITEMS

@router.get("/category/{category}", response_model=List[FAQItem])
def get_faq_by_category(category: str) -> Any:
    """Get FAQ items by category"""
    return [item for item in FAQ_ITEMS if item.category.lower() == category.lower()]
