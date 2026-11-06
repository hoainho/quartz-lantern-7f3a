# Requirement traceability (Part 1)

Source: the assignment PDF. Pass bar: 70 pts = Scrape 25 + Upload 20 + Job 15 + Code/README 10.
Tick an item only when it is verified and the evidence is linked.

## 0. Warm-up
- [ ] Trial account created; chatted with the reference bot
- [x] Gemini API key (stored only in local `.env` and Secret Manager; tracked files and logs scanned: no key)

## 1. Scrape -> Markdown (25)
- [x] >= 30 articles pulled from the Help Center (Zendesk API) - 398 published articles fetched live (4 pages)
- [x] Each article converted to clean Markdown - 17 unit tests; 398 files, avg ~4.7k chars, none under 400 chars, all with front-matter
- [x] One file per article (`<id>-<slug>.md`) - `python -m kbsync.scrape` wrote 398 files (2.6 MB)
- [x] Relative links, code blocks, headings preserved - verified in sampled files (fenced GraphQL query, 10 links, 5-6 headings per article)
- [x] Nav / ads / scripts removed - no TOC lists or fragment links left; only 2 files contain `<iframe>` and both are inside code samples
- [x] Spot-check of 5 random files (seed 7): powerpoint-transition, guardian-news-app, get-started-api, move-screen-to-other-team, feeds

## 2. Assistant + vector store (20)
- [x] System prompt used **verbatim** (`prompts/system_prompt.txt`) - file matches the PDF, asserted in tests, passed as system instruction by `kbsync.ask` in the live answers
- [x] Markdown uploaded to the Gemini File Search store **via Python script / API** (no UI) - 398 files by `main.py` ([first sync](logs/2026-11-06-first-full-sync-local.log))
- [x] Chunking strategy chosen and explained in README - whitespace, 400 tokens / 50 overlap (DECISIONS D4)
- [x] Log shows number of files and chunks embedded - `added=398 ... chunks_estimated=942` (chunks estimated locally, DECISIONS D5; the API reports none)
- [x] Sanity check "How do I add a YouTube video?" answered correctly with citations - five bullets + `Article URL:` ([sanity-check.md](sanity-check.md))
- [x] Screenshot saved in `docs/img/` - `docs/img/sanity-check.png`

## 3. Daily job (15)
- [x] `main.py` wraps scrape + upload - `kbsync.job.run`, exit 0 clean / 1 on any failure
- [x] `Dockerfile`; `docker run -e API_KEY=... ` runs once and exits 0 - [docker run log](logs/2026-11-06-docker-run-local.log): skipped=398, exit 0; image 198 MB, non-root
- [x] Re-scrape, detect new/updated (hash), upload delta only - live: second run `skipped=398`; deleted doc gives `added=1`; tampered doc gives `updated=1` with one copy left ([live delta log](logs/2026-11-06-live-delta-test.log)); removal path proven offline only
- [x] Logs counts: added / updated / skipped - `sync done added=398 updated=0 skipped=0 removed=0 failed=0 chunks_estimated=942` ([first sync](logs/2026-11-06-first-full-sync-local.log))
- [x] Scheduled once per day on a cloud platform - GCP Cloud Scheduler `kb-sync-daily` (02:23 UTC) -> Cloud Run Job `kb-sync`, deployed by `deploy/gcp/deploy.sh`; manual execution `kb-sync-9m6vc` succeeded; first scheduled run is 2026-11-07 02:23 UTC (not yet observed)
- [x] Link to job logs or last-run artefact in README - three artefacts under `docs/logs/`

## Deliverables
- [x] GitHub repo with cryptic name (no brand in name), clear commits - private repo `quartz-lantern-7f3a`, Conventional Commits (one exception: `02b3d06` also removes the superseded upload CLI)
- [x] No hard-coded keys; `.env.sample` complete - tracked-file and history scan found only `API_KEY=...` placeholders; `.env` untracked
- [x] README <= 1 page: setup, local run, job-logs link, screenshot - 47 lines with links to three run logs and the screenshot
- [x] Screenshot of assistant answering with cited URLs - `docs/img/sanity-check.png` (rendered from the unedited CLI output; `docs/sanity-check.md`)

## Code clarity + README (10)
- [ ] Modules small and single-purpose; type hints; docstrings where non-obvious (author's judgement)
- [x] README accurate against actual behaviour - every command in "Run locally" was run (scrape, main.py, ask, pytest, docker run)

## Bonus (+5)
- [x] Unit tests (slug/hash, cleaning, delta classification) pass - 65 tests locally and green on GitHub Actions (`.github/workflows/tests.yml`)

## Submission note
- [ ] State what was cut and why (assignment asks for this)
