"""Convert Help Center article HTML into clean Markdown."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

_NOISE_TAGS = ("script", "style", "noscript", "img", "hr", "colgroup", "col")
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"))


def _video_url(src: str) -> str:
    """Turn an embed URL into a plain watch link (YouTube/Vimeo); else keep as is."""
    parsed = urlparse(src if "://" in src else f"https:{src}")
    host = parsed.netloc.lower()
    if host.endswith(("youtube.com", "youtube-nocookie.com")):
        if parsed.path.startswith("/embed/"):
            return f"https://www.youtube.com/watch?v={parsed.path.rsplit('/', 1)[-1]}"
        video = parse_qs(parsed.query).get("v")
        if video:
            return f"https://www.youtube.com/watch?v={video[0]}"
    if host.endswith("vimeo.com") and parsed.path.startswith("/video/"):
        return f"https://vimeo.com/{parsed.path.rsplit('/', 1)[-1]}"
    return parsed.geturl()


def _is_toc(lst: Tag) -> bool:
    """A list whose every item is a single in-page (#fragment) link is navigation."""
    items = lst.find_all("li")
    anchors = lst.find_all("a")
    return bool(anchors) and len(items) == len(anchors) and all(
        (a.get("href") or "").startswith("#") for a in anchors
    )


def _simplify_tables(soup: BeautifulSoup) -> None:
    """Drop empty rows; turn single-column 'callout' tables into blockquotes."""
    for table in reversed(soup.find_all("table")):
        for row in table.find_all("tr"):
            if not row.get_text(strip=True):
                row.decompose()
        rows = table.find_all("tr")
        if not rows:
            table.decompose()
        elif all(len(row.find_all(["td", "th"])) == 1 for row in rows):
            quote = soup.new_tag("blockquote")
            for row in rows:
                paragraph = soup.new_tag("p")
                paragraph.extend(list(row.find(["td", "th"]).contents))
                quote.append(paragraph)
            table.replace_with(quote)
        elif not table.find("th"):
            # Markdown tables need a header row; markdownify would emit an empty one.
            for cell in rows[0].find_all("td"):
                cell.name = "th"


def _clean(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    for frame in soup.find_all("iframe"):
        src = frame.get("src")
        if src:
            link = soup.new_tag("p")
            link.string = f"Video: {_video_url(src)}"
            frame.replace_with(link)
        else:
            frame.decompose()

    for lst in soup.find_all(["ul", "ol"]):
        if lst.parent is not None and _is_toc(lst):
            lst.decompose()

    # Remaining fragment links point at heading ids that no longer exist.
    for anchor in soup.find_all("a", href=lambda h: bool(h) and h.startswith("#")):
        anchor.unwrap()

    _simplify_tables(soup)

    for tag in soup.find_all(["figure", "div", "p"]):
        if not tag.get_text(strip=True) and not tag.find(["table", "pre"]):
            tag.decompose()


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    _clean(soup)
    text = markdownify(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=["span", "u", "figure", "div"],
        escape_underscores=False,
    )
    text = text.replace("\xa0", " ").translate(_ZERO_WIDTH)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
