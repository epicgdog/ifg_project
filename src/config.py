from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    openrouter_http_referer: str
    openrouter_title: str
    apollo_api_key: str
    hunter_api_key: str
    serper_api_key: str
    apify_api_token: str
    apify_linkedin_actor_id: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3.2"),
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        openrouter_http_referer=os.getenv(
            "OPENROUTER_HTTP_REFERER", "https://ifg.local"
        ),
        openrouter_title=os.getenv("OPENROUTER_TITLE", "ForgeReach"),
        apollo_api_key=os.getenv("APOLLO_API_KEY", ""),
        hunter_api_key=os.getenv("HUNTER_API_KEY", ""),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        apify_api_token=os.getenv("APIFY_API_TOKEN", ""),
        apify_linkedin_actor_id=os.getenv("APIFY_LINKEDIN_ACTOR_ID", ""),
    )
