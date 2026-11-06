# Repository conventions

## Commits
- Conventional Commits: `type(scope): imperative summary` (<= 72 chars), body explains *why*.
- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
- One logical change per commit. Commit and push after each completed sub-task.
- Code commits include their tests. Never commit `.env`, keys, or `data/`.

## Code
- Python 3.12, type hints, small single-purpose modules under `src/`.
- Config only via environment variables (see `.env.sample`).
- Logs are structured one-liners; counts are logged as `added=N updated=N skipped=N`.
- `main.py` runs once and exits 0 on success, non-zero on any failure.

## Process
- Work is tracked in `docs/PLAN.md` (sprints) and `docs/CHECKLIST.md` (requirements).
- Decisions are recorded in `docs/DECISIONS.md` before they are coded.
- A checklist item is ticked only with verified evidence.
- The system prompt in `prompts/system_prompt.txt` is verbatim from the assignment; do not edit it.
