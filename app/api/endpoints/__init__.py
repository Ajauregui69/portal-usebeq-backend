from fastapi import APIRouter
from app.api.endpoints import auth, users, students, grades, certificates, reports, scholarships, usebeq_external

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(grades.router, prefix="/grades", tags=["grades"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(scholarships.router, prefix="/scholarships", tags=["scholarships"])
api_router.include_router(usebeq_external.router, prefix="/usebeq", tags=["usebeq-external"])
