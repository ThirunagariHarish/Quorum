import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.core.encryption import decrypt_value, encrypt_value
from backend.app.models.setting import Setting
from backend.app.models.user import User
from backend.app.schemas.setting import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["settings"])
logger = structlog.get_logger()

ENCRYPTED_KEYS = {
    "anthropic_api_key",
    "openai_api_key",
    "google_api_key",
    "telegram_bot_token",
    "devto_api_key",
}


def _mask_value(value: str) -> str:
    if len(value) <= 8:
        return "****"
    return value[:6] + "..." + "****"


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Setting).where(Setting.user_id == current_user.id)
    )
    settings_rows = result.scalars().all()

    output = {}
    for s in settings_rows:
        if s.is_encrypted and s.value:
            try:
                decrypted = decrypt_value(s.value)
                output[s.key] = _mask_value(decrypted)
                output[f"{s.key}_set"] = True
            except Exception:
                output[f"{s.key}_set"] = False
        else:
            output[s.key] = s.value

    return SettingsResponse(settings=output)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for key, value in body.settings.items():
        is_encrypted = key in ENCRYPTED_KEYS
        stored_value = encrypt_value(str(value)) if is_encrypted and value else str(value)

        result = await db.execute(
            select(Setting).where(
                Setting.user_id == current_user.id, Setting.key == key
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = stored_value
            existing.is_encrypted = is_encrypted
        else:
            db.add(
                Setting(
                    user_id=current_user.id,
                    key=key,
                    value=stored_value,
                    is_encrypted=is_encrypted,
                )
            )

    await db.flush()
    logger.info("settings_updated", user_id=str(current_user.id), keys=list(body.settings.keys()))

    return await get_settings(current_user=current_user, db=db)
