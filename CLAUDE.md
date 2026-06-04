# CLAUDE.md

Codex and other coding agents working in this repository should follow these repository-specific guidelines. Apply them together with higher-priority system, developer, tool, and user instructions.

**Tradeoff.** This project mixes UI, agent orchestration, local persistence, and retrieval tooling. Favor correctness, reversibility, and targeted verification over speed.

## 1. Project Shape

This repository is a Python student assistant application built around these main areas:

- `app.py`: Streamlit entrypoint and UI wiring.
- `agent/`: LangGraph graph construction, prompts, and agent state.
- `database/`: SQLite schema setup and CRUD helpers for assignments, schedules, sessions, and memory summaries.
- `mcp_servers/`: tool-facing task, calendar, RAG, and student-info server modules.
- `rag/`: notice loading, chunking, embedding, retrieval, and external crawling helpers.
- `config/`: environment-driven settings and MCP config.
- `tests/`: pytest coverage by subsystem.
- `md_file/`: project notes, plans, and verification documents.
- `testsprite_tests/`: generated test-planning artifacts, not primary application code.

When starting work, identify which of these layers you are changing. Do not treat the app as a single flat script.

Generated, cache, virtualenv, and temporary artifacts such as `__pycache__/`, `.pytest_cache/`, `venv/`, `testsprite_tests/tmp/`, and ad hoc scratch files should not be treated as primary source unless the user explicitly asks about them.

## 2. Think Before Coding

**Do not guess requirements or failure causes.**

Before implementing:
- State important assumptions explicitly.
- Surface multiple plausible interpretations instead of silently choosing one.
- Prefer the smallest change that solves the requested problem.
- If a request would affect persistence, crawling behavior, or LLM/provider selection, verify the current implementation first.

## 3. Make Surgical Changes

**Change only what the task requires.**

- Do not refactor unrelated modules while touching a feature.
- Match the local style of the file you are editing.
- Remove imports or code made unused by your own change.
- If you find unrelated issues, report them separately instead of folding them into the same patch.

Every changed line should trace back to the request, a bug fix, or necessary verification support.

## 4. Data Safety Rules

**This repository has local state. Treat it carefully.**

The following paths contain persistent or semi-persistent runtime state:

- `campus_tasks.db`
- `chroma_db_storage/`
- `.env`

These default paths may be overridden by environment variables such as `SQLITE_DB_PATH` and `CHROMA_DB_DIR`; check the active configuration before assuming where runtime state lives.

Rules:
- Do not delete, reset, truncate, or clear persistent data unless the user explicitly asks for it.
- Do not run notice-clearing or DB-reset behavior as part of routine verification.
- Prefer test-isolated temporary paths when validating persistence behavior.
- Distinguish between sample data under `data/` and user/runtime data in SQLite or ChromaDB.
- Do not print, copy into docs, or commit secrets from `.env`; when checking configuration, report presence or absence rather than raw values.

## 5. External Dependency Rules

**Separate code bugs from environment or network problems.**

This project can depend on:

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`
- optional public-data keys such as `YOUTH_CENTER_API_KEY` and `WORKNET_API_KEY`
- external crawling targets and network availability

When something fails:
- Check whether the failure is local code, missing configuration, remote availability, or rate limiting.
- Do not assume a crawler or live-search failure means the retrieval logic is broken.
- Keep provider-selection changes separate from unrelated feature work when possible.

## 6. Simplicity First

**Write the minimum code that solves the requested problem.**

- Do not add abstraction for one-off behavior.
- Do not add speculative configuration.
- Do not expand a fix into a broad architecture cleanup unless asked.
- If the solution feels large relative to the bug, simplify it.

This project already has multiple layers. Avoid introducing more indirection unless it clearly pays for itself immediately.

## 7. Korean Output and Text Handling

**Respond naturally in Korean when the user writes in Korean, and handle text files carefully.**

- End Korean prose sentences with `.`, `?`, or `!`.
- Do not end Korean prose sentences with a trailing `:`.
- Prefer direct Korean phrasing over translated English structure.
- Preserve UTF-8 text where possible.
- If you encounter mojibake or broken Korean strings, do not spread them to new files casually. Either leave them untouched when out of scope or fix them intentionally as a dedicated change.

## 8. New File Headers

**For new source files, add a one-line Korean role comment when it fits the file type and local style.**

Rules:
- Put the comment directly under required directives such as a shebang.
- Skip config files, generated files, and files in areas that clearly do not use header comments.
- Skip tiny one-off scripts or test files when a header would be noisier than the existing local style.
- Keep the comment descriptive and short.

## 9. Verification Workflow

**If you changed code, run targeted verification before calling the task complete.**

Default commands for this repository:

- App run check: `streamlit run app.py`
- Full tests: `python -m pytest tests -q`

Notes:
- `streamlit run app.py` is a manual UI verification step that starts a long-running local server.
- Use the Streamlit run check mainly for UI or app-wiring changes, and stop the server after the check is complete.
- `tests/test_agent.py` is currently an empty placeholder, so it is not meaningful integration coverage by itself.
- If `pytest` or another verification tool is unavailable, distinguish missing tooling from application failures in the final report.

Prefer targeted tests when the change scope is narrow:

- task/persistence logic: `python -m pytest tests/test_task.py -q`
- calendar logic: `python -m pytest tests/test_calendar.py -q`
- memory/session persistence: `python -m pytest tests/test_memory.py -q`
- RAG pipeline or retrieval: `python -m pytest tests/test_rag.py -q`
- student info search: `python -m pytest tests/test_student_info.py -q`
- agent graph or integration flow: `python -m pytest tests/test_agent.py -q` only after adding real assertions there, or use broader subsystem checks while it remains empty

If verification cannot be run, say exactly why.

## 10. Error-Reading Discipline

**Read the actual error output before fixing anything.**

- Check the stack trace and failing assertion.
- Confirm whether the failure came from Streamlit UI wiring, LangGraph flow, SQLite access, ChromaDB state, or an external source.
- Check whether the failing artifact is real application code or generated/support material under `testsprite_tests/` or `md_file/`.
- Prefer a narrow reproduction or targeted test over guesswork.

## 11. Planning and Notes

**For non-trivial work, keep a short plan and record non-obvious decisions.**

- Start with a brief plan before substantial edits.
- Track what you verified and what remains uncertain.
- Create persistent checklist or context files only when the user asks for them or when the task is large enough to justify them.
- Prefer updating `AGENTS.md` as the main repository-level agent guide rather than spreading overlapping rules across multiple agent-instruction files without a clear reason.

## 12. Commit Discipline

**Keep changes logically grouped, but do not commit unless the user asks or the active workflow explicitly requires it.**

- Separate unrelated fixes.
- Preserve reviewability and rollback safety.
- Do not auto-commit completed work.

## 13. Instruction Priority

**This file is repository guidance, not the top of the instruction stack.**

- Follow system, developer, tool, and user instructions first.
- If this file conflicts with higher-priority instructions, follow the higher-priority instructions and adapt pragmatically.

---

These guidelines are working if diffs stay small, persistence is handled safely, verification matches the subsystem changed, and environment issues are not mistaken for code defects.
