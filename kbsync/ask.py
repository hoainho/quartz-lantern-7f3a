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
                sources.append(Source(title=context.title or url, url=url))
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
    """Answer followed by the retrieved sources; no duplicate lines if the model cited them."""
    lines = [reply.text.rstrip()]
    missing = [s for s in reply.sources if s.url not in reply.text]
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
    if not config.gemini_file_search_store:
        raise SystemExit("GEMINI_FILE_SEARCH_STORE is required to ask questions")

    from google import genai

    client = genai.Client(api_key=config.gemini_api_key)
    reply = ask(client, config.gemini_model, config.gemini_file_search_store, args.question)
    print(format_reply(reply))


if __name__ == "__main__":
    main()
