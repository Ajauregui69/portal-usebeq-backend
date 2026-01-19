# Guía de Configuración de APIs de Google y OAuth 2.0

Esta guía describe los pasos para configurar un proyecto en Google Cloud Console, habilitar las APIs de Google y Gmail, y obtener las credenciales de cliente OAuth 2.0 necesarias para la integración con esta aplicación.

## Paso 1: Crear un Proyecto en Google Cloud

1.  Ve a la [Consola de Google Cloud](https://console.cloud.google.com/).
2.  En la parte superior, haz clic en el selector de proyectos (al lado del logo de "Google Cloud Platform").
3.  Haz clic en **"Proyecto nuevo"**.
4.  Asigna un nombre a tu proyecto (por ejemplo, `Portal Usebeq Auth`) y selecciona una organización si es necesario.
5.  Haz clic en **"Crear"**.

## Paso 2: Habilitar las APIs Necesarias

1.  Asegúrate de que tu nuevo proyecto esté seleccionado.
2.  En el menú de navegación de la izquierda, ve a **"APIs y servicios" > "Biblioteca"**.
3.  Busca y habilita las siguientes APIs, una por una:
    *   **Google People API**: Se usa para obtener la información del perfil del usuario (nombre, correo, etc.) después de la autenticación.
    *   **Gmail API**: Necesaria para poder enviar correos electrónicos en nombre del usuario.

## Paso 3: Configurar la Pantalla de Consentimiento de OAuth

Antes de crear las credenciales, debes configurar cómo se presentará tu aplicación a los usuarios cuando soliciten acceso.

1.  En el menú de navegación, ve a **"APIs y servicios" > "Pantalla de consentimiento de OAuth"**.
2.  Selecciona el tipo de usuario:
    *   **Externo**: Para cualquier usuario con una cuenta de Google. Es la opción más común para empezar.
    *   **Interno**: Solo para usuarios dentro de tu organización de Google Workspace.
3.  Haz clic en **"Crear"**.
4.  Rellena la información de la aplicación:
    *   **Nombre de la aplicación**: El nombre que verán los usuarios (ej. "Portal Usebeq").
    *   **Correo electrónico de asistencia del usuario**: Tu correo de contacto.
    *   **Logotipo de la aplicación** (Opcional).
    *   **Información de contacto del desarrollador**: Tu correo.
5.  Haz clic en **"Guardar y continuar"**.
6.  En la sección **"Permisos"**, no necesitas agregar nada por ahora. Haz clic en **"Guardar y continuar"**.
7.  En la sección **"Usuarios de prueba"**:
    *   Mientras tu aplicación esté en modo de prueba, solo los usuarios que agregues aquí podrán autenticarse.
    *   Haz clic en **"+ Add Users"** y agrega las cuentas de Google con las que realizarás las pruebas (por ejemplo, tu propio correo).
    *   Cuando la aplicación esté lista para producción, deberás publicarla desde esta misma pantalla para que cualquier usuario pueda acceder.
8.  Haz clic en **"Guardar y continuar"** y luego en **"Volver al panel"**.

## Paso 4: Crear las Credenciales de Cliente OAuth 2.0

1.  En el menú de navegación, ve a **"APIs y servicios" > "Credenciales"**.
2.  Haz clic en **"+ Crear credenciales"** y selecciona **"ID de cliente de OAuth"**.
3.  En **"Tipo de aplicación"**, selecciona **"Aplicación web"**.
4.  Asígnale un nombre (ej. `Cliente Web Portal Usebeq`).
5.  En la sección **"URI de redireccionamiento autorizados"**, debes agregar la URL a la que Google redirigirá a los usuarios después de que autoricen la aplicación. Para el desarrollo local, esta será la URL de tu backend.
    *   Haz clic en **"+ Agregar URI"**.
    *   Ingresa `http://localhost:8000/api/auth/google/callback`
    *   *Nota: Si tu backend corre en un puerto diferente, ajústalo según corresponda.*
6.  Haz clic en **"Crear"**.
7.  Aparecerá una ventana con tu **ID de cliente** y tu **Secreto de cliente**. **¡Copia estos valores y guárdalos en un lugar seguro!** Los necesitarás para la configuración del backend.

## Paso 5: Configurar las Variables de Entorno en el Backend

Una vez que tengas tu ID y Secreto de cliente, debes agregarlos a tu archivo `.env` en el proyecto del backend. Si no tienes un archivo `.env`, puedes crear uno a partir de `.env.example`.

```
GOOGLE_CLIENT_ID="TU_ID_DE_CLIENTE_AQUI"
GOOGLE_CLIENT_SECRET="TU_SECRETO_DE_CLIENTE_AQUI"
GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/google/callback"
```

Con estos pasos, tu proyecto de Google Cloud estará listo para manejar la autenticación y el envío de correos, y tu backend tendrá las credenciales necesarias para comunicarse con los servicios de Google.
