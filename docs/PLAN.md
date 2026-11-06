# Part 1 sprint plan (budget: ~8h)

Every sprint ends with a working, committed increment and an observable
"Done when". Time-box is a ceiling; if a sprint overruns, cut scope from the
bottom of the "Cut order" list, never the graded core.

| Sprint | Goal | Est. | Done when |
|---|---|---|---|
| 0 | Foundation: repo, conventions, plan, checklist, decisions | 0.5h | Repo on GitHub, docs committed, decisions recorded |
| 1 | Scrape -> clean Markdown | 1.5h | >= 30 `.md` files; 5 random files spot-checked clean (headings, code, relative links kept; nav/ads gone) |
| 2 | Vector store upload via API + assistant | 2h | Log shows `files=N chunks=M`; sanity question answered with `Article URL:` citations; screenshot saved |
| 3 | Delta detection, `main.py`, Docker | 2h | Run 1 -> `added=N`; run 2 -> `added=0 updated=0 skipped=N`; `docker run` exits 0 |
| 4 | Deploy as daily cloud job | 1.5h | One real scheduled/triggered run on the cloud with counts in logs; link or artefact saved |
| 5 | README (<= 1 page), tests, cleanup | 1h (inside budget) | README complete; `pytest` green; no secrets in history |

## Sprint detail

### Sprint 0 - Foundation
- [x] Private repo with a neutral, cryptic name
- [x] `.gitignore`, `.env.sample`, pinned dependencies
- [ ] `docs/PLAN.md`, `docs/CHECKLIST.md`, `docs/DECISIONS.md`
- [ ] `AGENTS.md` (conventions), README skeleton

### Sprint 1 - Scrape to Markdown (25 pts)
- Read `/api/v2/help_center/{locale}/articles.json` with pagination; honour `next_page`.
- Skip drafts; keep `id`, `title`, `html_url`, `updated_at`, `body`.
- Convert `body` HTML with BeautifulSoup + markdownify: drop nav/ads/scripts, keep headings, fenced code, lists, tables, links (relative links preserved, absolute article URL in front-matter).
- File name: `<id>-<slug>.md` (stable across title edits is not guaranteed, so id is the identity).
- Front-matter: `title`, `url`, `updated_at`, `content_hash`.

### Sprint 2 - Vector store upload (20 pts)
- Create/reuse vector store; upload each file via API; attach with static chunking (see DECISIONS).
- Wait for indexing; log files and chunks.
- Create the assistant surface (Responses + File Search; Playground test) with the system prompt verbatim from `prompts/system_prompt.txt`.
- Sanity check: "How do I add a YouTube video?" -> screenshot with citations.

### Sprint 3 - Delta + Docker (part of 15 pts)
- Identity = article id. Change signal = `content_hash` (sha256 of rendered Markdown), `updated_at` as cheap pre-filter.
- State lives on the vector store file `attributes`, so the container needs no persistent disk.
- added: no file with that id; updated: hash differs -> replace; skipped: hash equal.
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
