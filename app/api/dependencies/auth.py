from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserStatus
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if token_data.sub is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Query user from database
    user = db.query(User).filter(User.u_id == token_data.sub).first()

    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
):
    """
    Get current active (validated) user
    """
    if current_user.estatus != UserStatus.VALIDADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated"
        )
    return current_user
