"""Shared constants for BadBuilder (Linux)."""
from __future__ import annotations

from pathlib import Path

WORKING_DIR = Path("Work")
DOWNLOAD_DIR = WORKING_DIR / "Download"
EXTRACTED_DIR = WORKING_DIR / "Extract"

# This is a *path fragment*, joined with pathlib elsewhere, so it produces
# the right separator on Linux. The original C# tool hardcoded Windows
# backslashes into this string ("Content\\0000000000000000\\"), which is
# one of the things that made it Windows-only - a literal backslash isn't
# a path separator on Linux, it's just a character in a filename.
CONTENT_FOLDER = Path("Content") / "0000000000000000"

KB = 1024
MB = 1024**2
GB = 1024**3
TB = 1024**4

# (org/repo) pairs we pull the *latest* GitHub release assets from.
GITHUB_REPOS = [
    "grimdoomer/Xbox360BadUpdate",
    "Byrom90/XeUnshackle",
    "FreeMyXe/FreeMyXe",
]

# Direct asset downloads bundled with BadBuilder itself.
DIRECT_DOWNLOADS = [
    ("XeXmenu", "https://github.com/Pdawg-bytes/BadBuilder/releases/download/v0.10a/MenuData.7z"),
    ("Rock Band Blitz", "https://github.com/Pdawg-bytes/BadBuilder/releases/download/v0.10a/GameData.zip"),
    ("Simple 360 NAND Flasher", "https://github.com/Pdawg-bytes/BadBuilder/releases/download/v0.10a/Flasher.7z"),
]
