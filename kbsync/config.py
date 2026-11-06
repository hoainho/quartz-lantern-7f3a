"""Environment-driven configuration. Nothing is hard-coded; see .env.sample."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# The job must run with nothing but an API key (`docker run -e API_KEY=... `), so the
# source site has a default; override with ZENDESK_BASE_URL.
DEFAULT_ZENDESK_BASE_URL = "https://support.optisigns.com"
# gemini-3.8-flash answered 503/504 "high demand" in testing; 3.6-flash supports File Search and responds.
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


@dataclass(frozen=True)
class Config:
    zendesk_base_url: str
    zendesk_locale: str
    min_articles: int
    data_dir: Path
    log_level: str
    gemini_api_key: str = ""
    gemini_file_search_store: str = ""
    gemini_model: str = DEFAULT_GEMINI_MODEL
    upload_workers: int = 4  # parallel uploads; the first full sync is ~400 files at ~10 s each

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        base_url = os.environ.get("ZENDESK_BASE_URL", DEFAULT_ZENDESK_BASE_URL).rstrip("/")
        return cls(
            zendesk_base_url=base_url,
            zendesk_locale=os.environ.get("ZENDESK_LOCALE", "en-us"),
            min_articles=int(os.environ.get("MIN_ARTICLES", "30")),
            data_dir=Path(os.environ.get("DATA_DIR", "data/articles")),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            gemini_api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY", ""),
            gemini_file_search_store=os.environ.get("GEMINI_FILE_SEARCH_STORE", ""),
            gemini_model=os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
            upload_workers=max(1, int(os.environ.get("UPLOAD_WORKERS", "4"))),
        )

    def require_gemini(self) -> None:
        """Fail fast, before any network call, when the API key is missing."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY (or API_KEY) is required (see .env.sample)")
