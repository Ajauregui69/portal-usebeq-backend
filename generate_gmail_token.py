"""
Script para obtener el GOOGLE_SYSTEM_REFRESH_TOKEN necesario para enviar correos via Gmail API.

INSTRUCCIONES:
1. Asegurate de tener GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en tu .env
2. Asegurate de que la Gmail API este habilitada en Google Cloud Console
3. Ejecuta: python3 generate_gmail_token.py
4. Se abrira una ventana del navegador para autorizar la cuenta de Gmail
5. Inicia sesion con la cuenta que enviara los correos del sistema
6. Copia el REFRESH_TOKEN que aparecera y agregalo al .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET deben estar en el archivo .env")
    exit(1)

print("=" * 60)
print("  Generador de GOOGLE_SYSTEM_REFRESH_TOKEN")
print("  Para envio de correos via Gmail API")
print("=" * 60)
print()
print(f"CLIENT_ID: {CLIENT_ID[:20]}...")
print(f"CLIENT_SECRET: {CLIENT_SECRET[:10]}...")
print()

# Metodo 1: Usando google-auth-oauthlib (si esta en una maquina con navegador)
try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    flow = InstalledAppFlow.from_client_config(
        client_config={
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080"]
            }
        },
        scopes=SCOPES
    )

    print("Se abrira una ventana del navegador...")
    print("Inicia sesion con la cuenta de Gmail que enviara los correos del sistema.")
    print("(Ejemplo: portalusebeq@gmail.com o similar)")
    print()

    # Intenta abrir el navegador, si no puede usa modo consola
    try:
        creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
    except Exception:
        print("No se pudo abrir el navegador. Usando modo manual...")
        print()
        flow = InstalledAppFlow.from_client_config(
            client_config={
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                }
            },
            scopes=SCOPES
        )
        creds = flow.run_console()

    print()
    print("=" * 60)
    print("  TOKEN OBTENIDO EXITOSAMENTE")
    print("=" * 60)
    print()
    print("Agrega estas lineas a tu archivo .env:")
    print()
    print(f"GOOGLE_SYSTEM_REFRESH_TOKEN={creds.refresh_token}")
    print(f"GOOGLE_SYSTEM_EMAIL={input('Ingresa el correo de la cuenta que acabas de autorizar: ')}")
    print()
    print("Y en produccion (Azure), agrega las mismas variables de entorno.")
    print("=" * 60)

except ImportError:
    print("ERROR: google-auth-oauthlib no esta instalado.")
    print("Ejecuta: pip install google-auth-oauthlib")
    exit(1)
except Exception as e:
    print(f"Error: {e}")
    print()
    print("=" * 60)
    print("  METODO ALTERNATIVO (manual)")
    print("=" * 60)
    print()
    print("Si no puedes abrir un navegador desde esta maquina,")
    print("sigue estos pasos manualmente:")
    print()
    print("1. Abre esta URL en tu navegador:")
    print()

    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.send",
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    print(f"   {auth_url}")
    print()
    print("2. Autoriza la cuenta e ignora el error de redireccion.")
    print("3. Copia el 'code' de la URL resultante.")
    print("4. Ejecuta este comando curl para obtener el refresh_token:")
    print()
    print(f'   curl -X POST https://oauth2.googleapis.com/token \\')
    print(f'     -d "code=TU_CODIGO_AQUI" \\')
    print(f'     -d "client_id={CLIENT_ID}" \\')
    print(f'     -d "client_secret={CLIENT_SECRET}" \\')
    print(f'     -d "redirect_uri=urn:ietf:wg:oauth:2.0:oob" \\')
    print(f'     -d "grant_type=authorization_code"')
    print()
    print("5. En la respuesta JSON, copia el valor de 'refresh_token'")
    print("6. Agregalo al .env como GOOGLE_SYSTEM_REFRESH_TOKEN=...")
