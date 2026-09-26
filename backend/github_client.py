"""
github_client.py — thin async wrapper around the GitHub REST API.

Uses httpx for async HTTP.  Authenticates via GITHUB_TOKEN env var when
present (raises rate-limit ceiling from 60 → 5 000 req/hr).
"""
from __future__ import annotations

import os
import re
from typing import Optional

import httpx

_BASE = "https://api.github.com"
_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Matches "github.com" only when it is the actual host, not a substring like "notgithub.com"
_GITHUB_HOST_RE = re.compile(r"(?:^|[./])github\.com(?:/|$)")


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if _GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {_GITHUB_TOKEN}"
    return h


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL.

    Accepts:
      https://github.com/owner/repo
      https://github.com/owner/repo.git
      github.com/owner/repo
    """
    url = repo_url.strip().rstrip("/").removesuffix(".git")
    # Match only actual github.com — must be preceded by '.' or '/' or start of string
    if not _GITHUB_HOST_RE.search(url):
        raise ValueError(f"URL does not appear to be a GitHub URL: {repo_url!r}")
    parts = url.split("github.com/", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse GitHub URL: {repo_url!r}")
    segments = [s for s in parts[1].split("/") if s]
    if len(segments) < 2:
        raise ValueError(f"URL must include owner and repo name: {repo_url!r}")
    return segments[0], segments[1]


async def fetch_repo_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> list[dict]:
    """Return the flat recursive git tree for *branch*.

    Each item is a GitHub tree object::

        {"path": "src/index.ts", "type": "blob", "size": 1234, "sha": "..."}

    Raises ``ValueError`` on 404 (repo not found / private) and
    ``httpx.HTTPStatusError`` for other non-2xx responses.
    """
    url = f"{_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=20, follow_redirects=True)
    try:
        resp = await client.get(url, headers=_headers(), follow_redirects=True)
        if resp.status_code == 404:
            raise ValueError(
                f"Repository '{owner}/{repo}' not found or is private. "
                "Set GITHUB_TOKEN to access private repos."
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("tree", [])
    finally:
        if close:
            await client.aclose()


async def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[str]:
    """Fetch the decoded text content of a single file.

    Returns ``None`` if the file does not exist (404) or is binary / too large.
    """
    # Use the raw content endpoint — cheaper than the contents API for plain text
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=20)
    try:
        resp = await client.get(url, headers=_headers(), follow_redirects=True)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        # Guard against huge binary blobs
        if len(resp.content) > 500_000:
            return None
        try:
            return resp.text
        except UnicodeDecodeError:
            return None
    finally:
        if close:
            await client.aclose()


async def fetch_files_batch(
    owner: str,
    repo: str,
    paths: list[str],
    branch: str = "main",
) -> dict[str, Optional[str]]:
    """Fetch multiple files concurrently, returning a path → content mapping."""
    import asyncio

    async with httpx.AsyncClient(timeout=20) as client:
        tasks = [
            fetch_file_content(owner, repo, p, branch, client=client)
            for p in paths
        ]
        results = await asyncio.gather(*tasks)
    return dict(zip(paths, results))


async def fetch_default_branch(
    owner: str,
    repo: str,
    *,
    client: Optional[httpx.AsyncClient] = None,
) -> str:
    """Return the repository's default branch (e.g. 'main' or 'master')."""
    url = f"{_BASE}/repos/{owner}/{repo}"
    close = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=20, follow_redirects=True)
    try:
        resp = await client.get(url, headers=_headers(), follow_redirects=True)
        if resp.status_code == 404:
            raise ValueError(
                f"Repository '{owner}/{repo}' not found or is private. "
                "Set GITHUB_TOKEN to access private repos."
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("default_branch", "main")
    finally:
        if close:
            await client.aclose()
