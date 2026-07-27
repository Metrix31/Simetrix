"""Command-Pattern: Basisklasse und Registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import Config
from .history import HistoryManager
from .llm import LLMClient


@dataclass
class CommandContext:
    """Gemeinsamer Kontext für alle Befehle."""

    config: Config
    history: HistoryManager
    llm: LLMClient
    registry: "CommandRegistry"
    cwd: str = "."

    def reload_config(self) -> None:
        self.config = Config.load()

    def save_config(self) -> None:
        self.config.save()


class Command(ABC):
    """Basisklasse für alle Befehle."""

    name: str = ""
    aliases: tuple = ()
    description: str = ""
    usage: str = ""
    category: str = "Allgemein"

    @abstractmethod
    def execute(self, args: str, ctx: CommandContext) -> Optional[str]:
        """Führt den Befehl aus.

        Returns:
            None        → normale Ausführung
            "__EXIT__"  → Anwendung beenden
            str         → Status-/Fehlermeldung
        """
        raise NotImplementedError

    def matches(self, line: str) -> bool:
        """Prüft, ob der Befehl zu dieser Zeile passt."""
        stripped = line.strip()
        if not stripped.startswith("/"):
            return False
        parts = stripped[1:].split(None, 1)
        if not parts:
            return False
        cmd = parts[0].lower()
        return cmd == self.name.lower() or cmd in (a.lower() for a in self.aliases)


class CommandRegistry:
    """Registry zur Verwaltung aller Befehle."""

    EXIT_SENTINEL = "__EXIT__"

    def __init__(self):
        self._by_key: Dict[str, Command] = {}
        self._unique: List[Command] = []

    def register(self, command: Command) -> None:
        if not command.name:
            raise ValueError("Befehl benötigt einen Namen")
        if id(command) in (id(c) for c in self._unique):
            return
        self._unique.append(command)
        self._by_key[command.name.lower()] = command
        for alias in command.aliases:
            self._by_key[alias.lower()] = command

    def get(self, name: str) -> Optional[Command]:
        return self._by_key.get(name.lower())

    def all_commands(self) -> List[Command]:
        return sorted(self._unique, key=lambda c: (c.category, c.name))

    def execute(self, line: str, ctx: CommandContext) -> Optional[str]:
        """Parst eine Zeile und führt den passenden Befehl aus."""
        stripped = line.strip()
        if not stripped.startswith("/"):
            return None

        parts = stripped[1:].split(None, 1)
        cmd_name = parts[0]
        args = parts[1].strip() if len(parts) > 1 else ""

        command = self.get(cmd_name)
        if command is None:
            return f"Unbekannter Befehl: /{cmd_name}. /help für eine Liste."

        return command.execute(args, ctx)
