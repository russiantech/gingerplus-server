import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import require_staff
from app.core.config import settings
from app.core.exceptions import AppError

router = APIRouter(prefix="/admin/media", tags=["admin:media"], dependencies=[Depends(require_staff)])
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/svg+xml": ".svg", "image/gif": ".gif", "application/pdf": ".pdf"}


@router.post("", status_code=201)
async def upload(file: UploadFile):
    ext = ALLOWED.get(file.content_type or "")
    if not ext:
        raise AppError("Unsupported file type. Use JPG, PNG, WebP, SVG, GIF or PDF.", code="bad_file_type")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise AppError(f"File too large (max {settings.MAX_UPLOAD_MB}MB).", code="file_too_large")
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (folder / name).write_bytes(data)
    return {"url": f"{settings.API_URL.rstrip('/')}/static/uploads/{name}", "filename": name, "size": len(data)}
