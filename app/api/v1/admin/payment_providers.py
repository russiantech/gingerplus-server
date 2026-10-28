import logging
import uuid

from fastapi import APIRouter, Depends

from app.api.deps import DB, CurrentUser, require_permissions
from app.enums import Permission as P
from app.schemas.common import Message
from app.schemas.payment import ProviderOut, ProviderUpdate, TestResult
from app.services import provider_service

router = APIRouter(prefix="/admin/payment-providers", tags=["admin:payment-providers"], dependencies=[Depends(require_permissions(P.SETTINGS_MANAGE))])
log = logging.getLogger(__name__)


async def _one(db, provider: str) -> ProviderOut:
    return ProviderOut(**next(i for i in await provider_service.describe_all(db) if i["provider"] == provider))


@router.get("", response_model=list[ProviderOut])
async def list_providers(db: DB):
    """Masked view only — secrets are never returned. `source` says where the live credentials come from."""
    return [ProviderOut(**i) for i in await provider_service.describe_all(db)]


@router.put("/{provider}", response_model=ProviderOut)
async def update_provider(provider: str, data: ProviderUpdate, db: DB, actor: CurrentUser):
    await provider_service.upsert(db, provider, data.model_dump(exclude_unset=True), actor.id)
    log.info("payment provider %s updated by %s", provider, actor.email)
    return await _one(db, provider)


@router.post("/{provider}/default", response_model=ProviderOut)
async def make_default(provider: str, db: DB):
    await provider_service.set_default(db, provider)
    return await _one(db, provider)


@router.post("/{provider}/test", response_model=TestResult)
async def test_provider(provider: str, db: DB):
    ok, message, source = await provider_service.test_connection(db, provider)
    return TestResult(ok=ok, message=message, source=source)


@router.delete("/{provider}", response_model=Message)
async def remove_provider(provider: str, db: DB, actor: CurrentUser):
    """Delete the saved configuration → the provider falls back to environment variables (if any)."""
    await provider_service.remove(db, provider)
    log.info("payment provider %s config removed by %s", provider, actor.email)
    return Message(detail="Removed. Environment variables (if set) are used instead.")
