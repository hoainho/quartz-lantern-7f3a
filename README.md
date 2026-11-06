# Support-article sync job

Scrapes a Zendesk Help Center, converts articles to clean Markdown, and keeps a
Gemini File Search store in sync once per day. Only new or changed articles are
uploaded; articles removed at the source are deleted.

> Status: in progress. Plan: [docs/PLAN.md](docs/PLAN.md), checklist: [docs/CHECKLIST.md](docs/CHECKLIST.md), decisions: [docs/DECISIONS.md](docs/DECISIONS.md).

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.sample .env      # set GEMINI_API_KEY (or API_KEY); everything else has a default
```

## Run locally
```bash
.venv/bin/python -m kbsync.scrape                  # Markdown only -> data/articles/ (no API key needed)
.venv/bin/python main.py                           # scrape + sync delta; exits 0 on success
.venv/bin/python -m kbsync.ask "How do I add a YouTube video?"   # sanity check against the synced store
.venv/bin/python -m pytest                         # tests
docker build -t sync-job . && docker run --rm -e API_KEY=... sync-job
```
Each run logs `sync done added=N updated=N skipped=N removed=N failed=N chunks_estimated=M`.

## How it works
- **Scrape**: public Zendesk API, paginated, drafts skipped; fewer than `MIN_ARTICLES` aborts the run before anything is written or deleted.
- **Markdown**: HTML cleaned (scripts, images, in-page TOC removed; headings, lists, relative links, fenced code and tables kept; YouTube embeds become `Video:` links). File: `<id>-<slug>.md` with front-matter (`title`, `url`, `article_id`, `updated_at`, `content_hash`).
- **Delta**: identity is the article id, change signal is a SHA-256 of title + body. Sync state lives in each document's `custom_metadata` on the store, so the container needs no disk or database. A changed article is uploaded first and its old copy deleted afterwards.
- **Store**: found by display name `support-articles` (created if missing), so a fresh container reuses yesterday's store.

## Chunking strategy
Whitespace chunking, 400 tokens per chunk with 50 overlap. Articles are short step lists: chunks this size keep a heading with its steps, and a small overlap keeps a step that straddles a boundary retrievable without inflating storage (the quota counts roughly 3x the input). The API reports no chunk count, so `chunks_estimated` replays the same window locally.

## Daily job logs
_Pending: deployment (Sprint 4)._

## Sample answer
_Pending: screenshot of "How do I add a YouTube video?" (Sprint 2)._
