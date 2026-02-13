# Manual: Configurar Google OAuth 2.0 y Gmail API

Este manual explica cómo configurar Google OAuth para autenticación de usuarios y Gmail API para envío de correos desde el Portal USEBEQ.

---

## Parte 1: Crear Proyecto en Google Cloud Console

### 1.1 Acceder a Google Cloud Console

1. Ir a [Google Cloud Console](https://console.cloud.google.com)
2. Iniciar sesión con una cuenta de Google (preferiblemente institucional)

### 1.2 Crear Nuevo Proyecto

1. Click en el selector de proyectos (arriba a la izquierda)
2. Click en **"New Project"**
3. Configurar:
   - **Project name**: `Portal USEBEQ`
   - **Organization**: Seleccionar tu organización (si aplica)
   - **Location**: Seleccionar ubicación
4. Click en **"Create"**
5. Esperar a que se cree y seleccionarlo

---

## Parte 2: Habilitar APIs Necesarias

### 2.1 Habilitar Google People API

1. Ir a **"APIs & Services"** > **"Library"**
2. Buscar **"Google People API"**
3. Click en el resultado
4. Click en **"Enable"**

### 2.2 Habilitar Gmail API

1. En la misma sección Library
2. Buscar **"Gmail API"**
3. Click en el resultado
4. Click en **"Enable"**

---

## Parte 3: Configurar Pantalla de Consentimiento OAuth

### 3.1 Crear Pantalla de Consentimiento

1. Ir a **"APIs & Services"** > **"OAuth consent screen"**
2. Seleccionar **"External"** (para usuarios fuera de tu organización)
   - O **"Internal"** si solo será para usuarios de tu dominio Google Workspace
3. Click en **"Create"**

### 3.2 Información de la App

| Campo | Valor |
|-------|-------|
| App name | `Portal USEBEQ` |
| User support email | `soporte@usebeq.edu.mx` |
| App logo | (opcional) Subir logo de USEBEQ |

### 3.3 App Domain (Opcional pero Recomendado)

| Campo | Valor |
|-------|-------|
| Application home page | `https://tu-frontend.azurestaticapps.net` |
| Application privacy policy | `https://tu-frontend.azurestaticapps.net/privacidad` |
| Application terms of service | `https://tu-frontend.azurestaticapps.net/terminos` |

### 3.4 Developer Contact Information

- Agregar email del desarrollador o equipo técnico

5. Click en **"Save and Continue"**

### 3.5 Scopes (Permisos)

1. Click en **"Add or Remove Scopes"**
2. Buscar y seleccionar los siguientes scopes:

| Scope | Descripción |
|-------|-------------|
| `openid` | OpenID Connect |
| `email` | Ver email del usuario |
| `profile` | Ver información básica del perfil |
| `https://www.googleapis.com/auth/gmail.send` | Enviar correos (para emails de activación) |

3. Click en **"Update"**
4. Click en **"Save and Continue"**

### 3.6 Test Users (Mientras está en Testing)

Si la app está en modo "Testing":
1. Click en **"Add Users"**
2. Agregar los emails de las personas que probarán la app
3. Click en **"Save and Continue"**

### 3.7 Publicar App (Para Producción)

Cuando esté lista para producción:
1. Ir a **"OAuth consent screen"**
2. Click en **"Publish App"**
3. Completar el proceso de verificación de Google (puede tomar días/semanas)

---

## Parte 4: Crear Credenciales OAuth 2.0

### 4.1 Crear OAuth Client ID

1. Ir a **"APIs & Services"** > **"Credentials"**
2. Click en **"+ Create Credentials"**
3. Seleccionar **"OAuth client ID"**

### 4.2 Configurar Cliente OAuth

| Campo | Valor |
|-------|-------|
| Application type | **Web application** |
| Name | `Portal USEBEQ Web Client` |

### 4.3 Authorized JavaScript Origins

Agregar las URLs desde donde se hará login:

**Desarrollo:**
```
http://localhost:3000
http://localhost:5173
```

**Producción:**
```
https://jolly-coast-03240f610.4.azurestaticapps.net
https://portal.usebeq.edu.mx (si tienes dominio personalizado)
```

### 4.4 Authorized Redirect URIs

Agregar las URLs de callback del backend:

**Desarrollo:**
```
http://localhost:8000/api/v1/auth/google/callback
```

**Producción:**
```
https://portal-usebeq-backend-app.azurewebsites.net/api/v1/auth/google/callback
```

5. Click en **"Create"**

### 4.5 Guardar Credenciales

Aparecerá una ventana con:
- **Client ID**: `XXXXXX.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-XXXXXXXX`

**IMPORTANTE**: Guardar estas credenciales de forma segura. El Client Secret NO se puede ver de nuevo (tendrías que crear uno nuevo).

---

## Parte 5: Configurar el Backend

### 5.1 Variables de Entorno

Agregar en el archivo `.env` (desarrollo) o en Azure Configuration (producción):

```env
# Google OAuth
GOOGLE_CLIENT_ID=123456789-xxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Para desarrollo local (permite OAuth sobre HTTP)
OAUTHLIB_INSECURE_TRANSPORT=1

# URL del frontend (para redirección después del login)
FRONTEND_URL=http://localhost:3000
```

### 5.2 Variables en Azure (Producción)

En Azure Portal > Web App > Configuration:

| Variable | Valor |
|----------|-------|
| `GOOGLE_CLIENT_ID` | `tu-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-tu-client-secret` |
| `GOOGLE_REDIRECT_URI` | `https://tu-backend.azurewebsites.net/api/v1/auth/google/callback` |
| `FRONTEND_URL` | `https://tu-frontend.azurestaticapps.net` |

**NOTA**: NO agregar `OAUTHLIB_INSECURE_TRANSPORT` en producción.

---

## Parte 6: Configurar Gmail API para Emails del Sistema

Para enviar emails de activación de cuenta usando Gmail API, necesitas una cuenta de servicio del sistema.

### 6.1 Obtener Refresh Token del Sistema

1. Desplegar la aplicación
2. Iniciar sesión con la cuenta que enviará los emails del sistema (ej: `noreply@usebeq.edu.mx`)
3. Después del login exitoso, el `google_refresh_token` se guarda en la base de datos
4. Ejecutar en la base de datos:
   ```sql
   SELECT google_refresh_token FROM PP_usuarios WHERE u_correo = 'noreply@usebeq.edu.mx';
   ```
5. Copiar el token

### 6.2 Configurar Variables del Sistema

Agregar en Azure Configuration:

| Variable | Valor |
|----------|-------|
| `GOOGLE_SYSTEM_REFRESH_TOKEN` | `1//0fXXXXXX...` (el token copiado) |
| `GOOGLE_SYSTEM_EMAIL` | `noreply@usebeq.edu.mx` |

### 6.3 Alternativa: Usar SMTP

Si prefieres no usar Gmail API para emails del sistema, puedes usar SMTP:

```env
MAIL_USERNAME=noreply@usebeq.edu.mx
MAIL_PASSWORD=tu-password-de-app
MAIL_FROM=noreply@usebeq.edu.mx
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
```

**Para Gmail con SMTP**:
1. Habilitar "2-Step Verification" en la cuenta de Google
2. Crear "App Password" en https://myaccount.google.com/apppasswords
3. Usar ese password en `MAIL_PASSWORD`

---

## Parte 7: Flujo de Autenticación

### 7.1 Flujo de Login con Google

```
1. Usuario click en "Iniciar sesión con Google"
         ↓
2. Frontend redirige a: /api/v1/auth/google/login
         ↓
3. Backend redirige a Google OAuth consent screen
         ↓
4. Usuario autoriza la app en Google
         ↓
5. Google redirige a: /api/v1/auth/google/callback?code=XXX
         ↓
6. Backend intercambia code por tokens
         ↓
7. Backend obtiene perfil del usuario de Google
         ↓
8. Backend crea/actualiza usuario en BD
         ↓
9. Backend genera JWT y redirige a frontend: /auth/callback?token=XXX
         ↓
10. Frontend guarda token y carga usuario
         ↓
11. Usuario autenticado en el dashboard
```

### 7.2 Flujo de Envío de Email (Activación)

```
1. Usuario se registra con email/password
         ↓
2. Backend crea usuario con estatus "PENDIENTE"
         ↓
3. Backend usa Gmail API con GOOGLE_SYSTEM_REFRESH_TOKEN
         ↓
4. Gmail envía email de activación
         ↓
5. Usuario click en link de activación
         ↓
6. Backend activa la cuenta (estatus = "VALIDADO")
```

---

## Parte 8: Solución de Problemas

### Error: "OAuth 2 MUST utilize https"

**Causa**: Intentando usar OAuth en desarrollo con HTTP.

**Solución**: Agregar en `.env`:
```env
OAUTHLIB_INSECURE_TRANSPORT=1
```

Y en `main.py`:
```python
import os
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = os.getenv("OAUTHLIB_INSECURE_TRANSPORT", "0")
```

### Error: "redirect_uri_mismatch"

**Causa**: La URL de callback no coincide con las configuradas en Google Console.

**Solución**:
1. Verificar que `GOOGLE_REDIRECT_URI` coincida exactamente con una de las URIs en Google Console
2. Incluir el path completo: `https://backend.com/api/v1/auth/google/callback`
3. Sin trailing slash al final

### Error: "access_denied"

**Causa**: Usuario no está en la lista de test users (si la app está en Testing).

**Solución**:
1. Agregar el email del usuario en OAuth consent screen > Test users
2. O publicar la app para producción

### Error: "invalid_grant"

**Causa**: El refresh token expiró o fue revocado.

**Solución**:
1. El usuario debe iniciar sesión de nuevo
2. Se generará un nuevo refresh token

### Emails no se envían

**Verificar**:
1. Que Gmail API esté habilitada
2. Que el scope `gmail.send` esté configurado
3. Que el refresh token del sistema sea válido
4. Que la cuenta del sistema haya autorizado el scope de envío

---

## Parte 9: Seguridad

### Mejores Prácticas

1. **NUNCA** subir credenciales a Git
2. Usar variables de entorno para todas las credenciales
3. Rotar el Client Secret periódicamente
4. Limitar los scopes solo a los necesarios
5. Usar HTTPS en producción (obligatorio para OAuth)
6. Validar el state parameter para prevenir CSRF

### Ejemplo de `.gitignore`

```gitignore
# Environment variables
.env
.env.local
.env.*.local

# Google credentials
credentials.json
token.json
*.p12
*.pem
```

---

## Resumen de URLs

### Google Cloud Console
- Console: https://console.cloud.google.com
- APIs: https://console.cloud.google.com/apis
- Credentials: https://console.cloud.google.com/apis/credentials
- OAuth Consent: https://console.cloud.google.com/apis/credentials/consent

### Endpoints del Backend
- Login: `GET /api/v1/auth/google/login`
- Callback: `GET /api/v1/auth/google/callback`

### Endpoints del Frontend
- Callback: `/auth/callback?token=XXX`
