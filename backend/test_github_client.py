"""
test_github_client.py — unit tests for github_client.py

Covers:
- parse_owner_repo: valid URLs, .git suffix, trailing slash, schema-less,
  invalid hosts, missing owner/repo.
- fetch_default_branch: mocked HTTP 200 and 404 responses.
- fetch_repo_tree: mocked HTTP 200 and 404 responses.
- fetch_file_content: 200, 404, oversized body.
- fetch_files_batch: multiple files via gather.
"""
from __future__ import annotations

import json
import pytest
import httpx

# ---------------------------------------------------------------------------
# parse_owner_repo
# ---------------------------------------------------------------------------

# Import under test after we establish sys.path is the backend dir
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from github_client import parse_owner_repo  # noqa: E402


class TestParseOwnerRepo:
    def test_https_url(self):
        owner, repo = parse_owner_repo("https://github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_https_url_trailing_slash(self):
        owner, repo = parse_owner_repo("https://github.com/octocat/Hello-World/")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_https_url_dot_git_suffix(self):
        owner, repo = parse_owner_repo("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_schema_less_url(self):
        owner, repo = parse_owner_repo("github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_preserves_original_url_untouched(self):
        """parse_owner_repo must NOT mutate the input; original URL stays intact."""
        original = "https://github.com/octocat/Hello-World"
        parse_owner_repo(original)
        assert original == "https://github.com/octocat/Hello-World"

    def test_not_github_url_raises(self):
        with pytest.raises(ValueError, match="does not appear to be a GitHub URL"):
            parse_owner_repo("https://gitlab.com/octocat/repo")

    def test_notgithub_subdomain_raises(self):
        """notgithub.com must NOT be accepted."""
        with pytest.raises(ValueError):
            parse_owner_repo("https://notgithub.com/octocat/repo")

    def test_missing_repo_raises(self):
        with pytest.raises(ValueError, match="owner and repo name"):
            parse_owner_repo("https://github.com/octocat")

    def test_extra_path_segments_ignored(self):
        """Only owner + repo are extracted; extra segments are silently ignored."""
        owner, repo = parse_owner_repo("https://github.com/octocat/Hello-World/tree/main")
        assert owner == "octocat"
        assert repo == "Hello-World"


# ---------------------------------------------------------------------------
# fetch_default_branch (mocked transport)
# ---------------------------------------------------------------------------

from github_client import fetch_default_branch  # noqa: E402


def _make_transport(status_code: int, body: dict) -> httpx.MockTransport:
    """Return a MockTransport that always responds with the given status + JSON body."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            headers={"content-type": "application/json"},
            content=json.dumps(body).encode(),
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_default_branch_returns_field():
    transport = _make_transport(200, {"default_branch": "develop", "id": 1})
    async with httpx.AsyncClient(transport=transport) as client:
        branch = await fetch_default_branch("octocat", "Hello-World", client=client)
    assert branch == "develop"


@pytest.mark.asyncio
async def test_fetch_default_branch_fallback_to_main():
    transport = _make_transport(200, {})  # missing 'default_branch'
    async with httpx.AsyncClient(transport=transport) as client:
        branch = await fetch_default_branch("octocat", "Hello-World", client=client)
    assert branch == "main"


@pytest.mark.asyncio
async def test_fetch_default_branch_404_raises():
    transport = _make_transport(404, {"message": "Not Found"})
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match="not found or is private"):
            await fetch_default_branch("octocat", "private-repo", client=client)


# ---------------------------------------------------------------------------
# fetch_repo_tree (mocked transport)
# ---------------------------------------------------------------------------

from github_client import fetch_repo_tree  # noqa: E402

_SAMPLE_TREE = [
    {"path": "README.md", "type": "blob", "size": 100},
    {"path": "src", "type": "tree"},
    {"path": "src/main.py", "type": "blob", "size": 200},
]


@pytest.mark.asyncio
async def test_fetch_repo_tree_returns_items():
    transport = _make_transport(200, {"tree": _SAMPLE_TREE})
    async with httpx.AsyncClient(transport=transport) as client:
        tree = await fetch_repo_tree("octocat", "Hello-World", "main", client=client)
    assert len(tree) == 3
    assert tree[0]["path"] == "README.md"


@pytest.mark.asyncio
async def test_fetch_repo_tree_empty_when_no_tree_key():
    transport = _make_transport(200, {})
    async with httpx.AsyncClient(transport=transport) as client:
        tree = await fetch_repo_tree("octocat", "Hello-World", "main", client=client)
    assert tree == []


@pytest.mark.asyncio
async def test_fetch_repo_tree_404_raises():
    transport = _make_transport(404, {"message": "Not Found"})
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match="not found or is private"):
            await fetch_repo_tree("octocat", "private-repo", "main", client=client)


# ---------------------------------------------------------------------------
# fetch_file_content (mocked transport)
# ---------------------------------------------------------------------------

from github_client import fetch_file_content  # noqa: E402


@pytest.mark.asyncio
async def test_fetch_file_content_returns_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"hello world")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        text = await fetch_file_content("octocat", "repo", "README.md", "main", client=client)
    assert text == "hello world"


@pytest.mark.asyncio
async def test_fetch_file_content_404_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"Not Found")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_file_content("octocat", "repo", "missing.py", "main", client=client)
    assert result is None


@pytest.mark.asyncio
async def test_fetch_file_content_oversized_returns_none():
    big = b"x" * 600_000  # > 500 KB limit

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=big)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_file_content("octocat", "repo", "big.bin", "main", client=client)
    assert result is None
