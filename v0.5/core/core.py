"""Hauptklasse, die alle Module verbindet."""
from __future__ import annotations

from typing import List, Optional

from . import file_ops
from .commands import CommandContext, CommandRegistry
from .config import Config
from .history import HistoryManager
from .llm import LLMClient
from .builtin_commands import register_defaults
from .ui import (
    _c,
    bold,
    dim,
    err,
    highlight,
    info,
    ok,
    prompt_label,
    title,
    warn,
    APP_NAME,
    APP_VERSION,
    C,
)


class Core:
    """Zentrale Fassade für SIMETRIX."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.history = HistoryManager(
            self.config.history_file,
            self.config.max_history_entries,
        )
        self.llm = LLMClient(self.config)
        self.registry = CommandRegistry()
        register_defaults(self.registry)
        self._context: Optional[CommandContext] = None

    # ------------------------------------------------------------------
    # Kontext
    # ------------------------------------------------------------------
    @property
    def context(self) -> CommandContext:
        if self._context is None:
            self._context = CommandContext(
                config=self.config,
                history=self.history,
                llm=self.llm,
                registry=self.registry,
            )
        return self._context

    def reload_config(self) -> None:
        self.config = Config.load()
        self.context.config = self.config
        self.llm.config = self.config

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def chat(self, user_input: str) -> str:
        """Sendet eine Eingabe an die KI (gestreamt) und speichert die Antwort."""
        if not user_input.strip():
            return ""

        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": user_input},
        ]

        print()
        full = ""
        try:
            for chunk in self.llm.chat(messages, stream=True):
                print(chunk, end="", flush=True)
                full += chunk
        except Exception as e:
            print()
            print(err(f"LLM-Fehler: {e}"))
            full = f"[Fehler] {e}"
        print()
        self.history.add(user_input, full)
        return full

    # ------------------------------------------------------------------
    # Befehlsausführung
    # ------------------------------------------------------------------
    def execute(self, line: str) -> Optional[str]:
        """Führt eine Zeile aus. Gibt True zurück, wenn die App beendet werden soll."""
        if not line.strip():
            return None

        # Befehl?
        if line.strip().startswith("/"):
            result = self.registry.execute(line, self.context)
            return result
        # Regulärer Chat
        self.chat(line)
        return None

    # ------------------------------------------------------------------
    # Anzeige
    # ------------------------------------------------------------------
    def print_banner(self) -> None:
        print(_c(f"╔══ {APP_NAME} v{APP_VERSION} ", C.BOLD + C.BRIGHT_MAGENTA)
              + _c("═" * 35, C.DIM))
        print(_c("║ ", C.BRIGHT_MAGENTA) + dim("Coding-Agent mit Ollama"))
        print(_c("║ ", C.BRIGHT_MAGENTA)
              + "Modell: " + highlight(self.llm.model, C.BRIGHT_CYAN))
        print(_c("╚", C.BRIGHT_MAGENTA) + _c("═" * 50, C.DIM))
        print(dim("  /help für Befehle   /exit zum Beenden\n"))
