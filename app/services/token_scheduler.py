import httpx
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class TokenSchedulerService:
    """
    Service to automatically refresh the USEBEQ API token before it expires.
    The token has a 24-hour lifespan, so we refresh it every 23 hours.
    """

    _scheduler: AsyncIOScheduler = None
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()

    async def refresh_usebeq_token(self):
        """
        Refresh the USEBEQ API token proactively.
        This runs every 23 hours to ensure the token is always valid.
        """
        db = SessionLocal()
        try:
            logger.info("Starting scheduled USEBEQ token refresh...")

            # Get the most recent token
            query = text("""
                SELECT id, token, refresh_token, fecha_registro
                FROM pp_token
                ORDER BY fecha_registro DESC
                LIMIT 1
            """)
            result = db.execute(query).fetchone()

            if result:
                token_id, access_token, refresh_token, fecha_registro = result
                time_diff = datetime.now() - fecha_registro

                # If token is older than 20 hours, refresh it
                if time_diff >= timedelta(hours=20):
                    logger.info(f"Token is {time_diff.total_seconds() / 3600:.1f} hours old. Refreshing...")
                    new_tokens = await self._refresh_token(access_token, refresh_token, db)

                    if new_tokens:
                        logger.info("Token refreshed successfully via refresh_token")
                    else:
                        logger.info("Refresh failed, getting new token via authentication...")
                        await self._authenticate(db)
                        logger.info("New token obtained via authentication")
                else:
                    logger.info(f"Token is only {time_diff.total_seconds() / 3600:.1f} hours old. No refresh needed.")
            else:
                # No token exists, get a new one
                logger.info("No token found in database. Getting new token...")
                await self._authenticate(db)
                logger.info("Initial token obtained")

        except Exception as e:
            logger.error(f"Error during scheduled token refresh: {str(e)}")
        finally:
            db.close()

    async def _refresh_token(self, access_token: str, refresh_token: str, db) -> dict:
        """
        Refresh the access token using the refresh token
        """
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{settings.USEBEQ_AUTH_API_URL}/get-refresh-tokens",
                    json={
                        "accessToken": access_token,
                        "refreshToken": refresh_token
                    },
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    new_access_token = data.get("AccessToken") or data.get("accessToken")
                    new_refresh_token = data.get("RefreshToken") or data.get("refreshToken")

                    # Store new tokens
                    query = text("""
                        INSERT INTO pp_token (token, refresh_token, fecha_registro)
                        VALUES (:token, :refresh_token, :fecha_registro)
                    """)
                    db.execute(query, {
                        "token": new_access_token,
                        "refresh_token": new_refresh_token,
                        "fecha_registro": datetime.now()
                    })
                    db.commit()

                    return data

        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")

        return None

    async def _authenticate(self, db) -> str:
        """
        Authenticate with the API and get new tokens
        """
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{settings.USEBEQ_AUTH_API_URL}/simple",
                json={
                    "correo": settings.USEBEQ_API_EMAIL,
                    "contrasenia": settings.USEBEQ_API_PASSWORD
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            data = response.json()
            access_token = data.get("AccessToken") or data.get("accessToken")
            refresh_token = data.get("RefreshToken") or data.get("refreshToken")

            # Store tokens in database
            query = text("""
                INSERT INTO pp_token (token, refresh_token, fecha_registro)
                VALUES (:token, :refresh_token, :fecha_registro)
            """)
            db.execute(query, {
                "token": access_token,
                "refresh_token": refresh_token,
                "fecha_registro": datetime.now()
            })
            db.commit()

            return access_token

    def start(self):
        """
        Start the scheduler with a job that runs every 23 hours
        """
        if not self._scheduler.running:
            # Add job to refresh token every 23 hours
            self._scheduler.add_job(
                self.refresh_usebeq_token,
                trigger=IntervalTrigger(hours=23),
                id="refresh_usebeq_token",
                name="Refresh USEBEQ API Token",
                replace_existing=True
            )

            self._scheduler.start()
            logger.info("Token scheduler started - will refresh token every 23 hours")

    def stop(self):
        """
        Stop the scheduler
        """
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Token scheduler stopped")


# Singleton instance
token_scheduler = TokenSchedulerService()
