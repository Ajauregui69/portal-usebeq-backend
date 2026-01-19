# Guía Técnica de la Integración de Google

Este documento ofrece una descripción técnica de la implementación de Google OAuth y la API de Gmail en el backend.

## 1. Visión General de la Arquitectura

La integración se compone de tres partes principales:

1.  **Configuración y Modelos:** Nuevas variables de entorno y campos en la base de datos para almacenar las credenciales y la información del usuario de Google.
2.  **Flujo de Autenticación OAuth 2.0:** Nuevos endpoints de API para gestionar el proceso de inicio de sesión con Google.
3.  **Servicio de Envío de Correo:** Un servicio que utiliza los tokens de OAuth para enviar correos a través de la API de Gmail en nombre del usuario.

---

## 2. Cambios en la Base de Datos y Configuración

### 2.1. Archivo de Configuración (`app/core/config.py`)

Se han añadido las siguientes variables a la clase `Settings` para gestionar las credenciales de Google desde el archivo `.env`:

-   `GOOGLE_CLIENT_ID`: El ID de cliente de la aplicación OAuth.
-   `GOOGLE_CLIENT_SECRET`: El secreto de cliente de la aplicación OAuth.
-   `GOOGLE_REDIRECT_URI`: La URL de callback a la que Google redirige después de la autenticación. Debe coincidir exactamente con una de las URIs configuradas en la Google Cloud Console.

### 2.2. Modelo de Usuario (`app/models/user.py`)

La tabla `PP_usuarios` ha sido extendida con los siguientes campos:

-   `google_id` (String): Almacena el ID de perfil único que Google asigna a cada usuario. Es la clave principal para identificar a un usuario que se ha registrado con Google. Es único.
-   `google_refresh_token` (String): Almacena el token de actualización de OAuth. Este token es de larga duración y es **esencial** para poder obtener nuevos `access_token` sin que el usuario tenga que volver a iniciar sesión. Se solicita durante el primer consentimiento con el parámetro `access_type="offline"`.
-   `u_pass` (String): Se ha hecho `nullable` para que los usuarios registrados con Google no necesiten tener una contraseña local.

---

## 3. Flujo de Autenticación OAuth 2.0

El flujo de autenticación es el estándar de OAuth 2.0 para aplicaciones web y se gestiona en `app/api/endpoints/auth.py`.

### 3.1. Inicio del Login: `GET /api/v1/auth/google/login`

1.  **Activación:** El usuario hace clic en un enlace en el frontend que apunta a este endpoint.
2.  **Construcción de la URL:** Se instancia un objeto `Flow` de la librería `google_auth_oauthlib`. Este objeto se configura con el `client_id`, `client_secret`, y los `scopes` (permisos) que la aplicación solicita.
3.  **Generación de Estado (State):** Se genera un `state` aleatorio y se guarda en la sesión del usuario. Este `state` se incluye en la URL de autorización y sirve para mitigar ataques de tipo CSRF.
4.  **Redirección:** El endpoint responde con una redirección (HTTP 307) a la URL de autorización de Google. El navegador del usuario es redirigido a la página de consentimiento de Google.

### 3.2. Callback de Google: `GET /api/v1/auth/google/callback`

1.  **Recepción:** Después de que el usuario da su consentimiento, Google redirige su navegador a esta URL. La URL incluye un `code` de autorización y el `state` que generamos.
2.  **Validación del Estado:** Se compara el `state` de la sesión con el `state` recibido en los parámetros de la URL. Si no coinciden, el proceso se detiene para prevenir ataques CSRF.
3.  **Intercambio de Código por Tokens:** Se utiliza `flow.fetch_token()` para enviar el `code` de autorización a Google. A cambio, Google devuelve un `access_token`, un `refresh_token` (solo la primera vez), y la información de su caducidad.
4.  **Obtención de Perfil de Usuario:** Con el `access_token` obtenido, se hace una llamada a la **Google People API** para obtener los datos del usuario (ID de Google, nombre, correo).
5.  **Gestión de Usuario en BD:**
    *   Se busca un usuario en la BD con el `google_id` recibido.
    *   **Si existe:** Se actualiza su `refresh_token` si se ha recibido uno nuevo y se procede a generar el token de la aplicación.
    *   **Si no existe:** Se comprueba si ya hay un usuario con ese `u_correo`.
        *   Si existe (un usuario que se registró por contraseña antes), se "vincula" la cuenta guardando su `google_id` y `refresh_token`.
        *   Si no existe, se crea un nuevo registro `User` con los datos de Google, se marca como `VALIDADO` y se guarda en la BD.
6.  **Creación de Token de Aplicación:** Se genera un token JWT propio de la aplicación (`create_access_token`) que contiene el `u_id` del usuario en el campo `sub`.
7.  **Redirección al Frontend:** Finalmente, se redirige al usuario a una URL del frontend (ej. `/auth/callback`), pasando el token JWT como un parámetro en la URL para que el frontend pueda iniciar la sesión.

---

## 4. Servicio de Envío de Correo (`app/services/email_service.py`)

Este servicio encapsula la lógica para usar la API de Gmail.

### Función `send_gmail`

1.  **Obtención del Usuario:** Recibe un `user_id` y carga el objeto `User` correspondiente desde la base de datos.
2.  **Refresco de Credenciales:**
    *   Usa el `google_refresh_token` del usuario para crear un objeto `Credentials` de Google.
    *   Si el `access_token` asociado está caducado (que casi siempre lo estará), el objeto `Credentials` utiliza automáticamente el `refresh_token` para obtener un nuevo `access_token` válido en segundo plano (`creds.refresh(GoogleRequest())`).
3.  **Construcción del Servicio de Gmail:** Se instancia el cliente de la API de Gmail (`build("gmail", "v1", ...)`), pasándole las credenciales actualizadas.
4.  **Creación y Envío del Mensaje:**
    *   Se crea un objeto `MIMEText` estándar de Python para el correo.
    *   Se codifica en Base64 URL-safe, que es el formato que la API de Gmail espera.
    *   Se llama a `gmail_service.users().messages().send()` con el mensaje codificado y el `userId="me"` (que se refiere al usuario autenticado).
5.  **Retorno:** Devuelve el resultado de la llamada a la API o lanza una `HTTPException` si algo falla.
