# Guía de Implementación del Botón "Login with Google" en el Frontend

Esta guía detalla cómo implementar el flujo de autenticación de Google en el frontend, interactuando con los endpoints del backend que se han creado.

## 1. Crear el Botón de Login con Google

En tu componente de inicio de sesión (por ejemplo, `LoginPage.js` o `Login.vue`), agrega un nuevo botón:

```html
<a href="http://localhost:8000/api/v1/auth/google/login" class="google-login-button">
  <img src="/path/to/your/google-icon.svg" alt="Google icon" />
  <span>Iniciar sesión con Google</span>
</a>
```

**Puntos Clave:**

*   **URL del Backend:** El `href` del botón debe apuntar directamente al endpoint de login de Google en el backend: `http://localhost:8000/api/v1/auth/google/login`.
*   **No es una llamada AJAX/Fetch:** Esto no es una solicitud de API tradicional desde JavaScript. Es un enlace de navegación directo. El usuario hace clic, el navegador navega a la URL del backend, y el backend lo redirige a la página de consentimiento de Google.
*   **Estilo:** Asegúrate de que el botón siga las [guías de branding de Google](https://developers.google.com/identity/branding-guidelines).

## 2. Manejar la Redirección de Google (Callback)

Una vez que el usuario se autentica con Google y da su consentimiento, el backend maneja el callback, obtiene un token de acceso de la aplicación (JWT), y necesita devolverlo al frontend.

El endpoint del backend `/api/v1/auth/google/callback` actualmente devuelve el token como una respuesta JSON. Para que el frontend lo reciba, el enfoque más simple es que el backend redirija al usuario de vuelta a una página específica del frontend, incluyendo el token en la URL.

**Acción Requerida en el Backend:**

Se necesita modificar el endpoint `/api/v1/auth/google/callback` en `app/api/endpoints/auth.py` para que, en lugar de devolver un JSON, redirija al frontend.

**Ejemplo de modificación en `auth.py`:**

```python
# ... al final de la función google_callback ...

    # En lugar de: return {"access_token": access_token, "token_type": "bearer"}
    
    # Redirigir al frontend con el token
    frontend_url = f"http://localhost:3000/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_url)
```

## 3. Crear una Página de Callback en el Frontend

En tu aplicación de frontend, crea una nueva ruta y componente (por ejemplo, `/auth/callback`).

**Lógica del Componente de Callback:**

1.  **Extraer el Token:** Cuando el componente se carga, debe leer el token de los parámetros de la URL.
2.  **Guardar el Token:** Almacena el token de acceso en el almacenamiento local (`localStorage` o `sessionStorage`) o en el estado de tu aplicación (Redux, Vuex, etc.), de la misma manera que lo harías con un login por correo y contraseña.
3.  **Redirigir al Usuario:** Después de guardar el token, redirige al usuario a la página principal o al dashboard de la aplicación.

**Ejemplo en React:**

```jsx
// src/components/AuthCallback.js
import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // 1. Extraer el token de la URL
    const params = new URLSearchParams(location.search);
    const token = params.get('token');

    if (token) {
      // 2. Guardar el token
      localStorage.setItem('access_token', token);
      
      // Opcional: Actualizar el estado de autenticación en tu app
      // auth.login(token);

      // 3. Redirigir al dashboard
      navigate('/dashboard'); 
    } else {
      // Si no hay token, redirigir al login con un error
      navigate('/login?error=auth_failed');
    }
  }, [location, navigate]);

  return (
    <div>
      <p>Procesando autenticación...</p>
    </div>
  );
};

export default AuthCallback;
```

**Ruta en React Router:**

```jsx
<Route path="/auth/callback" element={<AuthCallback />} />
```

Con estos tres pasos, el flujo de autenticación de Google estará completo y se integrará con el sistema de autenticación JWT existente en tu frontend.
