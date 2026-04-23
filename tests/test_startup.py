import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from keyswitcher import startup


class StartupTests(unittest.TestCase):
    def test_build_startup_command_for_source_uses_pythonw_and_absolute_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            python = tmp_path / "python.exe"
            pythonw = tmp_path / "pythonw.exe"
            config_path = tmp_path / "config.local.json"
            entrypoint = tmp_path / "keyswitcher" / "__main__.py"
            python.write_text("", encoding="utf-8")
            pythonw.write_text("", encoding="utf-8")
            config_path.write_text("{}", encoding="utf-8")
            entrypoint.parent.mkdir(parents=True, exist_ok=True)
            entrypoint.write_text("", encoding="utf-8")

            with (
                patch("keyswitcher.startup.application_dir", return_value=tmp_path),
                patch("keyswitcher.startup.sys.executable", str(python)),
                patch.object(startup.sys, "frozen", False, create=True),
            ):
                command = startup.build_startup_command(config_path)

            self.assertIn(str(pythonw), command)
            self.assertIn(str(entrypoint.resolve()), command)
            self.assertIn(str(config_path), command)

    def test_build_startup_command_for_frozen_app_uses_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exe_path = Path(tmp) / "KeySwitcher.exe"
            exe_path.write_text("", encoding="utf-8")

            with patch.object(startup.sys, "frozen", True, create=True), patch(
                "keyswitcher.startup.sys.executable",
                str(exe_path),
            ):
                command = startup.build_startup_command()

            self.assertEqual(command, str(exe_path))

    def test_enable_startup_writes_registry_value(self) -> None:
        registry_key = MagicMock()
        registry_key.__enter__.return_value = registry_key
        registry_key.__exit__.return_value = None
        fake_winreg = MagicMock()
        fake_winreg.HKEY_CURRENT_USER = object()
        fake_winreg.REG_SZ = 1
        fake_winreg.CreateKey.return_value = registry_key

        with (
            patch("keyswitcher.startup.winreg", fake_winreg),
            patch("keyswitcher.startup.sys.platform", "win32"),
            patch("keyswitcher.startup.build_startup_command", return_value="command"),
        ):
            startup.enable_startup()

        fake_winreg.CreateKey.assert_called_once_with(fake_winreg.HKEY_CURRENT_USER, startup.RUN_KEY_PATH)
        fake_winreg.SetValueEx.assert_called_once_with(
            registry_key,
            startup.RUN_VALUE_NAME,
            0,
            fake_winreg.REG_SZ,
            "command",
        )


if __name__ == "__main__":
    unittest.main()
