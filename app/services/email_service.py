import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


def get_google_credentials(user: User) -> Credentials:
    """
    Refreshes and returns Google credentials for a user.
    """
    if not user.google_id or not user.google_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not configured for Google services."
        )

    creds = Credentials.from_authorized_user_info(
        info={
            "refresh_token": user.google_refresh_token,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.send"
        ]
    )

    # Refresh the token if it's expired
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
    
    return creds


def send_gmail(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    to_email: str,
    subject: str,
    message_text: str
) -> dict:
    """
    Sends an email using the Gmail API on behalf of a user.
    """
    user = db.query(User).filter(User.u_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    try:
        credentials = get_google_credentials(user)
        gmail_service = build("gmail", "v1", credentials=credentials)

        message = MIMEText(message_text)
        message["to"] = to_email
        message["from"] = user.u_correo
        message["subject"] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        create_message = {
            'raw': raw_message
        }
        
        send_message_result = (
            gmail_service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        
        return send_message_result

    except HTTPException as e:
        raise e # Re-raise HTTPException
    except Exception as e:
        # Catch other potential errors from the Google API client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {e}"
        )


def get_system_credentials() -> Credentials:
    """
    Returns Google credentials for the system account (used for sending system emails).
    """
    if not settings.GOOGLE_SYSTEM_REFRESH_TOKEN:
        raise Exception("GOOGLE_SYSTEM_REFRESH_TOKEN not configured")

    creds = Credentials.from_authorized_user_info(
        info={
            "refresh_token": settings.GOOGLE_SYSTEM_REFRESH_TOKEN,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=[
            "https://www.googleapis.com/auth/gmail.send"
        ]
    )

    # Refresh the token if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())

    return creds


def send_system_email(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """
    Sends a system email using Gmail API with the system account credentials.
    """
    try:
        credentials = get_system_credentials()
        gmail_service = build("gmail", "v1", credentials=credentials)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.GOOGLE_SYSTEM_EMAIL}>"
        message["To"] = to_email

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_result = (
            gmail_service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        print(f"Email sent successfully: {send_result.get('id')}")
        return True

    except Exception as e:
        print(f"Error sending system email: {e}")
        return False


def send_activation_email(to_email: str, token: str, user_name: str) -> bool:
    """
    Sends an activation email to a newly registered user.
    """
    activation_url = f"{settings.FRONTEND_URL}/activate/{token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #2563eb, #4f46e5); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #2563eb, #4f46e5); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Portal USEBEQ</h1>
            </div>
            <div class="content">
                <h2>¡Hola {user_name}!</h2>
                <p>Gracias por registrarte en el Portal USEBEQ. Para activar tu cuenta, haz clic en el siguiente botón:</p>
                <p style="text-align: center;">
                    <a href="{activation_url}" class="button">Activar mi cuenta</a>
                </p>
                <p>Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:</p>
                <p style="word-break: break-all; color: #2563eb;">{activation_url}</p>
                <p>Si no solicitaste esta cuenta, puedes ignorar este correo.</p>
            </div>
            <div class="footer">
                <p>Portal Académico USEBEQ - Querétaro, México</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_system_email(
        to_email=to_email,
        subject="Activa tu cuenta - Portal USEBEQ",
        html_content=html_content
    )
