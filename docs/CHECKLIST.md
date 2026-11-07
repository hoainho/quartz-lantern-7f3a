# Part 1 requirement traceability

Reviewed against the original assignment on 2026-11-07. The rubric totals 70 core points: scrape 25, API upload 20, daily job 15, code and README 10. Tests offer 5 bonus points. These are rubric weights, not points awarded by this review.

Checked means the stated behavior has evidence. Unchecked means an exact requirement is still unmet or unverified. A documented substitute is not the same as full compliance.

| Graded area | Weight | Evidence and remaining qualification |
|---|---:|---|
| Scrape and clean quality | 25 | 398 articles in the first live run, Markdown conversion and file output. Headings, relative links and fenced code covered by tests. |
| API-based vector-store upload | 20 | 398 documents uploaded through Gemini File Search, with operation polling and a cited answer. UI setup/sanity check and exact embedded chunk counts remain deviations. |
| Daily job deployment and logs | 15 | Daily Scheduler trigger and completed Cloud Run execution recorded on 7 Nov. Updates, skips and removals observed against the live store. |
| Code clarity and README | 10 | Small typed Python modules, reproducible setup, Docker commands, chunking explanation, logs and screenshot. Final scoring remains the evaluator's judgment. |
| Tests | +5 | Offline unit and pipeline tests plus GitHub Actions. This does not replace live integration evidence. |

## 0. Warm-up

- [ ] Record the required conversation with the original OptiBot. The Part 1 repository does not contain evidence of this step. Trial portal use alone does not prove it.
- [x] Gemini platform credentials work: the [first upload](logs/2026-11-06-first-full-sync-local.log) and [answer transcript](sanity-check.md) exercise the service.

## 1. Scrape to Markdown

- [x] Fetch at least 30 articles from `support.optisigns.com`: [first run](logs/2026-11-06-first-full-sync-local.log), 398 articles across four API pages.
- [x] Save one Markdown file per article using `<id>-<slug>.md`: [scraper](../kbsync/scrape.py), [document construction](../kbsync/document.py), [pipeline test](../tests/test_pipeline.py).
- [x] Preserve headings, relative links and code blocks: [conversion tests](../tests/test_convert.py).
- [x] Remove navigation and noise: API article bodies exclude page chrome, while the [converter](../kbsync/convert.py) removes scripts, styles and in-page navigation. Images are intentionally omitted.
- [x] Local file output mirrors the fetched set, including stale-file removal: [pipeline test](../tests/test_pipeline.py).

## 2. Assistant and API upload

- [x] Use the [system prompt](../prompts/system_prompt.txt) verbatim as the model's system instruction: [assistant implementation](../kbsync/ask.py).
- [x] Upload Markdown through Python and the API, not drag and drop: [provider adapter](../kbsync/gemini_store.py), [398-document upload log](logs/2026-11-06-first-full-sync-local.log).
- [x] Configure and explain chunking: 400 whitespace tokens, 50 overlap. See [README](../README.md#design) and [D4](DECISIONS.md#d4---chunking-whitespace-config-accepted).
- [x] Log successful file counts and explicitly labelled local chunk estimates: `added=398`, `chunks_estimated=942`.
- [ ] Report the provider's actual number of embedded chunks. The implementation does not obtain this metric. A local estimate is supplied instead.
- [x] Answer the exact YouTube sanity question with citations: [live transcript](sanity-check.md) and [local UI screenshot](img/chat-ui.png).
- [ ] Create and test the assistant in AI Studio or Playground as requested. The implementation uses the API and a local UI instead. [Explanation](SUBMISSION_NOTE.md).

## 3. Daily cloud job

- [x] `main.py` wraps scrape and upload, exits 0 on success and 1 on failure: [job](../kbsync/job.py), [job tests](../tests/test_job.py).
- [x] Docker runs once using only an API key: [Dockerfile](../Dockerfile), [recorded container run](logs/2026-11-06-docker-run-local.log).
- [x] Re-scrape, compare article IDs and content hashes, and upload only the delta: [live delta test](logs/2026-11-06-live-delta-test.log).
- [x] Run daily on public cloud infrastructure: `23 2 * * *`, `Etc/UTC`, enabled Cloud Scheduler job `kb-sync-daily` targeting Cloud Run job `kb-sync`.
- [x] Observe the clock-triggered run, not just a manual launch: [Scheduler events](logs/2026-11-07-scheduler-clock.json), scheduled time `2026-11-07T02:23:02.36798Z`, HTTP 200.
- [x] Observe downstream completion and counts: [execution kb-sync-x4b7h](logs/2026-11-07T065056Z-kb-sync-x4b7h.log), `added=0 updated=2 skipped=394 removed=2 failed=0`, container exit 0.
- [x] Provide readable log artefacts through the README without requiring GCP access.

## 4. Code, README and deliverables

- [x] Cryptic GitHub repository name: `quartz-lantern-7f3a`, not a brand-based name.
- [x] Conventional Commits and focused modules. The earlier mixed commit is disclosed in [submission notes](SUBMISSION_NOTE.md#process-notes).
- [x] Environment-driven credentials and an [.env.sample](../.env.sample). `.env` and generated article data are excluded from version control.
- [x] README includes prerequisites, setup, local run, expected rerun result, Docker usage, chunking, job logs and an assistant screenshot.
- [x] Separate responsibilities: Zendesk retrieval, HTML conversion, document identity, delta classification, provider operations and job orchestration. See [kbsync](../kbsync).
- [x] Explain substitutions, omissions and unproven behavior in [submission notes](SUBMISSION_NOTE.md).
- [ ] Confirm reviewer access to the private repository before emailing the submission.

## 5. Bonus tests and verification

- [x] Tests cover Markdown preservation, slug/hash behavior, delta classification, failed uploads, deletion guards and repeated-run pipeline state.
- [x] [GitHub Actions run 42331256011](https://github.com/hoainho/quartz-lantern-7f3a/actions/runs/42331256011) succeeded for code commit `4bf7c4a`. The [workflow](../.github/workflows/tests.yml) uses Python 3.12 and `python -m pytest -q`.
- [x] Fresh-environment review on 2026-11-07: Python 3.12.15, dependencies installed from `requirements-dev.txt`, `python -m pytest -q` reported **80 passed in 1.39s**.
- [x] Live README smoke: `main.py` exited 0 with `added=0 updated=0 skipped=396 removed=0 failed=0`. The exact YouTube question returned five factual bullets and the correct support article citation. In this response the URL followed the `Article URL:` label on the next line.
- [x] Historical README print check, before the responsive UI revision: 328 words, one A4 page at 10.5pt body text with 12mm margins and a linked thumbnail. Visual inspection found no clipping. The earlier thumbnail opened the full 1125 × 1356 image. Pagination depends on the renderer and print settings.
- [x] Credential-pattern scan of tracked files, new evidence and Git history found no Google API key, GitHub token or private-key patterns. This is a bounded pattern scan, not a proof that every possible secret is absent.
- Fresh Docker build/run was not repeated: the installed Docker client's daemon socket refused connections. The linked successful container run remains historical evidence, not a new result.
- [x] Responsive local chat: browser-emulated widths 320–2560px and 667×375 landscape with the context panel open show no horizontal overflow or composer overlap. Loading skeletons, reduced motion, safe answer/link rendering, error recovery and resize-aware scrolling were exercised. These checks are not physical-device or Safari coverage.
- [x] Real provider streaming through `POST /api/ask`: [nine deltas and a final cited answer](logs/2026-11-07-local-chat-stream.json). The updated regression suite reported **95 passed in 9.77s**.

This checklist records coverage, not a guarantee of 70/70. The exact UI workflow, actual embedded chunk metric, warm-up evidence and recipient access must not be presented as already satisfied.
