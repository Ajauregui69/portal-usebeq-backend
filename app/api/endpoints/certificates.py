from typing import Any
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, text

from app.core.database import get_db
from app.models.certificate import (
    CertificateRequest,
    TipoTramite,
    TramiteStatus,
    TramiteEntregado
)
from app.schemas.certificate import (
    CertificateRequestCreate,
    CertificateRequestResponse,
    CertificateStatusResponse,
    CertificateListResponse
)

router = APIRouter()


def generate_folio(db: Session, region: str) -> str:
    """
    Generate new folio for certificate request based on region
    Format: YEAR-REGION-00001
    """
    year = datetime.now().year

    # Map region number to roman numerals
    region_map = {
        "1": "I",
        "2": "II",
        "3": "III",
        "4": "IV"
    }

    region_roman = region_map.get(region, "IV")

    # Get last folio for this region
    last_request = db.query(CertificateRequest).filter(
        CertificateRequest.region == region
    ).order_by(desc(CertificateRequest.folio)).first()

    if not last_request or not last_request.folio:
        return f"{year}-{region_roman}-00001"

    # Check if folio is from current year
    folio_year = int(last_request.folio.split('-')[0])

    if folio_year != year:
        return f"{year}-{region_roman}-00001"

    # Increment folio
    folio_parts = last_request.folio.split('-')
    folio_num = int(folio_parts[2]) + 1

    return f"{year}-{region_roman}-{folio_num:05d}"


def check_existing_request(db: Session, curp: str, tipo_tramite: TipoTramite) -> dict:
    """
    Check if there's an existing certificate request
    Returns dict with status and message
    """
    # Check for existing requests
    existing_count = db.query(CertificateRequest).filter(
        CertificateRequest.curp == curp,
        CertificateRequest.tipo_tramite == tipo_tramite
    ).count()

    if existing_count == 0:
        return {"status": "NEW", "requires_payment": False}

    # Check for firmado or REIMPRESION status
    firmado_count = db.query(CertificateRequest).filter(
        CertificateRequest.curp == curp,
        CertificateRequest.tipo_tramite == tipo_tramite,
        CertificateRequest.status.in_([TramiteStatus.FIRMADO, TramiteStatus.REIMPRESION])
    ).count()

    if firmado_count == 0:
        # There's a request in process
        latest = db.query(CertificateRequest).filter(
            CertificateRequest.curp == curp,
            CertificateRequest.tipo_tramite == tipo_tramite
        ).order_by(desc(CertificateRequest.folio)).first()

        return {
            "status": "IN_PROCESS",
            "folio": latest.folio,
            "requires_payment": False
        }

    # Get latest firmado/REIMPRESION request
    latest = db.query(CertificateRequest).filter(
        CertificateRequest.curp == curp,
        CertificateRequest.tipo_tramite == tipo_tramite,
        CertificateRequest.status.in_([TramiteStatus.FIRMADO, TramiteStatus.REIMPRESION])
    ).order_by(desc(CertificateRequest.fecha_elaborado)).first()

    # Calculate days difference
    today = date.today()
    days_diff = (today - latest.fecha_elaborado).days if latest.fecha_elaborado else 0

    # Check if payment/delivery status allows free reprint
    if latest.entregado in [TramiteEntregado.PAGADO, TramiteEntregado.ENTREGADO] and days_diff >= 30:
        return {"status": "NEW", "requires_payment": False}

    # Check if more than 1 year passed
    if days_diff >= 366:
        return {"status": "NEW", "requires_payment": False}

    # Requires payment
    return {
        "status": "IN_PROCESS",
        "folio": latest.folio,
        "requires_payment": True
    }


def check_duplicate_in_system(db: Session, curp: str, cct: str, ciclo_terminacion: str) -> bool:
    """
    Check if certificate was already issued in SCE039_DUPLI table
    """
    year_ini = ciclo_terminacion.split('-')[0]

    # Query SCE039_DUPLI table
    query = text("""
        SELECT COUNT(*) as count
        FROM SCE039_DUPLI
        WHERE ce_inicic = :year_ini
        AND clavecct = :cct
        AND al_curp = :curp
    """)

    result = db.execute(query, {"year_ini": year_ini, "cct": cct, "curp": curp}).fetchone()

    return result[0] > 0 if result else False


@router.post("/request", response_model=CertificateRequestResponse)
def request_certificate(
    *,
    db: Session = Depends(get_db),
    certificate_data: CertificateRequestCreate
) -> Any:
    """
    Request a new certificate

    Logic:
    - First time: FREE
    - Reprint after 30 days if paid/delivered: FREE
    - Reprint after 1 year: FREE
    - Otherwise: REQUIRES PAYMENT
    """
    # Normalize data
    curp = certificate_data.curp.strip().upper()
    cct = certificate_data.cct.strip().upper()

    # Validate CCT belongs to Queretaro (state code 22)
    if not cct.startswith('22'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave de la escuela no corresponde a Queretaro"
        )

    # Get CCT level code (position 2-4)
    nivel_cct = cct[2:5]

    # Validate nivel matches tipo_tramite
    nivel_map = {
        TipoTramite.CERTIFICADO_PREESCOLAR: ['DJN', 'PJN', 'DCC', 'DML', 'EJN'],
        TipoTramite.CERTIFICADO_PRIMARIA: ['DPR', 'PPR', 'DPB', 'DML', 'EPR', 'ADG', 'NBA'],
        TipoTramite.CERTIFICADO_SECUNDARIA: ['DST', 'DES', 'DTV', 'EST', 'ETV']
    }

    if nivel_cct not in nivel_map.get(certificate_data.tipo_tramite, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La clave de la escuela no corresponde al nivel solicitado"
        )

    # Check for existing requests
    existing_check = check_existing_request(db, curp, certificate_data.tipo_tramite)

    if existing_check["status"] == "IN_PROCESS" and not existing_check.get("requires_payment", False):
        return CertificateRequestResponse(
            success=False,
            message=f"Ya existe un tramite en proceso con folio: {existing_check['folio']}. "
                    f"Consulta el estatus en la opcion 'Estatus del Tramite'.",
            folio=existing_check["folio"],
            requires_payment=False
        )

    # Check if it's a duplicate (already issued)
    is_duplicate = check_duplicate_in_system(
        db,
        curp,
        cct,
        certificate_data.ciclo_terminacion
    )

    requires_payment = existing_check.get("requires_payment", False) or is_duplicate

    # Determine region (default to 4 if not found)
    region = "4"

    # Generate folio
    folio = generate_folio(db, region)

    # Create request
    fecha_str = datetime.now().strftime("%d-%m-%Y")
    fecha_elaborado = date.today()

    new_request = CertificateRequest(
        folio=folio,
        nombre_alumno=certificate_data.nombre_alumno.upper(),
        a_paterno=certificate_data.a_paterno.upper(),
        a_materno=certificate_data.a_materno.upper() if certificate_data.a_materno else None,
        telefono=certificate_data.telefono,
        email=certificate_data.email.lower(),
        curp=curp,
        cct=cct,
        nombre_esc=certificate_data.nombre_esc.upper(),
        dom_esc=certificate_data.dom_esc.upper() if certificate_data.dom_esc else None,
        turno=certificate_data.turno.upper(),
        ciclo_terminacion=certificate_data.ciclo_terminacion,
        tipo_tramite=certificate_data.tipo_tramite,
        usuario='SISCER',
        foto='',
        zona='',
        sector='',
        fecha=fecha_str,
        fecha_elaborado=fecha_elaborado if is_duplicate else None,
        status=TramiteStatus.REIMPRESION if is_duplicate else TramiteStatus.SOLICITADO,
        entregado=TramiteEntregado.PENDIENTE,
        region=region,
        correccion=certificate_data.correccion,
        core=certificate_data.core
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Generate payment URL if required
    payment_url = None
    if requires_payment:
        # Payment system URL (REGER)
        payment_url = "https://reger.usebeq.edu.mx/PortalServicios/externalGuest.jsp"

    message = "La solicitud ya ha sido generada, favor de proceder con el pago del tramite." if requires_payment else \
              "La solicitud esta en proceso de validacion y elaboracion. Consulta el estatus con tu folio."

    return CertificateRequestResponse(
        success=True,
        message=message,
        folio=folio,
        status=new_request.status,
        requires_payment=requires_payment,
        payment_url=payment_url,
        data={
            "nombre_completo": f"{certificate_data.nombre_alumno} {certificate_data.a_paterno} {certificate_data.a_materno or ''}".strip(),
            "tipo_tramite": certificate_data.tipo_tramite.value
        }
    )


@router.get("/status/{folio}", response_model=CertificateStatusResponse)
def get_certificate_status(
    *,
    db: Session = Depends(get_db),
    folio: str
) -> Any:
    """
    Get certificate request status by folio
    """
    request = db.query(CertificateRequest).filter(
        CertificateRequest.folio == folio.upper()
    ).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro solicitud con este folio"
        )

    requires_payment = request.status == TramiteStatus.REIMPRESION and request.entregado == TramiteEntregado.PENDIENTE

    return CertificateStatusResponse(
        folio=request.folio,
        nombre_alumno=request.nombre_alumno,
        a_paterno=request.a_paterno,
        a_materno=request.a_materno,
        curp=request.curp,
        tipo_tramite=request.tipo_tramite,
        status=request.status,
        entregado=request.entregado,
        fecha=request.fecha,
        fecha_elaborado=request.fecha_elaborado,
        region=request.region,
        requires_payment=requires_payment
    )


@router.get("/list/{curp}", response_model=CertificateListResponse)
def list_certificates_by_curp(
    *,
    db: Session = Depends(get_db),
    curp: str
) -> Any:
    """
    List all certificate requests for a given CURP
    """
    curp_upper = curp.strip().upper()

    requests = db.query(CertificateRequest).filter(
        CertificateRequest.curp == curp_upper
    ).order_by(desc(CertificateRequest.created_at)).all()

    certificates = []
    for req in requests:
        requires_payment = req.status == TramiteStatus.REIMPRESION and req.entregado == TramiteEntregado.PENDIENTE
        certificates.append(
            CertificateStatusResponse(
                folio=req.folio,
                nombre_alumno=req.nombre_alumno,
                a_paterno=req.a_paterno,
                a_materno=req.a_materno,
                curp=req.curp,
                tipo_tramite=req.tipo_tramite,
                status=req.status,
                entregado=req.entregado,
                fecha=req.fecha,
                fecha_elaborado=req.fecha_elaborado,
                region=req.region,
                requires_payment=requires_payment
            )
        )

    return CertificateListResponse(
        curp=curp_upper,
        certificates=certificates,
        total=len(certificates)
    )
