from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, require_permissions
from app.enums import Permission
from app.services import analytics_service

router = APIRouter(prefix="/admin", tags=["admin:dashboard"])


@router.get("/dashboard", dependencies=[Depends(require_permissions(Permission.DASHBOARD_VIEW))])
async def dashboard(db: DB, days: int = Query(30, ge=7, le=365)):
    return await analytics_service.dashboard(db, days)


@router.get("/traffic", dependencies=[Depends(require_permissions(Permission.ANALYTICS_VIEW))])
async def traffic(db: DB, days: int = Query(30, ge=7, le=365)):
    return await analytics_service.traffic(db, days)
