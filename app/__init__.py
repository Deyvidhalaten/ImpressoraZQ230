# app/__init__.py
# Export do Flask app para compatibilidade com waitress-serve e cx_Freeze

from app.__main__ import app

__all__ = ["app"]
