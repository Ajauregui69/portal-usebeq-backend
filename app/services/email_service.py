import base64
from email.mime.text import MIMEText
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
