# HandoverIQ Round 2 MVP Design

## Intent

Build a usable handover workflow for a departing student club developer and the incoming developer who must continue the project. HandoverIQ turns a small set of authorized Markdown or plain text sources into reviewable, source-linked claims, then presents only approved claims allowed for the incoming role.

## Goals

- Run locally with Python, Flask, SQLite, SQLAlchemy, and server-rendered Jinja pages.
- Accept `.md` and `.txt` project files with an access label and retain a stable source ID and source span.
- Extract candidate decisions, owners, open work, risks, dependencies, dates, and questions, attaching a quoted source passage to every claim.
- Use the OpenAI Responses API with a strict JSON schema when configured; provide a labeled deterministic extraction fallback without a key or when the model call fails.
- Check quote presence using whitespace normalization while retaining the original quote for display.
- Keep claims pending until a human edits, rejects, or approves them.
- Build a single incoming-developer view from approved, permitted claims and show a clearly labeled suggested first-two-weeks plan.
- Include a synthetic demo project with a restricted source and visible conflicts or knowledge gaps.
- Disclose AI assistance and describe limitations accurately.

## Non-goals for this build

- Production identity, authorization, or confidential-data protection.
- Live GitHub, chat, task-board, or meeting integrations.
- Multiple organizational roles, multi-source claim support, support-quality judgments, conflict automation, version history, acknowledgements, or the Round 3 knowledge-at-risk map and evaluation harness.
- Claiming that quote presence establishes that a claim is true or supported.

## User workflow

1. Open the local dashboard and choose the synthetic demo or upload authorized Markdown/plain text files.
2. Assign an access label at intake. The demo uses `team` and `restricted`; the product labels this as a simulation.
3. Extract candidate claims. If the API is unavailable, label the rules-based fallback. Each claim is tied to one source and one quoted chunk.
4. Review the evidence and quote-match state. Edit, reject, or approve claims; approvals are disabled for missing or mismatched quotes.
5. Open the incoming-developer handover. It includes approved claims at `team` access or lower, open actions, known risks/dependencies, unresolved review items only where safe to reveal, and a suggested continuation plan separated from source facts.

## Architecture

- `handoveriq/app.py`: Flask application factory and HTTP routes.
- `handoveriq/db.py` and `handoveriq/models.py`: SQLAlchemy engine/session and relational records.
- `handoveriq/services/ingest.py`: file validation, normalization, deterministic source/chunk IDs, quote matching.
- `handoveriq/services/extraction.py`: optional structured model call plus deterministic fallback.
- `handoveriq/services/permissions.py`: access ordering and role filtering.
- `handoveriq/services/handover.py`: grouped handover data and next-step suggestions.
- `handoveriq/templates/` and `handoveriq/static/`: accessible, responsive server-rendered UI.
- `demo_sources/`: synthetic project files and access manifest.
- `instance/handoveriq.sqlite3`: local database created at runtime; ignored by Git.

## Data and safety rules

- Allowed uploads: `.md` and `.txt`, UTF-8, maximum 1 MiB per file.
- Access ordering: `public < team < restricted`. Incoming developer can see `public` and `team`; reviewer view can see all labels. This is a local demo simulation, not production authorization.
- A claim is linked to exactly one source and one chunk in this MVP. This makes its access level unambiguous; any later multi-source claim must inherit the strictest source level.
- Filter claims before generating the incoming view. Do not include restricted source titles, filenames, text, IDs, or counts in that view.
- Store model keys only in environment variables. Do not send restricted sources to the optional API path; skip them during extraction and disclose this behavior.
- Render all user and model text with Jinja autoescaping. Validate model output before storing it. A failed model call must use the local fallback and show the chosen mode.
- Quote comparison normalizes line endings and repeated whitespace only; it does not remove punctuation. A match confirms presence only.
- Use synthetic demo content only. Do not imply simulated access labels secure real data.

## UI direction

A calm, review-oriented workspace: a compact navigation rail; a dashboard with the source, review, and handover steps; clear counts and status labels; claim cards with the quoted evidence adjacent to the claim; accessible review actions; and a handover page with source links and a visually separated suggested plan. Prioritize readable contrast and responsive layouts over decorative effects.

## Technology decisions

- Flask and SQLAlchemy keep the server and local data model small.
- Jinja and native forms keep the application usable without a frontend build tool or external JavaScript service. HTMX is deferred because the Round 2 core workflow does not need asynchronous UI behavior.
- OpenAI Structured Outputs via the Responses API is optional. The core demo must not require an API key or network access.
- SQLite is the local single-project store.

## Success criteria

- A new user can load the synthetic demo, extract claims, inspect source evidence, review a claim, and open the incoming view without setup beyond installing requirements.
- Quote checks are visible and missing evidence cannot be approved.
- The incoming view contains no content or metadata from restricted sources.
- Model/API absence or errors leave a working, clearly labeled fallback path.
- The README explains setup, use, limitations, data handling, and AI assistance.

## Approval and scope note

This design implements the previously discussed Round 2 vertical slice after the user confirmed that the official build window is open. Round 3 features remain roadmap items.
