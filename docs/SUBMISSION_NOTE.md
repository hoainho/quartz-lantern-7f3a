# Submission note: what was cut, changed, or is unproven

The assignment asks candidates to say what they cut. Updated 2026-11-06 after the live runs.

## Part 1 - deviations from the brief
| Item | What I did instead | Why |
|---|---|---|
| "Create the assistant in the OpenAI Playground / AI Studio" | The assistant is Gemini `gemini-3.6-flash` + the `file_search` tool + the verbatim system prompt, driven by `python -m kbsync.ask`; the prompt is versioned in `prompts/system_prompt.txt`. The screenshot is rendered from the unedited CLI output. | The OpenAI Assistants API was shut down on 2026-08-26 and saved Prompt objects are scheduled for removal on 2026-11-30; AI Studio chat does not document attaching a File Search store. |
| Model | `gemini-3.6-flash` | `gemini-3.8-flash` (the docs' example) answered 503/504 "high demand" on every call in testing, with and without File Search. |
| "Log how many chunks were embedded" | `chunks_estimated=942`, computed locally by replaying the 400/50 whitespace window | The File Search API documents no chunk count or chunk listing |
| Store state for "upload only the delta" | Hash and article id are `custom_metadata` on each document; no database or volume | Scheduled containers have no durable disk |
| Delta also deletes | Articles removed from the source are deleted, with a guard that refuses to delete more than max(5, 20%) at once | A knowledge base must not answer from unpublished articles; the guard stops a partial source response from wiping it |
| Images in articles | Dropped (alt text not kept); YouTube/Vimeo embeds become `Video: <url>` lines | Image URLs add retrieval noise; the brief lists headings, code and links only |
| Hosting | GCP Cloud Run Job + Cloud Scheduler (not DigitalOcean) | Chosen by the author; free within quota. Spec: `deploy/gcp/deploy.sh` |

## Part 1 - evidence (all under `docs/logs/`, `docs/sanity-check.md`)
- First full sync: 398 articles, 942 estimated chunks, 0 failures, 14m34s with 4 upload workers.
- A second run, a Docker run with only `API_KEY`, and a Cloud Run execution all report `skipped=398`, exit 0.
- Live delta test: a deleted document is re-added (`added=1`); a changed article is replaced and exactly one copy remains (`updated=1`).
- Answers: five bullets and model-written `Article URL:` lines for two in-scope questions; an out-of-scope question is refused.

## Part 1 - not proven
- The first run triggered by Cloud Scheduler itself (due 2026-11-07 02:23 UTC); only a manual execution of the same job has run.
- The removal path (article unpublished at the source) has been exercised by tests, not against the live store.
- The ask CLI uses `generate_content`, which the Gemini docs label "Legacy" in favour of the Interactions API; the job itself uses neither.
- First-sync time depends on `UPLOAD_WORKERS` and Gemini rate limits; 4 workers gave no 429s in this run, which does not bound a busier day.
- The rendered screenshot is not an AI Studio or Playground capture.

## Process notes
- Commit `02b3d06` also removes the superseded upload CLI because two git commands ran in parallel; every later commit is one change.
- A Gemini API key created by the assistant in a suspended project was deleted immediately; the key in use was supplied by the author, lives in `.env` and Secret Manager, and was checked absent from all tracked files and git history.
