# Submission notes

Reviewed on 2026-11-07 against the original Part 1 brief. This document separates working behavior from substitutions and gaps. The [checklist](CHECKLIST.md) maps each requirement to evidence.

## Deviations from the brief

| Requirement | Submitted implementation | Qualification |
|---|---|---|
| Create and test the assistant in AI Studio or Playground | Gemini File Search through the Python API, with the verbatim system instruction, a CLI and a local chat UI | The [recorded AI Studio experiment](img/ai-studio-tools.png) did not establish the required File Search setup. The local UI demonstrates retrieval but is not the requested platform UI. Acceptance of this substitution has not been confirmed. |
| Screenshot of the sanity check in that platform | [Real local browser capture](img/chat-ui.png) and a [transcript](sanity-check.md) of the exact YouTube question | `img/sanity-check.png` is rendered from CLI output. Neither image is an AI Studio or Playground capture. |
| Number of chunks embedded | `chunks_estimated=942` for the first 398-document upload | Calculated locally from the configured 400-token window and 50-token overlap. It is not a provider-reported count, so exact compliance with this metric is unverified. |

## Implementation choices and scope

- **Provider:** Gemini File Search handles indexing and retrieval. The original sanity-check answers used `gemini-3.6-flash` after `gemini-3.8-flash` returned 503/504 errors. The completed browser demo used `gemini-3.1-flash-lite` because the original model's daily quota was exhausted. The brief does not require a particular Gemini model.
- **Daily hosting:** Cloud Run Jobs and Cloud Scheduler on GCP, which is explicitly allowed by the brief. Deployment requires a billing-enabled project. Free-tier allowances are not a guarantee of zero cost.
- **State:** article IDs and content hashes live in remote document metadata. The scheduled container needs no persistent volume or separate database.
- **Replacement safety:** upload and index the replacement before deleting the old document. Failed uploads leave the old copy available.
- **Extra deletion behavior:** documents missing from the source are removed, with a per-run budget of the greater of five articles or 20% of remote article IDs. This limits a large accidental deletion, but it does not prove that a smaller source omission is intentional.
- **Content omitted:** article images and alt text. Headings, relative links and code blocks remain. YouTube and Vimeo embeds become plain video links.
- **Local demo only:** the responsive chat UI has no authentication and is not publicly deployed. It streams real Gemini text through NDJSON, shows a loading skeleton before the first text, and adds source links at completion. The UI identifies itself as the Part 1 local demo, not the official OptiSigns service. A hosted chat product was not built.

## Recorded runtime evidence

| Scenario | Observed result | Evidence |
|---|---|---|
| First full API upload | 398 articles, 942 estimated chunks, zero failures, 14m34s with four upload workers | [Full sync](logs/2026-11-06-first-full-sync-local.log) |
| Container with only `API_KEY` | 398 skipped, no upload needed | [Docker run](logs/2026-11-06-docker-run-local.log) |
| Controlled live delta | Missing document re-added, modified document replaced, one final copy, original content restored | [Delta test](logs/2026-11-06-live-delta-test.log) |
| Daily clock trigger | Scheduled for 2026-11-07 02:23 UTC, Scheduler received HTTP 200 | [Scheduler events](logs/2026-11-07-scheduler-clock.json) |
| Scheduled job completion | `added=0 updated=2 skipped=394 removed=2 failed=0`, exit 0 | [Cloud Run kb-sync-x4b7h](logs/2026-11-07T065056Z-kb-sync-x4b7h.log) |
| Answers | Two in-scope answers with article citations and one out-of-scope refusal | [Transcript](sanity-check.md) |
| Local HTTP streaming | Nine provider text deltas followed by a final answer with the YouTube article citation; first event after 9.782s, completion after 10.673s | [HTTP stream capture](logs/2026-11-07-local-chat-stream.json) |
| Responsive chat verification | No horizontal overflow or composer overlap at 320, 390, 768, 1440, 1920 and 2560px widths, plus 667×375 landscape with the context panel open | Chromium viewport emulation; not physical-phone or Safari evidence |
| Streaming and UI regression checks | 95 offline tests passed; loading, partial-answer errors, truncated streams, safe rendering, reduced motion, keyboard input and resize scroll recovery exercised | Existing test suite and controlled browser-provider fixtures; fixtures are not live model answers |
| User-Chrome conversation | Seven consecutive questions received real, cited Gemini 3.6 Flash answers; native per-character keyboard input was exercised | [Conversation transcript](logs/2026-11-07-chrome-seven-questions.json). The recording failed during finalization; this is **not** a completed video. |
| Completed browser demo | Seven consecutive native-typed questions and seven real cited answers in the user's Chrome using Gemini 3.1 Flash-Lite | [Full MP4](media/part1-demo.mp4), [looping GIF](media/part1-demo.gif), [recorded transcript](logs/2026-11-07-recorded-demo.json) |

The source changed between runs: the first run fetched 398 articles, while the scheduled run fetched 396. These are dated observations, not a fixed corpus-size promise. The scheduled run now provides live evidence for removal, which was previously covered only by tests.

**Video status:** complete. The MP4 contains all seven questions, real-time typing, API waits and real responses, with technical recording pauses omitted between capture segments. The looping GIF additionally removes API waiting intervals and plays the remaining real footage at 1.5×. Gemini 3.1 Flash-Lite was verified with File Search and used only for the recording process after the 3.6 quota and other model availability failures. The default model, system prompt and knowledge store were not changed. Earlier failed-capture evidence remains historical; no archived answers were replayed as live responses.

## Remaining limitations and pre-submission checks

- The repository does not record the required warm-up conversation with the original OptiBot. Do not mark this complete based only on trial portal access.
- The system prompt is passed verbatim, but answer formatting remains model behavior. The app appends missing retrieved article URLs. It does not enforce a global maximum of five bullets or three URL lines across arbitrary model output. In the 7 Nov live smoke, the correct URL appeared on the line after `Article URL:`, not on that same line.
- The three recorded answers are examples, not proof that the model always refuses unsupported questions or never hallucinates.
- Sync duration and success depend on source availability, API quotas and rate limits. The first-run duration is an observation, not a performance guarantee.
- The clock-triggered execution used the deployed job image. Later local documentation and demo changes are not evidence that the cloud image was redeployed.
- Confirm that the evaluator can access the private GitHub repository before sending it. GCP access is not needed to read the committed logs.
- Never send API keys with the submission. A clean repository scan does not establish that a key shared outside Git has been rotated.

## Process notes

- Commit `9ab0f9f` also removed a superseded upload CLI because two Git commands were issued in parallel. This is disclosed rather than described as a perfectly isolated history.
- Credentials are read from local environment configuration and Secret Manager. `.env` and generated source articles are excluded from version control.
- The brief's time budget is approximately eight focused hours. The planning estimates are not a measured time log, so no claim of actual completion within that budget is made.
