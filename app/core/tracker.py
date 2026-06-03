"""Tracking wrapper boundary for API-safe imports."""

from __future__ import annotations


class TrackerFactory:
    """Create trackers lazily so API import has no tracker/model side effects."""

    @staticmethod
    def create_byte_tracker(*args, **kwargs):
        # Coexistence: tracker dependencies are imported only when tracking mode
        # starts, not when FastAPI imports app.api.main.
        from tracker.byte_tracker import BYTETracker

        return BYTETracker(*args, **kwargs)
