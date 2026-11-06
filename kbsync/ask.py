"""Sanity-check CLI: ask the support bot a question against the File Search store.

    python -m kbsync.ask "How do I add a YouTube video?"

Uses the verbatim system prompt from prompts/system_prompt.txt and prints the
model's answer plus the source articles the retrieval step actually used.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kbsync.config import Config
from kbsync.gemini_store import META_ARTICLE_URL
from kbsync.log import configure_logging

log = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
MAX_SOURCES = 3  # the system prompt allows at most 3 "Article URL:" lines


@dataclass(frozen=True)
class Source:
    title: str
    url: str


@dataclass(frozen=True)
class Reply:
    text: str
    sources: list[Source]


def load_system_prompt(path: Path = SYSTEM_PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8").strip()


def title_from_url(url: str) -> str:
    """'.../articles/360051014713-How-to-Use-YouTube' -> 'How to Use YouTube'.

    The retrieved document's own title is its file name, which is not readable.
    """
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    slug = slug.split("-", 1)[1] if slug.split("-", 1)[0].isdigit() and "-" in slug else slug
    return slug.replace("-", " ") or url


def extract_sources(response: Any, limit: int = MAX_SOURCES) -> list[Source]:
    """Distinct article URLs from retrieval grounding, in retrieval order."""
    sources: list[Source] = []
    seen: set[str] = set()
    for candidate in response.candidates or []:
        grounding = candidate.grounding_metadata
        for chunk in (grounding.grounding_chunks or []) if grounding else []:
            context = chunk.retrieved_context
            if context is None:
                continue
            meta = {m.key: m.string_value for m in (context.custom_metadata or [])}
            url = meta.get(META_ARTICLE_URL)
            if url and url not in seen:
                seen.add(url)
                sources.append(Source(title=title_from_url(url), url=url))
    return sources[:limit]


def ask(client: Any, model: str, store_name: str, question: str) -> Reply:
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=load_system_prompt(),
            tools=[types.Tool(file_search=types.FileSearch(file_search_store_names=[store_name]))],
        ),
    )
    return Reply(text=response.text or "", sources=extract_sources(response))


def format_reply(reply: Reply) -> str:
    """Answer followed by 'Article URL:' lines for retrieved sources.

    The system prompt asks the model for those lines but does not always comply (it sometimes
    writes markdown links instead). If the model used the prefix, only sources it did not cite
    are added; if it never used the prefix, every retrieved source is listed in the required form.
    """
    lines = [reply.text.rstrip()]
    if "Article URL:" in reply.text:
        missing = [s for s in reply.sources if s.url not in reply.text]
    else:
        missing = list(reply.sources)
    if missing:
        lines.append("")
        lines.extend(f"Article URL: {s.url}" for s in missing)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("question")
    args = parser.parse_args()

    config = Config.from_env()
    configure_logging(config.log_level)
    config.require_gemini()

    from kbsync.gemini_store import ensure_store, make_client
    from kbsync.job import STORE_DISPLAY_NAME

    client = make_client(config.gemini_api_key)
    store_name = ensure_store(client, config.gemini_file_search_store, STORE_DISPLAY_NAME)
    reply = ask(client, config.gemini_model, store_name, args.question)
    print(format_reply(reply))


if __name__ == "__main__":
    main()
