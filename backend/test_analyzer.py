"""
test_analyzer.py — unit tests for analyzer.py

Covers:
- Language detection from file extension counts.
- Framework detection from file content signals.
- Dependency extraction: requirements.txt, package.json, Cargo.toml, go.mod.
  go.mod tests exercise the fixed parser:
    • block form "require (" and "require(" (no space)
    • closing ")" with a trailing inline comment
    • single-line form
    • // indirect entries inside a block
- Key path selection (manifests, README, entry points, depth cap, 30-file cap).
- Entry point detection.
- Folder structure mapping (depth truncation).
- API route detection (FastAPI, Express, NestJS patterns).
- README extraction (first 600 chars).
- Full RepoAnalyzer.analyze() with mocked network calls, verifying repo_url
  is preserved verbatim in the returned AnalysisResult.
"""
from __future__ import annotations

import json
import sys
import os
from typing import Optional

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import AsyncMock, patch  # noqa: E402
from analyzer import RepoAnalyzer  # noqa: E402


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_analyzer(url: str = "https://github.com/owner/repo") -> RepoAnalyzer:
    return RepoAnalyzer(url, branch="main")


# ── Language detection ────────────────────────────────────────────────────────

class TestDetectLanguages:
    def test_basic_counts(self):
        a = _make_analyzer()
        paths = ["a.py", "b.py", "c.ts", "d.js"]
        langs = a._detect_languages(paths)
        assert langs["Python"] == 2
        assert langs["TypeScript"] == 1
        assert langs["JavaScript"] == 1

    def test_sorted_descending(self):
        a = _make_analyzer()
        paths = ["a.go", "b.go", "c.go", "d.py"]
        langs = a._detect_languages(paths)
        keys = list(langs.keys())
        assert keys[0] == "Go"
        assert keys[1] == "Python"

    def test_unknown_extensions_ignored(self):
        a = _make_analyzer()
        langs = a._detect_languages(["a.unknownext", "b.xyz"])
        assert langs == {}

    def test_extension_case_insensitive(self):
        a = _make_analyzer()
        langs = a._detect_languages(["Main.PY"])
        assert langs.get("Python") == 1

    def test_no_extension_ignored(self):
        a = _make_analyzer()
        langs = a._detect_languages(["Makefile", "Dockerfile"])
        assert langs == {}


# ── Framework detection ───────────────────────────────────────────────────────

class TestDetectFrameworks:
    def test_fastapi_detected_from_requirements(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"requirements.txt": "fastapi>=0.100\nuvicorn\n"}
        assert "FastAPI" in a._detect_frameworks(files)

    def test_react_detected_from_package_json(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"package.json": '{"dependencies": {"react": "^18", "vite": "^5"}}'}
        fw = a._detect_frameworks(files)
        assert "React" in fw
        assert "Vite" in fw

    def test_gin_detected_from_go_mod(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"go.mod": "module example.com\n\nrequire github.com/gin-gonic/gin v1.9.0\n"}
        assert "Gin" in a._detect_frameworks(files)

    def test_none_file_content_skipped(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"requirements.txt": None}
        assert a._detect_frameworks(files) == []

    def test_no_duplicates(self):
        a = _make_analyzer()
        # Two files both mention fastapi
        files: dict[str, Optional[str]] = {
            "requirements.txt": "fastapi\n",
            "backend/requirements.txt": "fastapi\n",
        }
        fw = a._detect_frameworks(files)
        assert fw.count("FastAPI") == 1


# ── Dependency extraction ─────────────────────────────────────────────────────

class TestExtractDependencies:

    # requirements.txt
    def test_requirements_txt_basic(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"requirements.txt": "fastapi>=0.111\nuvicorn[standard]\npydantic\n"}
        deps = a._extract_dependencies(files)
        assert "python" in deps
        assert "fastapi>=0.111" in deps["python"]
        assert "uvicorn[standard]" in deps["python"]

    def test_requirements_txt_ignores_comments(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"requirements.txt": "# comment\nfastapi\n"}
        deps = a._extract_dependencies(files)
        assert "# comment" not in deps.get("python", [])
        assert "fastapi" in deps["python"]

    def test_requirements_txt_empty_skips(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"requirements.txt": "# only comments\n"}
        deps = a._extract_dependencies(files)
        assert "python" not in deps

    # package.json
    def test_package_json_merges_dev_and_prod(self):
        a = _make_analyzer()
        pkg = {"dependencies": {"react": "^18"}, "devDependencies": {"vite": "^5"}}
        files: dict[str, Optional[str]] = {"package.json": json.dumps(pkg)}
        deps = a._extract_dependencies(files)
        assert "npm" in deps
        assert "react" in deps["npm"]
        assert "vite" in deps["npm"]

    def test_package_json_invalid_json_skipped(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"package.json": "NOT JSON"}
        deps = a._extract_dependencies(files)
        assert "npm" not in deps

    # Cargo.toml
    def test_cargo_toml_parses_dependencies(self):
        a = _make_analyzer()
        cargo = "[package]\nname = \"foo\"\n\n[dependencies]\nactix-web = \"4\"\nserde = { version = \"1\" }\n"
        files: dict[str, Optional[str]] = {"Cargo.toml": cargo}
        deps = a._extract_dependencies(files)
        assert "cargo" in deps
        assert "actix-web" in deps["cargo"]
        assert "serde" in deps["cargo"]

    # go.mod — the fixed parser
    def test_go_mod_block_require_standard(self):
        """Standard block form: require ("""
        a = _make_analyzer()
        content = (
            "module example.com\n\ngo 1.21\n\n"
            "require (\n"
            "\tgithub.com/gin-gonic/gin v1.9.0\n"
            "\tgithub.com/stretchr/testify v1.8.4 // indirect\n"
            ")\n"
        )
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "go" in deps
        assert "github.com/gin-gonic/gin" in deps["go"]
        assert "github.com/stretchr/testify" in deps["go"]

    def test_go_mod_block_require_no_space(self):
        """Fixed: require( without space before paren."""
        a = _make_analyzer()
        content = (
            "module example.com\n\ngo 1.21\n\n"
            "require(\n"
            "\tgithub.com/some/pkg v1.0.0\n"
            ")\n"
        )
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "go" in deps
        assert "github.com/some/pkg" in deps["go"]

    def test_go_mod_block_close_with_trailing_comment(self):
        """Fixed: ) // end of requires must close the block."""
        a = _make_analyzer()
        content = (
            "module example.com\n\ngo 1.21\n\n"
            "require (\n"
            "\tgithub.com/first/pkg v1.0.0\n"
            ") // end of requires\n"
            "\n"
            "require github.com/outside/block v2.0.0\n"
        )
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "go" in deps
        assert "github.com/first/pkg" in deps["go"]
        # The line after the closed block is a single-line require
        assert "github.com/outside/block" in deps["go"]

    def test_go_mod_single_line_require(self):
        a = _make_analyzer()
        content = "module example.com\n\nrequire github.com/foo/bar v1.2.3\n"
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "go" in deps
        assert "github.com/foo/bar" in deps["go"]

    def test_go_mod_comment_lines_inside_block_skipped(self):
        a = _make_analyzer()
        content = (
            "require (\n"
            "\t// this is a comment\n"
            "\tgithub.com/real/dep v1.0.0\n"
            ")\n"
        )
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "// this is a comment" not in deps.get("go", [])
        assert "github.com/real/dep" in deps["go"]

    def test_go_mod_multiple_blocks(self):
        """Two separate require blocks both parsed."""
        a = _make_analyzer()
        content = (
            "require (\n"
            "\tgithub.com/a/a v1.0.0\n"
            ")\n"
            "\n"
            "require (\n"
            "\tgithub.com/b/b v2.0.0\n"
            ")\n"
        )
        files: dict[str, Optional[str]] = {"go.mod": content}
        deps = a._extract_dependencies(files)
        assert "github.com/a/a" in deps["go"]
        assert "github.com/b/b" in deps["go"]

    def test_none_file_skipped(self):
        a = _make_analyzer()
        deps: dict[str, Optional[str]] = {"requirements.txt": None}
        assert a._extract_dependencies(deps) == {}


# ── Key path selection ────────────────────────────────────────────────────────

class TestSelectKeyPaths:
    def test_manifest_at_root_included(self):
        a = _make_analyzer()
        paths = ["requirements.txt", "README.md", "src/app.py"]
        selected = a._select_key_paths(paths)
        assert "requirements.txt" in selected

    def test_readme_at_root_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["README.md", "src/README.md"])
        assert "README.md" in selected
        # Sub-directory README not picked (depth > 0)
        assert "src/README.md" not in selected

    def test_manifest_depth_3_excluded(self):
        a = _make_analyzer()
        # depth > 2 should be excluded
        paths = ["a/b/c/requirements.txt"]
        selected = a._select_key_paths(paths)
        assert "a/b/c/requirements.txt" not in selected

    def test_manifest_depth_2_included(self):
        a = _make_analyzer()
        paths = ["backend/api/requirements.txt"]  # depth == 2
        selected = a._select_key_paths(paths)
        assert "backend/api/requirements.txt" in selected

    def test_entry_point_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["main.py", "src/helpers.py"])
        assert "main.py" in selected

    def test_cap_at_30_files(self):
        a = _make_analyzer()
        # Use a mix of entry-point names + filler files to exceed the 30-file cap
        paths = ["main.py"] + [f"file{i}.py" for i in range(40)]
        selected = a._select_key_paths(paths)
        assert len(selected) <= 30


# ── Entry point detection ─────────────────────────────────────────────────────

class TestDetectEntryPoints:
    def test_main_py_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["main.py", "utils.py"])
        assert "main.py" in eps

    def test_nested_main_go_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["cmd/main.go", "internal/helper.go"])
        assert "cmd/main.go" in eps

    def test_non_entry_point_ignored(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["helper.py", "utils.ts"])
        assert eps == []


# ── Folder structure mapping ──────────────────────────────────────────────────

class TestMapFolderStructure:
    def test_root_files(self):
        a = _make_analyzer()
        struct = a._map_folder_structure(["README.md", "main.py"])
        assert "README.md" in struct
        assert struct["README.md"] is None

    def test_nested_dirs(self):
        a = _make_analyzer()
        struct = a._map_folder_structure(["src/utils/helper.py"])
        assert "src" in struct
        assert "utils" in struct["src"]
        assert "helper.py" in struct["src"]["utils"]

    def test_depth_truncated_at_3(self):
        a = _make_analyzer()
        struct = a._map_folder_structure(["a/b/c/d/e/deep.py"])
        # max_depth=3 → parts[:4] = ["a","b","c","d"]
        assert "a" in struct
        node = struct["a"]["b"]["c"]
        assert "d" in node  # truncated filename


# ── API route detection ───────────────────────────────────────────────────────

class TestDetectApiRoutes:
    def test_fastapi_get(self):
        a = _make_analyzer()
        content = '@app.get("/health")\ndef health(): ...\n'
        routes = a._detect_api_routes({"main.py": content})
        assert any(r["method"] == "GET" and r["path"] == "/health" for r in routes)

    def test_fastapi_post(self):
        a = _make_analyzer()
        content = '@router.post("/users")\nasync def create_user(): ...\n'
        routes = a._detect_api_routes({"router.py": content})
        assert any(r["method"] == "POST" and r["path"] == "/users" for r in routes)

    def test_express_get(self):
        a = _make_analyzer()
        content = "router.get('/api/items', handler);\n"
        routes = a._detect_api_routes({"routes.js": content})
        assert any(r["method"] == "GET" and r["path"] == "/api/items" for r in routes)

    def test_none_content_skipped(self):
        a = _make_analyzer()
        routes = a._detect_api_routes({"main.py": None})
        assert routes == []

    def test_route_includes_file_key(self):
        a = _make_analyzer()
        content = '@app.get("/ping")\ndef ping(): ...\n'
        routes = a._detect_api_routes({"backend/main.py": content})
        assert routes[0]["file"] == "backend/main.py"


# ── README extraction ─────────────────────────────────────────────────────────

class TestGetReadme:
    def test_readme_truncated_at_600(self):
        a = _make_analyzer()
        long_readme = "x" * 1000
        result = a._get_readme({"README.md": long_readme})
        assert result is not None
        assert len(result) <= 600

    def test_readme_rst_variant(self):
        a = _make_analyzer()
        result = a._get_readme({"README.rst": "Hello"})
        assert result == "Hello"

    def test_no_readme_returns_none(self):
        a = _make_analyzer()
        result = a._get_readme({"main.py": "code"})
        assert result is None

    def test_none_readme_skipped(self):
        a = _make_analyzer()
        result = a._get_readme({"README.md": None})
        assert result is None


# ── Full analyze() — network mocked ──────────────────────────────────────────

FAKE_TREE = [
    {"path": "README.md", "type": "blob"},
    {"path": "main.py", "type": "blob"},
    {"path": "requirements.txt", "type": "blob"},
    {"path": "go.mod", "type": "blob"},
    {"path": "src", "type": "tree"},  # tree node — should be filtered
    {"path": "src/helper.py", "type": "blob"},
]

FAKE_FILES = {
    "README.md": "# My Project\nThis is a test.",
    "main.py": '@app.get("/health")\ndef health(): pass\n',
    "requirements.txt": "fastapi>=0.111\nuvicorn\n",
    "go.mod": "module example.com\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.0\n)\n",
}


@pytest.mark.asyncio
async def test_analyze_preserves_full_repo_url():
    """repo_url in AnalysisResult must be the original URL passed in."""
    original_url = "https://github.com/owner/repo"
    analyzer = RepoAnalyzer(original_url, branch="main")

    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES

        result = await analyzer.analyze()

    assert result.repo_url == original_url


@pytest.mark.asyncio
async def test_analyze_repo_name_and_owner():
    analyzer = RepoAnalyzer("https://github.com/myorg/myrepo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    assert result.owner == "myorg"
    assert result.repo_name == "myrepo"
    assert result.branch == "main"


@pytest.mark.asyncio
async def test_analyze_detects_languages():
    analyzer = RepoAnalyzer("https://github.com/owner/repo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    assert "Python" in result.languages


@pytest.mark.asyncio
async def test_analyze_detects_frameworks_and_deps():
    analyzer = RepoAnalyzer("https://github.com/owner/repo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    assert "FastAPI" in result.frameworks
    assert "python" in result.dependencies
    assert "fastapi>=0.111" in result.dependencies["python"]


@pytest.mark.asyncio
async def test_analyze_go_deps_in_result():
    analyzer = RepoAnalyzer("https://github.com/owner/repo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    assert "go" in result.dependencies
    assert "github.com/gin-gonic/gin" in result.dependencies["go"]


@pytest.mark.asyncio
async def test_analyze_entry_points_detected():
    analyzer = RepoAnalyzer("https://github.com/owner/repo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    assert "main.py" in result.entry_points


@pytest.mark.asyncio
async def test_analyze_tree_nodes_excluded_from_paths():
    """Tree-type items must not appear as paths or languages."""
    analyzer = RepoAnalyzer("https://github.com/owner/repo", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = FAKE_TREE
        mock_files.return_value = FAKE_FILES
        result = await analyzer.analyze()

    # "src" is a tree node and should not appear as a language file
    all_paths = list(result.folder_structure.keys())
    assert "src" in all_paths  # it appears as folder key
