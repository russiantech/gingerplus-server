import uuid

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import require_staff
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.storage import get_storage

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
    storage = get_storage()
    name = f"{uuid.uuid4().hex}{ext}"
    url = await storage.save(name, data, file.content_type or "application/octet-stream")
    return {"url": url, "filename": name, "size": len(data), "storage": storage.name}
