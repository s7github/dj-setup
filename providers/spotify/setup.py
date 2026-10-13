import argparse
import json
import os
import sys
from pathlib import Path


DEFAULTS = {
    "SAVE_CREDENTIALS": True,
    "BULK_WAIT_TIME": 30,
    "SKIP_EXISTING": True,
    "SKIP_PREVIOUSLY_DOWNLOADED": True,
    "DOWNLOAD_FORMAT": "mp3",
}


def config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; Zotify's Windows config location is unknown.")
    return Path(appdata) / "Zotify" / "config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read Zotify configuration at {path}: {error}") from error
    if not isinstance(config, dict):
        raise RuntimeError(f"Zotify configuration must contain a JSON object: {path}")
    return config


def choose_root_path(current: object) -> Path:
    current_value = os.path.expandvars(os.path.expanduser(current)) if isinstance(current, str) else ""
    current_path = Path(current_value) if current_value else None
    default = str(current_path) if current_path and current_path.is_absolute() else str(
        Path.home() / "Music" / "Zotify"
    )
    while True:
        entered = input(f"Download folder [{default}]: ").strip()
        value = os.path.expandvars(os.path.expanduser(entered or default))
        destination = Path(value)
        if destination.is_absolute():
            return destination
        print("Enter an absolute folder path (for example C:\\DJIncoming\\SpotifyRips).")


def write_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as error:
        raise RuntimeError(f"Could not save Zotify configuration at {path}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Zotify's download settings.")
    parser.add_argument(
        "--root-path",
        type=Path,
        help="Absolute folder for downloaded music (prompt if omitted).",
    )
    args = parser.parse_args()

    try:
        path = config_path()
        config = load_config(path)
        if args.root_path is None:
            destination = choose_root_path(config.get("ROOT_PATH"))
        else:
            destination = Path(
                os.path.expandvars(os.path.expanduser(str(args.root_path)))
            )
            if not destination.is_absolute():
                raise RuntimeError("--root-path must be an absolute folder path.")
        destination.mkdir(parents=True, exist_ok=True)
        config["ROOT_PATH"] = str(destination)
        config.update(DEFAULTS)
        write_config(path, config)
    except (OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Zotify configuration saved to: {path}")
    print(f"Downloaded songs will be stored in: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
