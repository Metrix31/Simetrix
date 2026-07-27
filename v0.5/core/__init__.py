"""SIMETRIX – Coding-Agent mit Ollama."""
from __future__ import annotations

from .builtin_commands import register_defaults
from .commands import Command, CommandContext, CommandRegistry
from .config import Config
from .core import Core
from .history import HistoryEntry, HistoryManager
from .llm import LLMClient
from .ui import APP_NAME, APP_VERSION

__version__ = APP_VERSION
__author__ = "Metrix31"

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "Core",
    "Config",
    "HistoryEntry",
    "HistoryManager",
    "LLMClient",
    "Command",
    "CommandContext",
    "CommandRegistry",
    "register_defaults",
]
