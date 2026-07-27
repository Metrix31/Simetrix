"""Persistente Konversationshistorie."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, List

from .ui import MAX_HISTORY_ENTRIES, log


@dataclass
class HistoryEntry:
    """Ein einzelner Verlaufseintrag."""

    timestamp: str
    user: str
    assistant: str

    @classmethod
    def create(cls, user: str, assistant: str) -> "HistoryEntry":
        return cls(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            user=user,
            assistant=assistant,
        )

    def to_dict(self) -> dict:
        return asdict(self)


class HistoryManager:
    """Verwaltet die Konversationshistorie persistent."""

    def __init__(self, path: str | Path, max_entries: int = MAX_HISTORY_ENTRIES):
        self.path = Path(path)
        self.max_entries = max_entries
        self._entries: List[HistoryEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistenz
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return
            self._entries = [
                HistoryEntry(**e) for e in data if _is_valid_entry(e)
            ]
        except (json.JSONDecodeError, OSError, TypeError) as e:
            log.warning("Historie konnte nicht geladen werden: %s", e)
            self._entries = []

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(
                    [e.to_dict() for e in self._entries],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except OSError as e:
            log.error("Historie konnte nicht gespeichert werden: %s", e)

    # ------------------------------------------------------------------
    # Operationen
    # ------------------------------------------------------------------
    def add(self, user: str, assistant: str) -> None:
        """Fügt einen Eintrag hinzu und begrenzt die Länge."""
        self._entries.append(HistoryEntry.create(user, assistant))
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]
        self.save()

    def clear(self) -> None:
        """Löscht die gesamte Historie."""
        self._entries.clear()
        self.save()

    def recent(self, n: int) -> List[HistoryEntry]:
        """Gibt die letzten n Einträge zurück."""
        if n <= 0:
            return []
        return self._entries[-n:]

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[HistoryEntry]:
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, index: int) -> HistoryEntry:
        return self._entries[index]


def _is_valid_entry(entry: object) -> bool:
    """Prüft, ob ein Dict ein gültiger HistoryEntry ist."""
    if not isinstance(entry, dict):
        return False
    return all(k in entry for k in ("timestamp", "user", "assistant"))
