#!/usr/bin/env python
"""Celery worker entry point."""
from app import create_app

app = create_app()
from app.tasks import celery
