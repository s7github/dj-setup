import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from providers.spotify import download, setup


class SpotifySetupTests(unittest.TestCase):
    def test_setup_updates_options_and_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = Path(temporary_directory) / "config.json"
            destination = Path(temporary_directory) / "DJIncoming" / "SpotifyRips"
            config_path.write_text(
                json.dumps({"ROOT_PATH": "old", "CUSTOM_OPTION": "keep"}),
                encoding="utf-8",
            )
            with (
                patch.object(setup, "config_path", return_value=config_path),
                patch.object(setup, "choose_root_path", return_value=destination),
            ):
                self.assertEqual(setup.main(), 0)

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["ROOT_PATH"], str(destination))
            self.assertEqual(config["CUSTOM_OPTION"], "keep")
            self.assertTrue(config["SAVE_CREDENTIALS"])
            self.assertEqual(config["BULK_WAIT_TIME"], 30)
            self.assertTrue(config["SKIP_EXISTING"])
            self.assertTrue(config["SKIP_PREVIOUSLY_DOWNLOADED"])
            self.assertEqual(config["DOWNLOAD_FORMAT"], "mp3")
            self.assertTrue(destination.is_dir())

    def test_relative_existing_root_uses_absolute_default(self):
        with patch("builtins.input", return_value=""):
            destination = setup.choose_root_path("relative-folder")
        self.assertTrue(destination.is_absolute())


class SpotifyDownloadTests(unittest.TestCase):
    def test_clean_link_removes_tracking_parameter(self):
        self.assertEqual(
            download.clean_link("https://open.spotify.com/track/id?si=abc&context=def"),
            "https://open.spotify.com/track/id?context=def",
        )

    def test_clean_link_rejects_non_spotify_urls(self):
        with self.assertRaises(ValueError):
            download.clean_link("https://example.com/track/id")

    def test_successful_url_is_marked_and_failure_is_left_pending(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            links_path = Path(temporary_directory) / "links.txt"
            links_path.write_text(
                "# Playlist\nhttps://open.spotify.com/track/ok\n"
                "https://open.spotify.com/track/fail\n",
                encoding="utf-8",
            )
            with (
                patch.object(
                    download.subprocess,
                    "run",
                    side_effect=[None, subprocess.CalledProcessError(1, "zotify")],
                ),
                patch.object(download.time, "sleep"),
            ):
                self.assertEqual(download.process_file(links_path, 30), 1)

            self.assertEqual(
                links_path.read_text(encoding="utf-8"),
                "# Playlist\nhttps://open.spotify.com/track/ok [DONE]\n"
                "https://open.spotify.com/track/fail\n",
            )


if __name__ == "__main__":
    unittest.main()
