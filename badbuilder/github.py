"""GitHub release asset discovery + file downloading."""
from __future__ import annotations

import os
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com"


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_release_assets(repo: str) -> list[tuple[str, str]]:
    """Returns [(asset_name, browser_download_url), ...] for repo's latest release."""
    url = f"{GITHUB_API}/repos/{repo}/releases/latest"
    resp = requests.get(url, timeout=30, headers=_github_headers())

    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError(
            f"GitHub API rate limit hit while checking {repo}. "
            "Unauthenticated requests are capped at 60/hour per IP - wait a bit and try again, "
            "or set a GITHUB_TOKEN env var and we'll use it automatically."
        )

    resp.raise_for_status()
    data = resp.json()
    return [(a["name"], a["browser_download_url"]) for a in data.get("assets", [])]


def friendly_name_for_asset(asset_name: str) -> str:
    """Maps a GitHub release asset filename to one of BadBuilder's known
    pipeline stages, mirroring the original C# switch in DownloadHelper."""
    lower = asset_name.lower()
    if "free" in lower:
        return "FreeMyXe"
    if "tools" in lower:
        return "BadUpdate Tools"
    if "badupdate" in lower:
        return "BadUpdate"
    if "xeunshackle" in lower:
        return "XeUnshackle"
    # Original C# did asset.Name[:-4] here, which only correctly strips a
    # 4-character extension like ".zip" (and mangles ".7z"). Strip known
    # archive extensions properly instead, including two-part ones like
    # ".tar.gz".
    name = asset_name
    for ext in (".tar.gz", ".tar.bz2", ".tar.xz", ".tar", ".zip", ".7z", ".rar"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return Path(asset_name).stem


def download_file(url: str, dest: Path, progress, task_id) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        if total:
            progress.update(task_id, total=total)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))
