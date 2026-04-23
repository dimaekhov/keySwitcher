from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .language import normalize_word


@dataclass(slots=True)
class TypoExceptions:
    words: set[str] = field(default_factory=set)
    suffixes: tuple[str, ...] = ()

    def matches(self, text: str) -> bool:
        norm = normalize_word(text)
        if not norm:
            return False
        if norm in self.words:
            return True
        return any(len(norm) > len(suffix) and norm.endswith(suffix) for suffix in self.suffixes)


def normalize_exception_word(text: str) -> str:
    return normalize_word(text)


def normalize_exception_suffix(text: str) -> str:
    value = normalize_word(text)
    return value.lstrip("-")


class TypoExceptionStore:
    def __init__(self, path: str | Path, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self._exceptions = TypoExceptions()
        self._last_mtime_ns: int | None = None
        if enabled:
            self.load()

    def load(self) -> None:
        loaded = self._load_data()
        if loaded is not None:
            self._exceptions = loaded
        self._last_mtime_ns = self._current_mtime_ns()

    def reload(self) -> int:
        if not self.enabled:
            return 0
        self.load()
        return self.count()

    def reload_if_changed(self) -> int | None:
        if not self.enabled:
            return None
        current_mtime_ns = self._current_mtime_ns()
        if current_mtime_ns == self._last_mtime_ns:
            return None
        self.load()
        return self.count()

    def count(self) -> int:
        return len(self._exceptions.words) + len(self._exceptions.suffixes)

    def ensure_file(self) -> Path:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._exceptions = TypoExceptions(set(), ("less",))
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "version": 1,
                        "protected_words": [],
                        "protected_suffixes": ["less"],
                    },
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
            self._last_mtime_ns = self._current_mtime_ns()
        return self.path

    def words(self) -> list[str]:
        return sorted(self._exceptions.words)

    def suffixes(self) -> list[str]:
        return sorted(self._exceptions.suffixes)

    def snapshot(self) -> TypoExceptions:
        return TypoExceptions(set(self._exceptions.words), tuple(self._exceptions.suffixes))

    def replace_all(self, words: list[str], suffixes: list[str]) -> None:
        if not self.enabled:
            return
        normalized_words = {
            normalize_exception_word(word)
            for word in words
            if normalize_exception_word(word)
        }
        normalized_suffixes = sorted(
            {
                normalize_exception_suffix(suffix)
                for suffix in suffixes
                if normalize_exception_suffix(suffix)
            }
        )
        self._exceptions = TypoExceptions(normalized_words, tuple(normalized_suffixes))
        self.save()

    def save(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "version": 1,
            "protected_words": sorted(self._exceptions.words),
            "protected_suffixes": list(self._exceptions.suffixes),
        }
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp_path.replace(self.path)
        self._last_mtime_ns = self._current_mtime_ns()

    def _load_data(self) -> TypoExceptions | None:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        words_raw = raw.get("protected_words", [])
        suffixes_raw = raw.get("protected_suffixes", [])
        if not isinstance(words_raw, list) or not isinstance(suffixes_raw, list):
            return None

        words = {
            normalize_exception_word(str(word))
            for word in words_raw
            if normalize_exception_word(str(word))
        }
        suffixes = tuple(
            sorted(
                {
                    normalize_exception_suffix(str(suffix))
                    for suffix in suffixes_raw
                    if normalize_exception_suffix(str(suffix))
                }
            )
        )
        return TypoExceptions(words, suffixes)

    def _current_mtime_ns(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None
