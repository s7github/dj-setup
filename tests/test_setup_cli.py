import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from providers.spotify import setup


class ZotifyConfigCliTests(unittest.TestCase):
    def test_explicit_root_path_updates_config_without_prompting(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            config_path = temporary_root / "Zotify" / "config.json"
            destination = temporary_root / "DJ Incoming" / "Spotify"
            with (
                patch.dict(os.environ, {"APPDATA": temporary_directory}),
                patch.object(setup, "config_path", return_value=config_path),
                patch.object(
                    sys,
                    "argv",
                    ["setup.py", "--root-path", str(destination)],
                ),
                patch("builtins.input", side_effect=AssertionError("Unexpected prompt")),
            ):
                self.assertEqual(setup.main(), 0)

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["ROOT_PATH"], str(destination))
            self.assertTrue(destination.is_dir())


if __name__ == "__main__":
    unittest.main()
