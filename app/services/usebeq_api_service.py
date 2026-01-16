import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.models.api_token import APIToken
from app.schemas.usebeq_api import EstudianteUSEBEQ, TipoBaja, SolicitudBajaResponse


class USEBEQAPIService:
    """
    Service to handle authentication and requests to USEBEQ external API
    """

    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.USEBEQ_API_BASE_URL
        self.auth_url = settings.USEBEQ_AUTH_API_URL
        self.email = settings.USEBEQ_API_EMAIL
        self.password = settings.USEBEQ_API_PASSWORD

    async def _get_valid_token(self) -> str:
        """
        Get a valid access token. If expired, refresh it or get a new one.
        Token has 24 hours of life.
        """
        # Get the most recent token
        query = text("""
            SELECT id, token, refresh_token, fecha_registro
            FROM pp_token
            ORDER BY fecha_registro DESC
            LIMIT 1
        """)
        result = self.db.execute(query).fetchone()

        if result:
            token_id, access_token, refresh_token, fecha_registro = result

            # Check if token is still valid (less than 24 hours old)
            time_diff = datetime.now() - fecha_registro
            if time_diff < timedelta(hours=24):
                return access_token

            # Token expired, try to refresh
            try:
                new_tokens = await self._refresh_token(access_token, refresh_token)
                if new_tokens:
                    return new_tokens["accessToken"]
            except Exception:
                pass

        # If no valid token or refresh failed, get a new one
        return await self._authenticate()

    async def _authenticate(self) -> str:
        """
        Authenticate with the API and get new tokens
        """
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.auth_url}/simple",
                json={
                    "correo": self.email,
                    "contrasenia": self.password
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()
            # API externa usa AccessToken y RefreshToken (con mayúsculas)
            access_token = data.get("AccessToken") or data.get("accessToken")
            refresh_token = data.get("RefreshToken") or data.get("refreshToken")

            # Store tokens in database
            query = text("""
                INSERT INTO pp_token (token, refresh_token, fecha_registro)
                VALUES (:token, :refresh_token, :fecha_registro)
            """)
            self.db.execute(query, {
                "token": access_token,
                "refresh_token": refresh_token,
                "fecha_registro": datetime.now()
            })
            self.db.commit()

            return access_token

    async def _refresh_token(self, access_token: str, refresh_token: str) -> Optional[dict]:
        """
        Refresh the access token using the refresh token
        """
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.auth_url}/get-refresh-tokens",
                json={
                    "accessToken": access_token,
                    "refreshToken": refresh_token
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                # API externa usa AccessToken y RefreshToken (con mayúsculas)
                new_access_token = data.get("AccessToken") or data.get("accessToken")
                new_refresh_token = data.get("RefreshToken") or data.get("refreshToken")

                # Store new tokens
                query = text("""
                    INSERT INTO pp_token (token, refresh_token, fecha_registro)
                    VALUES (:token, :refresh_token, :fecha_registro)
                """)
                self.db.execute(query, {
                    "token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "fecha_registro": datetime.now()
                })
                self.db.commit()

                return data

            return None

    async def get_estudiante_by_curp_cct(self, curp: str, cct: str) -> EstudianteUSEBEQ:
        """
        Get student information by CURP and CCT
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.base_url}/estudiante/{curp}/{cct}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return EstudianteUSEBEQ(**response.json())

    async def get_estudiante_by_id(self, id_alumno: int) -> EstudianteUSEBEQ:
        """
        Get student information by ID
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.base_url}/estudiante/{id_alumno}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return EstudianteUSEBEQ(**response.json())

    async def get_boleta(self, id_alumno: int) -> bytes:
        """
        Get student report card (boleta) as PDF stream
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.base_url}/boleta/{id_alumno}",
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            response.raise_for_status()
            return response.content

    async def get_boleta_historica(self, id_alumno: int, anio_inicio: int) -> bytes:
        """
        Get historical student report card (boleta) as PDF stream
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.base_url}/boleta-historica/{id_alumno}/{anio_inicio}",
                headers={
                    "Authorization": f"Bearer {token}"
                }
            )
            response.raise_for_status()
            return response.content

    async def solicitar_baja(self, id_alumno: int, id_motivo_baja: int) -> SolicitudBajaResponse:
        """
        Request student withdrawal (baja)
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.base_url}/baja/",
                json={
                    "idAlumno": id_alumno,
                    "idMotivoBaja": id_motivo_baja
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return SolicitudBajaResponse(**response.json())

    async def get_tipos_baja(self) -> List[TipoBaja]:
        """
        Get catalog of withdrawal types (tipos de baja)
        """
        token = await self._get_valid_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{self.base_url}/catalogo/tipos-de-baja",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            data = response.json()
            return [TipoBaja(**item) for item in data]
