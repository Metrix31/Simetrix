"""Versionssicherer Ollama-Client."""
from __future__ import annotations

import subprocess
from typing import Any, Dict, Iterator, List, Union

try:
    import ollama
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Das 'ollama' Python-Paket fehlt. Installation: pip install ollama"
    ) from e

from .config import Config
from .ui import LLMError, ModelNotAvailableError, log


class LLMClient:
    """Kapselt die Ollama-API (abwärtskompatibel)."""

    def __init__(self, config: Config):
        self.config = config
        self._model = config.model

    # ------------------------------------------------------------------
    # Eigenschaften
    # ------------------------------------------------------------------
    @property
    def model(self) -> str:
        return self._model

    def set_model(self, name: str) -> None:
        self._model = name

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
    ) -> Union[str, Iterator[str]]:
        """Synchroner oder Streaming-Chat."""
        if stream:
            return self._stream_chat(messages)
        return self._blocking_chat(messages)

    def _blocking_chat(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = ollama.chat(
                model=self._model,
                messages=messages,
                stream=False,
                options={"temperature": self.config.temperature},
            )
            return self._extract_content(response) or ""
        except Exception as e:
            raise LLMError(f"LLM-Aufruf fehlgeschlagen: {e}") from e

    def _stream_chat(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        try:
            stream = ollama.chat(
                model=self._model,
                messages=messages,
                stream=True,
                options={"temperature": self.config.temperature},
            )
            for chunk in stream:
                content = self._extract_content(chunk)
                if content:
                    yield content
        except Exception as e:
            raise LLMError(f"LLM-Streaming fehlgeschlagen: {e}") from e

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extrahiert Text aus einer Ollama-Antwort (alt + neu)."""
        try:
            # Neue API: ollama-python >= 0.4
            msg = getattr(response, "message", None)
            if msg is not None:
                content = getattr(msg, "content", None)
                if content is not None:
                    return str(content)
            # Alte API: dict
            if isinstance(response, dict):
                msg = response.get("message") or {}
                if isinstance(msg, dict):
                    return str(msg.get("content", ""))
                return str(getattr(msg, "content", ""))
        except (AttributeError, TypeError):
            pass
        return ""

    # ------------------------------------------------------------------
    # Modelle
    # ------------------------------------------------------------------
    def list_models(self) -> List[str]:
        """Listet alle lokal verfügbaren Modelle."""
        try:
            result = ollama.list()
        except Exception as e:
            raise LLMError(f"Modelle konnten nicht geladen werden: {e}") from e

        names: List[str] = []

        # Neue API
        models_attr = getattr(result, "models", None)
        if models_attr is not None:
            for m in models_attr:
                name = getattr(m, "name", None) or getattr(m, "model", None)
                if name:
                    names.append(str(name))
            return names

        # Alte API
        if isinstance(result, dict):
            for m in result.get("models", []):
                if isinstance(m, dict):
                    name = m.get("name") or m.get("model")
                    if name:
                        names.append(str(name))
        return names

    def pull_model(self, name: str) -> bool:
        """Lädt ein Modell herunter."""
        try:
            ollama.pull(name)
            return True
        except Exception as e:
            log.error("Pull fehlgeschlagen für %s: %s", name, e)
            return False

    def ensure_model(self, name: str) -> bool:
        """Stellt sicher, dass ein Modell verfügbar ist (lädt es ggf. herunter)."""
        try:
            available = self.list_models()
        except LLMError:
            return False
        if name in available:
            return True
        return self.pull_model(name)

    # ------------------------------------------------------------------
    # Version
    # ------------------------------------------------------------------
    def ollama_version(self) -> str:
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (result.stdout or result.stderr).strip()
            return out or "Unbekannt"
        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            OSError,
        ):
            return "Nicht verfügbar"
