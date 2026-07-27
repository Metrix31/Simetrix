"""Alle eingebauten Befehle für SIMETRIX."""
from __future__ import annotations

import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from . import file_ops
from .commands import Command, CommandContext, CommandRegistry
from .ui import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    C,
    HISTORY_DISPLAY_LIMIT,
    MAX_LIST_ITEMS,
    _c,
    bold,
    dim,
    err,
    highlight,
    info,
    ok,
    print_header,
    print_section,
    prompt_label,
    title,
    warn,
)


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------
def _ask(message: str, required: bool = True, default: str = "") -> str:
    """Fragt den Benutzer nach einer Eingabe."""
    suffix = "" if required else " (optional)"
    while True:
        try:
            val = input(f"{message}{suffix}> ").strip()
        except EOFError:
            return default
        if val:
            return val
        if not required:
            return default
        print(err("Eingabe erforderlich."))


def _read_multiline(terminator: str = "END") -> str:
    """Liest mehrzeilige Eingabe bis zum Terminator."""
    print(dim(f"  Beende Eingabe mit einer Zeile '{terminator}'"))
    lines: List[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.rstrip() == terminator:
            break
        lines.append(line)
    return "\n".join(lines)


def _confirm(question: str, default: bool = False) -> bool:
    """Fragt nach einer Bestätigung."""
    suffix = " (J/n): " if default else " (j/N): "
    try:
        ans = input(question + suffix).strip().lower()
    except EOFError:
        return False
    if not ans:
        return default
    return ans in ("j", "ja", "y", "yes", "1", "true")


def _truncate(text: str, limit: int = 100) -> str:
    """Kürzt einen Text für die Anzeige."""
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _stream_response(llm, messages: list) -> str:
    """Streamt eine LLM-Antwort und gibt den vollständigen Text zurück."""
    full = ""
    try:
        for chunk in llm.chat(messages, stream=True):
            print(chunk, end="", flush=True)
            full += chunk
    except Exception as e:
        print()
        print(err(f"LLM-Fehler: {e}"))
    print()
    return full


def _strip_markdown_fence(text: str) -> str:
    """Entfernt umschließende Markdown-Codeblöcke."""
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# Allgemein
# ---------------------------------------------------------------------------
class ExitCommand(Command):
    name = "exit"
    aliases = ("quit", "q")
    description = "Beendet SIMETRIX"
    category = "Allgemein"

    def execute(self, args, ctx):
        print(ok("Auf Wiedersehen!"))
        return CommandRegistry.EXIT_SENTINEL


class HelpCommand(Command):
    name = "help"
    aliases = ("h", "?")
    description = "Zeigt diese Hilfe an"
    usage = "/help [befehl]"
    category = "Allgemein"

    def execute(self, args, ctx):
        if args.strip():
            cmd = ctx.registry.get(args.strip().lstrip("/"))
            if cmd is None:
                return err(f"Unbekannter Befehl: {args.strip()}")
            print_section(f"/{cmd.name}")
            print(f"  Beschreibung: {cmd.description}")
            if cmd.aliases:
                print(f"  Aliase:       {', '.join('/' + a for a in cmd.aliases)}")
            if cmd.usage:
                print(f"  Verwendung:   {cmd.usage}")
            return None

        print_header(f"{APP_NAME} v{APP_VERSION} — Befehle")
        by_cat: dict = {}
        for c in ctx.registry.all_commands():
            by_cat.setdefault(c.category, []).append(c)

        for category, commands in by_cat.items():
            print()
            print(bold(f"  ── {category} ──"))
            for c in commands:
                aliases = ""
                if c.aliases:
                    aliases = dim(f"  ({', '.join('/' + a for a in c.aliases)})")
                line = f"    /{c.name:<14} {c.description}{aliases}"
                print(line)
        print()
        print(dim("  Alles, was nicht mit / beginnt, wird an die KI gesendet."))
        return None


class ClearCommand(Command):
    name = "clear"
    aliases = ("cls",)
    description = "Löscht den Bildschirm"
    category = "Allgemein"

    def execute(self, args, ctx):
        os.system("cls" if os.name == "nt" else "clear")
        return None


class VersionCommand(Command):
    name = "version"
    aliases = ("v",)
    description = "Zeigt die Version"
    category = "Allgemein"

    def execute(self, args, ctx):
        print(f"{APP_NAME} v{APP_VERSION}  ({APP_AUTHOR})")
        return None


class SystemCommand(Command):
    name = "system"
    aliases = ("info",)
    description = "Zeigt Systeminformationen"
    category = "Allgemein"

    def execute(self, args, ctx):
        print_section("Systeminformationen")
        rows = [
            ("App",            f"{APP_NAME} v{APP_VERSION}"),
            ("Autor",          APP_AUTHOR),
            ("Python",         sys.version.split()[0]),
            ("Plattform",      f"{platform.system()} {platform.release()}"),
            ("Arbeitsverzeichnis", os.getcwd()),
            ("Modell",         ctx.llm.model),
            ("Ollama",         ctx.llm.ollama_version()),
            ("Temperatur",     f"{ctx.config.temperature}"),
            ("Verlauf",        f"{len(ctx.history)} Einträge"),
            ("Backup-Verzeichnis", ctx.config.backup_dir),
        ]
        for k, v in rows:
            print(f"  {highlight(k, C.BRIGHT_CYAN):<22} {v}")
        return None


class HistoryCommand(Command):
    name = "history"
    description = "Zeigt die letzten Konversationen"
    usage = "/history [anzahl]"
    category = "Allgemein"

    def execute(self, args, ctx):
        try:
            n = int(args.strip()) if args.strip() else HISTORY_DISPLAY_LIMIT
        except ValueError:
            return err("Anzahl muss eine Zahl sein")
        n = max(1, min(n, len(ctx.history)))

        entries = ctx.history.recent(n)
        if not entries:
            return info("Keine Konversationen im Verlauf.")

        print_section(f"Letzte {n} Konversationen")
        for i, entry in enumerate(entries, 1):
            print(f"  {bold(f'[{i}]')}  {dim(entry.timestamp)}")
            print(f"       {_c('User:', C.BRIGHT_BLUE)} {_truncate(entry.user)}")
            print(f"       {_c('KI:  ', C.BRIGHT_GREEN)} {_truncate(entry.assistant)}")
            print()
        return None


class ClearHistoryCommand(Command):
    name = "clearhistory"
    description = "Löscht den gesamten Verlauf"
    category = "Allgemein"

    def execute(self, args, ctx):
        if ctx.history and not _confirm("Verlauf wirklich löschen?", default=False):
            return warn("Abgebrochen.")
        ctx.history.clear()
        return ok("Verlauf gelöscht.")


# ---------------------------------------------------------------------------
# Dateien
# ---------------------------------------------------------------------------
class PwdCommand(Command):
    name = "pwd"
    description = "Zeigt das aktuelle Verzeichnis"
    category = "Dateien"

    def execute(self, args, ctx):
        print(os.getcwd())
        return None


class CdCommand(Command):
    name = "cd"
    description = "Wechselt das Verzeichnis"
    usage = "/cd <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip() or str(Path.home())
        try:
            os.chdir(path)
            ctx.cwd = os.getcwd()
            return ok(f"Wechsel zu: {os.getcwd()}")
        except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
            return err(str(e))


class LsCommand(Command):
    name = "ls"
    aliases = ("list", "dir")
    description = "Listet Dateien im Verzeichnis"
    usage = "/ls [pfad] [--hidden]"
    category = "Dateien"

    def execute(self, args, ctx):
        show_hidden = "--hidden" in args or "-a" in args
        clean_args = [a for a in args.split() if not a.startswith("-")]
        path = clean_args[0] if clean_args else "."

        try:
            files = file_ops.list_files(path, show_hidden=show_hidden)
        except Exception as e:
            return err(str(e))

        if not files:
            return info(f"Keine Dateien in: {path}")

        print_section(f"Dateien in {path}")
        shown = files[:MAX_LIST_ITEMS]
        for f in shown:
            try:
                size = f.stat().st_size
                size_str = file_ops.format_size(size)
            except OSError:
                size_str = "?"
            print(f"  {f.name}  {dim('(' + size_str + ')')}")
        if len(files) > MAX_LIST_ITEMS:
            print(dim(f"  … und {len(files) - MAX_LIST_ITEMS} weitere"))
        return None


class TreeCommand(Command):
    name = "tree"
    description = "Zeigt Verzeichnisbaum"
    usage = "/tree [pfad] [tiefe]"
    category = "Dateien"

    def execute(self, args, ctx):
        parts = args.split()
        path = parts[0] if parts else "."
        depth = 3
        if len(parts) > 1:
            try:
                depth = int(parts[1])
            except ValueError:
                return err("Tiefe muss eine Zahl sein")
        try:
            print(file_ops.build_tree(path, max_depth=depth))
        except Exception as e:
            return err(str(e))
        return None


class CatCommand(Command):
    name = "cat"
    description = "Gibt eine Datei direkt aus (ohne KI)"
    usage = "/cat <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /cat <pfad>")
        try:
            content = file_ops.read_file(path)
        except Exception as e:
            return err(str(e))
        print_section(f"Inhalt: {path}")
        print(content)
        print(dim("─" * 50))
        return None


class ReadCommand(Command):
    name = "read"
    description = "Liest Datei und verarbeitet sie optional mit der KI"
    usage = "/read <pfad> [anweisung]"
    category = "Dateien"

    def execute(self, args, ctx):
        if not args:
            return err("Verwendung: /read <pfad> [anweisung]")
        parts = args.split(maxsplit=1)
        path = parts[0]
        instruction = parts[1].strip() if len(parts) > 1 else ""

        try:
            content = file_ops.read_file(path)
        except Exception as e:
            return err(str(e))

        if not instruction:
            print_section(f"Inhalt: {path}")
            print(content)
            print(dim("─" * 50))
            return None

        prompt = (
            f"{instruction}\n\n"
            f"--- Dateiinhalt ({path}) ---\n{content}\n"
            f"--- Ende ---"
        )
        print(bold("\nKI-Antwort:"))
        full = _stream_response(
            ctx.llm,
            [
                {"role": "system", "content": ctx.config.system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        ctx.history.add(f"READ {path} :: {instruction}", full)
        return None


class WriteCommand(Command):
    name = "write"
    description = "Schreibt mehrzeiligen Inhalt in eine Datei"
    usage = "/write <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /write <pfad>")

        # Backup falls Datei existiert
        if os.path.exists(path) and ctx.config.auto_backup:
            try:
                file_ops.create_backup(path, ctx.config.backup_dir)
            except Exception as e:
                print(warn(f"Backup fehlgeschlagen: {e}"))

        content = _read_multiline()
        if not content:
            return warn("Kein Inhalt eingegeben.")

        try:
            file_ops.write_file(path, content)
        except Exception as e:
            return err(str(e))
        ctx.history.add(f"WRITE {path}", f"{len(content)} Zeichen geschrieben")
        return ok(f"Datei geschrieben: {path} ({file_ops.format_size(len(content))})")


class CreateCommand(Command):
    name = "create"
    description = "Erstellt Datei mit KI-generiertem Inhalt"
    usage = "/create <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /create <pfad>")
        if os.path.exists(path):
            return err(f"Datei existiert bereits: {path}")

        description = _ask("Beschreibung des Inhalts")
        if not description:
            return warn("Abgebrochen.")

        prompt = (
            f"Erstelle den vollständigen Inhalt für die Datei '{path}'.\n"
            f"Beschreibung: {description}\n\n"
            f"Regeln:\n"
            f"- Nur den reinen Dateiinhalt ausgeben\n"
            f"- KEINE Markdown-Codeblöcke (``` oder ```python)\n"
            f"- Keine Erklärungen vor oder nach dem Inhalt\n"
            f"- Vollständig und produktionsreif"
        )
        print(bold("\nKI generiert Inhalt…"))
        full = _stream_response(
            ctx.llm,
            [
                {"role": "system", "content": ctx.config.system_prompt},
                {"role": "user", "content": prompt},
            ],
        )

        full = _strip_markdown_fence(full)
        try:
            file_ops.write_file(path, full)
        except Exception as e:
            return err(str(e))
        ctx.history.add(
            f"CREATE {path} :: {description}",
            f"Datei erstellt: {file_ops.format_size(len(full))}",
        )
        return ok(f"Datei erstellt: {path} ({file_ops.format_size(len(full))})")


class EditCommand(Command):
    name = "edit"
    description = "Bearbeitet eine bestehende Datei mit der KI"
    usage = "/edit <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /edit <pfad>")
        if not os.path.exists(path):
            return err(f"Datei nicht gefunden: {path}")

        instruction = _ask("Was soll geändert werden?")
        if not instruction:
            return warn("Abgebrochen.")

        try:
            current = file_ops.read_file(path)
        except Exception as e:
            return err(str(e))

        # Backup anlegen
        if ctx.config.auto_backup:
            try:
                bp = file_ops.create_backup(path, ctx.config.backup_dir)
                print(dim(f"  Backup: {bp}"))
            except Exception as e:
                print(warn(f"Backup fehlgeschlagen: {e}"))

        prompt = (
            f"Bearbeite die folgende Datei gemäß der Anweisung.\n"
            f"Anweisung: {instruction}\n\n"
            f"--- Datei ({path}) ---\n{current}\n--- Ende ---\n\n"
            f"Gib NUR den neuen vollständigen Dateiinhalt zurück, "
            f"ohne Markdown-Blöcke und ohne Erklärungen."
        )
        print(bold("\nKI bearbeitet…"))
        new_content = _stream_response(
            ctx.llm,
            [
                {"role": "system", "content": ctx.config.system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        new_content = _strip_markdown_fence(new_content)

        # Diff anzeigen
        diff = file_ops.make_diff(current, new_content, fromfile=path, tofile=f"{path} (neu)")
        if diff:
            print_section("Diff")
            for line in diff.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    print(_c(line, C.BRIGHT_GREEN))
                elif line.startswith("-") and not line.startswith("---"):
                    print(_c(line, C.BRIGHT_RED))
                elif line.startswith("@@"):
                    print(_c(line, C.BRIGHT_CYAN))
                else:
                    print(dim(line))

        if not _confirm("Änderungen übernehmen?", default=True):
            return warn("Abgebrochen. Datei unverändert.")

        try:
            file_ops.write_file(path, new_content)
        except Exception as e:
            return err(str(e))
        ctx.history.add(f"EDIT {path} :: {instruction}", "Datei bearbeitet")
        return ok(f"Datei gespeichert: {path}")


class AppendCommand(Command):
    name = "append"
    description = "Hängt Inhalt an eine Datei an"
    usage = "/append <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /append <pfad>")

        content = _read_multiline()
        if not content:
            return warn("Kein Inhalt eingegeben.")

        try:
            file_ops.append_to_file(path, "\n" + content if not content.startswith("\n") else content)
        except Exception as e:
            return err(str(e))
        ctx.history.add(f"APPEND {path}", f"{len(content)} Zeichen angehängt")
        return ok(f"Angehängt: {path}")


class DeleteCommand(Command):
    name = "delete"
    aliases = ("rm", "del")
    description = "Löscht eine Datei"
    usage = "/delete <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /delete <pfad>")

        if ctx.config.confirm_destructive and not _confirm(
            f"Wirklich löschen: {path}?", default=False
        ):
            return warn("Abgebrochen.")
        try:
            file_ops.delete_file(path)
        except Exception as e:
            return err(str(e))
        ctx.history.add(f"DELETE {path}", "Datei gelöscht")
        return ok(f"Gelöscht: {path}")


class SearchCommand(Command):
    name = "search"
    aliases = ("grep",)
    description = "Sucht einen Begriff in Dateien"
    usage = "/search <begriff> [pfad]"
    category = "Dateien"

    def execute(self, args, ctx):
        parts = args.split(maxsplit=1)
        if not parts:
            return err("Verwendung: /search <begriff> [pfad]")
        term = parts[0]
        path = parts[1] if len(parts) > 1 else "."

        try:
            results = file_ops.search_in_files(term, path)
        except Exception as e:
            return err(str(e))

        if not results:
            return info(f"Keine Treffer für '{term}'.")

        print_section(f"Treffer für '{term}' ({len(results)})")
        current_file = None
        for file_path, line_num, line in results[:MAX_LIST_ITEMS]:
            if file_path != current_file:
                print(f"\n  {highlight(str(file_path), C.BRIGHT_CYAN)}")
                current_file = file_path
            print(f"    {dim(f'{line_num:>4}')}: {line}")
        if len(results) > MAX_LIST_ITEMS:
            print(dim(f"\n  … und {len(results) - MAX_LIST_ITEMS} weitere"))
        return None


class BackupCommand(Command):
    name = "backup"
    description = "Erstellt ein Backup einer Datei"
    usage = "/backup <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /backup <pfad>")
        try:
            dest = file_ops.create_backup(path, ctx.config.backup_dir)
        except Exception as e:
            return err(str(e))
        return ok(f"Backup erstellt: {dest}")


class RestoreCommand(Command):
    name = "restore"
    description = "Stellt ein Backup wieder her"
    usage = "/restore <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /restore <pfad>")
        backups = file_ops.list_backups(path, ctx.config.backup_dir)
        if not backups:
            return err(f"Keine Backups gefunden für: {path}")

        print_section(f"Backups für {path}")
        for i, b in enumerate(backups[:20], 1):
            ts = b.stem.split(".", 1)[1] if "." in b.stem else "?"
            print(f"  {i:>2}. {ts}  {dim(str(b))}")

        try:
            choice = input("Nummer wählen (leer = neuestes): ").strip()
        except EOFError:
            return warn("Abgebrochen.")
        idx = int(choice) - 1 if choice else 0
        if not (0 <= idx < len(backups)):
            return err("Ungültige Auswahl.")

        try:
            target = file_ops.restore_backup(backups[idx], path)
        except Exception as e:
            return err(str(e))
        return ok(f"Wiederhergestellt: {target}")


class SyntaxCommand(Command):
    name = "syntax"
    description = "Syntax-Check für Python-Dateien"
    usage = "/syntax <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /syntax <pfad>")
        ok_flag, msg = file_ops.syntax_check_python(path)
        return ok(msg) if ok_flag else err(msg)


class RunCommand(Command):
    name = "run"
    description = "Führt eine Python-Datei aus"
    usage = "/run <pfad>"
    category = "Dateien"

    def execute(self, args, ctx):
        path = args.strip()
        if not path:
            return err("Verwendung: /run <pfad>")
        if not os.path.exists(path):
            return err(f"Datei nicht gefunden: {path}")
        if ctx.config.confirm_destructive and not _confirm(
            f"Ausführen: {path}?", default=True
        ):
            return warn("Abgebrochen.")
        try:
            result = subprocess.run(
                [sys.executable, path],
                capture_output=False,
                text=True,
            )
            return info(f"Exit-Code: {result.returncode}")
        except OSError as e:
            return err(f"Ausführung fehlgeschlagen: {e}")


# ---------------------------------------------------------------------------
# KI / Modell
# ---------------------------------------------------------------------------
class ModelCommand(Command):
    name = "model"
    description = "Wechselt das KI-Modell"
    usage = "/model [name]"
    category = "KI"

    def execute(self, args, ctx):
        name = args.strip()
        if not name:
            return info(f"Aktives Modell: {ctx.llm.model}")
        if not ctx.llm.ensure_model(name):
            return err(f"Modell nicht verfügbar: {name}")
        ctx.llm.set_model(name)
        ctx.config.model = name
        ctx.save_config()
        return ok(f"Modell gewechselt: {name}")


class ModelsCommand(Command):
    name = "models"
    description = "Listet verfügbare Modelle"
    category = "KI"

    def execute(self, args, ctx):
        try:
            models = ctx.llm.list_models()
        except Exception as e:
            return err(str(e))
        if not models:
            return info("Keine Modelle installiert.")
        print_section("Verfügbare Modelle")
        for m in models:
            marker = highlight("●", C.BRIGHT_GREEN) if m == ctx.llm.model else dim("○")
            print(f"  {marker} {m}")
        return None


class PullCommand(Command):
    name = "pull"
    description = "Lädt ein Modell herunter"
    usage = "/pull <name>"
    category = "KI"

    def execute(self, args, ctx):
        name = args.strip()
        if not name:
            return err("Verwendung: /pull <name>")
        print(info(f"Lade {name} herunter …"))
        if ctx.llm.pull_model(name):
            return ok(f"Modell verfügbar: {name}")
        return err(f"Download fehlgeschlagen: {name}")


class TempCommand(Command):
    name = "temp"
    aliases = ("temperature",)
    description = "Setzt die Temperatur (0.0 – 1.0)"
    usage = "/temp [wert]"
    category = "KI"

    def execute(self, args, ctx):
        val = args.strip()
        if not val:
            return info(f"Aktuelle Temperatur: {ctx.config.temperature}")
        try:
            t = float(val)
            if not 0.0 <= t <= 2.0:
                return err("Temperatur muss zwischen 0.0 und 2.0 liegen")
        except ValueError:
            return err("Wert muss eine Zahl sein")
        ctx.config.temperature = t
        ctx.save_config()
        return ok(f"Temperatur: {t}")


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
class ConfigCommand(Command):
    name = "config"
    description = "Zeigt die Konfiguration"
    category = "Konfiguration"

    def execute(self, args, ctx):
        print_section("Aktuelle Konfiguration")
        d = ctx.config.as_dict()
        for k, v in d.items():
            if k == "system_prompt" and isinstance(v, str) and len(v) > 60:
                v = v[:57] + "…"
            print(f"  {highlight(k, C.BRIGHT_CYAN):<22} {v}")
        return None


class SetCommand(Command):
    name = "set"
    description = "Setzt einen Konfigurationswert"
    usage = "/set <schlüssel> <wert>"
    category = "Konfiguration"

    def execute(self, args, ctx):
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return err("Verwendung: /set <schlüssel> <wert>")
        key, value = parts[0], parts[1]
        if not ctx.config.set(key, value):
            return err(f"Ungültiger Schlüssel oder Wert: {key}")
        ctx.save_config()
        return ok(f"{key} = {value}")


# ---------------------------------------------------------------------------
# Sonstiges
# ---------------------------------------------------------------------------
class ShellCommand(Command):
    name = "shell"
    aliases = ("sh", "!")
    description = "Führt einen Shell-Befehl aus"
    usage = "/shell <befehl>"
    category = "Sonstiges"

    def execute(self, args, ctx):
        if not args:
            return err("Verwendung: /shell <befehl>")
        try:
            result = subprocess.run(
                args,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(_c(result.stderr.rstrip(), C.BRIGHT_RED))
            return info(f"Exit-Code: {result.returncode}")
        except subprocess.TimeoutExpired:
            return err("Timeout (30s)")
        except OSError as e:
            return err(str(e))


# ---------------------------------------------------------------------------
# Registrierung
# ---------------------------------------------------------------------------
def register_defaults(registry: CommandRegistry) -> None:
    """Registriert alle eingebauten Befehle."""
    commands: List[Command] = [
        # Allgemein
        ExitCommand(),
        HelpCommand(),
        ClearCommand(),
        VersionCommand(),
        SystemCommand(),
        HistoryCommand(),
        ClearHistoryCommand(),
        # Dateien
        PwdCommand(),
        CdCommand(),
        LsCommand(),
        TreeCommand(),
        CatCommand(),
        ReadCommand(),
        WriteCommand(),
        CreateCommand(),
        EditCommand(),
        AppendCommand(),
        DeleteCommand(),
        SearchCommand(),
        BackupCommand(),
        RestoreCommand(),
        SyntaxCommand(),
        RunCommand(),
        # KI
        ModelCommand(),
        ModelsCommand(),
        PullCommand(),
        TempCommand(),
        # Konfiguration
        ConfigCommand(),
        SetCommand(),
        # Sonstiges
        ShellCommand(),
    ]
    for c in commands:
        registry.register(c)
