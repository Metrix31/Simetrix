"""Sichere Datei-Operationen."""
from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Generator, List, Tuple

from .ui import (
    BACKUP_DIR,
    MAX_FILE_SIZE,
    FileError,
    FileTooLargeError,
    SimetrixFileExistsError,
    SimetrixFileNotFoundError,
    format_size,
    log,
)


# ---------------------------------------------------------------------------
# Lesen / Schreiben
# ---------------------------------------------------------------------------
def read_file(path: str | Path, max_size: int = MAX_FILE_SIZE) -> str:
    """Liest eine Textdatei (mit Encoding-Fallback)."""
    p = Path(path)
    if not p.exists():
        raise SimetrixFileNotFoundError(f"Datei nicht gefunden: {path}")
    if not p.is_file():
        raise FileError(f"Pfad ist keine Datei: {path}")

    size = p.stat().st_size
    if size > max_size:
        raise FileTooLargeError(
            f"Datei zu groß: {format_size(size)} (max: {format_size(max_size)})"
        )

    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return p.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise FileError(f"Fehler beim Lesen: {e}") from e
    raise FileError(f"Encoding nicht erkannt: {path}")


def write_file(
    path: str | Path,
    content: str,
    overwrite: bool = True,
    create_dirs: bool = True,
) -> None:
    """Schreibt eine Datei sicher."""
    p = Path(path)
    if p.exists() and not overwrite:
        raise SimetrixFileExistsError(f"Datei existiert bereits: {path}")

    try:
        if create_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except OSError as e:
        raise FileError(f"Fehler beim Schreiben: {e}") from e


def append_to_file(path: str | Path, content: str) -> None:
    """Hängt Text an eine Datei an."""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise FileError(f"Fehler beim Anhängen: {e}") from e


def delete_file(path: str | Path) -> None:
    """Löscht eine Datei."""
    p = Path(path)
    if not p.exists():
        raise SimetrixFileNotFoundError(f"Datei nicht gefunden: {path}")
    try:
        p.unlink()
    except OSError as e:
        raise FileError(f"Fehler beim Löschen: {e}") from e


def copy_file(src: str | Path, dest: str | Path) -> None:
    """Kopiert eine Datei."""
    s, d = Path(src), Path(dest)
    if not s.exists():
        raise SimetrixFileNotFoundError(f"Quelle nicht gefunden: {src}")
    try:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
    except OSError as e:
        raise FileError(f"Fehler beim Kopieren: {e}") from e


def rename_file(src: str | Path, dest: str | Path) -> None:
    """Verschiebt/benennt eine Datei um."""
    s, d = Path(src), Path(dest)
    if not s.exists():
        raise SimetrixFileNotFoundError(f"Quelle nicht gefunden: {src}")
    try:
        d.parent.mkdir(parents=True, exist_ok=True)
        s.rename(d)
    except OSError as e:
        raise FileError(f"Fehler beim Umbenennen: {e}") from e


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------
def create_backup(path: str | Path, backup_dir: str | Path = BACKUP_DIR) -> Path:
    """Erstellt eine zeitstempelbasierte Sicherungskopie."""
    src = Path(path)
    if not src.exists():
        raise SimetrixFileNotFoundError(f"Datei nicht gefunden: {path}")

    backup_root = Path(backup_dir)
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_root / f"{src.name}.{timestamp}.bak"

    try:
        shutil.copy2(src, dest)
        log.info("Backup erstellt: %s", dest)
        return dest
    except OSError as e:
        raise FileError(f"Backup fehlgeschlagen: {e}") from e


def list_backups(path: str | Path, backup_dir: str | Path = BACKUP_DIR) -> List[Path]:
    """Listet alle Backups einer Datei (neueste zuerst)."""
    name = Path(path).name
    root = Path(backup_dir)
    if not root.exists():
        return []
    return sorted(
        root.glob(f"{name}.*.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def restore_backup(
    backup_path: str | Path,
    target_path: str | Path | None = None,
) -> Path:
    """Stellt ein Backup wieder her."""
    src = Path(backup_path)
    if not src.exists():
        raise SimetrixFileNotFoundError(f"Backup nicht gefunden: {backup_path}")
    if target_path is None:
        # Aus dem Namen "datei.20240101_120000.bak" -> "datei" rekonstruieren
        target = Path(src.name.split(".", 1)[0])
    else:
        target = Path(target_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        return target
    except OSError as e:
        raise FileError(f"Restore fehlgeschlagen: {e}") from e


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
def list_files(
    directory: str | Path = ".",
    pattern: str = "*",
    show_hidden: bool = False,
) -> List[Path]:
    """Listet Dateien (sortiert)."""
    p = Path(directory)
    if not p.exists():
        raise SimetrixFileNotFoundError(f"Verzeichnis nicht gefunden: {directory}")
    if not p.is_dir():
        raise FileError(f"Pfad ist kein Verzeichnis: {directory}")

    files: List[Path] = []
    for item in p.glob(pattern):
        if item.is_file() and (show_hidden or not item.name.startswith(".")):
            files.append(item)
    return sorted(files, key=lambda x: x.name.lower())


def build_tree(
    directory: str | Path = ".",
    max_depth: int = 3,
    show_hidden: bool = False,
) -> str:
    """Erzeugt einen Verzeichnisbaum als String."""
    p = Path(directory)
    if not p.exists():
        raise SimetrixFileNotFoundError(f"Verzeichnis nicht gefunden: {directory}")
    if not p.is_dir():
        raise FileError(f"Pfad ist kein Verzeichnis: {directory}")

    lines: List[str] = [f"{p.resolve()}/"]
    _tree_recurse(p, max_depth, "", lines, current_depth=0, show_hidden=show_hidden)
    return "\n".join(lines)


def _tree_recurse(
    directory: Path,
    max_depth: int,
    prefix: str,
    lines: List[str],
    current_depth: int,
    show_hidden: bool,
) -> None:
    if current_depth >= max_depth:
        return

    entries = sorted(
        (
            e for e in directory.iterdir()
            if show_hidden or not e.name.startswith(".")
        ),
        key=lambda e: (not e.is_dir(), e.name.lower()),
    )

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "│   "
            _tree_recurse(
                entry, max_depth, prefix + extension, lines,
                current_depth + 1, show_hidden,
            )
        else:
            try:
                size = entry.stat().st_size
                size_str = format_size(size)
            except OSError:
                size_str = "?"
            lines.append(f"{prefix}{connector}{entry.name}  ({size_str})")


# ---------------------------------------------------------------------------
# Suche
# ---------------------------------------------------------------------------
def search_in_files(
    term: str,
    directory: str | Path = ".",
    file_pattern: str = "*",
) -> List[Tuple[Path, int, str]]:
    """Durchsucht Dateien nach einem Begriff."""
    p = Path(directory)
    if not p.exists() or not p.is_dir():
        raise FileError(f"Verzeichnis nicht gefunden: {directory}")

    pattern = re.compile(re.escape(term), re.IGNORECASE)
    results: List[Tuple[Path, int, str]] = []

    for file_path in p.rglob(file_pattern):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_num, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                results.append((file_path, line_num, line.strip()))
    return results


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------
def make_diff(old: str, new: str, fromfile: str = "alt", tofile: str = "neu") -> str:
    """Erzeugt einen Unified-Diff."""
    return "".join(
        unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )


# ---------------------------------------------------------------------------
# Syntax-Check
# ---------------------------------------------------------------------------
def syntax_check_python(path: str | Path) -> Tuple[bool, str]:
    """Prüft eine Python-Datei auf Syntaxfehler."""
    p = Path(path)
    try:
        content = p.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"Fehler beim Lesen: {e}"

    try:
        ast.parse(content, filename=str(p))
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntaxfehler in Zeile {e.lineno}: {e.msg}"
