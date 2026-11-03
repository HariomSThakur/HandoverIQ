# HandoverIQ Round 2 MVP Implementation Plan

> **For agentic workers:** implement the tasks in order in this standalone project. Preserve the project’s visible AI disclosure and the limitations below.

**Goal:** Create a local, working student-project handover application with evidence-linked extraction, human review, and one role-filtered handover view.

**Architecture:** Flask routes call small ingestion, extraction, permission, and handover services backed by SQLAlchemy/SQLite. Jinja templates render a responsive, server-side workflow. A configured Responses API model is optional; deterministic extraction is the default fallback.

**Tech Stack:** Python 3.11+, Flask, SQLAlchemy 2.x, SQLite, Jinja, native browser forms/CSS; Python standard library HTTP client for optional model requests.

**Spec:** `docs/superpowers/specs/2026-11-01-handoveriq-mvp-design.md`

## Global Constraints

- Only `.md` and `.txt` uploads, UTF-8, at most 1 MiB each.
- Demo content is synthetic; never include real project secrets or private material.
- Permission labels are simulated and must not be described as production security.
- Each MVP claim belongs to one source/chunk; filter restricted sources before extraction and before displaying viewer-specific data.
- No API key in source files or database; optional Responses API errors fall back visibly.
- Every claim starts pending; missing/mismatched evidence cannot be approved.
- AI assistance and all unbuilt capabilities must be disclosed accurately.

## Review Focus

- Unicode or Windows-style line endings: quote matching should normalize whitespace but preserve punctuation.
- Duplicate filenames or repeated uploads: stable IDs must avoid overwrites and duplicate demo inserts.
- Corrupt UTF-8, wrong extensions, oversized uploads, and empty files: reject with a useful message and no partial source row.
- Model timeout, refusal, invalid JSON, or citation outside the supplied chunk: reject the output and use deterministic extraction.
- Restricted source title, filename, quote, or count: none may appear in the incoming-developer response.

## File Map

- `handoveriq/app.py`: app factory and user-facing routes.
- `handoveriq/db.py`, `handoveriq/models.py`: database setup and source/chunk/claim/review-event models.
- `handoveriq/services/ingest.py`: validation, hashing, chunks, quote checks.
- `handoveriq/services/extraction.py`: model schema/API client and local fallback.
- `handoveriq/services/permissions.py`: role and access-level rules.
- `handoveriq/services/handover.py`: grouped output and suggested actions.
- `handoveriq/templates/*.html`, `handoveriq/static/*`: pages and UI assets.
- `demo_sources/*`: synthetic scenario and manifest.
- `README.md`, `AI_ASSISTANCE.md`, `requirements.txt`, `.gitignore`: honest setup and submission documentation.

## Tasks

### Task 1: Project shell and persistence

Create package, configuration, Flask factory, SQLAlchemy models, base template, and polished dashboard. Model `Source` with stable ID, original filename, access level, text, and timestamp. Model `Claim` with text, kind, owner, due date, source/chunk reference, quoted evidence, evidence status, review state, and reviewer note. Create local tables on startup and keep the instance database out of version control.

### Task 2: Authorized source intake and synthetic demo

Add upload validation and source storage. Preserve original text and chunk offsets; assign deterministic SHA-256 IDs. Add ten small synthetic files with a manifest, including an owner conflict, competing dates, unresolved question, missing rationale, dependency, and one restricted file. Add an idempotent “Load demo” action and list uploaded/seeded sources with access labels in reviewer view.

### Task 3: Evidence-linked extraction

Split sources into stable paragraph-sized chunks. For non-restricted sources, call the Responses API with a strict JSON schema when configured. Validate every field and require the quoted evidence to be present in the exact source chunk. When no key is configured or the request/output fails, use a rules-based extractor and show “Local fallback” status. Never invent evidence to repair a failed model response.

### Task 4: Review, permissions, and handover

Build a claim review page showing claim, source title, quote, quote-match state, extraction mode, and review status. Support edit, reject, and approve; enforce quote presence on approval. Build an incoming-developer page from approved `public`/`team` claims only, grouped by type. Hide restricted metadata completely. Separate suggested first-two-weeks actions from source facts and link source evidence for each surfaced claim.

### Task 5: Run instructions and handoff

Write installation/startup instructions, optional API setup, limitations, demo steps, data-handling statement, and AI assistance disclosure. Keep the app runnable without a key. Review the source files, compile Python and Jinja templates, register Flask routes, then package the source folder as a downloadable zip without the local database or `.git` internals.

## Execution notes

- Keep the user-facing path short: load demo → extract → review → handover.
- Do not implement connectors, support scoring, conflict automation, multi-role access, version history, acknowledgements, or risk ranking in this build.
- HTMX is deferred; use native forms so the local app has no external frontend dependency.
- No automated test suite is included in this implementation pass; follow the user-facing request for a runnable project and do not represent manual inspection as automated testing.

## Completion Record

- [x] Task 1: Python modules compile; Flask route registration lists all nine app routes.
- [x] Task 2: Ten synthetic Markdown sources and an idempotent manifest loader are present.
- [x] Task 3: Optional structured Responses API extraction and local fallback are implemented; live model use was not exercised.
- [x] Task 4: Reviewer actions and database-filtered incoming view are implemented; full browser workflow was not exercised.
- [x] Task 5: Setup guide, AI disclosure, status note, and source package are present.
- [x] All six Jinja templates compile.
- [x] Native forms were used in place of HTMX because the scope needs no asynchronous UI and offline behavior is useful. Trade-off: less reactive page updates.
- [x] No automated tests were added or run; the user-facing walkthrough remains for the participant to perform.
