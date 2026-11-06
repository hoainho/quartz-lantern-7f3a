"""Turn an Article into the Markdown file that gets stored and uploaded."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

from kbsync.convert import html_to_markdown
from kbsync.zendesk import Article

_MAX_SLUG = 80


@dataclass(frozen=True)
class Document:
    article_id: int
    filename: str
    content: str  # full file text, front-matter included
    content_hash: str  # sha256 of title + body; ignores volatile metadata
    title: str
    url: str
    updated_at: str


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:_MAX_SLUG].strip("-") or "article"


def _front_matter(fields: dict[str, str]) -> str:
    lines = [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()]
    return "\n".join(["---", *lines, "---"])


def build_document(article: Article) -> Document:
    """Render an article; the hash covers only what the reader sees (title + body).

    `updated_at` is excluded on purpose: Zendesk bumps it on edits that do not
    change the text, which would cause pointless re-uploads.
    """
    body = html_to_markdown(article.body_html)
    core = f"# {article.title}\n\n{body}\n"
    content_hash = hashlib.sha256(core.encode()).hexdigest()
    front = _front_matter(
        {
            "title": article.title,
            "url": article.url,
            "article_id": str(article.id),
            "updated_at": article.updated_at,
            "content_hash": content_hash,
        }
    )
    return Document(
        article_id=article.id,
        filename=f"{article.id}-{slugify(article.title)}.md",
        content=f"{front}\n\n{core}",
        content_hash=content_hash,
        title=article.title,
        url=article.url,
        updated_at=article.updated_at,
    )
