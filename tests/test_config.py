import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from keyswitcher.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_resolves_learning_path_relative_to_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.local.json"
            config_path.write_text(
                json.dumps({"learning_path": "data/learning.json"}),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(
                Path(config.learning_path),
                (config_path.parent / "data" / "learning.json").resolve(),
            )

    def test_load_config_without_file_uses_application_directory_for_learning_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("keyswitcher.config.application_dir", return_value=Path(tmp)):
                config = load_config(None)

            self.assertEqual(
                Path(config.learning_path),
                (Path(tmp) / "learning.local.json").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
