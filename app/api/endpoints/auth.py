from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserStatus
from app.schemas.user import Token, UserCreate, User as UserSchema
import secrets

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register new user account
    """
    # Check if user already exists
    user = db.query(User).filter(User.u_correo == user_in.u_correo).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        u_correo=user_in.u_correo,
        u_pass=get_password_hash(user_in.u_pass),
        u_nombre=user_in.u_nombre,
        u_appat=user_in.u_appat,
        u_apmat=user_in.u_apmat,
        u_tel=user_in.u_tel,
        domicilio=user_in.domicilio,
        sexo=user_in.sexo,
        estatus=UserStatus.PENDIENTE,
        token_activacion=secrets.token_urlsafe(32)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # TODO: Send activation email here
    # send_activation_email(user.u_correo, user.token_activacion)

    return user


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Special case: USEBEQ API credentials
    # This user is used by the system to authenticate with the external USEBEQ API
    if form_data.username == settings.USEBEQ_API_EMAIL and form_data.password == settings.USEBEQ_API_PASSWORD:
        # Check if system user exists in database, create if not
        system_user = db.query(User).filter(User.u_correo == settings.USEBEQ_API_EMAIL).first()

        if not system_user:
            # Create system user
            system_user = User(
                u_correo=settings.USEBEQ_API_EMAIL,
                u_pass=get_password_hash(settings.USEBEQ_API_PASSWORD),
                u_nombre="Sistema",
                u_appat="USEBEQ",
                u_apmat="API",
                estatus=UserStatus.VALIDADO
            )
            db.add(system_user)
            db.commit()
            db.refresh(system_user)

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=system_user.u_id,
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    # Normal user authentication
    user = db.query(User).filter(User.u_correo == form_data.username).first()

    if not user or not verify_password(form_data.password, user.u_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if user.estatus != UserStatus.VALIDADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please check your email."
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.u_id, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/activate/{token}")
def activate_account(
    *,
    db: Session = Depends(get_db),
    token: str,
) -> Any:
    """
    Activate user account with token
    """
    user = db.query(User).filter(User.token_activacion == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid activation token"
        )

    if user.estatus == UserStatus.VALIDADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already activated"
        )

    user.estatus = UserStatus.VALIDADO
    user.token_activacion = None
    from datetime import datetime
    user.fecha_validacion = datetime.utcnow()

    db.commit()

    return {"message": "Account activated successfully"}
