"""Archive extraction (replacement for SharpCompress' ArchiveFactory)."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


def _extract_zip_robust(archive_path: Path, dest_dir: Path) -> None:
    """Extracts a .zip, normalizing backslash-separated entry names.

    Some Windows-built zip tools store internal paths like
    "Content\\5841122D\\000D0000\\file.bin" instead of the zip-spec-correct
    forward slash. Python's zipfile (and shutil.unpack_archive) treats a
    backslash as a literal filename character on Linux, not a separator -
    so instead of nested folders you silently get one oddly-named flat
    file, and anything that expects the nested structure breaks later.
    """
    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name:
                continue
            if name.endswith("/"):
                (dest_dir / name).mkdir(parents=True, exist_ok=True)
                continue
            target = dest_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def extract_archive(archive_path: Path, dest_dir: Path) -> None:
    """Extracts archive_path into dest_dir. Supports .7z (via py7zr), .zip
    (via the backslash-safe extractor above), and anything else shutil
    already knows about (.tar, .tar.gz, etc)."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    suffix = archive_path.suffix.lower()

    if suffix == ".7z":
        import py7zr  # imported lazily so the dependency is optional until needed

        with py7zr.SevenZipFile(archive_path, mode="r") as z:
            z.extractall(path=dest_dir)
        return

    if suffix == ".zip":
        _extract_zip_robust(archive_path, dest_dir)
        return

    try:
        shutil.unpack_archive(str(archive_path), str(dest_dir))
    except (ValueError, shutil.ReadError) as e:
        raise ValueError(
            f"Don't know how to extract '{archive_path.name}': {e}\n"
            f"    Extract it manually into: {dest_dir}"
        ) from e
