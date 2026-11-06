# Decision log

Format: context, decision, consequence. Status: Proposed -> Accepted.

## D1 - Vector store provider: Gemini File Search (Accepted)
- Context: the assignment allows OpenAI Vector Store or Gemini equivalent.
- Decision: Gemini File Search, behind a small `VectorStore` interface (list, upsert, delete) so scraper and delta logic never touch the SDK and another provider can be added as an adapter.
- Why: storage and query-time embeddings are free; indexing is billed per token (cheap for ~400 short articles); a free tier exists; the OpenAI Assistants API the assignment links to is shut down (2026-08-26), so the "assistant in a playground" step has no like-for-like OpenAI path either.
- Consequence: answers are produced by a Gemini model with the `file_search` tool; AI Studio is used for the screenshot if it exposes File Search stores, otherwise a CLI reproduces the sanity check and its output is the evidence.

## D2 - System prompt kept in the repo (Accepted)
- Decision: the verbatim prompt lives in `prompts/system_prompt.txt` and is passed as system instruction by the sanity-check CLI; the same text is pasted into AI Studio.
- Why: reproducible and reviewable; no dependency on saved UI objects.

## D3 - Delta state on document `custom_metadata` (Accepted, verify in Sprint 2)
- Context: scheduled containers have no durable disk; Gemini `Document` supports up to 20 `customMetadata` entries (string, string list, numeric) and `documents.list/get/delete`. There is no update method for document content.
- Decision: each document carries `article_id`, `content_hash`, `updated_at`, `article_url`. Every run lists the store, diffs against the fresh scrape, and for changed articles uploads the new document then deletes the old one.
- Bonus: the docs state `custom_metadata` is returned on each `file_citation` annotation, so `article_url` can drive the required `Article URL:` lines.
- Consequence: identity is `article_id`, never the display name or title.

## D4 - Chunking: whitespace config (Proposed, tune in Sprint 2)
- Decision: `chunking_config.white_space_config` with `max_tokens_per_chunk=400`, `max_overlap_tokens=50` (~12%).
- Why: support articles are short step lists; chunks big enough to keep a heading with its steps, overlap small enough not to inflate storage (store quota counts ~3x input size).
- Consequence: README explains it; revisit if the "How do I add a YouTube video?" check retrieves poorly.

## D5 - Chunk count logging (Proposed, verify in Sprint 2)
- Context: the assignment asks to log chunks embedded. The Document resource documents no chunk count and no chunk-list method for File Search stores.
- Decision: log file counts from the API and compute chunk counts locally by replaying the whitespace window (size, overlap) over each document, labelled `chunks_estimated`. Replace with the real number if the API exposes one.
