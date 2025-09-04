"""Simple JSON-backed chat history service.

Stores the last N entries containing either a tech trends result or a
general chat response. Designed to be lightweight and require no external
dependencies. Data is persisted to a JSON file so it survives restarts.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class HistoryEntry:
    """A single history record.

    Attributes:
        id: Unique identifier of the entry
        type: Either "trends" or "chat"
        input: Original user input text
        title: Short title suitable for sidebar display
        timestamp: ISO-8601 timestamp when entry was created
        data: The payload returned to the client (trends or chat content)

    """

    id: str
    type: str
    input: str
    title: str
    timestamp: str
    data: dict[str, Any]


class HistoryService:
    """Manage chat history with a simple JSON file store."""

    def __init__(self, storage_path: Path, max_entries: int = 10) -> None:
        self.storage_path = storage_path
        self.max_entries = max_entries
        self._entries: list[HistoryEntry] = []
        self._ensure_dir()
        self._load()

    # Public API -----------------------------------------------------------
    def add_entry(
        self,
        entry_type: str,
        user_input: str,
        payload: dict[str, Any],
    ) -> HistoryEntry:
        """Add a new history entry and persist to disk.

        Args:
            entry_type: "trends" or "chat"
            user_input: The original user message/query
            payload: The response payload to be shown when reopened

        """
        entry_id = str(uuid.uuid4())
        title = self._make_title(entry_type, user_input, payload)
        timestamp = datetime.utcnow().isoformat()

        entry = HistoryEntry(
            id=entry_id,
            type=entry_type,
            input=user_input,
            title=title,
            timestamp=timestamp,
            data=payload,
        )

        # Insert at the front (newest first)
        self._entries.insert(0, entry)
        # Enforce max entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[: self.max_entries]

        self._save()
        return entry

    def get_recent(self, limit: int | None = None) -> list[HistoryEntry]:
        """Return recent entries (newest first)."""
        limit = limit or self.max_entries
        return self._entries[:limit]

    def get_by_id(self, entry_id: str) -> HistoryEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    # Internal helpers ----------------------------------------------------
    def _ensure_dir(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._entries = []
            return
        try:
            raw = json.loads(self.storage_path.read_text())
            self._entries = [HistoryEntry(**item) for item in raw.get("entries", [])]
        except Exception:
            # If corrupted, start fresh but do not crash the app
            self._entries = []

    def _save(self) -> None:
        serializable: dict[str, Any] = {
            "version": 1,
            "entries": [asdict(e) for e in self._entries],
        }
        tmp_path = self.storage_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(serializable, indent=2))
        tmp_path.replace(self.storage_path)

    def _make_title(
        self,
        entry_type: str,
        user_input: str,
        payload: dict[str, Any],
    ) -> str:
        base = user_input.strip().replace("\n", " ")
        if len(base) > 60:
            base = base[:57] + "..."
        if entry_type == "trends":
            return f"Trends: {base or 'Analysis'}"
        return f"Chat: {base or 'Conversation'}"


def build_default_history_service(
    project_root: Path | None = None,
) -> HistoryService:
    """Factory to create a default HistoryService under data/chat_history.json."""
    root = project_root or Path(__file__).resolve().parents[2]
    storage = root / "data" / "chat_history.json"
    return HistoryService(storage_path=storage, max_entries=10)
