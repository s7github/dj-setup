import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import launcher


class LauncherSettingsTests(unittest.TestCase):
    def test_load_and_save_settings_under_appdata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(os.environ, {"APPDATA": temporary_directory}):
                initial = launcher.load_settings()
                initial["download_root"] = str(Path(temporary_directory) / "Music")
                saved_path = launcher.save_settings(initial)
                loaded = launcher.load_settings()

            self.assertEqual(
                saved_path,
                Path(temporary_directory) / "DJ Setup" / "settings.json",
            )
            self.assertEqual(loaded, initial)

    def test_load_settings_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings_path = Path(temporary_directory) / "DJ Setup" / "settings.json"
            settings_path.parent.mkdir()
            settings_path.write_text("{invalid", encoding="utf-8")
            with patch.dict(os.environ, {"APPDATA": temporary_directory}):
                with self.assertRaisesRegex(RuntimeError, "Could not read DJ Setup settings"):
                    launcher.load_settings()


if __name__ == "__main__":
    unittest.main()
