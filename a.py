"""Wasmer's Python preset looks for an ``a:app`` module.

Keep the canonical Flask application in app.py while exposing the expected
entry point for the web-only deployment.
"""

from app import app

__all__ = ["app"]
