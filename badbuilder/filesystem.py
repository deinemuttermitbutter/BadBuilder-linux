"""Filesystem helpers (replacement for FileSystemHelper.cs)."""
from __future__ import annotations

import shutil
from pathlib import Path


def mirror_directory(src: Path, dst: Path) -> None:
    """Recursively copies the *contents* of src into dst, creating dst (and
    any subfolders) as needed. Equivalent to the original's
    MirrorDirectoryAsync."""
    if not src.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src}")

    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            mirror_directory(item, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
