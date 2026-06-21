"""Console / UI helpers - a rich-based replacement for Spectre.Console.

No arrow-key menu library is used on purpose: a plain numbered prompt works
in any terminal (including over SSH, in tmux, etc.) without curses quirks.
"""
from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()

ORANGE = "#ff7200"
GREEN = "#76b900"
PEACH = "#ffd899"


def info(msg: str) -> None:
    console.print(f"[{GREEN}][*][/{GREEN}] {msg}")


def success(msg: str) -> None:
    console.print(f"[{GREEN}][+][/{GREEN}] {msg}")


def error(msg: str) -> None:
    console.print(f"[{ORANGE}][-][/{ORANGE}] {msg}")


def warn(msg: str) -> None:
    console.print(f"[{ORANGE}]WARNING:[/{ORANGE}] {msg}")


def select(title: str, choices: list[str]) -> str:
    """Numbered single-choice menu. Returns the chosen string."""
    console.print(f"\n[bold]{title}[/bold]")
    for i, choice in enumerate(choices, start=1):
        console.print(f"  [{GREEN}]{i}[/{GREEN}]) {choice}")
    while True:
        raw = Prompt.ask("Enter choice number")
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        error("Invalid selection, try again.")


def multi_select(title: str, choices: list[str], preselected: set[int] | None = None) -> list[str]:
    """Numbered multi-choice menu. Enter comma-separated numbers, 'all', or 'none'."""
    preselected = preselected or set()
    console.print(f"\n[bold]{title}[/bold]")
    for i, choice in enumerate(choices, start=1):
        mark = f"[{GREEN}]x[/{GREEN}]" if i in preselected else " "
        console.print(f"  [{mark}] {i}) {choice}")
    console.print("[dim]Enter numbers separated by commas, 'all', or 'none'.[/dim]")

    default = ",".join(str(i) for i in sorted(preselected)) if preselected else "none"
    raw = Prompt.ask("Selection", default=default).strip().lower()

    if raw == "all":
        return list(choices)
    if raw in ("none", ""):
        return []

    indices: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(choices):
            indices.add(int(part))
    return [choices[i - 1] for i in sorted(indices)]


def confirm(msg: str, default: bool = False) -> bool:
    return Confirm.ask(msg, default=default)
