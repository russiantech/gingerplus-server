from fastapi import APIRouter, Request

from app.api.deps import DB, OptionalUser
from app.schemas.analytics import TrackEvent
from app.schemas.common import Message
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/track", response_model=Message, status_code=202)
async def track(ev: TrackEvent, request: Request, db: DB, user: OptionalUser):
    if ev.path.startswith("/admin"):
        return Message(detail="ignored")
    await analytics_service.track_view(db, ev, request.headers.get("user-agent", ""), user.id if user else None)
    return Message(detail="ok")
