from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from .language import Language, normalize_word


@dataclass(slots=True)
class LearnedCorrection:
    actual: str
    replacement: str
    target_language: Language
    count: int
    updated_at: float


def learning_key(text: str) -> str:
    return text.strip().casefold()


class LearningStore:
    def __init__(self, path: str | Path, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self._items: dict[str, LearnedCorrection] = {}
        self._last_mtime_ns: int | None = None
        if enabled:
            self.load()

    def load(self) -> None:
        loaded = self._load_items()
        if loaded is not None:
            self._items = loaded
        self._last_mtime_ns = self._current_mtime_ns()

    def reload(self) -> int:
        if not self.enabled:
            return 0
        self.load()
        return len(self._items)

    def reload_if_changed(self) -> int | None:
        if not self.enabled:
            return None
        current_mtime_ns = self._current_mtime_ns()
        if current_mtime_ns == self._last_mtime_ns:
            return None
        self.load()
        return len(self._items)

    def items(self) -> list[LearnedCorrection]:
        return [
            LearnedCorrection(
                actual=item.actual,
                replacement=item.replacement,
                target_language=item.target_language,
                count=item.count,
                updated_at=item.updated_at,
            )
            for _, item in sorted(self._items.items())
        ]

    def ensure_file(self) -> Path:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump({"version": 1, "corrections": {}}, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            self._last_mtime_ns = self._current_mtime_ns()
        return self.path

    def _current_mtime_ns(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def _load_items(self) -> dict[str, LearnedCorrection] | None:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        corrections = raw.get("corrections", raw if isinstance(raw, dict) else {})
        if not isinstance(corrections, dict):
            return None

        loaded: dict[str, LearnedCorrection] = {}
        for key, value in corrections.items():
            if not isinstance(value, dict):
                continue
            target_language = value.get("target_language")
            if target_language not in {"en", "ru"}:
                continue
            actual = str(value.get("actual") or key)
            replacement = str(value.get("replacement") or "")
            if not actual or not replacement:
                continue
            loaded[str(key)] = LearnedCorrection(
                actual=actual,
                replacement=replacement,
                target_language=target_language,
                count=max(1, int(value.get("count") or 1)),
                updated_at=float(value.get("updated_at") or 0),
            )
        return loaded

    def find(self, actual: str) -> LearnedCorrection | None:
        if not self.enabled:
            return None
        return self._items.get(learning_key(actual))

    def learn(self, actual: str, replacement: str, target_language: Language) -> LearnedCorrection | None:
        if not self.enabled:
            return None
        actual = actual.strip()
        replacement = replacement.strip()
        if not actual or not replacement or actual == replacement:
            return None
        if normalize_word(actual) == normalize_word(replacement):
            return None

        key = learning_key(actual)
        existing = self._items.get(key)
        now = time.time()
        if existing:
            existing.replacement = replacement
            existing.target_language = target_language
            existing.count += 1
            existing.updated_at = now
            learned = existing
        else:
            learned = LearnedCorrection(
                actual=actual,
                replacement=replacement,
                target_language=target_language,
                count=1,
                updated_at=now,
            )
            self._items[key] = learned
        self.save()
        return learned

    def save(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "version": 1,
            "corrections": {
                key: {
                    "actual": item.actual,
                    "replacement": item.replacement,
                    "target_language": item.target_language,
                    "count": item.count,
                    "updated_at": item.updated_at,
                }
                for key, item in sorted(self._items.items())
            },
        }
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp_path.replace(self.path)
        self._last_mtime_ns = self._current_mtime_ns()

    def replace_all(self, items: list[LearnedCorrection]) -> None:
        if not self.enabled:
            return
        replaced: dict[str, LearnedCorrection] = {}
        for item in items:
            actual = item.actual.strip()
            replacement = item.replacement.strip()
            if not actual or not replacement:
                continue
            if item.target_language not in {"en", "ru"}:
                continue
            key = learning_key(actual)
            replaced[key] = LearnedCorrection(
                actual=actual,
                replacement=replacement,
                target_language=item.target_language,
                count=max(1, int(item.count)),
                updated_at=float(item.updated_at),
            )
        self._items = replaced
        self.save()
