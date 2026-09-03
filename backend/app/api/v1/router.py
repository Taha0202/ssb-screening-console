from fastapi import APIRouter
from app.api.v1.endpoints import auth, checkpoints, officers, screening, audit, reference, system

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(checkpoints.router, prefix="/checkpoints", tags=["Checkpoints"])
api_router.include_router(officers.router, prefix="/officers", tags=["Personnel Management"])
api_router.include_router(screening.router, prefix="/screening", tags=["Screening & Verification"])
api_router.include_router(audit.router, prefix="/audit", tags=["Supervisor Audit Trail"])
api_router.include_router(reference.router, prefix="/reference", tags=["Reference Database"])
api_router.include_router(system.router, prefix="/system", tags=["System Status & Health"])
