"""Production WSGI entry point for HTTPS hosting."""

from .app import create_app

app = create_app({"SESSION_COOKIE_SECURE": True})
