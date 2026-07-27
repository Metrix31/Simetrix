"""UI-Helfer, Exceptions, Logger und Konstanten für SIMETRIX."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
APP_NAME = "SIMETRIX"
APP_VERSION = "0.5.0"
APP_AUTHOR = "Metrix31"

DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_TEMPERATURE = 0.7

MAX_FILE_SIZE = 5_000_000            # 5 MB
MAX_HISTORY_ENTRIES = 1000
HISTORY_DISPLAY_LIMIT = 10
MAX_LIST_ITEMS = 200

BACKUP_DIR = ".simetrix_backups"
CONFIG_FILE = ".simetrix.json"
HISTORY_FILE = ".simetrix_history.json"
LOG_FILE = ".simetrix.log"

DEFAULT_SYSTEM_PROMPT = (
    "Du bist SIMETRIX, ein präziser, logischer und effizienter Coding-Agent. "
    "Du analysierst Probleme, planst Schritte und erzeugst sauberen, "
    "funktionalen Code. Wenn Tools verfügbar sind, nutzt du sie. "
    "Du erklärst klar und knapp. "
    "Antworte immer auf Deutsch, es sei denn, der Benutzer verlangt "
    "eine andere Sprache."
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class SimetrixError(Exception):
    """Basis-Exception für SIMETRIX."""


class FileError(SimetrixError):
    """Datei-bezogener Fehler."""


class SimetrixFileNotFoundError(FileError):
    pass


class SimetrixFileExistsError(FileError):
    pass


class FileTooLargeError(FileError):
    pass


class LLMError(SimetrixError):
    """LLM-bezogener Fehler."""


class ModelNotAvailableError(LLMError):
    pass


class CommandError(SimetrixError):
    """Befehls-bezogener Fehler."""


class ConfigError(SimetrixError):
    pass


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
def setup_logging(level: int = logging.WARNING) -> logging.Logger:
    """Richtet das Logging ein (Konsole + Datei)."""
    logger = logging.getLogger("simetrix")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsole
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    console.setLevel(logging.WARNING)
    logger.addHandler(console)

    # Datei
    try:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger


log = setup_logging()


# ---------------------------------------------------------------------------
# Farben (ANSI)
# ---------------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def _supports_color() -> bool:
    """Prüft, ob das Terminal Farben unterstützt."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        # Windows 10+ unterstützt ANSI nativ
        return True
    return True


_COLOR_ENABLED = _supports_color()


def _c(text: str, color: str) -> str:
    """Färbt einen Text (oder lässt ihn unverändert)."""
    return f"{color}{text}{C.RESET}" if _COLOR_ENABLED else text


# Öffentliche Formatierer
def info(text: str) -> str:
    return _c(f"[i] {text}", C.BRIGHT_BLUE)


def ok(text: str) -> str:
    return _c(f"[OK] {text}", C.BRIGHT_GREEN)


def warn(text: str) -> str:
    return _c(f"[WARN] {text}", C.BRIGHT_YELLOW)


def err(text: str) -> str:
    return _c(f"[FEHLER] {text}", C.BRIGHT_RED)


def dim(text: str) -> str:
    return _c(text, C.DIM)


def bold(text: str) -> str:
    return _c(text, C.BOLD)


def title(text: str) -> str:
    return _c(text, C.BOLD + C.BRIGHT_CYAN)


def highlight(text: str, color: str = C.BRIGHT_YELLOW) -> str:
    return _c(text, color)


def prompt_label() -> str:
    return _c(APP_NAME, C.BOLD + C.BRIGHT_MAGENTA) + _c(" ❯ ", C.DIM)


def print_header(text: str, char: str = "═") -> None:
    width = max(60, len(text) + 4)
    print(_c(char * width, C.BRIGHT_CYAN))
    print(_c(f"  {text}", C.BOLD + C.BRIGHT_CYAN))
    print(_c(char * width, C.BRIGHT_CYAN))


def print_section(text: str) -> None:
    print()
    line = "─" * max(40, len(text) + 4)
    print(_c(f"── {text} ", C.BRIGHT_CYAN) + _c(line, C.DIM))


def format_size(size: int) -> str:
    """Formatiert eine Bytegröße."""
    n = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")
