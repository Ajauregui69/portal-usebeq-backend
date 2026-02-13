"""
PDF Receipt Generation for tramites.
Generates PDF receipts for bajas, revocaciones, solicitudes, and duplicados.
Matches PHP portal's imprime_*.php files using reportlab.
"""
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User

router = APIRouter()


def get_nivel_completo(nivel: str) -> str:
    mapping = {
        'PRE': 'PREESCOLAR',
        'PRI': 'PRIMARIA',
        'SEC': 'SECUNDARIA',
    }
    return mapping.get(nivel.upper().strip() if nivel else '', nivel or '')


def create_pdf_header(c, title: str):
    """Create standard USEBEQ PDF header."""
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor

    # Header bar
    c.setFillColor(HexColor('#1a3a6c'))
    c.rect(0, 770, 612, 50, fill=True)

    c.setFillColor(HexColor('#ffffff'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, 800, "UNIDAD DE SERVICIOS PARA LA EDUCACION BASICA")
    c.setFont("Helvetica", 8)
    c.drawString(30, 788, "EN EL ESTADO DE QUERETARO")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(30, 775, "PORTAL PARA PADRES DE FAMILIA")

    # Title
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, 750, title)

    # Separator line
    c.setStrokeColor(HexColor('#1a3a6c'))
    c.setLineWidth(2)
    c.line(30, 745, 582, 745)


def create_section(c, y, label, value, x_label=30, x_value=200):
    """Create a label-value pair in the PDF."""
    from reportlab.lib.colors import HexColor
    c.setFillColor(HexColor('#555555'))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_label, y, label)
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica", 9)
    c.drawString(x_value, y, str(value) if value else "")
    return y - 18


def create_legal_notice(c, y):
    """Add standard legal notice."""
    from reportlab.lib.colors import HexColor
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor('#666666'))
    c.drawString(30, y, "SE GENERA EL PRESENTE DOCUMENTO A SOLICITUD DEL PADRE, MADRE DE FAMILIA O TUTOR,")
    c.drawString(30, y - 10, "PARA LOS FINES ACADEMICOS QUE CONSIDERE.")
    c.setFont("Helvetica", 7)
    c.drawString(30, y - 25, f"FECHA DE IMPRESION: {datetime.now().strftime('%d-%m-%Y %H:%M')}")


# ==================== BAJA POR TRASLADO PDF ====================

class BajaReceiptRequest(BaseModel):
    curp: str
    nombre: str
    cct: str
    nombre_escuela: str
    grado: str
    grupo: str
    nivel: str
    motivo: str
    parentesco: str


@router.post("/baja")
def generate_baja_pdf(
    data: BajaReceiptRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate PDF receipt for withdrawal (baja) request."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    create_pdf_header(c, "SOLICITUD DE BAJA POR TRASLADO")

    # CURP and date
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(HexColor('#cc0000'))
    c.drawRightString(582, 730, f"CURP: {data.curp}")
    c.setFillColor(HexColor('#333333'))
    c.setFont("Helvetica", 9)
    c.drawRightString(582, 718, f"Fecha: {datetime.now().strftime('%d-%m-%Y')}")

    # Request body
    y = 690
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica", 9)

    nivel_completo = get_nivel_completo(data.nivel)
    texto = (
        f"Yo, {data.parentesco} del menor: {data.nombre}, que esta inscrito en el grado {data.grado}, "
        f"grupo {data.grupo}, de la escuela {data.nombre_escuela} con clave {data.cct}, del nivel "
        f"{nivel_completo}, solicito su intervencion para gestionar la baja en el Sistema en Linea "
        f"de Control Escolar del Estado de Queretaro (SILCEQ)."
    )

    # Word wrap
    from reportlab.lib.utils import simpleSplit
    lines = simpleSplit(texto, "Helvetica", 9, 530)
    for line in lines:
        c.drawString(30, y, line)
        y -= 14

    # Student info section
    y -= 20
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS DEL ESTUDIANTE")

    y -= 25
    y = create_section(c, y, "Nombre del Estudiante:", data.nombre)
    y = create_section(c, y, "CURP:", data.curp)
    y = create_section(c, y, "CCT Escuela:", data.cct)
    y = create_section(c, y, "Escuela:", data.nombre_escuela)
    y = create_section(c, y, "Estado:", "QUERETARO")

    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS ACADEMICOS")

    y -= 25
    y = create_section(c, y, "Nivel:", nivel_completo)
    y = create_section(c, y, "Grado:", data.grado)
    y = create_section(c, y, "Grupo:", data.grupo)
    y = create_section(c, y, "Fecha de Baja:", datetime.now().strftime('%d-%m-%Y'))

    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "MOTIVO Y SOLICITANTE")

    y -= 25
    y = create_section(c, y, "Motivo:", data.motivo)
    y = create_section(c, y, "Solicita:", data.parentesco)

    y -= 30
    create_legal_notice(c, y)

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=solicitud_baja_{data.curp}.pdf"}
    )


# ==================== REVOCACION DE GRADO PDF (ANEXO 8) ====================

class RevocacionReceiptRequest(BaseModel):
    nombre_alumno: str
    curp: str
    grado: str
    nivel: str
    cct: str
    nombre_escuela: str
    ciclo: str
    nombre_padre: str
    telefono: str
    correo: str
    folio: Optional[str] = None


@router.post("/revocacion")
def generate_revocacion_pdf(
    data: RevocacionReceiptRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate Anexo 8 PDF for grade revocation authorization."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Header
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#333333'))
    c.drawRightString(582, 790, "Direccion General de Acreditacion, Incorporacion y Revalidacion")

    create_pdf_header(c, "ANEXO 8 - AUTORIZACION EXPRESA PARA REVOCAR PROMOCION")

    nivel_completo = get_nivel_completo(data.nivel)
    fecha = datetime.now().strftime('%d de %B de %Y')
    folio = data.folio or "PENDIENTE"

    y = 720
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#000000'))

    # Subtitle
    lines = simpleSplit(
        "Anexo 8. Autorizacion Expresa de la madre, el padre de familia o tutor para "
        "revocar la promocion de cualquier grado de su hijo.",
        "Helvetica", 9, 530
    )
    for line in lines:
        c.drawString(30, y, line)
        y -= 14

    y -= 15
    y = create_section(c, y, "Escuela:", data.nombre_escuela)
    y = create_section(c, y, "CCT:", data.cct)
    y = create_section(c, y, "Fecha:", fecha)
    y = create_section(c, y, "Folio:", folio)

    y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, y, "P R E S E N T E :")

    y -= 25
    c.setFont("Helvetica", 9)
    texto = (
        f"Por medio del presente, manifiesto que soy madre, padre de familia o tutor del alumno(a) "
        f"{data.nombre_alumno} con CURP {data.curp}, inscrito(a) en el {data.grado} grado de nivel "
        f"{nivel_completo} del ciclo escolar {data.ciclo}, y que otorgo mi consentimiento para que "
        f"sea reinstalado(a) en el mismo grado."
    )
    lines = simpleSplit(texto, "Helvetica", 9, 530)
    for line in lines:
        c.drawString(30, y, line)
        y -= 14

    y -= 10
    texto2 = (
        "Estoy enterado(a) de las consecuencias pedagogicas, psicologicas y legales que conlleva "
        "la decision de revocar la promocion de mi hijo(a)."
    )
    lines = simpleSplit(texto2, "Helvetica", 9, 530)
    for line in lines:
        c.drawString(30, y, line)
        y -= 14

    y -= 10
    texto3 = (
        "Asi mismo, estoy enterado(a) que en caso de solicitar un cambio de plantel, la "
        "inscripcion se realizara con base en la colocacion de grado y NO por la edad del alumno(a)."
    )
    lines = simpleSplit(texto3, "Helvetica", 9, 530)
    for line in lines:
        c.drawString(30, y, line)
        y -= 14

    # Signature section
    y -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(306, y, "Atentamente")

    y -= 35
    c.line(200, y, 420, y)
    y -= 12
    c.setFont("Helvetica", 9)
    c.drawCentredString(306, y, data.nombre_padre)

    y -= 20
    y = create_section(c, y, "Correo:", data.correo)
    y = create_section(c, y, "Telefono:", data.telefono)

    y -= 20
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor('#666666'))
    c.drawString(30, y, "c.c.p. Area de Control Escolar de la Supervision de Zona")

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=anexo8_revocacion_{data.curp}.pdf"}
    )


# ==================== COMPROBANTE DE REVOCACION APROBADA ====================

@router.get("/revocacion/comprobante/{folio}")
def generate_revocacion_comprobante(
    folio: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate PDF receipt for approved grade revocation."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor

    query = text("""
        SELECT curp, nombre_alumno, cct, nombre_escuela, grado, folio,
               nivel, ciclo, nombre_padre, fecha_elaborado
        FROM tramite_revocaciong
        WHERE folio = :folio AND estatus = 'APROBADA'
    """)

    result = db.execute(query, {"folio": folio}).fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro solicitud aprobada con ese folio"
        )

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    create_pdf_header(c, "COMPROBANTE DE REVOCACION DE GRADO")

    y = 720
    # Student section
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS DEL ESTUDIANTE")

    y -= 25
    y = create_section(c, y, "Nombre:", result[1])
    y = create_section(c, y, "CURP:", result[0])

    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS ESCOLARES")

    y -= 25
    y = create_section(c, y, "CCT:", result[2])
    y = create_section(c, y, "Escuela:", result[3])
    y = create_section(c, y, "Estado:", "QUERETARO")

    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS ACADEMICOS")

    nivel_completo = get_nivel_completo(result[6])
    y -= 25
    y = create_section(c, y, "Ciclo Escolar:", result[7])
    y = create_section(c, y, "Nivel:", nivel_completo)
    y = create_section(c, y, "Grado:", result[4])
    y = create_section(c, y, "Folio:", result[5])
    y = create_section(c, y, "Fecha Aprobacion:", str(result[9]) if result[9] else "")

    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "PROCESO")

    y -= 25
    y = create_section(c, y, "Tramite:", "REVOCACION DE GRADO")
    y = create_section(c, y, "Solicitante:", result[8])

    y -= 30
    create_legal_notice(c, y)

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comprobante_revocacion_{folio}.pdf"}
    )


# ==================== SOLICITUD EN LINEA PDF ====================

class SolicitudReceiptRequest(BaseModel):
    tipo_tramite: str
    nombre_alumno: str
    apellido_paterno: str
    apellido_materno: str
    folio: str


@router.post("/solicitud")
def generate_solicitud_pdf(
    data: SolicitudReceiptRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate PDF receipt for online process request."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    create_pdf_header(c, "COMPROBANTE DE SOLICITUD EN LINEA")

    y = 720

    # Folio
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(HexColor('#cc0000'))
    c.drawRightString(582, y, data.folio)

    y -= 20
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#333333'))
    c.drawRightString(582, y, f"Fecha de solicitud: {datetime.now().strftime('%d-%m-%Y')}")

    y -= 30
    nombre_completo = f"{data.nombre_alumno} {data.apellido_paterno} {data.apellido_materno}"
    y = create_section(c, y, "Alumno:", nombre_completo)
    y = create_section(c, y, "Tipo de Tramite:", data.tipo_tramite)

    y -= 20
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "INSTRUCCIONES")

    y -= 25
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#000000'))
    instrucciones = [
        f"- En caso de dudas comunicarse a: epena@usebeq.edu.mx",
        f"- El tiempo de procesamiento es de 6 dias habiles.",
        f"- Los documentos que no sean recogidos en un plazo de 3 meses seran cancelados.",
        f"- Los documentos NO se envian por correo electronico.",
        f"- Puede consultar el estatus de su tramite en el portal.",
    ]
    for inst in instrucciones:
        c.drawString(40, y, inst)
        y -= 14

    y -= 30
    create_legal_notice(c, y)

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comprobante_solicitud_{data.folio}.pdf"}
    )


# ==================== DUPLICADO DE CERTIFICADO PDF ====================

class DuplicadoReceiptRequest(BaseModel):
    curp: str
    folio: str
    nombre_alumno: str
    apellido_paterno: str
    apellido_materno: str
    nombre_escuela: str
    turno: str
    cct: str
    tipo_tramite: str
    ciclo: str


@router.post("/duplicado")
def generate_duplicado_pdf(
    data: DuplicadoReceiptRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate PDF receipt for certificate duplicate request."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    create_pdf_header(c, "COMPROBANTE DE SOLICITUD DE DUPLICADO")

    y = 720

    # Folio
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(HexColor('#cc0000'))
    c.drawCentredString(306, y, data.folio)

    y -= 20
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#333333'))
    c.drawRightString(582, y, f"Fecha de solicitud: {datetime.now().strftime('%d-%m-%Y')}")

    # Student info
    y -= 20
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS DEL ALUMNO")

    nombre_completo = f"{data.nombre_alumno} {data.apellido_paterno} {data.apellido_materno}"
    y -= 25
    y = create_section(c, y, "Alumno:", nombre_completo)
    y = create_section(c, y, "CURP:", data.curp)

    # School info
    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS ESCOLARES")

    y -= 25
    y = create_section(c, y, "Escuela:", data.nombre_escuela)
    y = create_section(c, y, "Turno:", data.turno)
    y = create_section(c, y, "CCT:", data.cct)

    # Process info
    y -= 10
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "DATOS DEL TRAMITE")

    y -= 25
    y = create_section(c, y, "Tipo de Tramite:", data.tipo_tramite)
    y = create_section(c, y, "Ciclo de Terminacion:", data.ciclo)

    # Instructions
    y -= 20
    c.setFillColor(HexColor('#e8e8e8'))
    c.rect(30, y - 5, 552, 18, fill=True)
    c.setFillColor(HexColor('#1a3a6c'))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(35, y, "INSTRUCCIONES")

    y -= 25
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor('#000000'))
    instrucciones = [
        "- En caso de dudas comunicarse a: epena@usebeq.edu.mx o al 442-238-6000 ext. 1330",
        "- El tiempo de procesamiento es de 6 dias habiles.",
        "- Los documentos que no sean recogidos en un plazo de 3 meses seran cancelados.",
        "- IMPORTANTE: Los documentos NO se envian por correo electronico.",
        "- Puede consultar el estatus de su tramite a traves del portal.",
    ]
    for inst in instrucciones:
        c.drawString(40, y, inst)
        y -= 14

    y -= 30
    create_legal_notice(c, y)

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comprobante_duplicado_{data.folio}.pdf"}
    )
