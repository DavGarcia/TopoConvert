"""In-memory + temporary-file session store with TTL cleanup."""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from survey_core.models import SurveyState


@dataclass
class SessionRecord:
    """Single user session holding pipeline state and temporary workspace path."""

    session_id: str
    state: SurveyState
    active_step: int
    created_at: float
    updated_at: float
    temp_dir: Path


class SessionStore:
    """Thread-safe in-memory + temp-directory session store with automatic TTL expiration."""

    def __init__(self, ttl_minutes: float | None = None) -> None:
        env_ttl = float(os.environ.get("SESSION_TTL_MIN", "120"))
        self.ttl_seconds: float = (
            ttl_minutes if ttl_minutes is not None else env_ttl
        ) * 60.0
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionRecord] = {}
        self._base_temp = Path(tempfile.gettempdir()) / "topoconvert_sessions"
        self._base_temp.mkdir(parents=True, exist_ok=True)

    def cleanup_expired(self) -> int:
        """Delete sessions older than `ttl_seconds` and remove their temp directories."""
        now = time.time()
        removed = 0
        with self._lock:
            expired_ids = [
                sid
                for sid, rec in self._sessions.items()
                if (now - rec.updated_at) > self.ttl_seconds
            ]
            for sid in expired_ids:
                rec = self._sessions.pop(sid, None)
                if rec and rec.temp_dir.exists():
                    shutil.rmtree(rec.temp_dir, ignore_errors=True)
                removed += 1
        return removed

    def create(
        self, state: SurveyState, raw_bytes: bytes | None = None
    ) -> SessionRecord:
        """Create a new session record and persist uploaded file in temp storage."""
        self.cleanup_expired()
        sid = uuid.uuid4().hex[:16]
        now = time.time()
        s_dir = self._base_temp / sid
        s_dir.mkdir(parents=True, exist_ok=True)
        if raw_bytes is not None:
            (s_dir / "input.txt").write_bytes(raw_bytes)

        rec = SessionRecord(
            session_id=sid,
            state=state,
            active_step=max(state.completed_steps) if state.completed_steps else 1,
            created_at=now,
            updated_at=now,
            temp_dir=s_dir,
        )
        with self._lock:
            self._sessions[sid] = rec
        return rec

    def get(self, session_id: str) -> SessionRecord | None:
        """Retrieve a session record if it exists and has not expired."""
        self.cleanup_expired()
        with self._lock:
            rec = self._sessions.get(session_id)
            if rec is not None:
                rec.updated_at = time.time()
            return rec

    def update(
        self, session_id: str, state: SurveyState, active_step: int
    ) -> SessionRecord:
        """Update pipeline state and active step for an existing session."""
        with self._lock:
            rec = self._sessions.get(session_id)
            if rec is None:
                raise KeyError(session_id)
            rec.state = state
            rec.active_step = active_step
            rec.updated_at = time.time()
            return rec

    def count(self) -> int:
        """Return number of active sessions."""
        self.cleanup_expired()
        with self._lock:
            return len(self._sessions)
