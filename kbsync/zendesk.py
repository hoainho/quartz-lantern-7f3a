"""Read published articles from the Zendesk Help Center API (no auth required)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

PAGE_SIZE = 100  # Zendesk maximum
TIMEOUT_S = 30


@dataclass(frozen=True)
class Article:
    id: int
    title: str
    url: str
    updated_at: str
    body_html: str


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_articles(
    base_url: str, locale: str, session: requests.Session | None = None
) -> Iterator[Article]:
    """Yield every published article, following `next_page` until exhausted."""
    session = session or _session()
    url: str | None = f"{base_url}/api/v2/help_center/{locale}/articles.json"
    params: dict[str, int] | None = {"per_page": PAGE_SIZE}
    page = 0
    while url:
        resp = session.get(url, params=params, timeout=TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
        page += 1
        log.info("fetched page=%d articles=%d", page, len(payload["articles"]))
        for raw in payload["articles"]:
            if raw.get("draft") or not raw.get("body"):
                continue
            yield Article(
                id=raw["id"],
                title=raw["title"].strip(),
                url=raw["html_url"],
                updated_at=raw["updated_at"],
                body_html=raw["body"],
            )
        url = payload.get("next_page")
        params = None  # next_page already carries the query string
