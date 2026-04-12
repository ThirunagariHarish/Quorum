"""Resolve per-user LLM provider and API key (DB settings + env fallbacks)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Final

from sqlalchemy import select

from backend.app.core.config import settings as app_settings
from backend.app.core.encryption import decrypt_value
from backend.app.models.setting import Setting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

VALID_PROVIDERS: Final[tuple[str, ...]] = ("anthropic", "openai", "google")


async def resolve_llm_for_user(
    db: AsyncSession, user_id: uuid.UUID | str
) -> tuple[str, str]:
    """Return ``(provider, api_key)`` for the user's chosen LLM provider."""

    uid = uuid.UUID(str(user_id))

    async def get_setting(key: str) -> str | None:
        result = await db.execute(
            select(Setting).where(Setting.user_id == uid, Setting.key == key)
        )
        row = result.scalar_one_or_none()
        if not row or not row.value:
            return None
        if row.is_encrypted:
            return decrypt_value(row.value)
        return str(row.value)

    raw = await get_setting("llm_provider")
    provider = (raw or "anthropic").strip().lower()
    if provider not in VALID_PROVIDERS:
        provider = "anthropic"

    env_keys = {
        "anthropic": app_settings.ANTHROPIC_API_KEY or "",
        "openai": app_settings.OPENAI_API_KEY or "",
        "google": app_settings.GOOGLE_API_KEY or "",
    }
    setting_keys = {
        "anthropic": "anthropic_api_key",
        "openai": "openai_api_key",
        "google": "google_api_key",
    }

    sk = setting_keys[provider]
    key = await get_setting(sk) or env_keys[provider]
    if not key:
        raise ValueError(
            f"No API key configured for '{provider}'. "
            "Add the key in Settings → API Keys, or set the matching environment variable on the server."
        )

    return provider, key
