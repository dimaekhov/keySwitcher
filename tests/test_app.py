import logging
import unittest
from unittest.mock import patch

from keyswitcher.app import KeySwitcherApp, TypedToken, UiLogHandler, build_rules_editor_command, main
from keyswitcher.config import AppConfig
from keyswitcher.language import (
    ContextAwareDetector,
    SentenceContext,
    convert_layout_text,
    convert_layout_text_preserving_punctuation,
)
from keyswitcher.ui import _clamp_overlay_position, _debug_log_style
from keyswitcher.winapi import ClipboardSelection, KeyboardEvent, VK_DELETE, VK_RETURN, WM_KEYDOWN


class _FakeLayouts:
    def foreground_language(self):
        return "en"


class _RecordingLayouts(_FakeLayouts):
    def __init__(self) -> None:
        self.switched = []

    def switch_foreground_layout(self, language):
        self.switched.append(language)


class _RecordingUi:
    def __init__(self) -> None:
        self.hints = []
        self.debug_log_lines = []
        self.debug_log_state = False

    def show_switch_hint(self, language, detail):
        self.hints.append((language, detail))

    def append_debug_log(self, line):
        self.debug_log_lines.append(line)

    def debug_log_visible(self):
        return self.debug_log_state

    def set_debug_log_visible(self, visible):
        self.debug_log_state = visible


class _NoLearning:
    def find(self, actual):
        return None


class _RecordingLearning(_NoLearning):
    def __init__(self) -> None:
        self.learned = []

    def learn(self, actual, replacement, target_language):
        self.learned.append((actual, replacement, target_language))
        return object()


class _EnsureFileLearning:
    def __init__(self, path) -> None:
        self.path = path

    def ensure_file(self):
        return self.path


class _EnsureFileExceptions:
    def __init__(self, path) -> None:
        self.path = path

    def ensure_file(self):
        return self.path

    def reload(self):
        return 2

    def reload_if_changed(self):
        return None

    def snapshot(self):
        class _Snapshot:
            words = set()
            suffixes = ()

        return _Snapshot()


class _PollingLearning:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def reload_if_changed(self):
        self.calls += 1
        return self.result


class KeySwitcherAppRoutingTests(unittest.TestCase):
    def test_build_rules_editor_command_uses_module_entrypoint(self) -> None:
        with patch("keyswitcher.app.sys.executable", "C:\\Python\\python.exe", create=True):
            command = build_rules_editor_command(None)

        self.assertEqual(command, ["C:\\Python\\python.exe", "-m", "keyswitcher", "--edit-rules"])

    def test_edit_rules_launches_builtin_editor_process(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.learning = _EnsureFileLearning("D:\\tmp\\learning.local.json")
        app.typo_exceptions = _EnsureFileExceptions("D:\\tmp\\exceptions.local.json")
        app.config_path = None
        app.current_language = "en"
        app.ui = _RecordingUi()

        with patch("keyswitcher.app.subprocess.Popen") as popen:
            KeySwitcherApp.edit_rules(app)

        popen.assert_called_once()
        command = popen.call_args.args[0]
        self.assertEqual(command[-1], "--edit-rules")
        self.assertEqual(app.ui.hints, [("en", "rules")])

    def test_main_routes_edit_rules_flag_to_editor(self) -> None:
        with patch("keyswitcher.app.open_rules_editor", return_value=7) as open_editor:
            exit_code = main(["--edit-rules"])

        self.assertEqual(exit_code, 7)
        open_editor.assert_called_once()
        self.assertEqual(len(open_editor.call_args.args), 2)

    def test_toggle_debug_log_updates_ui_state(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.ui = _RecordingUi()

        enabled = KeySwitcherApp.toggle_debug_log(app)
        disabled = KeySwitcherApp.toggle_debug_log(app)

        self.assertTrue(enabled)
        self.assertFalse(disabled)

    def test_ui_log_handler_forwards_formatted_records(self) -> None:
        messages = []
        handler = UiLogHandler(messages.append)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))

        record = logging.LogRecord("keyswitcher", logging.INFO, __file__, 10, "hello", (), None)
        handler.emit(record)

        self.assertEqual(messages, ["INFO hello"])

    def test_debug_log_style_assigns_badges(self) -> None:
        self.assertEqual(_debug_log_style("13:00:00 I Correcting 'a' -> 'b'").badge, "OK")
        self.assertEqual(_debug_log_style("13:00:00 I Skipped auto-correct for 'a'").badge, "SKIP")
        self.assertEqual(_debug_log_style("13:00:00 E Failed to apply correction").badge, "ERR")
        self.assertEqual(_debug_log_style("13:00:00 I Debug log overlay enabled.").badge, "INFO")

    def test_overlay_position_clamps_to_screen(self) -> None:
        with (
            patch("keyswitcher.ui.user32.GetSystemMetrics", side_effect=[800, 600]),
        ):
            position = _clamp_overlay_position(700, 500, 200, 150)

        self.assertEqual(position, (600, 450))

    def test_poll_learning_reload_reloads_at_most_once_per_interval(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.learning = _PollingLearning(3)
        app.typo_exceptions = _EnsureFileExceptions("D:\\tmp\\exceptions.local.json")
        app._next_learning_poll_at = 0.0

        with patch("keyswitcher.app.time.monotonic", side_effect=[10.0, 10.2, 11.3]):
            KeySwitcherApp.poll_learning_reload(app)
            KeySwitcherApp.poll_learning_reload(app)
            KeySwitcherApp.poll_learning_reload(app)

        self.assertEqual(app.learning.calls, 2)

    def test_enter_commits_without_correction_even_if_translated_as_character(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.enabled = True
        app.config = AppConfig()
        app.layouts = _FakeLayouts()

        commit_calls = []
        finish_calls = []

        app._update_status = lambda language: None
        app._commit_token_without_correction = lambda delimiter: commit_calls.append(delimiter)
        app._char_for = lambda event, language: "\r"
        app._punctuation_replacement = lambda actual, alternate, actual_language: None
        app._clear_punctuation_fix_if_break = lambda actual: None
        app._should_add_to_token = lambda actual, alternate, actual_language: False
        app._finish_token = lambda delimiter: finish_calls.append(delimiter) or False

        handled = KeySwitcherApp.handle_event(
            app,
            KeyboardEvent(vk_code=VK_RETURN, scan_code=28, flags=0, message=WM_KEYDOWN),
        )

        self.assertFalse(handled)
        self.assertEqual(commit_calls, ["\n"])
        self.assertEqual(finish_calls, [])

    def test_shift_delete_routes_to_selected_text_switch(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.enabled = True
        app.config = AppConfig()
        app.layouts = _FakeLayouts()

        selected_calls = []
        delete_calls = []

        app._update_status = lambda language: None
        app._handle_selected_text_switch = lambda language: selected_calls.append(language) or True
        app._handle_delete_switch = lambda language: delete_calls.append(language) or True

        with patch("keyswitcher.app.is_shift_down", return_value=True):
            handled = KeySwitcherApp.handle_event(
                app,
                KeyboardEvent(vk_code=VK_DELETE, scan_code=83, flags=0, message=WM_KEYDOWN),
            )

        self.assertTrue(handled)
        self.assertEqual(selected_calls, ["en"])
        self.assertEqual(delete_calls, [])

    def test_selected_text_switch_converts_selection_and_restores_clipboard(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.config = AppConfig()
        app.layouts = _RecordingLayouts()
        app.learning = _RecordingLearning()
        app.ui = _RecordingUi()
        app.token = TypedToken()
        app.context = SentenceContext()
        app.last_committed = object()
        app.last_punctuation_fix = object()

        status_updates = []
        sent_text = []
        restored_clipboard = []
        replacement = convert_layout_text("ghbdtn", "ru") + "."

        app._update_status = lambda language: status_updates.append(language)

        with (
            patch(
                "keyswitcher.app.copy_selected_text",
                return_value=ClipboardSelection("ghbdtn.", "previous clipboard"),
            ),
            patch("keyswitcher.app.send_text", side_effect=sent_text.append),
            patch("keyswitcher.app.restore_clipboard_text", side_effect=restored_clipboard.append),
        ):
            handled = KeySwitcherApp._handle_selected_text_switch(app, "en")

        self.assertTrue(handled)
        self.assertEqual(sent_text, [replacement])
        self.assertEqual(app.layouts.switched, ["ru"])
        self.assertEqual(status_updates, ["ru"])
        self.assertEqual(app.ui.hints, [("ru", replacement)])
        self.assertEqual(restored_clipboard, ["previous clipboard"])
        self.assertIsNone(app.last_committed)
        self.assertIsNone(app.last_punctuation_fix)
        self.assertEqual(app.learning.learned, [("ghbdtn", convert_layout_text("ghbdtn", "ru"), "ru")])

    def test_learn_selected_text_switch_saves_each_word_pair(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.learning = _RecordingLearning()

        KeySwitcherApp._learn_selected_text_switch(
            app,
            "ghbdtn, vbh!",
            convert_layout_text_preserving_punctuation("ghbdtn, vbh!", "ru"),
            "ru",
        )

        self.assertEqual(
            app.learning.learned,
            [
                ("ghbdtn", "привет", "ru"),
                ("vbh", "мир", "ru"),
            ],
        )

    def test_commit_without_correction_uses_resolved_context_for_short_token(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.config = AppConfig()
        app.detector = ContextAwareDetector(app.config)
        app.context = SentenceContext()
        app.layouts = _FakeLayouts()
        app.token = TypedToken(
            actual_language="en",
            actual_chars=list("ns"),
            alternate_chars=list(convert_layout_text("ns", "ru")),
        )
        app.last_committed = None

        KeySwitcherApp._commit_token_without_correction(app, " ")

        self.assertEqual(app.context.recent, [(convert_layout_text("ns", "ru"), "ru")])
        self.assertIsNotNone(app.last_committed)
        self.assertEqual(app.last_committed.text, "ns")

    def test_finish_token_fixes_adjacent_transposed_letters(self) -> None:
        app = object.__new__(KeySwitcherApp)
        app.config = AppConfig()
        app.detector = ContextAwareDetector(app.config)
        app.context = SentenceContext()
        app.layouts = _RecordingLayouts()
        app.ui = _RecordingUi()
        app.token = TypedToken(
            actual_language="en",
            actual_chars=list("hlelo"),
            alternate_chars=list(convert_layout_text("hlelo", "ru")),
        )
        app.learning = _NoLearning()
        app.last_committed = None
        app.last_punctuation_fix = None

        status_updates = []
        backspaces = []
        sent_text = []
        app._update_status = lambda language: status_updates.append(language)

        with (
            patch("keyswitcher.app.send_backspaces", side_effect=backspaces.append),
            patch("keyswitcher.app.send_text", side_effect=sent_text.append),
        ):
            handled = KeySwitcherApp._finish_token(app, " ")

        self.assertTrue(handled)
        self.assertEqual(backspaces, [5])
        self.assertEqual(sent_text, ["hello "])
        self.assertEqual(status_updates, ["en"])
        self.assertEqual(app.layouts.switched, [])
        self.assertEqual(app.ui.hints, [("en", "hello")])
        self.assertIsNotNone(app.last_committed)
        self.assertEqual(app.last_committed.text, "hello")


if __name__ == "__main__":
    unittest.main()
