from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate
from app.services.email_service import send_gmail

router = APIRouter()


class EmailSchema(BaseModel):
    to_email: EmailStr
    subject: str
    message: str


@router.post("/me/send-email")
def send_email_from_user(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    email_data: EmailSchema,
):
    """
    Send an email from the current user's Google account.
    """
    if not current_user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not authenticated with a Google account."
        )

    try:
        result = send_gmail(
            db=db,
            user_id=current_user.u_id,
            to_email=email_data.to_email,
            subject=email_data.subject,
            message_text=email_data.message,
        )
        return {"message": "Email sent successfully", "details": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/me", response_model=UserSchema)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user profile
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_current_user_profile(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    user_in: UserUpdate,
) -> Any:
    """
    Update current user profile
    """
    update_data = user_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.put("/update-address")
def update_user_address(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    domicilio: str
) -> Any:
    """
    Update current user address
    """
    current_user.domicilio = domicilio.upper()

    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "message": "Domicilio actualizado correctamente",
        "domicilio": current_user.domicilio
    }
