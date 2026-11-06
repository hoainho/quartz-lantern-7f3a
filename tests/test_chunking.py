import pytest

from kbsync.chunking import ChunkingConfig, estimate_chunks

CFG = ChunkingConfig(max_tokens_per_chunk=10, max_overlap_tokens=2)


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


@pytest.mark.parametrize(
    ("words", "expected"),
    [
        (0, 0),
        (1, 1),
        (10, 1),  # exactly one full window
        (11, 2),  # one token spills into a second window
        (18, 2),  # windows cover [0:10] and [8:18]
        (19, 3),  # needs a third window
        (26, 3),
        (27, 4),
    ],
)
def test_estimate_replays_sliding_window(words, expected):
    assert estimate_chunks(_words(words), CFG) == expected


def test_whitespace_of_any_kind_separates_tokens():
    assert estimate_chunks("a\tb\nc  d", ChunkingConfig(2, 0)) == 2


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1)])
def test_invalid_config_is_rejected(size, overlap):
    with pytest.raises(ValueError):
        ChunkingConfig(size, overlap)
