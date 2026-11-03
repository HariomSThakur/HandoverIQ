# HandoverIQ - Round 2 Project Update

**Team name:** None  
**Participant:** Hariom Thakur (solo participant)  
**Role:** Product direction, requirements, review, and presentation. OpenAI Codex provided substantial implementation and documentation assistance; see `AI_ASSISTANCE.md`.

## Project links

- **Working public project link:** Not deployed yet. The local app runs at `http://127.0.0.1:5000` after following the README setup steps; that address is only reachable on the machine running it.
- **Source-code repository link:** Not created yet. The source is included in the project folder and the accompanying ZIP. Render deployment files are prepared for use after a repository is available.
- **Updated project PDF:** `HandoverIQ_Round2_Submission.pdf` (provided with the project package).

The public links are marked as pending rather than guessed or fabricated.

## 1. Problem statement understanding

When a person leaves a project, useful decisions, ownership, open actions, risks, and rationale can remain scattered across notes and chat exports. A new contributor has to reconstruct the current state, and unsupported assumptions can be mistaken for facts. HandoverIQ focuses on one tractable part of that problem: turning authorized project notes into a reviewable handover where each shared claim keeps its source passage visible.

## 2. Users affected

The primary users are the person preparing a handover and the incoming contributor who needs to continue the work. A reviewer checks candidate claims before sharing. The demo uses a fictional student makers-club project; it contains no interview or survey evidence and no real member data.

## 3. Proposed solution

HandoverIQ accepts Markdown or plain-text notes, extracts candidate project claims with a quote and source reference, and keeps them pending until a person reviews them. The incoming view includes only approved claims from sources labeled public or team. A quote match checks that the text appears in its source; it does not prove that a claim is true, current, or logically supported.

## 4. Product workflow

1. Load the synthetic demo or upload an authorized `.md` or `.txt` file and choose a demo access label.
2. Extract candidate decisions, owners, actions, risks, dependencies, dates, questions, and context. Restricted demo sources are skipped.
3. Review each claim alongside its quoted source passage. Edit, approve, or reject it. Approval is blocked when the quote is missing or no longer present in the cited chunk.
4. Open the incoming-developer view to read approved, evidence-linked claims and a clearly labeled suggested first-two-weeks plan.

## 5. Completed features

- Flask web app with SQLite and SQLAlchemy storage.
- Markdown/plain-text upload validation, stable source and chunk IDs, and access labels.
- Ten synthetic demo notes with conflicting dates and owners, an unresolved question, missing rationale, and one restricted source.
- Structured extraction through the optional OpenAI Responses API, with a visible rules-based local fallback.
- Claim review and quote-presence validation before approval.
- Incoming view filters approved public/team claims before building the view; restricted source details are not exposed there.
- CSRF protection on POST forms and basic security response headers.
- Main server-side workflow verified with Flask's test client: 10 sources loaded, 17 local candidate claims extracted, a quote-matched claim approved and shown in the handover, and restricted-source access checked.

## 6. Technology and implementation

- **Python 3.13** and **Flask 3** for request handling and server-rendered pages.
- **Jinja templates**, HTML, and CSS for the interface.
- **SQLAlchemy 2** with **SQLite** for sources, chunks, claims, review status, and review events.
- **OpenAI Responses API structured output** is optional. The default works locally without a key using deterministic sentence rules.
- **Render Blueprint + Gunicorn** deployment configuration is included, but the service has not been created or deployed.

The main technical challenge is preserving a trustworthy path from source to shared claim. The app stores source chunks, requires the cited quote to remain present before approval, and filters restricted sources in the database query for the incoming view. These are demo controls; the app has no user authentication or production authorization.

## 7. Solo participant responsibilities

Hariom Thakur is the sole participant and is responsible for the product direction, requirements, review of the output, demo, and presentation. Codex contributed substantially to design, implementation, synthetic demo content, and documentation. This assistance is disclosed in `AI_ASSISTANCE.md`; generated work is not represented as unaided coding.

## 8. Development plan across the three rounds

- **Round 1:** Define the knowledge-loss problem, identify the handover workflow, and propose an evidence-linked assistant with human review and access filtering.
- **Round 2:** Deliver a focused vertical slice: source intake, claim extraction, quote checking, human review, and one incoming view. The route journey is verified with the local rules fallback. The public repository and deployment remain pending.
- **Round 3:** Add three substantive improvements described below, then validate their behavior against a small, documented dataset before making impact claims.

## 9. Expected impact

The expected benefit is less time spent searching scattered notes and a clearer distinction between source-backed information and suggestions. This is a design hypothesis, not a measured result. No interviews, usability study, or impact evaluation has been completed.

## 10. Three major Round 3 improvements

1. **Knowledge-at-risk map:** Rank decisions, ownership, rationale, and open actions by missing context, uncertainty, and documentation gaps so teams can capture the most fragile knowledge first.
2. **Versioned handovers and acknowledgements:** Preserve handover versions and let incoming contributors acknowledge, question, or flag stale items, creating a concrete follow-up loop.
3. **Evaluation and audit harness:** Measure quote validity, human-rated claim support, seeded conflict detection, fact recall, and restricted-source leakage on a labeled scenario; keep review actions auditable.

## 11. Changes from the original plan and future scope

The Round 2 build was narrowed from a broader proposal that included automated conflict detection, deeper support verification, multiple role views, and a knowledge-at-risk map. The MVP uses one reviewer flow, one incoming view, a quote-presence check, and simulated access labels. It does not automatically resolve conflicting dates or decide whether a quote logically supports a claim. Later work may add real authentication and authorization, connectors with consent controls, multi-source provenance, freshness checks, and validated evaluation results.

## Current limitations

- No public demo URL or public repository exists yet.
- Upload and role labels are demonstration workflow controls; there is no sign-in or production authorization.
- The local fallback is heuristic and can miss or misclassify claims.
- The optional live model call has not been exercised.
- A Flask test-client journey passed, but a visual browser walkthrough and usability study have not been completed.
- Free Render services can sleep while idle and use an ephemeral filesystem; the local SQLite database and uploads may be lost after restart. The demo can be reloaded from its synthetic files.

Render details are documented at [Free Render instances](https://render.com/docs/free) and the [Blueprint YAML reference](https://render.com/docs/blueprint-spec).
