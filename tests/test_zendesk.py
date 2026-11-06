from kbsync.zendesk import fetch_articles


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return FakeResponse(self.pages[len(self.calls) - 1])


def _raw(id_, *, draft=False, body="<p>x</p>"):
    return {
        "id": id_,
        "title": f"  Title {id_} ",
        "html_url": f"https://h.example/hc/en-us/articles/{id_}",
        "updated_at": "2026-01-01T00:00:00Z",
        "draft": draft,
        "body": body,
    }


def test_follows_next_page_and_skips_drafts_and_empty_bodies():
    pages = [
        {"articles": [_raw(1), _raw(2, draft=True)], "next_page": "https://h.example/next?page=2"},
        {"articles": [_raw(3, body=""), _raw(4)], "next_page": None},
    ]
    session = FakeSession(pages)

    articles = list(fetch_articles("https://h.example", "en-us", session))

    assert [a.id for a in articles] == [1, 4]
    assert articles[0].title == "Title 1"
    assert session.calls[0][1] == {"per_page": 100}
    assert session.calls[1] == ("https://h.example/next?page=2", None)
