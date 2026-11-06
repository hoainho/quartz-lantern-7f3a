"""Chunking parameters and a local chunk-count estimate.

Gemini File Search chunks server-side and does not report how many chunks a
document produced, so the job logs an estimate computed by replaying the same
sliding window over whitespace-separated tokens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingConfig:
    max_tokens_per_chunk: int = 400
    max_overlap_tokens: int = 50

    def __post_init__(self) -> None:
        if self.max_tokens_per_chunk <= 0:
            raise ValueError("max_tokens_per_chunk must be positive")
        if not 0 <= self.max_overlap_tokens < self.max_tokens_per_chunk:
            raise ValueError("max_overlap_tokens must be in [0, max_tokens_per_chunk)")


DEFAULT_CHUNKING = ChunkingConfig()


def estimate_chunks(text: str, config: ChunkingConfig = DEFAULT_CHUNKING) -> int:
    """Number of windows needed to cover `text`; 0 for blank text."""
    tokens = len(text.split())
    if tokens == 0:
        return 0
    if tokens <= config.max_tokens_per_chunk:
        return 1
    stride = config.max_tokens_per_chunk - config.max_overlap_tokens
    return 1 + math.ceil((tokens - config.max_tokens_per_chunk) / stride)
