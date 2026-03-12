from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserStatus
from app.schemas.user import Token, UserCreate, User as UserSchema
from app.services.email_service import send_activation_email
import secrets

router = APIRouter()

# --- Google OAuth Configuration ---
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

def get_google_flow() -> Flow:
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

@router.get("/google/login")
async def google_login(request: Request):
    """
    Generate a redirect to Google's OAuth 2.0 consent screen.
    """
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    request.session["state"] = state
    # Persist code_verifier (PKCE) so the callback can reuse it
    if getattr(flow, "code_verifier", None):
        request.session["code_verifier"] = flow.code_verifier
    return RedirectResponse(authorization_url)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Process the OAuth 2.0 callback from Google.
    """
    from datetime import datetime
    state = request.session.get("state")
    if not state or state != request.query_params.get("state"):
        raise HTTPException(status_code=401, detail="Parametro de estado invalido")

    flow = get_google_flow()
    # Restore code_verifier (PKCE) from session so fetch_token can send it to Google
    code_verifier = request.session.get("code_verifier")
    if code_verifier:
        flow.code_verifier = code_verifier
    try:
        # Force HTTPS scheme for OAuth callback URL
        # Azure App Service terminates SSL at the proxy level, so request.url might have http://
        # We need to replace it with https:// for OAuth to work correctly
        authorization_response = str(request.url)
        if authorization_response.startswith("http://"):
            authorization_response = authorization_response.replace("http://", "https://", 1)

        # Use code and state from query params instead of full URL to avoid redirect_uri mismatch
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Codigo de autorizacion no encontrado")

        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener token: {e}")

    credentials = flow.credentials
    
    # Get user info from Google
    try:
        people_service = build("people", "v1", credentials=credentials)
        profile = people_service.people().get(
            resourceName="people/me",
            personFields="names,emailAddresses,photos"
        ).execute()

        google_id = profile["resourceName"].split("/")[1]
        email = profile["emailAddresses"][0]["value"]
        first_name = profile["names"][0].get("givenName", "")
        last_name = profile["names"][0].get("familyName", "")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo obtener la informacion del perfil: {e}")

    # Check if user exists
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        # If not, check if an account with that email exists
        user = db.query(User).filter(User.u_correo == email).first()
        if user:
            # Link existing account
            user.google_id = google_id
            user.google_refresh_token = credentials.refresh_token
            # If linking, user might need validation
            if user.estatus == UserStatus.PENDIENTE:
                user.estatus = UserStatus.VALIDADO
                user.fecha_validacion = datetime.utcnow()
            
        else:
            # Create new user
            # Google OAuth users don't have a password (u_pass is NULL)
            user = User(
                u_correo=email,
                u_nombre=first_name,
                u_appat=last_name if last_name else ".",  # Ensure u_appat is not empty
                google_id=google_id,
                google_refresh_token=credentials.refresh_token,
                u_pass=None,  # No password for Google OAuth users
                estatus=UserStatus.VALIDADO,
                fecha_validacion=datetime.utcnow()
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)

    else:
        # Update refresh token if it has changed
        if credentials.refresh_token:
            user.google_refresh_token = credentials.refresh_token
            db.commit()


    # Create access token for our app
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.u_id, expires_delta=access_token_expires
    )

    # Redirect to the frontend with the token
    frontend_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_url)


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
            detail="Este correo ya esta registrado"
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

    # Send activation email
    user_name = f"{user.u_nombre} {user.u_appat}".strip()
    send_activation_email(user.u_correo, user.token_activacion, user_name)

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

    if user and user.google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta cuenta esta registrada con Google. Por favor usa el inicio de sesion con Google."
        )

    if not user or not user.u_pass or not verify_password(form_data.password, user.u_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )

    if user.estatus != UserStatus.VALIDADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta no activada. Por favor revisa tu correo electronico."
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
            detail="Token de activacion invalido"
        )

    if user.estatus == UserStatus.VALIDADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta ya fue activada"
        )

    user.estatus = UserStatus.VALIDADO
    user.token_activacion = None
    from datetime import datetime
    user.fecha_validacion = datetime.utcnow()

    db.commit()

    return {"message": "Cuenta activada exitosamente"}


@router.post("/forgot-password")
def forgot_password(
    *,
    db: Session = Depends(get_db),
    email: str,
) -> Any:
    """
    Send password reset token via email
    """
    user = db.query(User).filter(User.u_correo == email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña"}

    if user.google_id and not user.u_pass:
        return {"message": "Esta cuenta está registrada con Google. Por favor usa el inicio de sesión con Google."}

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.token_activacion = reset_token
    db.commit()

    # Send reset email
    user_name = f"{user.u_nombre} {user.u_appat}".strip()
    try:
        from app.services.email_service import send_password_reset_email
        send_password_reset_email(user.u_correo, reset_token, user_name)
    except Exception:
        pass  # Don't fail if email sending fails

    return {"message": "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña"}


@router.post("/reset-password/{token}")
def reset_password(
    *,
    db: Session = Depends(get_db),
    token: str,
    new_password: str,
) -> Any:
    """
    Reset password using token
    """
    user = db.query(User).filter(User.token_activacion == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token inválido o expirado"
        )

    user.u_pass = get_password_hash(new_password)
    user.token_activacion = None

    # Si la cuenta estaba pendiente, activarla
    if user.estatus != UserStatus.VALIDADO:
        user.estatus = UserStatus.VALIDADO
        from datetime import datetime
        user.fecha_validacion = datetime.utcnow()

    db.commit()

    return {"message": "Contraseña actualizada correctamente"}
