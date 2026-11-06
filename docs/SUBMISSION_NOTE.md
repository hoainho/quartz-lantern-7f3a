# Submission note: what was cut, changed, or is unproven

The assignment asks candidates to say what they cut. This list is kept current; items marked
**open** are not yet done at the time of writing.

## Part 1 - deviations from the brief
| Item | What I did instead | Why |
|---|---|---|
| "Create the assistant in the OpenAI Playground / AI Studio" | The assistant is the Gemini model + `file_search` tool + the verbatim system prompt, driven by `python -m kbsync.ask`; the prompt is versioned in `prompts/system_prompt.txt` | The OpenAI Assistants API was shut down on 2026-08-26, and saved Prompt objects are scheduled for removal on 2026-11-30; AI Studio support for choosing a File Search store was not confirmable from the docs. **Open:** screenshot (AI Studio if it exposes stores, otherwise CLI output). |
| "Log how many chunks were embedded" | `chunks_estimated`, computed locally by replaying the 400/50 whitespace window | The File Search API documents no chunk count or chunk listing |
| Store state for "upload only the delta" | Hash and article id are stored as `custom_metadata` on each document; no database or volume | Scheduled containers have no durable disk |
| Delta also deletes | Articles removed from the source are deleted, with a guard that refuses to delete more than max(5, 20%) at once | A knowledge base must not keep answering from unpublished articles; the guard stops a partial source response from wiping it |
| Images in articles | Dropped (alt text is not kept); YouTube/Vimeo embeds become `Video: <url>` lines | Image URLs add noise to retrieval and the brief lists headings, code and links only |
| Tests | 65 unit tests plus a no-network end-to-end flow; CI on GitHub Actions | Bonus item |

## Part 1 - not yet proven (open)
- Live Gemini behaviour: mime type `text/markdown`, metadata round-trip in citations, model name `gemini-3.8-flash`.
- Time of the first full upload (sequential, one document at a time).
- Deployed daily run and its log artefact (`.do/app.yaml` is written from the docs and has not been deployed).
- Whether the model itself emits `Article URL:` lines; the CLI appends up to three from retrieval metadata if it does not.

## Process note
Commit `02b3d06` also removes the superseded upload CLI because two git commands ran in parallel; the later history is one change per commit.
