from pydantic import BaseModel
from typing import Optional


class BoletaResponse(BaseModel):
    """
    Response schema for boleta (report card) request
    """
    success: bool
    message: str
    pdf_url: Optional[str] = None
    error_detail: Optional[str] = None

    class Config:
        from_attributes = True
