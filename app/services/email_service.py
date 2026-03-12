import httpx

from app.core.config import settings


def send_system_email(
    to_email: str,
    subject: str,
    html_content: str
) -> bool:
    """
    Sends a system email using the SendGrid API.
    """
    if not settings.SENDGRID_API_KEY:
        print("SENDGRID_API_KEY not configured, skipping email send")
        return False

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.MAIL_FROM, "name": settings.MAIL_FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_content}],
    }

    try:
        response = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if response.status_code == 202:
            print(f"Email sent successfully to {to_email}")
            return True
        else:
            print(f"SendGrid error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email via SendGrid: {e}")
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
                <p>Portal Académico USEBEQ</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_system_email(
        to_email=to_email,
        subject="Activa tu cuenta - Portal USEBEQ",
        html_content=html_content,
    )


def send_password_reset_email(email: str, token: str, user_name: str) -> bool:
    """Send password reset email."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #1e40af, #4f46e5); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: #1e40af; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Portal USEBEQ</h1>
            </div>
            <div class="content">
                <h2>Hola, {user_name}</h2>
                <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                <p>Haz clic en el siguiente botón para crear una nueva contraseña:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                </p>
                <p>Si el botón no funciona, copia y pega el siguiente enlace en tu navegador:</p>
                <p style="word-break: break-all; color: #1e40af;">{reset_url}</p>
                <p style="color: #64748b; font-size: 14px;">Si no solicitaste este cambio, puedes ignorar este correo.</p>
                <p style="color: #64748b; font-size: 14px;">Este enlace expirará cuando sea utilizado.</p>
            </div>
            <div class="footer">
                <p>Portal Académico USEBEQ</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_system_email(email, subject="Restablecer contraseña - Portal USEBEQ", html_content=html_content)
