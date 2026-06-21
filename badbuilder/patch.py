"""XEX patching (replacement for PatchHelper.cs).

XexTool.exe is a Windows-only binary with no Linux build, so it's run
through Wine here. Install Wine first - on MX Linux (Debian-based):

    sudo apt install wine
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import console as ui


def _wine_available() -> bool:
    return shutil.which("wine") is not None


def patch_xex(xex_path: Path, xextool_path: Path) -> None:
    if not xextool_path.exists():
        ui.error(f"XexTool not found at {xextool_path}, skipping patch for {xex_path.name}.")
        return

    if not xex_path.exists():
        ui.error(f"XEX not found at {xex_path}, skipping patch.")
        return

    if not _wine_available():
        ui.error(
            f"'wine' is not installed, so {xex_path.name} could not be patched. "
            "Install it with: sudo apt install wine"
        )
        return

    result = subprocess.run(
        ["wine", str(xextool_path), "-m", "r", "-r", "a", str(xex_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        ui.error(f"The program {xex_path.stem} was unable to be patched. XexTool output:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
