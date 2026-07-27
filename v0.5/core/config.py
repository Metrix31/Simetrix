"""Konfigurationsverwaltung für SIMETRIX."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict

from .ui import (
    CONFIG_FILE,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    MAX_FILE_SIZE,
    MAX_HISTORY_ENTRIES,
    BACKUP_DIR,
    HISTORY_FILE,
    ConfigError,
    log,
)


@dataclass
class Config:
    """SIMETRIX-Konfiguration."""

    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_file_size: int = MAX_FILE_SIZE
    max_history_entries: int = MAX_HISTORY_ENTRIES
    backup_dir: str = BACKUP_DIR
    history_file: str = HISTORY_FILE
    auto_backup: bool = True
    confirm_destructive: bool = True
    show_token_estimate: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Laden / Speichern
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path = CONFIG_FILE) -> "Config":
        """Lädt die Konfiguration aus einer JSON-Datei."""
        config_path = Path(path)
        if not config_path.exists():
            cfg = cls()
            cfg.save(config_path)
            return cfg

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Konfiguration beschädigt, verwende Standard: %s", e)
            return cls()

        if not isinstance(data, dict):
            return cls()

        known = {f for f in cls.__dataclass_fields__ if f != "extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        filtered = {k: v for k, v in data.items() if k in known}

        try:
            return cls(extra=extra, **filtered)
        except TypeError as e:
            log.warning("Konfigurationsfelder ungültig: %s", e)
            return cls()

    def save(self, path: str | Path = CONFIG_FILE) -> None:
        """Speichert die Konfiguration als JSON."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.error("Konfiguration konnte nicht gespeichert werden: %s", e)

    # ------------------------------------------------------------------
    # Manipulation
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any) -> bool:
        """Setzt einen Konfigurationswert. Gibt True bei Erfolg zurück."""
        if key == "extra":
            return False
        if not hasattr(self, key):
            self.extra[key] = value
            return True
        # Typcoercion für bekannte Felder
        try:
            current = getattr(self, key)
            if current is not None and not isinstance(current, (dict, list, str)):
                value = type(current)(value)
        except (ValueError, TypeError):
            return False
        setattr(self, key, value)
        return True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
