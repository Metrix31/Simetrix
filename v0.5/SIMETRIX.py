#!/usr/bin/env python3
"""SIMETRIX v0.5 — Coding-Agent mit Ollama."""
from __future__ import annotations

import sys

from core import APP_NAME, APP_VERSION, Core


def main() -> int:
    core = Core()
    core.print_banner()

    while True:
        try:
            user_input = input(core.context_label() if hasattr(core, "context_label") else "SIMETRIX> ")
        except KeyboardInterrupt:
            print("\n" + "  Verwende /exit zum Beenden.")
            continue
        except EOFError:
            print("\nBeende " + APP_NAME + " ...")
            break

        result = core.execute(user_input)
        if result == "__EXIT__":
            break
        if isinstance(result, str) and result:
            print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
