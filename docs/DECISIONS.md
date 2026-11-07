# Decision log

Format: context, decision, consequence. Status: Proposed -> Accepted.

## D1 - Vector store provider: Gemini File Search (Accepted)
- Context: the assignment allows OpenAI Vector Store or Gemini equivalent.
- Decision: Gemini File Search, behind a small `VectorStore` interface (list, upload, delete) so scraper and delta logic do not depend directly on the SDK.
- Why: the API supports managed indexing, retrieval and per-document metadata, which are enough for the required upload and daily delta job without another database.
- Consequence: answers use a Gemini model with the `file_search` tool. The submitted screenshot is from the local UI, not AI Studio. This is an explicit deviation, not a completed UI requirement.

## D2 - System prompt kept in the repo (Accepted)
- Decision: the verbatim prompt lives in `prompts/system_prompt.txt` and is passed as the system instruction by the CLI and local UI. The separate AI Studio experiment is not evidence of this configuration.
- Why: reproducible and reviewable; no dependency on saved UI objects.

## D3 - Delta state on document `custom_metadata` (Accepted)
- Context: scheduled containers have no durable disk; Gemini `Document` supports up to 20 `customMetadata` entries (string, string list, numeric) and `documents.list/get/delete`. There is no update method for document content.
- Decision: each document carries `article_id`, `content_hash`, `updated_at`, `article_url`. Every run lists the store, diffs against the fresh scrape, and for changed articles uploads the new document then deletes the old one.
- Evidence: retrieval metadata supplies `article_url` for citations. The first upload, live delta test and scheduled execution are linked in `CHECKLIST.md`.
- Consequence: identity is `article_id`, never the display name or title.

## D4 - Chunking: whitespace config (Accepted)
- Decision: `chunking_config.white_space_config` with `max_tokens_per_chunk=400`, `max_overlap_tokens=50` (~12%).
- Why: support articles are short step lists. This window aims to keep a heading with its instructions while limiting duplicated overlap. It is a chosen starting configuration, not a measured optimum.
- Evidence: the API accepted this configuration during the 398-document upload and the recorded sanity question retrieved a relevant article. No comparison against alternative chunk sizes was performed.

## D5 - Chunk count logging (Accepted with limitation)
- Context: the assignment asks for the number of chunks embedded. The integration does not retrieve a provider-reported chunk count.
- Decision: log successful file operations and estimate chunks locally using the configured whitespace window. The metric is named `chunks_estimated` to avoid claiming it is measured.
- Consequence: 942 is an estimate for the first upload, not proof of the exact indexed count. This requirement remains qualified in `CHECKLIST.md` and `SUBMISSION_NOTE.md`.
