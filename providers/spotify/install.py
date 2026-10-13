import argparse
import subprocess
import sys
from pathlib import Path


ZOTIFY_REPOSITORY = "git+https://github.com/Googolplexed0/zotify.git"
SCRIPT_DIRECTORY = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Zotify and configure its download folder.")
    parser.add_argument("--root-path", type=Path, help="Absolute destination folder for downloaded music.")
    args = parser.parse_args()
    setup_arguments = [str(SCRIPT_DIRECTORY / "setup.py")]
    if args.root_path is not None:
        setup_arguments.extend(["--root-path", str(args.root_path)])

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", ZOTIFY_REPOSITORY],
        check=True,
    )
    subprocess.run([sys.executable, "-m", "zotify", "--update-config"], check=True)
    subprocess.run([sys.executable, *setup_arguments], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
