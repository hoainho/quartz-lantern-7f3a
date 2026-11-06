# Requirement traceability (Part 1)

Source: the assignment PDF. Pass bar: 70 pts = Scrape 25 + Upload 20 + Job 15 + Code/README 10.
Tick an item only when it is verified and the evidence is linked.

## 0. Warm-up
- [ ] Trial account created; chatted with the reference bot
- [ ] Gemini API key (stored only in local `.env`; AI Studio account)

## 1. Scrape -> Markdown (25)
- [x] >= 30 articles pulled from the Help Center (Zendesk API) - 398 published articles fetched live (4 pages)
- [x] Each article converted to clean Markdown - 17 unit tests; 398 files, avg ~4.7k chars, none under 400 chars, all with front-matter
- [x] One file per article (`<id>-<slug>.md`) - `python -m kbsync.scrape` wrote 398 files (2.6 MB)
- [x] Relative links, code blocks, headings preserved - verified in sampled files (fenced GraphQL query, 10 links, 5-6 headings per article)
- [x] Nav / ads / scripts removed - no TOC lists or fragment links left; only 2 files contain `<iframe>` and both are inside code samples
- [x] Spot-check of 5 random files (seed 7): powerpoint-transition, guardian-news-app, get-started-api, move-screen-to-other-team, feeds

## 2. Assistant + vector store (20)
- [ ] System prompt used **verbatim** (`prompts/system_prompt.txt`) - file matches the PDF and is asserted in tests, used by `kbsync.ask`; pending: same text pasted into AI Studio
- [ ] Markdown uploaded to the Gemini File Search store **via Python script / API** (no UI)
- [x] Chunking strategy chosen and explained in README - whitespace, 400 tokens / 50 overlap (DECISIONS D4)
- [ ] Log shows number of files and chunks embedded (chunks estimated locally, see DECISIONS D5)
- [ ] Sanity check "How do I add a YouTube video?" answered correctly with citations
- [ ] Screenshot saved in `docs/img/`

## 3. Daily job (15)
- [x] `main.py` wraps scrape + upload - `kbsync.job.run`, exit 0 clean / 1 on any failure
- [ ] `Dockerfile`; `docker run -e API_KEY=... ` runs once and exits 0 - image builds (198 MB, non-root) and exits 1 without a key; pending: clean exit 0 with a real key
- [ ] Re-scrape, detect new/updated (hash), upload delta only - proven offline over three simulated days (tests/test_pipeline.py); pending: live run against the store
- [ ] Logs counts: added / updated / skipped - `sync done added= updated= skipped= removed= failed= chunks_estimated=` implemented; pending: real log line
- [ ] Scheduled once per day on a cloud platform
- [ ] Link to job logs or last-run artefact in README

## Deliverables
- [x] GitHub repo with cryptic name (no brand in name), clear commits - private repo `quartz-lantern-7f3a`, Conventional Commits (one exception: `02b3d06` also removes the superseded upload CLI)
- [x] No hard-coded keys; `.env.sample` complete - tracked-file and history scan found only `API_KEY=...` placeholders; `.env` untracked
- [ ] README <= 1 page: setup, local run, job-logs link, screenshot
- [ ] Screenshot of assistant answering with cited URLs

## Code clarity + README (10)
- [ ] Modules small and single-purpose; type hints; docstrings where non-obvious
- [ ] README accurate against actual behaviour

## Bonus (+5)
- [x] Unit tests (slug/hash, cleaning, delta classification) pass - 65 tests locally and green on GitHub Actions (`.github/workflows/tests.yml`)

## Submission note
- [ ] State what was cut and why (assignment asks for this)
