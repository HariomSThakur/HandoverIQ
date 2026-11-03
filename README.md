# HandoverIQ

HandoverIQ turns authorized project notes into a source-linked handover that a reviewer can inspect before an incoming developer sees it. This is a Round 2 MVP for one fictional student-club project.

## What is implemented

- Upload Markdown and plain text files (UTF-8, up to 1 MiB each) and assign a demo access label.
- Load a ten-file synthetic scenario with two launch dates, competing owners, an unresolved question, missing rationale, an undocumented operational detail, and one restricted source.
- Extract candidate claims and retain a quote, source, and source chunk for each one.
- Use an optional OpenAI Responses API call with strict JSON Schema output; otherwise use a visible rules-based local fallback.
- Review claims by editing, approving, or rejecting them. Approval is blocked when the quote is missing or no longer appears in its source.
- Build an incoming-developer view from approved public/team claims. Restricted sources are excluded from extraction and their metadata is omitted from the incoming view.
- Show source quotes beside handover claims and a separate, clearly labeled suggested first-two-weeks plan.

## Start on Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000` in a browser. The application binds to localhost. SQLite data is created in `instance/handoveriq.sqlite3` on first run.

For a one-step Windows start after Python is installed, double-click `start_handoveriq.bat`. The first run creates a local virtual environment and installs the listed packages.

## Optional model extraction

The app works without an API key. Without one, the extraction page labels its results as **Local fallback**.

To enable structured model extraction for non-restricted sources, set environment variables in PowerShell before starting the server:

```powershell
$env:OPENAI_API_KEY = "your API key"
$env:OPENAI_MODEL = "gpt-4o-mini"
python run.py
```

Use a model enabled for your API account. Model request or output errors fall back to local rules; the UI reports that fallback. Restricted sources are not sent to the model. API use may incur charges and sends eligible source text to the configured provider. Do not upload confidential material.

The optional integration uses the OpenAI Responses API and its `text.format` JSON Schema mode. See the [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Optional Render deployment

`render.yaml`, `requirements-render.txt`, and `handoveriq/wsgi.py` prepare this app for a Render Python web service. To publish it, push the project to a GitHub repository, connect that repository to Render, and create a Blueprint from `render.yaml`. The service uses a generated Flask secret and HTTPS-only session cookies. No public service has been created for this project yet.

The free service uses an ephemeral filesystem. Its SQLite database and uploaded sources can be lost after a restart or idle spin-down, so judges should load the synthetic demo again if the workspace is empty. Render also spins down free web services after 15 minutes without traffic and the next request can take about a minute to start. See [Render's free instance limitations](https://render.com/docs/free) and [Blueprint YAML reference](https://render.com/docs/blueprint-spec).

## Suggested demo walkthrough

1. Choose **Load demo sources** on the overview page.
2. Choose **Extract**. With no API key, the page reports that local fallback was used.
3. Open **Review claims**. Read the quote beside each candidate; approve, edit, or reject a few.
4. Open **Incoming view**. Confirm the handover only includes approved public/team items and inspect their evidence.
5. Compare the conflicting launch dates and ownership notes manually. HandoverIQ surfaces the source statements but does not resolve conflicts automatically.

## Data and permission limitations

- The project is a local demo for synthetic data. Access labels are simulated workflow controls, not production authentication or authorization.
- The reviewer and incoming views are demonstration routes without user sign-in. Do not use this app to protect confidential data or deploy it as-is.
- Claims link to one source chunk in this MVP. If future claims combine sources, they must inherit the strictest source access level.
- A quote-presence match confirms only that the text appears in the source. It does not prove the claim is true, current, or logically supported.
- The local fallback uses simple text rules and can miss or misclassify information. Human review is required.
- The main route journey was exercised with Flask's test client: load the ten-source synthetic dataset, extract 17 local claims, approve an evidence-matched claim, and confirm the incoming handover excludes the restricted source. This does not replace a visual browser walkthrough or a usability study.
- The optional live OpenAI request has not been exercised. Without an API key, the fully local rules-based fallback is used.
- Version history, acknowledgements, multi-role controls, conflict/freshness automation, support assessment, live connectors, the knowledge-at-risk map, and an evaluation harness remain future work.

## Source layout

- `handoveriq/app.py` — Flask application and routes
- `handoveriq/models.py`, `handoveriq/db.py` — SQLAlchemy models and SQLite setup
- `handoveriq/services/` — intake, extraction, permissions, handover assembly
- `handoveriq/templates/`, `handoveriq/static/` — Jinja UI and local assets
- `demo_sources/` — synthetic scenario and manifest
- `docs/superpowers/specs/` — project design
- `docs/superpowers/plans/` — implementation plan
- `AI_ASSISTANCE.md` — AI and contribution disclosure

## Event disclosure

This project received substantial OpenAI Codex assistance. Review `AI_ASSISTANCE.md`, follow the event's disclosure requirements, and describe personal contributions accurately. The submitted build should be accompanied by truthful repository history and any required API/model/data/library details.

The local folder has a Git repository initialized but no commits or remote yet. The downloadable source ZIP excludes Git internals. Before sharing a repository, use your own real Git identity and keep the disclosure file and original history intact.
