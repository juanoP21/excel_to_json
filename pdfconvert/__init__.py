
"""Utilities for processing PDFs and sending them to the webhook."""

from .tasks import process_and_send

__all__ = ["process_and_send"]
