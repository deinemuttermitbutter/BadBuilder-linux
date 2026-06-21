"""Main orchestration logic - the Linux equivalent of Program.cs, minus the
Windows-only disk formatting step (you format the USB yourself beforehand)."""
from __future__ import annotations

import concurrent.futures
import os
import shutil
from pathlib import Path

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from . import archive as arc
from . import console as ui
from . import constants as c
from . import filesystem as fs
from . import github
from . import homebrew as hb
from . import patch

WELCOME = r"""
[#4D8C00]██████╗  █████╗ ██████╗ ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗[/]
[#65A800]██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗[/]
[#76B900]██████╔╝███████║██║  ██║██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝[/]
[#A1CF3E]██╔══██╗██╔══██║██║  ██║██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗[/]
[#CCE388]██████╔╝██║  ██║██████╔╝██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║[/]
[#CCE388]╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝[/]

[#76B900]───────────────────────────────────────────────────────────────────────v0.31[/]
───────────────────────Xbox 360 [#FF7200]BadUpdate[/] USB Builder───────────────────────
                          [#848589]Linux port - original by Pdawg[/]
[#76B900]────────────────────────────────────────────────────────────────────────────[/]
"""


def show_welcome() -> None:
    ui.console.print(WELCOME)


class ActionQueue:
    """Equivalent of Utilities/ActionQueue.cs - runs queued callables in
    descending priority order."""

    def __init__(self) -> None:
        self._actions: dict[int, list] = {}

    def enqueue(self, priority: int, fn) -> None:
        self._actions.setdefault(priority, []).append(fn)

    def run(self) -> None:
        for priority in sorted(self._actions.keys(), reverse=True):
            for fn in self._actions[priority]:
                fn()


def prompt_target_path() -> Path:
    ui.console.print("\n[bold]Target USB drive[/bold]")
    ui.console.print(
        "[dim]Enter the mount point of your already-FAT32-formatted USB drive "
        "(e.g. /media/yourname/USBDRIVE or /run/media/yourname/USBDRIVE).[/dim]"
    )
    while True:
        raw = ui.Prompt.ask("Mount path")
        target = Path(raw.strip().strip('"')).expanduser()
        if not target.is_dir():
            ui.error("That path doesn't exist or isn't a directory.")
            continue
        if not os.access(target, os.W_OK):
            ui.error("That path isn't writable.")
            continue
        return target


def gather_download_items() -> list[tuple[str, str]]:
    """Returns [(friendly_name, url), ...] - same shape as the C# 'items' list."""
    items: list[tuple[str, str]] = list(c.DIRECT_DOWNLOADS)
    for repo in c.GITHUB_REPOS:
        ui.info(f"Checking latest release for {repo}...")
        for asset_name, url in github.get_latest_release_assets(repo):
            items.append((github.friendly_name_for_asset(asset_name), url))
    return items


def download_required_files() -> list[tuple[str, Path]]:
    """Returns [(friendly_name, archive_path), ...]."""
    items = gather_download_items()
    c.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    existing_names = {
        name for name, url in items if (c.DOWNLOAD_DIR / Path(url).name).exists()
    }

    choices = [f"{name} (already exists)" if name in existing_names else name for name, _ in items]
    preselected = {i + 1 for i, (name, _) in enumerate(items) if name in existing_names}

    selected_display = ui.multi_select(
        "Which files do you already have? (select all that apply)", choices, preselected
    )
    selected_names = {s.split(" (already exists)")[0] for s in selected_display}

    to_download = [(name, url) for name, url in items if name not in selected_names]

    if to_download:
        ui.info("Downloading required files.")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=ui.console,
        ) as progress:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures = []
                for name, url in to_download:
                    dest = c.DOWNLOAD_DIR / Path(url).name
                    task_id = progress.add_task(name, total=None)
                    futures.append(pool.submit(github.download_file, url, dest, progress, task_id))
                for f in concurrent.futures.as_completed(futures):
                    f.result()
        ui.success(f"{len(to_download)} download(s) completed.")
    else:
        ui.success("No downloads required. All files already exist.")

    print()
    for name in selected_names:
        url = next(u for n, u in items if n == name)
        dest = c.DOWNLOAD_DIR / Path(url).name
        if dest.exists():
            continue
        while True:
            raw = ui.Prompt.ask(f"Enter the path to the {name} archive")
            src = Path(raw.strip().strip('"')).expanduser()
            if src.is_file():
                break
            ui.error("File does not exist.")
        try:
            fs.copy_file(src, dest)
            ui.success(f"Copied {name} to the working directory.\n")
        except Exception as e:
            ui.error(f"Failed to copy {name} to the working directory: {e}\n")

    return [(name, c.DOWNLOAD_DIR / Path(url).name) for name, url in items]


def extract_files(items: list[tuple[str, Path]]) -> None:
    ui.info("Extracting files.")
    for name, archive_path in items:
        dest = c.EXTRACTED_DIR / name
        try:
            arc.extract_archive(archive_path, dest)
            ui.success(f"Extracted {name}.")
        except Exception as e:
            ui.error(f"Failed to extract {name}: {e}")


def copy_extracted_files(target: Path, default_app: str) -> Path | None:
    """Walks Work/Extract/<friendly name>/ folders and copies each one to the
    right place on the USB drive, mirroring the switch-statement in the
    original Program.cs."""
    queue = ActionQueue()
    xextool_path: list[Path | None] = [None]

    if not c.EXTRACTED_DIR.is_dir():
        ui.error("Nothing was extracted - skipping file copy step.")
        return None

    for folder in sorted(p for p in c.EXTRACTED_DIR.iterdir() if p.is_dir()):
        name = folder.name

        if name == "XeXmenu":
            queue.enqueue(
                7,
                lambda folder=folder: fs.mirror_directory(
                    folder / c.CONTENT_FOLDER / "C0DE9999",
                    target / c.CONTENT_FOLDER / "C0DE9999",
                ),
            )

        elif name == "FreeMyXe":
            if default_app == "FreeMyXe":
                queue.enqueue(
                    9,
                    lambda folder=folder: fs.copy_file(
                        folder / "FreeMyXe.xex", target / "BadUpdatePayload" / "default.xex"
                    ),
                )

        elif name == "XeUnshackle":
            if default_app == "XeUnshackle":
                def _xeunshackle(folder=folder):
                    subfolders = [d for d in folder.iterdir() if d.is_dir()]
                    if not subfolders:
                        ui.error("XeUnshackle archive had no subfolder; skipping.")
                        return
                    sub = subfolders[0]
                    readme = sub / "README - IMPORTANT.txt"
                    if readme.exists():
                        readme.unlink()
                    fs.mirror_directory(sub, target)

                queue.enqueue(9, _xeunshackle)

        elif name == "BadUpdate":
            def _badupdate(folder=folder):
                (target / "name.txt").write_text("USB Storage Device\n")
                (target / "info.txt").write_text(
                    "This drive was created with BadBuilder (Linux port) by Pdawg.\n"
                    "Find more info here: https://github.com/Pdawg-bytes/BadBuilder\n"
                    f"Configuration: \n-  BadUpdate target binary: {default_app}\n"
                )
                (target / "Apps").mkdir(parents=True, exist_ok=True)
                fs.mirror_directory(folder / "Rock Band Blitz", target)

            queue.enqueue(10, _badupdate)

        elif name == "BadUpdate Tools":
            xextool_path[0] = folder / "XePatcher" / "XexTool.exe"

        elif name == "Rock Band Blitz":
            queue.enqueue(
                8,
                lambda folder=folder: fs.mirror_directory(
                    folder / c.CONTENT_FOLDER / "5841122D" / "000D0000",
                    target / c.CONTENT_FOLDER / "5841122D" / "000D0000",
                ),
            )

        elif name == "Simple 360 NAND Flasher":
            def _nand(folder=folder):
                xex = folder / "Simple 360 NAND Flasher" / "Default.xex"
                if xextool_path[0]:
                    patch.patch_xex(xex, xextool_path[0])
                fs.mirror_directory(
                    folder / "Simple 360 NAND Flasher", target / "Apps" / "Simple 360 NAND Flasher"
                )

            queue.enqueue(6, _nand)

        else:
            raise RuntimeError(f"Unexpected directory in working folder: {folder}")

    ui.info("Copying required files and folders.")
    queue.run()
    return xextool_path[0]


def _write_homebrew_log(target: Path, count: int) -> None:
    with open(target / "info.txt", "a") as f:
        f.write(f"-  {count} homebrew app(s) added (including Simple 360 NAND Flasher)\n")


def run() -> None:
    show_welcome()

    while True:
        action = ui.select("Choose an action", ["Build exploit USB", "Exit"])
        if action == "Exit":
            return

        target = prompt_target_path()
        ui.warn(f"Files will be written to {target}. Existing files with matching names will be overwritten.")
        if ui.confirm("Continue?", default=False):
            break

    download_items = download_required_files()
    extract_files(download_items)

    default_app = ui.select("Which program should be launched by BadUpdate?", ["FreeMyXe", "XeUnshackle"])

    total_size = shutil.disk_usage(target).total

    xextool_path = copy_extracted_files(target, default_app)

    with open(target / "info.txt", "a") as f:
        f.write("-  Disk was pre-formatted manually (Linux build does not format drives)\n")
        f.write(f"-  Disk total size: {total_size} bytes\n")

    if not ui.confirm("Would you like to add homebrew programs?", default=False):
        _write_homebrew_log(target, 1)
        ui.success("\nYour USB drive is ready to go.")
        return

    apps = hb.manage_homebrew_apps()

    ui.info("Copying and patching homebrew apps.")
    for app in apps:
        fs.mirror_directory(app.folder, target / "Apps" / app.name)
        if xextool_path:
            patch.patch_xex(app.entry_point, xextool_path)

    _write_homebrew_log(target, len(apps) + 1)
    ui.success(f"\n{len(apps)} apps copied.")
    ui.success("Your USB drive is ready to go.")
