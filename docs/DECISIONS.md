# Decision log

Format: context, decision, consequence. Status: Proposed -> Accepted.

## D1 - Vector store provider: OpenAI (Proposed)
- Context: assignment allows OpenAI Vector Store or Gemini File Search.
- Decision: OpenAI, behind a small `VectorStore` interface so a Gemini adapter can be added without touching scraper or delta logic.
- Why: per-file `attributes` (<= 16 key/values) let sync state live on the store itself; explicit static chunking is documented and configurable; citations come back as file annotations.
- Consequence: needs a funded OpenAI project (File Search calls billed per call, storage free up to 1 GB).

## D2 - Responses API + File Search instead of Assistants API (Accepted)
- Context: the Assistants API was shut down on 2026-08-26; saved Prompt objects are scheduled for deprecation on 2026-11-30. The assignment text still says "create the assistant in the Playground".
- Decision: the assistant is a Responses call with the `file_search` tool and the verbatim system prompt, versioned in `prompts/system_prompt.txt`. A tiny CLI reproduces the sanity check outside the Playground.
- Consequence: README states this deviation explicitly. Playground is used for the screenshot if it exposes File Search + vector store; otherwise the CLI output is the evidence.

## D3 - Delta state stored on vector-store file attributes (Proposed)
- Decision: attributes `article_id`, `content_hash`, `updated_at` on each attached file; each run lists the store and diffs it against fresh scrape.
- Why: scheduled containers have no durable disk; no external DB to operate.
- Consequence: update = upload new file, attach, delete old file (attributes endpoint cannot change content or chunking).

## D4 - Chunking: static, 800 tokens, 400 overlap (Proposed)
- Why: matches the documented default; support articles are short step lists, so overlap keeps a procedure and its heading in the same chunk. Valid range is 100-4096 tokens, overlap <= half of chunk size.
- Consequence: README explains it.

## D5 - Chunk count logging (Proposed, needs verification)
- Context: the assignment asks to log chunks embedded. Not confirmed that the API returns a chunk count.
- Decision: log file counts from the API and compute the chunk count locally with `tiktoken` using the same static parameters, labelled as an estimate unless the API exposes the real number.
