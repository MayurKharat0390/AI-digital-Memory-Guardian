"""
memory/apps.py
--------------
Load the embedding model once at Django startup (not per-request).
Stored as a module-level singleton and reused across all API calls.
"""
from django.apps import AppConfig


class MemoryConfig(AppConfig):
    name = 'memory'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Called once when Django starts.
        Pre-loads the sentence-transformer model into memory so the
        first API request isn't slow.
        """
        # Import here to avoid circular imports / premature loading
        from pipeline.embedder import get_model
        print("[Memory Guardian] Loading embedding model…")
        get_model()
        print("[Memory Guardian] Model ready.")
