"""Pluggable file storage.

Backends (STORAGE_BACKEND = auto | local | supabase | s3 | vercel_blob):
  local        – writes to UPLOAD_DIR and serves from /static/uploads (dev / VPS / Docker volume; NOT for Vercel/serverless)
  supabase     – Supabase Storage (public bucket)         SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_BUCKET
  s3           – any S3-compatible store: AWS S3, Cloudflare R2, DigitalOcean Spaces, Backblaze B2, MinIO …
                 S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, S3_ENDPOINT_URL (omit for AWS), S3_PUBLIC_BASE_URL
  vercel_blob  – Vercel Blob                              BLOB_READ_WRITE_TOKEN
`auto` picks the first configured remote backend, otherwise local.
"""
import datetime as dt
import hashlib
import hmac
import logging
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.exceptions import AppError

log = logging.getLogger("storage")
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class StorageError(AppError):
    status_code = 502


class Storage:
    name = "base"

    async def save(self, key: str, data: bytes, content_type: str) -> str:  # returns public URL
        raise NotImplementedError

    async def delete(self, key: str) -> None:  # best-effort
        return None


class LocalStorage(Storage):
    name = "local"

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        try:
            folder = Path(settings.UPLOAD_DIR)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / key).write_bytes(data)
        except OSError as exc:
            raise StorageError("This server cannot store files locally (read-only filesystem). Configure Supabase, S3/R2 or Vercel Blob storage, or paste an image URL instead.", code="storage_unavailable") from exc
        return f"{settings.API_URL.rstrip('/')}/static/uploads/{key}"

    async def delete(self, key: str) -> None:
        try:
            (Path(settings.UPLOAD_DIR) / key).unlink(missing_ok=True)
        except OSError:
            pass


class SupabaseStorage(Storage):
    name = "supabase"

    def __init__(self) -> None:
        base = settings.SUPABASE_URL.strip().rstrip("/")
        for tail in ("/rest/v1", "/storage/v1", "/auth/v1"):  # tolerate a pasted API URL; we only need the project root
            if base.endswith(tail):
                base = base[: -len(tail)]
        self.base = base
        self.bucket = settings.SUPABASE_BUCKET
        self.headers = {"Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}", "apikey": settings.SUPABASE_SERVICE_KEY}

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(f"{self.base}/storage/v1/object/{self.bucket}/{key}", content=data, headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"})
        if r.status_code >= 300:
            log.error("supabase upload failed %s %s", r.status_code, r.text[:200])
            raise StorageError("Image upload failed (Supabase). Check bucket name and service key.", code="storage_failed")
        return f"{self.base}/storage/v1/object/public/{self.bucket}/{key}"

    async def delete(self, key: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                await c.delete(f"{self.base}/storage/v1/object/{self.bucket}/{key}", headers=self.headers)
        except httpx.HTTPError:
            pass


class VercelBlobStorage(Storage):
    name = "vercel_blob"

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        headers = {"Authorization": f"Bearer {settings.BLOB_READ_WRITE_TOKEN}", "x-api-version": "7", "x-content-type": content_type, "x-add-random-suffix": "0", "access": "public"}
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.put(f"https://blob.vercel-storage.com/{key}", content=data, headers=headers)
        if r.status_code >= 300:
            log.error("vercel blob upload failed %s %s", r.status_code, r.text[:200])
            raise StorageError("Image upload failed (Vercel Blob). Check BLOB_READ_WRITE_TOKEN.", code="storage_failed")
        return r.json()["url"]


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


class S3Storage(Storage):
    """S3-compatible object storage using a small SigV4 signer (no boto3 needed → light for serverless)."""
    name = "s3"

    def __init__(self) -> None:
        self.bucket, self.region = settings.S3_BUCKET, settings.S3_REGION or "auto"
        self.endpoint = (settings.S3_ENDPOINT_URL or f"https://s3.{self.region}.amazonaws.com").rstrip("/")
        # path-style addressing works for AWS, R2, Spaces, B2 and MinIO alike
        self.host = self.endpoint.split("://", 1)[1]

    def _url(self, key: str) -> str:
        return f"{self.endpoint}/{self.bucket}/{quote(key)}"

    def _sign(self, method: str, key: str, payload: bytes, content_type: str | None) -> dict[str, str]:
        now = dt.datetime.now(dt.timezone.utc)
        amz, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
        phash = hashlib.sha256(payload).hexdigest()
        hdrs = {"host": self.host, "x-amz-content-sha256": phash, "x-amz-date": amz}
        if content_type:
            hdrs["content-type"] = content_type
        signed = ";".join(sorted(hdrs))
        canon = "\n".join([method, f"/{self.bucket}/{quote(key)}", "", "".join(f"{k}:{hdrs[k]}\n" for k in sorted(hdrs)), signed, phash])
        scope = f"{day}/{self.region}/s3/aws4_request"
        to_sign = "\n".join(["AWS4-HMAC-SHA256", amz, scope, hashlib.sha256(canon.encode()).hexdigest()])
        k = _hmac(_hmac(_hmac(_hmac(("AWS4" + settings.S3_SECRET_KEY).encode(), day), self.region), "s3"), "aws4_request")
        sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
        out = {k2: v for k2, v in hdrs.items() if k2 != "host"}
        out["Authorization"] = f"AWS4-HMAC-SHA256 Credential={settings.S3_ACCESS_KEY}/{scope}, SignedHeaders={signed}, Signature={sig}"
        return out

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.put(self._url(key), content=data, headers=self._sign("PUT", key, data, content_type))
        if r.status_code >= 300:
            log.error("s3 upload failed %s %s", r.status_code, r.text[:300])
            raise StorageError("Image upload failed (S3). Check bucket, region, endpoint and credentials.", code="storage_failed")
        base = settings.S3_PUBLIC_BASE_URL.rstrip("/") if settings.S3_PUBLIC_BASE_URL else f"{self.endpoint}/{self.bucket}"
        return f"{base}/{key}"

    async def delete(self, key: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                await c.delete(self._url(key), headers=self._sign("DELETE", key, b"", None))
        except httpx.HTTPError:
            pass


def resolve_backend() -> str:
    choice = (settings.STORAGE_BACKEND or "auto").lower()
    if choice != "auto":
        return choice
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        return "supabase"
    if settings.S3_BUCKET and settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
        return "s3"
    if settings.BLOB_READ_WRITE_TOKEN:
        return "vercel_blob"
    return "local"


def get_storage() -> Storage:
    backend = resolve_backend()
    try:
        return {"supabase": SupabaseStorage, "s3": S3Storage, "vercel_blob": VercelBlobStorage}.get(backend, LocalStorage)()
    except Exception as exc:  # mis-configured backend must not take the API down
        log.error("storage backend %s misconfigured: %s — using local", backend, exc)
        return LocalStorage()


_OUR_KEY = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp|svg|gif|pdf)$")


async def delete_by_url(url: str) -> bool:
    """Best-effort removal of a file we uploaded (names are `<uuid4hex>.<ext>`). Never touches bundled /images/ assets or foreign URLs."""
    try:
        key = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
        if not _OUR_KEY.match(key) or "/images/" in url:
            return False
        await get_storage().delete(key)
        return True
    except Exception:  # cleanup must never fail the user's save
        log.warning("could not delete %s", url)
        return False
