from __future__ import annotations

from dataclasses import dataclass, fields
import json
from pathlib import Path
import sys
from typing import Any


@dataclass(slots=True)
class AppConfig:
    auto_correct: bool = True
    dry_run: bool = False
    min_word_chars: int = 3
    score_margin: float = 2.8
    strong_score_margin: float = 5.5
    min_alternate_score: float = 5.0
    context_weight: float = 1.1
    max_token_chars: int = 64
    log_level: str = "INFO"
    tray_icon: bool = True
    switch_hint: bool = True
    hint_duration_ms: int = 950
    hint_opacity: int = 218
    fix_capitalized_common_words: bool = True
    delete_switch_enabled: bool = True
    learning_enabled: bool = True
    learning_path: str = "learning.local.json"
    typo_exceptions_path: str = "exceptions.local.json"
    fix_layout_punctuation: bool = True
    fix_transposed_letters: bool = True
    fix_repeated_consonants: bool = True


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_runtime_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
    value = Path(path).expanduser()
    if value.is_absolute():
        return value
    anchor = Path(base_dir).expanduser() if base_dir is not None else application_dir()
    return (anchor / value).resolve()


def load_config(path: str | Path | None) -> AppConfig:
    config = AppConfig()
    base_dir = application_dir()
    if path is not None:
        config_path = Path(path).expanduser()
        base_dir = config_path.parent
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as handle:
                data: dict[str, Any] = json.load(handle)

            known_fields = {field.name for field in fields(AppConfig)}
            for key, value in data.items():
                if key in known_fields:
                    setattr(config, key, value)
    config.learning_path = str(resolve_runtime_path(config.learning_path, base_dir))
    config.typo_exceptions_path = str(resolve_runtime_path(config.typo_exceptions_path, base_dir))
    return config
