"""Homebrew app management (replacement for HomebrewExperience.cs)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from . import console as ui


@dataclass
class HomebrewApp:
    name: str
    folder: Path
    entry_point: Path


def _add_homebrew_app() -> HomebrewApp | None:
    ui.console.print("\n[bold green]Add a new homebrew app[/bold green]\n")
    raw = ui.Prompt.ask("Enter the folder path for the app")
    folder = Path(raw.strip().strip('"')).expanduser()

    if not folder.is_dir():
        ui.error("Invalid folder path. Please try again.\n")
        return None

    xex_files = sorted(folder.glob("*.xex"))

    if len(xex_files) == 0:
        while True:
            raw_entry = ui.Prompt.ask(
                "No .xex files found in this folder. Enter the path to the entry point"
            )
            entry = Path(raw_entry.strip().strip('"')).expanduser()
            if entry.is_file() and entry.suffix.lower() == ".xex":
                break
            ui.error("File not found or is not an XEX file.\n")
    elif len(xex_files) == 1:
        entry = xex_files[0]
    else:
        choice = ui.select("Select entry point:", [f.name for f in xex_files])
        entry = folder / choice

    ui.console.print(f"[green]Added:[/green] {folder.name} -> [#ffac4d]{entry.name}[/#ffac4d]\n")
    return HomebrewApp(name=folder.name, folder=folder, entry_point=entry)


def _display_apps(apps: list[HomebrewApp]) -> None:
    if not apps:
        ui.error("No homebrew apps added.\n")
        return

    table = Table(title="Added Homebrew Apps")
    table.add_column("Folder", style="green")
    table.add_column("Entry Point", style="#ffac4d")
    for app in apps:
        table.add_row(app.folder.name, app.entry_point.name)
    ui.console.print(table)
    print()


def _remove_homebrew_app(apps: list[HomebrewApp]) -> None:
    if not apps:
        ui.error("No apps to remove.\n")
        return

    choice = ui.select("Select an app to remove:", [a.folder.name for a in apps])
    app = next(a for a in apps if a.folder.name == choice)
    apps.remove(app)
    ui.console.print(f"[#ffac4d]Removed:[/#ffac4d] {app.folder.name}\n")


def manage_homebrew_apps() -> list[HomebrewApp]:
    apps: list[HomebrewApp] = []
    while True:
        choice = ui.select(
            "Homebrew menu",
            ["Add Homebrew App", "View Added Apps", "Remove App", "Finish & Save"],
        )

        if choice == "Add Homebrew App":
            app = _add_homebrew_app()
            if app:
                apps.append(app)

        elif choice == "View Added Apps":
            _display_apps(apps)

        elif choice == "Remove App":
            _remove_homebrew_app(apps)

        elif choice == "Finish & Save":
            if not apps:
                ui.error("No apps added.")
                return apps
            if ui.confirm("Save and exit?", default=True):
                ui.success(f"Saved {len(apps)} app(s).\n")
                return apps
