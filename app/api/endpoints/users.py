from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate

router = APIRouter()


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
