"""bibi's command-line entry point: `bibi` launches the TUI, `bibi init`
sets up the config file for new users."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import config

# Just a suggested starting point for the `init` prompt -- bibi itself has
# no built-in default and won't run until a library_dir is actually set.
_SUGGESTED_LIBRARY_DIR = Path.home() / ".local" / "share" / "bibi" / "library"


def _prompt_library_dir() -> Path:
    existing = config._load().get("library_dir")
    default = existing or str(_SUGGESTED_LIBRARY_DIR)

    print("Where should bibi store your library?")
    print("(It'll be created automatically if it doesn't already exist.)")
    raw = input(f"Library directory [{default}]: ").strip()
    return Path(raw or default).expanduser()


def run_init() -> None:
    print("Welcome to bibi! Let's get you set up.\n")

    if config.CONFIG_PATH.exists():
        print(f"A config file already exists at {config.CONFIG_PATH} -- "
              "re-running this will let you change it.\n")

    try:
        library_dir = _prompt_library_dir()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted -- no changes made.")
        return

    already_existed = library_dir.exists()
    library_dir.mkdir(parents=True, exist_ok=True)
    config.write_library_dir(library_dir)

    print(f"\nWrote config to {config.CONFIG_PATH}")
    print(f"Library directory: {library_dir} "
          f"({'already existed' if already_existed else 'created'})")
    print("\nYou're all set -- run `bibi` to get started!")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bibi", description="A vim-keybound TUI for bibliography management.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init", help="Set up bibi's config file")
    args = parser.parse_args()

    if args.command == "init":
        run_init()
        return

    if not config.is_configured():
        print("bibi isn't set up yet -- run `bibi init` first.")
        raise SystemExit(1)

    from .app import BibiApp
    BibiApp().run()
