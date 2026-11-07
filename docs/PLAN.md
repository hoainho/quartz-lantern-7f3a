# Part 1 sprint plan (budget: ~8h)

This is the historical implementation plan, not the final acceptance record. See [CHECKLIST.md](CHECKLIST.md) for current evidence and [SUBMISSION_NOTE.md](SUBMISSION_NOTE.md) for deviations. The estimates below total 8.5 hours and are not a measured time log.

Every sprint ends with a working, committed increment and an observable
"Done when". Time-box is a ceiling; if a sprint overruns, cut scope from the
bottom of the "Cut order" list, never the graded core.

| Sprint | Goal | Est. | Done when |
|---|---|---|---|
| 0 | Foundation: repo, conventions, plan, checklist, decisions | 0.5h | Repo on GitHub, docs committed, decisions recorded |
| 1 | Scrape -> clean Markdown | 1.5h | >= 30 `.md` files; 5 random files spot-checked clean (headings, code, relative links kept; nav/ads gone) |
| 2 | Gemini File Search upload via API + sanity check | 2h | Log shows `files=N chunks_estimated=M`; sanity question answered with `Article URL:` citations; screenshot saved |
| 3 | Delta detection, `main.py`, Docker | 2h | Run 1 -> `added=N`; run 2 -> `added=0 updated=0 skipped=N`; `docker run` exits 0 |
| 4 | Deploy as daily cloud job | 1.5h | One real scheduled/triggered run on the cloud with counts in logs; link or artefact saved |
| 5 | README (<= 1 page), tests, cleanup | 1h | README complete; `pytest` green; no secrets in history |

## Sprint detail

### Sprint 0 - Foundation
- [x] Private repo with a neutral, cryptic name
- [x] `.gitignore`, `.env.sample`, pinned dependencies
- [x] `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/DECISIONS.md`
- [x] `AGENTS.md` (conventions), README skeleton

### Sprint 1 - Scrape to Markdown (25 pts)
- [x] Zendesk client with pagination, retries, draft filtering (398 published articles live)
- [x] HTML -> Markdown conversion, with [preservation and cleaning tests](../tests/test_convert.py).
- [x] `<id>-<slug>.md` file names and content hashes, with [document tests](../tests/test_document.py).
- [x] Scrape CLI wrote 398 articles in the [first live run](logs/2026-11-06-first-full-sync-local.log).

### Sprint 2 - Gemini File Search upload (20 pts)
- Create/reuse a File Search store; upload each file via API with `custom_metadata` and whitespace chunking (DECISIONS D3, D4).
- Poll the upload operations until done; log files and chunks (chunk count estimated, D5).
- Sanity-check CLI: Gemini model + `file_search` tool + system prompt verbatim from `prompts/system_prompt.txt`; AI Studio screenshot if it exposes File Search stores.
- Sanity check: "How do I add a YouTube video?" -> screenshot with citations.

### Sprint 3 - Delta + Docker (part of 15 pts)
- Identity = `article_id`. Change signal = `content_hash`; `updated_at` is informational.
- State lives on document `custom_metadata`, so the container needs no persistent disk.
- added: no document with that id; updated: hash differs -> upload new, delete old; skipped: hash equal.
- `main.py` runs once, logs counts, exits 0 (non-zero on failure).

### Sprint 4 - Daily job (part of 15 pts)
- Build image, push, schedule once per day on a cloud platform; secrets via platform env.
- Trigger once manually and capture the log artefact.

### Sprint 5 - Docs and tests (10 pts + bonus 5)
- README <= 1 page: setup, run locally, chunking explanation, job logs link, screenshot.
- Unit tests: slug/hash, HTML cleaning, delta classification.

## Cut order if time runs out
1. Bonus tests beyond delta classification
2. README polish
3. Extra Markdown cleaning edge cases

Never cut: API upload, delta logic, deployed daily job with logs.
