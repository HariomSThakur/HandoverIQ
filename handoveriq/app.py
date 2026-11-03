from __future__ import annotations

import os
import secrets
import uuid
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func, select
from werkzeug.exceptions import RequestEntityTooLarge

from .db import init_database, session_scope
from .models import Claim, ReviewEvent, Source
from .services.extraction import CLAIM_TYPES, extract_all, review_claim
from .services.handover import KIND_LABELS, build_handover, load_reviewer_claims, source_claims
from .services.ingest import ACCESS_LEVELS, IngestError, load_demo_sources, store_source
from .services.permissions import source_for_role


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    default_db = (Path(app.instance_path) / "handoveriq.sqlite3").as_posix()
    app.config.from_mapping(
        SECRET_KEY=os.getenv("HANDOVERIQ_SECRET_KEY") or secrets.token_hex(32),
        DATABASE_URL=os.getenv("HANDOVERIQ_DATABASE_URL") or f"sqlite:///{default_db}",
        MAX_CONTENT_LENGTH=1024 * 1024 + 64 * 1024,
        DEMO_ROOT=Path(app.root_path).parent / "demo_sources",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )
    if test_config:
        app.config.update(test_config)
    init_database(app)

    @app.before_request
    def protect_post_forms() -> None:
        if request.method != "POST":
            return
        supplied = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        import hmac
        if not supplied or not expected or not hmac.compare_digest(supplied, expected):
            abort(400, description="The form expired. Reload the page and try again.")

    @app.context_processor
    def template_helpers() -> dict:
        def csrf_token() -> str:
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]
        return {"csrf_token": csrf_token, "kind_labels": KIND_LABELS}

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error):
        return render_template("error.html", code=413, message="That upload is too large. Each source must be 1 MiB or smaller."), 413

    @app.get("/")
    def home():
        with session_scope(app) as db:
            source_count = db.scalar(select(func.count()).select_from(Source)) or 0
            claim_count = db.scalar(select(func.count()).select_from(Claim)) or 0
            pending_count = db.scalar(select(func.count()).select_from(Claim).where(Claim.review_status == "pending")) or 0
            approved_count = db.scalar(select(func.count()).select_from(Claim).where(Claim.review_status == "approved")) or 0
            sources = list(db.scalars(select(Source).order_by(Source.created_at.desc())))
        return render_template(
            "home.html",
            source_count=source_count,
            claim_count=claim_count,
            pending_count=pending_count,
            approved_count=approved_count,
            sources=sources,
            api_enabled=bool(os.getenv("OPENAI_API_KEY")),
            max_upload_mb=1,
        )

    @app.post("/sources/upload")
    def upload_source():
        upload = request.files.get("file")
        access_level = request.form.get("access_level", "team")
        if upload is None:
            flash("Choose a Markdown or text file first.", "error")
            return redirect(url_for("home"))
        try:
            raw = upload.stream.read(1024 * 1024 + 1)
            with session_scope(app) as db:
                source, created = store_source(db, upload.filename or "", raw, access_level)
            flash(
                f"Added {source.filename} to the workspace." if created else f"That exact source is already in the workspace: {source.filename}.",
                "success",
            )
        except IngestError as exc:
            flash(str(exc), "error")
        return redirect(url_for("home"))

    @app.post("/demo/load")
    def demo_load():
        try:
            with session_scope(app) as db:
                inserted, existing = load_demo_sources(db, app.config["DEMO_ROOT"])
            flash(f"Demo ready: {inserted} new synthetic sources added; {existing} were already present.", "success")
        except (OSError, ValueError, KeyError) as exc:
            app.logger.exception("Could not load the synthetic demo")
            flash(f"The demo could not be loaded: {str(exc)[:180]}", "error")
        return redirect(url_for("home"))

    @app.post("/extract")
    def extract():
        with session_scope(app) as db:
            source_count = db.scalar(select(func.count()).select_from(Source)) or 0
            if source_count == 0:
                flash("Add an authorized source or load the synthetic demo before extracting.", "error")
                return redirect(url_for("home"))
            summary = extract_all(db)
        message = f"Added {summary.created} new candidate claims."
        if summary.local:
            message += f" Local fallback used for {summary.local} source(s)."
        if summary.model:
            message += f" Structured model extraction used for {summary.model} source(s)."
        if summary.model_errors:
            message += f" {summary.model_errors} model request(s) fell back locally."
        if summary.skipped_restricted:
            message += f" {summary.skipped_restricted} restricted source(s) were not sent for extraction."
        flash(message, "success" if summary.created else "info")
        if summary.model_errors:
            app.logger.warning("Model extraction fell back for %d source(s)", summary.model_errors)
        return redirect(url_for("review"))

    @app.get("/review")
    def review():
        status = request.args.get("status", "pending")
        if status not in {"pending", "approved", "rejected", "all"}:
            status = "pending"
        with session_scope(app) as db:
            claims = load_reviewer_claims(db, status)
            counts = {
                name: db.scalar(select(func.count()).select_from(Claim).where(Claim.review_status == name)) or 0
                for name in ("pending", "approved", "rejected")
            }
        return render_template(
            "review.html", claims=claims, status=status, counts=counts,
            claim_types=sorted(CLAIM_TYPES),
        )

    @app.post("/review/<claim_id>")
    def save_review(claim_id: str):
        action = request.form.get("action", "save")
        with session_scope(app) as db:
            claim = db.get(Claim, claim_id)
            if claim is None:
                abort(404)
            previous_status = claim.review_status
            ok, message = review_claim(
                db,
                claim,
                action=action,
                claim_text=request.form.get("claim_text", ""),
                claim_type=request.form.get("claim_type", "context"),
                owner=request.form.get("owner", ""),
                due_date=request.form.get("due_date", ""),
                evidence_quote=request.form.get("evidence_quote", ""),
                reviewer_note=request.form.get("reviewer_note", ""),
            )
            if ok and (previous_status != claim.review_status or action != "save"):
                db.add(ReviewEvent(event_id=uuid.uuid4().hex, claim_id=claim.claim_id, action=action))
        flash(message, "success" if ok else "error")
        return redirect(url_for("review", status=request.args.get("status", "pending")))

    @app.get("/handover")
    def handover():
        with session_scope(app) as db:
            payload = build_handover(db)
        return render_template("handover.html", **payload)

    @app.get("/source/<source_id>")
    def source_detail(source_id: str):
        role = request.args.get("role", "reviewer")
        if role not in {"reviewer", "incoming"}:
            abort(404)
        with session_scope(app) as db:
            source = source_for_role(db, source_id, role)
            if source is None:
                abort(404)
            claims = source_claims(db, source_id)
            source_data = {
                "source_id": source.source_id,
                "filename": source.filename,
                "access_level": source.access_level,
                "content": source.content,
                "source_type": source.source_type,
            }
        return render_template("source.html", source=source_data, claims=claims, role=role)

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=getattr(error, "description", "The request was not valid.")), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="That page or source is not available."), 404

    return app
