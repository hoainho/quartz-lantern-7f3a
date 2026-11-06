"""Environment-driven configuration. Nothing is hard-coded; see .env.sample."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    zendesk_base_url: str
    zendesk_locale: str
    min_articles: int
    data_dir: Path
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        base_url = os.environ.get("ZENDESK_BASE_URL", "").rstrip("/")
        if not base_url:
            raise ValueError("ZENDESK_BASE_URL is required (see .env.sample)")
        return cls(
            zendesk_base_url=base_url,
            zendesk_locale=os.environ.get("ZENDESK_LOCALE", "en-us"),
            min_articles=int(os.environ.get("MIN_ARTICLES", "30")),
            data_dir=Path(os.environ.get("DATA_DIR", "data/articles")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
