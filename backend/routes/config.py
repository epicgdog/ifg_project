"""Config / health endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from src.config import load_settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/health")
def config_health() -> dict[str, object]:
    """Report which provider keys are present and which model is active."""
    settings = load_settings()
    return {
        "openrouter": bool(settings.openrouter_api_key),
        "apollo": bool(settings.apollo_api_key),
        "hunter": bool(settings.hunter_api_key),
        "apify": bool(settings.apify_api_token and settings.apify_linkedin_actor_id),
        "model": settings.openrouter_model,
    }
