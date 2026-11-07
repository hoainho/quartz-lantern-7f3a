# Submission notes

Reviewed on 2026-11-07 against the original Part 1 brief. This document separates working behavior from substitutions and gaps. The [checklist](CHECKLIST.md) maps each requirement to evidence.

## Deviations from the brief

| Requirement | Submitted implementation | Qualification |
|---|---|---|
| Create and test the assistant in AI Studio or Playground | Gemini File Search through the Python API, with the verbatim system instruction, a CLI and a local chat UI | The [recorded AI Studio experiment](img/ai-studio-tools.png) did not establish the required File Search setup. The local UI demonstrates retrieval but is not the requested platform UI. Acceptance of this substitution has not been confirmed. |
| Screenshot of the sanity check in that platform | [Real local browser capture](img/chat-ui.png) and a [transcript](sanity-check.md) of the exact YouTube question | `img/sanity-check.png` is rendered from CLI output. Neither image is an AI Studio or Playground capture. |
| Number of chunks embedded | `chunks_estimated=942` for the first 398-document upload | Calculated locally from the configured 400-token window and 50-token overlap. It is not a provider-reported count, so exact compliance with this metric is unverified. |

## Implementation choices and scope

- **Provider:** Gemini File Search handles indexing and retrieval. `gemini-3.6-flash` was used for the recorded answers after the attempted `gemini-3.8-flash` calls returned 503/504 errors. The brief does not require a particular Gemini model.
- **Daily hosting:** Cloud Run Jobs and Cloud Scheduler on GCP, which is explicitly allowed by the brief. Deployment requires a billing-enabled project. Free-tier allowances are not a guarantee of zero cost.
- **State:** article IDs and content hashes live in remote document metadata. The scheduled container needs no persistent volume or separate database.
- **Replacement safety:** upload and index the replacement before deleting the old document. Failed uploads leave the old copy available.
- **Extra deletion behavior:** documents missing from the source are removed, with a per-run budget of the greater of five articles or 20% of remote article IDs. This limits a large accidental deletion, but it does not prove that a smaller source omission is intentional.
- **Content omitted:** article images and alt text. Headings, relative links and code blocks remain. YouTube and Vimeo embeds become plain video links.
- **Local demo only:** the chat UI has no authentication and is not publicly deployed. A hosted chat product was not built.

## Recorded runtime evidence

| Scenario | Observed result | Evidence |
|---|---|---|
| First full API upload | 398 articles, 942 estimated chunks, zero failures, 14m34s with four upload workers | [Full sync](logs/2026-11-06-first-full-sync-local.log) |
| Container with only `API_KEY` | 398 skipped, no upload needed | [Docker run](logs/2026-11-06-docker-run-local.log) |
| Controlled live delta | Missing document re-added, modified document replaced, one final copy, original content restored | [Delta test](logs/2026-11-06-live-delta-test.log) |
| Daily clock trigger | Scheduled for 2026-11-07 02:23 UTC, Scheduler received HTTP 200 | [Scheduler events](logs/2026-11-07-scheduler-clock.json) |
| Scheduled job completion | `added=0 updated=2 skipped=394 removed=2 failed=0`, exit 0 | [Cloud Run kb-sync-x4b7h](logs/2026-11-07T065056Z-kb-sync-x4b7h.log) |
| Answers | Two in-scope answers with article citations and one out-of-scope refusal | [Transcript](sanity-check.md) |

The source changed between runs: the first run fetched 398 articles, while the scheduled run fetched 396. These are dated observations, not a fixed corpus-size promise. The scheduled run now provides live evidence for removal, which was previously covered only by tests.

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
