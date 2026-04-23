from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import subprocess
import sys
import time

from .config import AppConfig, application_dir, load_config, resolve_runtime_path
from .exceptions import TypoExceptionStore
from .learning import LearnedCorrection, LearningStore
from .language import (
    ContextAwareDetector,
    DetectionResult,
    InLayoutCorrection,
    Language,
    SentenceContext,
    convert_layout_text,
    convert_layout_text_preserving_punctuation,
    infer_language,
    layout_punctuation_replacement,
    normalize_word,
    opposite_language,
    resolve_context_entry,
    should_lowercase_common_word,
    update_context_from_delimiter,
)
from .rules_editor import open_rules_editor
from .startup import disable_startup, enable_startup, is_startup_enabled
from .winapi import (
    KeyboardEvent,
    KeyboardHook,
    KeyboardTranslator,
    LayoutManager,
    VK_BACK,
    VK_DELETE,
    VK_RETURN,
    VK_SPACE,
    VK_TAB,
    copy_selected_text,
    ensure_windows,
    is_navigation_key,
    is_shift_down,
    restore_clipboard_text,
    send_backspaces,
    send_text,
)
from .ui import KeySwitcherUI

LOGGER = logging.getLogger("keyswitcher")

SENTENCE_DELIMITERS = set(".!?")
WORD_BREAKERS = set(" \t\r\n,;:)]}\"")
TOKEN_JOINERS = {"'", "-"}


def build_rules_editor_command(config_path: Path | None) -> list[str]:
    if getattr(sys, "frozen", False):
        command = [str(Path(sys.executable).resolve()), "--edit-rules"]
    else:
        command = [sys.executable, "-m", "keyswitcher", "--edit-rules"]
    if config_path is not None:
        command.extend(["--config", str(config_path)])
    return command


class UiLogHandler(logging.Handler):
    def __init__(self, sink: Callable[[str], None]) -> None:
        super().__init__(level=logging.INFO)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            self.handleError(record)
            return
        self._sink(message)


@dataclass(slots=True)
class TypedToken:
    actual_language: Language | None = None
    actual_chars: list[str] = field(default_factory=list)
    alternate_chars: list[str] = field(default_factory=list)

    @property
    def actual(self) -> str:
        return "".join(self.actual_chars)

    @property
    def alternate(self) -> str:
        return "".join(self.alternate_chars)

    def __len__(self) -> int:
        return len(self.actual_chars)

    def clear(self) -> None:
        self.actual_language = None
        self.actual_chars.clear()
        self.alternate_chars.clear()

    def pop(self) -> None:
        if self.actual_chars:
            self.actual_chars.pop()
        if self.alternate_chars:
            self.alternate_chars.pop()
        if not self.actual_chars:
            self.actual_language = None

    def add(self, actual: str, alternate: str, actual_language: Language) -> None:
        if self.actual_language is None:
            self.actual_language = actual_language
        self.actual_chars.append(actual)
        self.alternate_chars.append(alternate)


@dataclass(slots=True)
class LastCommittedToken:
    text: str
    alternate: str
    language: Language
    delimiter: str


@dataclass(slots=True)
class LastPunctuationFix:
    actual: str
    replacement: str
    target_language: Language


class KeySwitcherApp:
    def __init__(self, config: AppConfig, config_path: Path | None = None) -> None:
        ensure_windows()
        self.config = config
        self.config_path = config_path
        self.context = SentenceContext()
        self.detector = ContextAwareDetector(config)
        self.layouts = LayoutManager()
        self.translator = KeyboardTranslator(self.layouts)
        self.token = TypedToken()
        self.last_committed: LastCommittedToken | None = None
        self.last_punctuation_fix: LastPunctuationFix | None = None
        self.learning = LearningStore(config.learning_path, config.learning_enabled)
        self.typo_exceptions = TypoExceptionStore(config.typo_exceptions_path, enabled=True)
        self.hook = KeyboardHook(self.handle_event)
        self.enabled = True
        self.current_language = self.layouts.foreground_language()
        self.ui = KeySwitcherUI(
            config,
            self.current_language,
            self.toggle_enabled,
            self.toggle_startup,
            self.startup_enabled,
            self.request_exit,
            self.edit_rules,
            self.reload_rules,
            self.toggle_debug_log,
            self.poll_learning_reload,
        )
        self._next_learning_poll_at = 0.0
        self._debug_log_handler = UiLogHandler(self.ui.append_debug_log)
        self._debug_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname).1s %(message)s", "%H:%M:%S"))
        logging.getLogger("keyswitcher").addHandler(self._debug_log_handler)

    def run(self) -> None:
        self.ui.show()
        self.hook.install()
        LOGGER.info("KeySwitcher запущен. Нажмите Ctrl+C в этой консоли, чтобы остановить программу.")
        try:
            self.hook.run_message_loop()
        finally:
            self.hook.uninstall()
            logging.getLogger("keyswitcher").removeHandler(self._debug_log_handler)
            self.ui.close()

    def stop(self) -> None:
        self.hook.stop()

    def request_exit(self) -> None:
        LOGGER.info("Получен запрос на выход из меню в трее.")
        self.stop()

    def toggle_enabled(self) -> None:
        self.enabled = not self.enabled
        self.token.clear()
        self._update_status(self.layouts.foreground_language())
        LOGGER.info("KeySwitcher %s.", "включён" if self.enabled else "на паузе")
        self.ui.show_state_hint(self.enabled)

    def startup_enabled(self) -> bool:
        try:
            return is_startup_enabled()
        except OSError:
            LOGGER.exception("Не удалось получить состояние автозапуска Windows")
            return False

    def toggle_startup(self) -> None:
        try:
            if self.startup_enabled():
                disable_startup()
                enabled = False
            else:
                enable_startup(self.config_path)
                enabled = True
        except OSError:
            LOGGER.exception("Не удалось изменить автозапуск Windows")
            self.ui.show_switch_hint(self.current_language, "startup error")
            return
        LOGGER.info("Автозапуск Windows %s.", "включён" if enabled else "выключен")
        self.ui.show_switch_hint(self.current_language, "startup on" if enabled else "startup off")

    def edit_rules(self) -> None:
        path = self.learning.ensure_file()
        exceptions_path = self.typo_exceptions.ensure_file()
        LOGGER.info("Открывается редактор правил: %s, исключения: %s", path, exceptions_path)
        subprocess.Popen(build_rules_editor_command(self.config_path), cwd=str(application_dir()))
        self.ui.show_switch_hint(self.current_language, "rules")

    def reload_rules(self) -> None:
        count = self.learning.reload()
        exception_count = self.typo_exceptions.reload()
        LOGGER.info("Перезагружено %s выученных правил и %s правил-исключений.", count, exception_count)
        self.ui.show_switch_hint(self.current_language, f"{count + exception_count} rules")

    def toggle_debug_log(self) -> bool:
        visible = not self.ui.debug_log_visible()
        self.ui.set_debug_log_visible(visible)
        LOGGER.info("Панель журнала отладки %s.", "включена" if visible else "выключена")
        return visible

    def poll_learning_reload(self) -> None:
        now = time.monotonic()
        if now < self._next_learning_poll_at:
            return
        self._next_learning_poll_at = now + 1.0
        count = self.learning.reload_if_changed()
        exception_count = self.typo_exceptions.reload_if_changed()
        if count is None and exception_count is None:
            return
        if count is not None:
            LOGGER.info("Автоматически перезагружено %s выученных правил.", count)
        if exception_count is not None:
            LOGGER.info("Автоматически перезагружено %s правил-исключений.", exception_count)

    def handle_event(self, event: KeyboardEvent) -> bool:
        if not event.is_key_down:
            return False

        actual_language = self.layouts.foreground_language()
        self._update_status(actual_language)
        if not self.enabled:
            self.token.clear()
            return False

        if event.vk_code == VK_DELETE and self.config.delete_switch_enabled:
            if is_shift_down():
                return self._handle_selected_text_switch(actual_language)
            return self._handle_delete_switch(actual_language)

        if event.vk_code == VK_BACK:
            self.token.pop()
            self.last_committed = None
            self.last_punctuation_fix = None
            return False

        if is_navigation_key(event.vk_code):
            self.token.clear()
            self.last_committed = None
            self.last_punctuation_fix = None
            return False

        if event.vk_code in {VK_RETURN, VK_TAB}:
            self._commit_token_without_correction(self._delimiter_for_vk(event.vk_code))
            return False

        alternate_language = opposite_language(actual_language)
        actual_char = self._char_for(event, actual_language)
        alternate_char = self._char_for(event, alternate_language)

        if not actual_char:
            if event.vk_code == VK_SPACE:
                delimiter = self._delimiter_for_vk(event.vk_code)
                return self._finish_token(delimiter)
            return False

        punctuation = self._punctuation_replacement(actual_char, alternate_char, actual_language)
        if punctuation:
            return self._apply_punctuation_replacement(actual_char, *punctuation)
        self._clear_punctuation_fix_if_break(actual_char)

        if self._should_add_to_token(actual_char, alternate_char, actual_language):
            if self.token.actual_language not in {None, actual_language}:
                self.token.clear()
            if len(self.token) == 0:
                self.last_committed = None
            self.token.add(actual_char, alternate_char, actual_language)
            if len(self.token) > self.config.max_token_chars:
                self.token.clear()
            return False

        return self._finish_token(actual_char)

    def _char_for(self, event: KeyboardEvent, language: Language) -> str:
        text = self.translator.char_for_event(event, language)
        if len(text) > 1:
            return text[0]
        return text

    def _delimiter_for_vk(self, vk_code: int) -> str:
        if vk_code == VK_RETURN:
            return "\n"
        if vk_code == VK_TAB:
            return "\t"
        return " "

    def _should_add_to_token(self, actual: str, alternate: str, actual_language: Language) -> bool:
        if actual.isalpha() or actual.isdigit():
            return True
        if actual in TOKEN_JOINERS and len(self.token) > 0:
            return True
        if not alternate.isalpha() or actual.isspace():
            return False
        if len(self.token) == 0:
            return actual not in SENTENCE_DELIMITERS
        if actual in SENTENCE_DELIMITERS and len(self.token) >= self.config.min_word_chars:
            probe = self.detector.detect(
                self.token.actual,
                self.token.alternate,
                actual_language,
                self.context,
            )
            if probe.actual.score >= probe.alternate.score + 1.0:
                return False
            if probe.alternate.score >= probe.actual.score + 1.0:
                return True
            return False
        if actual in WORD_BREAKERS and len(self.token) >= self.config.min_word_chars:
            probe = self.detector.detect(
                self.token.actual,
                self.token.alternate,
                actual_language,
                self.context,
            )
            if probe.actual.score >= probe.alternate.score + 1.0:
                return False
        return True

    def _finish_token(self, delimiter: str) -> bool:
        if len(self.token) == 0:
            self.last_committed = None
            update_context_from_delimiter(self.context, delimiter)
            return False

        actual_language = self.token.actual_language or self.layouts.foreground_language()
        learned = self.learning.find(self.token.actual)
        if learned:
            return self._apply_learned_correction(learned, actual_language, delimiter)

        detection = self.detector.detect(
            self.token.actual,
            self.token.alternate,
            actual_language,
            self.context,
        )

        if detection.should_correct:
            self._log_detection(detection)
            if self.config.dry_run or not self.config.auto_correct:
                self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
                update_context_from_delimiter(self.context, delimiter)
                self.token.clear()
                return False

            try:
                self._apply_correction(detection, delimiter)
            except OSError:
                LOGGER.exception("Не удалось применить исправление, исходный ввод сохранён")
                self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
                update_context_from_delimiter(self.context, delimiter)
                self.token.clear()
                return False
            self.context.add_word(detection.replacement, detection.target_language)
            self.last_committed = None
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return True

        committed_language = infer_language(self.token.actual, actual_language)
        transposition = self.detector.detect_transposed_letters(
            self.token.actual,
            committed_language,
            self.context,
        )
        if transposition:
            return self._apply_in_layout_correction(transposition, committed_language, delimiter)
        repeated_consonants = self.detector.detect_repeated_consonants(
            self.token.actual,
            committed_language,
            self.context,
            self.typo_exceptions.snapshot().words,
            self.typo_exceptions.snapshot().suffixes,
        )
        if repeated_consonants:
            return self._apply_in_layout_correction(repeated_consonants, committed_language, delimiter)

        case_replacement = self._case_replacement(self.token.actual, committed_language)
        if case_replacement:
            if self.config.dry_run or not self.config.auto_correct:
                LOGGER.info("Была бы выполнена нормализация регистра %r -> %r", self.token.actual, case_replacement)
                self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
                update_context_from_delimiter(self.context, delimiter)
                self.token.clear()
                return False
            try:
                self._apply_text_replacement(self.token.actual, case_replacement, delimiter)
            except OSError:
                LOGGER.exception("Не удалось нормализовать регистр, исходный ввод сохранён")
                self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
                update_context_from_delimiter(self.context, delimiter)
                self.token.clear()
                return False
            self.context.add_word(case_replacement, committed_language)
            corrected_alternate = convert_layout_text(case_replacement, opposite_language(committed_language))
            self._remember_committed(case_replacement, corrected_alternate, committed_language, delimiter)
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return True

        self._log_rejected_detection(detection)
        self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
        self._remember_committed(self.token.actual, self.token.alternate, committed_language, delimiter)
        update_context_from_delimiter(self.context, delimiter)
        self.token.clear()
        return False

    def _apply_learned_correction(
        self,
        learned: LearnedCorrection,
        actual_language: Language,
        delimiter: str,
    ) -> bool:
        LOGGER.info(
            "Применяется выученное исправление %r -> %r (%s)",
            self.token.actual,
            learned.replacement,
            learned.target_language,
        )
        if self.config.dry_run or not self.config.auto_correct:
            self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return False
        try:
            self._apply_text_replacement(self.token.actual, learned.replacement, delimiter)
            self.layouts.switch_foreground_layout(learned.target_language)
            self._update_status(learned.target_language)
            self.ui.show_switch_hint(learned.target_language, learned.replacement)
        except OSError:
            LOGGER.exception("Не удалось применить выученное исправление, исходный ввод сохранён")
            self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return False
        self.context.add_word(learned.replacement, learned.target_language)
        self.last_committed = None
        update_context_from_delimiter(self.context, delimiter)
        self.token.clear()
        return True

    def _commit_token_without_correction(self, delimiter: str) -> None:
        if len(self.token) > 0:
            actual_language = self.token.actual_language or self.layouts.foreground_language()
            committed_language = infer_language(self.token.actual, actual_language)
            self._add_token_to_context(self.token.actual, self.token.alternate, actual_language)
            self._remember_committed(self.token.actual, self.token.alternate, committed_language, delimiter)
            self.token.clear()
        else:
            self.last_committed = None
        update_context_from_delimiter(self.context, delimiter)

    def _log_detection(self, detection: DetectionResult) -> None:
        LOGGER.info(
            "Исправление %r -> %r (%s, уверенность %.2f, %s)",
            detection.actual.text,
            detection.replacement,
            detection.target_language,
            detection.confidence,
            detection.reason,
        )

    def _log_rejected_detection(self, detection: DetectionResult) -> None:
        LOGGER.info(
            "Автоисправление пропущено для %r -> %r (%s, уверенность %.2f)",
            detection.actual.text,
            detection.replacement,
            detection.reason,
            detection.confidence,
        )

    def _apply_correction(self, detection: DetectionResult, delimiter: str) -> None:
        self._apply_text_replacement(detection.actual.text, detection.replacement, delimiter)
        self.layouts.switch_foreground_layout(detection.target_language)
        self._update_status(detection.target_language)
        self.ui.show_switch_hint(detection.target_language, detection.replacement)

    def _apply_in_layout_correction(
        self,
        correction: InLayoutCorrection,
        language: Language,
        delimiter: str,
    ) -> bool:
        LOGGER.info(
            "Исправление токена в той же раскладке %r -> %r (%s, уверенность %.2f)",
            self.token.actual,
            correction.replacement,
            correction.reason,
            correction.confidence,
        )
        if self.config.dry_run or not self.config.auto_correct:
            self._add_token_to_context(self.token.actual, self.token.alternate, language)
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return False
        try:
            self._apply_text_replacement(self.token.actual, correction.replacement, delimiter)
            self._update_status(language)
            self.ui.show_switch_hint(language, correction.replacement)
        except OSError:
            LOGGER.exception("Не удалось исправить токен в той же раскладке, исходный ввод сохранён")
            self._add_token_to_context(self.token.actual, self.token.alternate, language)
            update_context_from_delimiter(self.context, delimiter)
            self.token.clear()
            return False

        corrected_alternate = convert_layout_text(correction.replacement, opposite_language(language))
        self.context.add_word(correction.replacement, language)
        self._remember_committed(correction.replacement, corrected_alternate, language, delimiter)
        update_context_from_delimiter(self.context, delimiter)
        self.token.clear()
        return True

    def _apply_text_replacement(self, original: str, replacement: str, delimiter: str) -> None:
        send_backspaces(len(original))
        send_text(replacement + delimiter)

    def _punctuation_replacement(
        self,
        actual: str,
        alternate: str,
        actual_language: Language,
    ) -> tuple[str, Language] | None:
        if not self.config.fix_layout_punctuation:
            return None
        allow_repeat = (
            self.last_punctuation_fix is not None
            and self.last_punctuation_fix.actual == actual
        )
        return layout_punctuation_replacement(actual, alternate, actual_language, self.context, allow_repeat)

    def _apply_punctuation_replacement(
        self,
        actual: str,
        replacement: str,
        target_language: Language,
    ) -> bool:
        had_token = len(self.token) > 0
        if had_token and self._finish_token(replacement):
            self._remember_punctuation_fix(actual, replacement, target_language)
            return True

        if not had_token:
            self.last_committed = None
            update_context_from_delimiter(self.context, replacement)

        LOGGER.info("Исправление пунктуации раскладки -> %r (%s)", replacement, target_language)
        if self.config.dry_run or not self.config.auto_correct:
            return False

        try:
            send_text(replacement)
            self.layouts.switch_foreground_layout(target_language)
            self._update_status(target_language)
            self.ui.show_switch_hint(target_language, replacement)
        except OSError:
            LOGGER.exception("Не удалось применить исправление пунктуации")
            return False
        self._remember_punctuation_fix(actual, replacement, target_language)
        return True

    def _remember_punctuation_fix(
        self,
        actual: str,
        replacement: str,
        target_language: Language,
    ) -> None:
        self.last_punctuation_fix = LastPunctuationFix(actual, replacement, target_language)

    def _clear_punctuation_fix_if_break(self, actual: str) -> None:
        if not self.last_punctuation_fix:
            return
        if actual not in {self.last_punctuation_fix.actual, self.last_punctuation_fix.replacement}:
            self.last_punctuation_fix = None

    def _handle_delete_switch(self, actual_language: Language) -> bool:
        target_language = opposite_language(actual_language)
        if len(self.token) > 0:
            return self._manual_switch_current_token(actual_language, target_language)
        if self.last_committed:
            return self._manual_switch_last_token(target_language)
        self.layouts.switch_foreground_layout(target_language)
        self._update_status(target_language)
        self.ui.show_switch_hint(target_language, "layout")
        return True

    def _handle_selected_text_switch(self, actual_language: Language) -> bool:
        selection = copy_selected_text()
        if not selection:
            LOGGER.info("Нажат Shift+Del, но выделенный текст не был скопирован.")
            return True

        source_language = infer_language(selection.text, actual_language)
        target_language = opposite_language(source_language)
        replacement = convert_layout_text_preserving_punctuation(selection.text, target_language)
        if replacement == selection.text:
            LOGGER.info("Для выделенного текста Shift+Del нет преобразования раскладки: %r", selection.text)
            try:
                restore_clipboard_text(selection.previous_text)
            except OSError:
                LOGGER.exception("Не удалось восстановить текст буфера обмена")
            return True

        if self.config.dry_run or not self.config.auto_correct:
            LOGGER.info("Было бы выполнено переключение выделенного текста %r -> %r", selection.text, replacement)
            try:
                restore_clipboard_text(selection.previous_text)
            except OSError:
                LOGGER.exception("Не удалось восстановить текст буфера обмена")
            return True

        try:
            send_text(replacement)
            self.layouts.switch_foreground_layout(target_language)
            self._update_status(target_language)
            self.ui.show_switch_hint(target_language, replacement)
        except OSError:
            LOGGER.exception("Не удалось переключить выделенный текст")
            return True
        finally:
            try:
                restore_clipboard_text(selection.previous_text)
            except OSError:
                LOGGER.exception("Не удалось восстановить текст буфера обмена")

        self.token.clear()
        self.last_committed = None
        self.last_punctuation_fix = None
        self._learn_selected_text_switch(selection.text, replacement, target_language)
        self.context.add_word(replacement, target_language)
        LOGGER.info("Shift+Del переключил выделенный текст %r -> %r", selection.text, replacement)
        return True

    def _learn_selected_text_switch(
        self,
        original_text: str,
        replacement_text: str,
        target_language: Language,
    ) -> None:
        original_token: list[str] = []
        replacement_token: list[str] = []
        learned_pairs = 0

        for original_char, replacement_char in zip(original_text, replacement_text):
            if self._selection_token_char(original_char, replacement_char):
                original_token.append(original_char)
                replacement_token.append(replacement_char)
                continue
            learned_pairs += self._learn_selected_token_pair(
                "".join(original_token),
                "".join(replacement_token),
                target_language,
            )
            original_token.clear()
            replacement_token.clear()

        learned_pairs += self._learn_selected_token_pair(
            "".join(original_token),
            "".join(replacement_token),
            target_language,
        )
        if learned_pairs:
            LOGGER.info("Shift+Del выучил %s токен(ов) из выделенного текста.", learned_pairs)

    def _selection_token_char(self, original_char: str, replacement_char: str) -> bool:
        if (
            original_char.isalpha()
            or original_char.isdigit()
            or replacement_char.isalpha()
            or replacement_char.isdigit()
        ):
            return True
        return original_char in TOKEN_JOINERS or replacement_char in TOKEN_JOINERS

    def _learn_selected_token_pair(
        self,
        original: str,
        replacement: str,
        target_language: Language,
    ) -> int:
        if not original.strip() or not replacement.strip():
            return 0
        learned = self.learning.learn(original, replacement, target_language)
        return 1 if learned else 0

    def _manual_switch_current_token(self, actual_language: Language, target_language: Language) -> bool:
        replacement = self.token.alternate
        original = self.token.actual
        if not replacement or replacement == original:
            self.layouts.switch_foreground_layout(target_language)
            self._update_status(target_language)
            self.token.clear()
            return True
        if self.config.dry_run or not self.config.auto_correct:
            LOGGER.info("Было бы выполнено ручное переключение %r -> %r", original, replacement)
            self.token.clear()
            return True
        try:
            self._apply_text_replacement(original, replacement, "")
            self.layouts.switch_foreground_layout(target_language)
            self._update_status(target_language)
            self.ui.show_switch_hint(target_language, replacement)
        except OSError:
            LOGGER.exception("Не удалось вручную переключить текущий токен")
            return False
        self.learning.learn(original, replacement, target_language)
        self.context.add_word(replacement, target_language)
        self.last_committed = None
        self.token.clear()
        LOGGER.info("Ручное переключение выучило %r -> %r", original, replacement)
        return True

    def _manual_switch_last_token(self, target_language: Language) -> bool:
        item = self.last_committed
        if not item:
            return False
        replacement = item.alternate
        if not replacement or replacement == item.text:
            self.last_committed = None
            return True
        if self.config.dry_run or not self.config.auto_correct:
            LOGGER.info("Было бы выполнено ручное переключение предыдущего токена %r -> %r", item.text, replacement)
            self.last_committed = None
            return True
        try:
            send_backspaces(len(item.text) + len(item.delimiter))
            send_text(replacement + item.delimiter)
            self.layouts.switch_foreground_layout(target_language)
            self._update_status(target_language)
            self.ui.show_switch_hint(target_language, replacement)
        except OSError:
            LOGGER.exception("Не удалось вручную переключить предыдущий токен")
            return False
        self.learning.learn(item.text, replacement, target_language)
        self.context.replace_last_word(replacement, target_language)
        self.last_committed = None
        LOGGER.info("Ручное переключение выучило %r -> %r", item.text, replacement)
        return True

    def _remember_committed(self, text: str, alternate: str, language: Language, delimiter: str) -> None:
        if any(char in "\n\r\t" for char in delimiter):
            self.last_committed = None
            return
        self.last_committed = LastCommittedToken(text, alternate, language, delimiter)

    def _add_token_to_context(self, actual_text: str, alternate_text: str, actual_language: Language) -> None:
        entry = resolve_context_entry(
            actual_text,
            alternate_text,
            actual_language,
            self.detector,
            self.context,
        )
        if entry is None:
            return
        text, language = entry
        self.context.add_word(text, language)

    def _case_replacement(self, text: str, language: Language) -> str | None:
        if not self.config.fix_capitalized_common_words:
            return None
        if should_lowercase_common_word(text, language, self.context):
            return text[0].lower() + text[1:]
        return None

    def _update_status(self, language: Language) -> None:
        self.current_language = language
        self.ui.set_status(language, self.enabled)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="keyswitcher",
        description="Контекстный автопереключатель раскладки RU/EN для Windows.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Путь к JSON-конфигу. По умолчанию используется config.local.json, если он существует.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Только писать исправления в лог, не вводя их.")
    parser.add_argument("--verbose", action="store_true", help="Включить подробный журнал отладки.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Запустить несколько примеров детектора и завершить работу.",
    )
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="Добавить KeySwitcher в автозапуск Windows для текущего пользователя и завершить работу.",
    )
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Убрать KeySwitcher из автозапуска Windows для текущего пользователя и завершить работу.",
    )
    parser.add_argument(
        "--edit-rules",
        action="store_true",
        help="Открыть встроенный редактор правил и завершить работу.",
    )
    return parser


def configure_logging(config: AppConfig, verbose: bool) -> None:
    level_name = "DEBUG" if verbose else config.log_level.upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run_self_test(config: AppConfig) -> int:
    detector = ContextAwareDetector(config)
    context = SentenceContext()
    samples = [
        ("ghbdtn", convert_layout_text("ghbdtn", "ru"), "en"),
        ("руддщ", convert_layout_text("руддщ", "en"), "ru"),
        ("hello", convert_layout_text("hello", "ru"), "en"),
        ("[jhjij", convert_layout_text("[jhjij", "ru"), "en"),
    ]
    for actual, alternate, language in samples:
        result = detector.detect(actual, alternate, language, context)
        print(
            f"{actual!r} vs {alternate!r}: "
            f"correct={result.should_correct}, target={result.target_language}, "
            f"confidence={result.confidence:.2f}, {result.reason}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = (
        resolve_runtime_path("config.local.json", application_dir())
        if args.config is None
        else Path(args.config).expanduser().resolve()
    )
    effective_config_path = config_path if config_path.exists() else None
    config = load_config(effective_config_path)
    if args.dry_run:
        config.dry_run = True
    configure_logging(config, args.verbose)

    if args.self_test:
        return run_self_test(config)

    if args.edit_rules:
        return open_rules_editor(config.learning_path, config.typo_exceptions_path)

    if sys.platform != "win32":
        LOGGER.error("KeySwitcher работает только в Windows.")
        return 2

    if args.install_startup:
        command = enable_startup(effective_config_path)
        LOGGER.info("Автозапуск Windows включён: %s", command)
        return 0

    if args.uninstall_startup:
        removed = disable_startup()
        LOGGER.info("Автозапуск Windows %s.", "выключен" if removed else "уже был выключен")
        return 0

    app = KeySwitcherApp(config, effective_config_path)
    try:
        app.run()
    except KeyboardInterrupt:
        LOGGER.info("Остановка KeySwitcher.")
        app.stop()
    return 0
