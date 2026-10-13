import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


DONE_TAG = "[DONE]"


def config_wait_time() -> int:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return 30
    config_path = Path(appdata) / "Zotify" / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 30
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read Zotify configuration at {config_path}: {error}") from error
    if not isinstance(config, dict):
        raise RuntimeError(f"Zotify configuration must contain a JSON object: {config_path}")
    wait_time = config.get("BULK_WAIT_TIME", 30)
    if not isinstance(wait_time, int) or isinstance(wait_time, bool) or wait_time < 0:
        raise RuntimeError(f"BULK_WAIT_TIME must be a non-negative integer in {config_path}")
    return wait_time


def clean_link(raw: str) -> str:
    parts = urlsplit(raw.strip())
    if parts.scheme not in ("http", "https") or not (
        parts.hostname == "spotify.com"
        or (parts.hostname is not None and parts.hostname.endswith(".spotify.com"))
    ):
        raise ValueError("not a Spotify URL")
    query = "&".join(part for part in parts.query.split("&") if not part.startswith("si="))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def write_lines_atomic(file_path: Path, lines: list[str]) -> None:
    temporary_path = file_path.with_suffix(file_path.suffix + ".tmp")
    temporary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary_path.replace(file_path)


def process_file(file_path: Path, wait_time: int) -> int:
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        print(f"ERROR: Could not read link list {file_path}: {error}", file=sys.stderr)
        return 1

    pending_indices = [
        index for index, line in enumerate(lines)
        if line.strip() and not line.lstrip().startswith("#") and DONE_TAG not in line
    ]
    if not pending_indices:
        print(f"No pending Spotify URLs in {file_path}.")
        return 0

    failed = False
    for pending_position, index in enumerate(pending_indices):
        original_line = lines[index]
        try:
            link = clean_link(original_line)
        except ValueError:
            print(f"Skip (not a Spotify URL): {original_line.strip()}")
            failed = True
            continue

        print(f"\n>>> Processing {link}")
        try:
            subprocess.run([sys.executable, "-m", "zotify", link], check=True)
        except subprocess.CalledProcessError as error:
            print(f"ERROR: Zotify failed for this URL (exit code {error.returncode}).")
            failed = True
        else:
            lines[index] = original_line.rstrip() + f" {DONE_TAG}"
            try:
                write_lines_atomic(file_path, lines)
            except OSError as error:
                print(f"ERROR: Could not save progress to {file_path}: {error}", file=sys.stderr)
                return 1
            print(">>> Done.")

        if pending_position + 1 < len(pending_indices):
            print(f">>> Waiting {wait_time}s before next URL...")
            try:
                time.sleep(wait_time)
            except KeyboardInterrupt:
                print("\nInterrupted. Completed progress has been saved.")
                return 130

    return 1 if failed else 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python download.py <path-to-text-file>", file=sys.stderr)
        return 2
    try:
        wait_time = config_wait_time()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return process_file(Path(sys.argv[1]), wait_time)


if __name__ == "__main__":
    raise SystemExit(main())
