# Requirement traceability (Part 1)

Source: the assignment PDF. Pass bar: 70 pts = Scrape 25 + Upload 20 + Job 15 + Code/README 10.
Tick an item only when it is verified and the evidence is linked.

## 0. Warm-up
- [ ] Trial account created; chatted with the reference bot
- [ ] AI platform account + API key (stored only in local `.env`)

## 1. Scrape -> Markdown (25)
- [ ] >= 30 articles pulled from the Help Center (Zendesk API)
- [ ] Each article converted to clean Markdown
- [ ] One file per article (`<id>-<slug>.md`)
- [ ] Relative links, code blocks, headings preserved
- [ ] Nav / ads / scripts removed
- [ ] Spot-check of 5 random files recorded in README or PR notes

## 2. Assistant + vector store (20)
- [ ] System prompt used **verbatim** (`prompts/system_prompt.txt`)
- [ ] Markdown uploaded to the vector store **via Python script / API** (no UI)
- [ ] Chunking strategy chosen and explained in README
- [ ] Log shows number of files and chunks embedded
- [ ] Sanity check "How do I add a YouTube video?" answered correctly with citations
- [ ] Screenshot saved in `docs/img/`

## 3. Daily job (15)
- [ ] `main.py` wraps scrape + upload
- [ ] `Dockerfile`; `docker run -e API_KEY=... ` runs once and exits 0
- [ ] Re-scrape, detect new/updated (hash), upload delta only
- [ ] Logs counts: added / updated / skipped
- [ ] Scheduled once per day on a cloud platform
- [ ] Link to job logs or last-run artefact in README

## Deliverables
- [ ] GitHub repo with cryptic name (no brand in name), clear commits
- [ ] No hard-coded keys; `.env.sample` complete
- [ ] README <= 1 page: setup, local run, job-logs link, screenshot
- [ ] Screenshot of assistant answering with cited URLs

## Code clarity + README (10)
- [ ] Modules small and single-purpose; type hints; docstrings where non-obvious
- [ ] README accurate against actual behaviour

## Bonus (+5)
- [ ] Unit tests (slug/hash, cleaning, delta classification) pass in CI/locally

## Submission note
- [ ] State what was cut and why (assignment asks for this)
