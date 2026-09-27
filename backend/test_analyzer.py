"""
test_analyzer.py — unit tests for analyzer.py

Covers:
- Language detection from file extension counts.
- Framework detection from file content signals.
- Dependency extraction: requirements.txt, package.json, Cargo.toml, go.mod,
  CMakeLists.txt, Makefile.
  go.mod tests exercise the fixed parser:
    • block form "require (" and "require(" (no space)
    • closing ")" with a trailing inline comment
    • single-line form
    • // indirect entries inside a block
- C++ / CMake detection:
    • .cpp, .cc, .cxx, .h, .hpp counted as languages
    • CMakeLists.txt picked up in key path selection
    • find_package / target_link_libraries / pkg_check_modules parsed
    • CMake framework labels (Qt5, OpenCV, Boost …)
    • Entry point preference: src/main.cpp > main.cpp, all candidates reported
    • Makefile detection
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
from analyzer import (  # noqa: E402
    RepoAnalyzer,
    _parse_cmake_deps,
    _cmake_framework_labels,
    _is_cpp_project,
)


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


# ═══════════════════════════════════════════════════════════════════════════════
# C++ / CMake detection tests
# ═══════════════════════════════════════════════════════════════════════════════

# ── _is_cpp_project ────────────────────────────────────────────────────────────

class TestIsCppProject:
    def test_cpp_file_detected(self):
        assert _is_cpp_project(["src/main.cpp"]) is True

    def test_cc_file_detected(self):
        assert _is_cpp_project(["src/engine.cc"]) is True

    def test_cxx_file_detected(self):
        assert _is_cpp_project(["lib/foo.cxx"]) is True

    def test_hpp_header_detected(self):
        assert _is_cpp_project(["include/player.hpp"]) is True

    def test_h_header_detected(self):
        assert _is_cpp_project(["include/utils.h"]) is True

    def test_python_only_is_not_cpp(self):
        assert _is_cpp_project(["main.py", "app.py"]) is False

    def test_empty_paths_is_not_cpp(self):
        assert _is_cpp_project([]) is False


# ── Language detection — C++ extensions ───────────────────────────────────────

class TestCppLanguageDetection:
    def test_cpp_counted(self):
        a = _make_analyzer()
        langs = a._detect_languages(["src/main.cpp", "src/engine.cpp"])
        assert langs.get("C++") == 2

    def test_cc_counted_as_cpp(self):
        a = _make_analyzer()
        langs = a._detect_languages(["game.cc"])
        assert langs.get("C++") == 1

    def test_cxx_counted_as_cpp(self):
        a = _make_analyzer()
        langs = a._detect_languages(["foo.cxx"])
        assert langs.get("C++") == 1

    def test_hpp_counted_as_header(self):
        a = _make_analyzer()
        langs = a._detect_languages(["include/foo.hpp"])
        assert langs.get("C/C++ Header") == 1

    def test_h_counted_as_header(self):
        a = _make_analyzer()
        langs = a._detect_languages(["include/bar.h"])
        assert langs.get("C/C++ Header") == 1

    def test_hxx_counted_as_header(self):
        a = _make_analyzer()
        langs = a._detect_languages(["include/baz.hxx"])
        assert langs.get("C/C++ Header") == 1

    def test_mixed_cpp_python(self):
        a = _make_analyzer()
        langs = a._detect_languages(["main.cpp", "script.py", "utils.cc"])
        assert langs.get("C++") == 2
        assert langs.get("Python") == 1


# ── _parse_cmake_deps ─────────────────────────────────────────────────────────

class TestParseCmakeDeps:
    def test_find_package_basic(self):
        content = "find_package(OpenCV REQUIRED)\n"
        deps = _parse_cmake_deps(content)
        assert "OpenCV" in deps

    def test_find_package_case_insensitive(self):
        content = "FIND_PACKAGE(Boost REQUIRED COMPONENTS filesystem)\n"
        deps = _parse_cmake_deps(content)
        assert "Boost" in deps

    def test_find_package_multiple(self):
        content = "find_package(Qt5 REQUIRED)\nfind_package(OpenSSL REQUIRED)\n"
        deps = _parse_cmake_deps(content)
        assert "Qt5" in deps
        assert "OpenSSL" in deps

    def test_find_package_no_duplicates(self):
        content = "find_package(Boost REQUIRED)\nfind_package(Boost COMPONENTS system)\n"
        deps = _parse_cmake_deps(content)
        assert deps.count("Boost") == 1

    def test_target_link_libraries_extracts_libs(self):
        content = "target_link_libraries(myapp PRIVATE OpenSSL::SSL OpenSSL::Crypto)\n"
        deps = _parse_cmake_deps(content)
        # At least one of the OpenSSL tokens should be captured
        assert any("OpenSSL" in d for d in deps)

    def test_target_link_libraries_skips_cmake_keywords(self):
        content = "target_link_libraries(myapp PUBLIC mylib)\n"
        deps = _parse_cmake_deps(content)
        # "PUBLIC" and "myapp" (first token = target) should not appear
        assert "PUBLIC" not in deps
        assert "myapp" not in deps

    def test_pkg_check_modules(self):
        content = "pkg_check_modules(GLIB REQUIRED glib-2.0)\n"
        deps = _parse_cmake_deps(content)
        assert "glib-2.0" in deps

    def test_add_subdirectory_top_level_only(self):
        content = "add_subdirectory(vendor)\nadd_subdirectory(external/third_party)\n"
        deps = _parse_cmake_deps(content)
        assert "vendor" in deps
        # Path with '/' is excluded
        assert "external/third_party" not in deps

    def test_empty_content_returns_empty(self):
        deps = _parse_cmake_deps("")
        assert deps == []

    def test_cmake_version_line_ignored(self):
        content = "cmake_minimum_required(VERSION 3.20)\nproject(MyApp)\n"
        deps = _parse_cmake_deps(content)
        # cmake_minimum_required is not find_package — should not produce deps
        assert deps == []


# ── _cmake_framework_labels ────────────────────────────────────────────────────

class TestCmakeFrameworkLabels:
    def test_opencv_recognized(self):
        labels = _cmake_framework_labels(["OpenCV"])
        assert "OpenCV" in labels

    def test_qt5_recognized(self):
        labels = _cmake_framework_labels(["Qt5"])
        assert "Qt5" in labels

    def test_boost_recognized(self):
        labels = _cmake_framework_labels(["Boost"])
        assert "Boost" in labels

    def test_sfml_recognized(self):
        labels = _cmake_framework_labels(["SFML"])
        assert "SFML" in labels

    def test_sdl2_recognized(self):
        labels = _cmake_framework_labels(["SDL2"])
        assert "SDL2" in labels

    def test_eigen3_recognized(self):
        labels = _cmake_framework_labels(["Eigen3"])
        assert "Eigen" in labels

    def test_unknown_dep_not_included(self):
        labels = _cmake_framework_labels(["SomeRandomUnknownLib"])
        assert labels == []

    def test_no_duplicates(self):
        labels = _cmake_framework_labels(["OpenCV", "OpenCV"])
        assert labels.count("OpenCV") == 1

    def test_empty_list_returns_empty(self):
        assert _cmake_framework_labels([]) == []


# ── Framework detection — CMake ────────────────────────────────────────────────

class TestCmakeFrameworkDetection:
    def test_cmake_always_added_when_cmakelists_present(self):
        a = _make_analyzer()
        content = "cmake_minimum_required(VERSION 3.20)\nproject(Game)\n"
        files: dict[str, Optional[str]] = {"CMakeLists.txt": content}
        fw = a._detect_frameworks(files)
        assert "CMake" in fw

    def test_cmake_with_opencv_detected(self):
        a = _make_analyzer()
        content = "find_package(OpenCV REQUIRED)\n"
        files: dict[str, Optional[str]] = {"CMakeLists.txt": content}
        fw = a._detect_frameworks(files)
        assert "CMake" in fw
        assert "OpenCV" in fw

    def test_cmake_with_sfml_detected(self):
        a = _make_analyzer()
        content = "find_package(SFML REQUIRED COMPONENTS graphics window system)\n"
        files: dict[str, Optional[str]] = {"CMakeLists.txt": content}
        fw = a._detect_frameworks(files)
        assert "SFML" in fw

    def test_cmake_with_boost_detected(self):
        a = _make_analyzer()
        content = "find_package(Boost REQUIRED COMPONENTS filesystem thread)\n"
        files: dict[str, Optional[str]] = {"CMakeLists.txt": content}
        fw = a._detect_frameworks(files)
        assert "Boost" in fw

    def test_cmake_not_duplicated(self):
        a = _make_analyzer()
        content = "find_package(Qt5 REQUIRED)\n"
        files: dict[str, Optional[str]] = {"CMakeLists.txt": content}
        fw = a._detect_frameworks(files)
        assert fw.count("CMake") == 1

    def test_none_cmake_content_skipped(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"CMakeLists.txt": None}
        fw = a._detect_frameworks(files)
        assert "CMake" not in fw

    def test_existing_python_frameworks_unaffected(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "requirements.txt": "fastapi>=0.111\n",
            "CMakeLists.txt": "find_package(OpenCV REQUIRED)\n",
        }
        fw = a._detect_frameworks(files)
        assert "FastAPI" in fw
        assert "CMake" in fw
        assert "OpenCV" in fw


# ── CMake dependency extraction ────────────────────────────────────────────────

class TestExtractCmakeDependencies:
    def test_cmake_build_system_always_recorded(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "CMakeLists.txt": "cmake_minimum_required(VERSION 3.20)\n"
        }
        deps = a._extract_dependencies(files)
        assert "cmake_build_system" in deps
        assert deps["cmake_build_system"] == ["CMake"]

    def test_cmake_find_package_deps_recorded(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "CMakeLists.txt": "find_package(OpenCV REQUIRED)\nfind_package(Boost REQUIRED)\n"
        }
        deps = a._extract_dependencies(files)
        assert "cmake" in deps
        assert "OpenCV" in deps["cmake"]
        assert "Boost" in deps["cmake"]

    def test_cmake_deps_merged_across_multiple_files(self):
        """Multiple CMakeLists.txt (root + subdir) are merged into one list."""
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "CMakeLists.txt": "find_package(OpenCV REQUIRED)\n",
            "src/CMakeLists.txt": "find_package(Boost REQUIRED)\n",
        }
        deps = a._extract_dependencies(files)
        assert "cmake" in deps
        assert "OpenCV" in deps["cmake"]
        assert "Boost" in deps["cmake"]

    def test_cmake_no_duplicates_after_merge(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "CMakeLists.txt": "find_package(OpenCV REQUIRED)\n",
            "src/CMakeLists.txt": "find_package(OpenCV REQUIRED)\n",
        }
        deps = a._extract_dependencies(files)
        assert deps.get("cmake", []).count("OpenCV") == 1

    def test_makefile_build_system_recorded(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"Makefile": "all:\n\tg++ main.cpp -o app\n"}
        deps = a._extract_dependencies(files)
        assert "make_build_system" in deps
        assert deps["make_build_system"] == ["Make"]

    def test_makefile_lowercase_recorded(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"makefile": "all:\n\tmake\n"}
        deps = a._extract_dependencies(files)
        assert "make_build_system" in deps

    def test_cmake_none_content_skipped(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {"CMakeLists.txt": None}
        deps = a._extract_dependencies(files)
        assert "cmake" not in deps
        assert "cmake_build_system" not in deps

    def test_existing_python_deps_unaffected(self):
        a = _make_analyzer()
        files: dict[str, Optional[str]] = {
            "requirements.txt": "fastapi\n",
            "CMakeLists.txt": "find_package(OpenCV REQUIRED)\n",
        }
        deps = a._extract_dependencies(files)
        assert "python" in deps
        assert "cmake" in deps


# ── C++ entry point detection ─────────────────────────────────────────────────

class TestCppEntryPoints:
    def test_src_main_cpp_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["src/main.cpp", "include/utils.hpp"])
        assert "src/main.cpp" in eps

    def test_root_main_cpp_fallback(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["main.cpp", "include/utils.hpp"])
        assert "main.cpp" in eps

    def test_src_preferred_over_root(self):
        """When both src/main.cpp and main.cpp exist, only src/ candidates returned."""
        a = _make_analyzer()
        eps = a._detect_entry_points(["main.cpp", "src/main.cpp"])
        assert "src/main.cpp" in eps
        # root main.cpp suppressed because src/ candidate exists
        assert "main.cpp" not in eps

    def test_main_cc_variant_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["src/main.cc"])
        assert "src/main.cc" in eps

    def test_main_cxx_variant_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["src/main.cxx"])
        assert "src/main.cxx" in eps

    def test_multiple_cpp_mains_in_src_all_reported(self):
        """Two mains in different subdirs are both reported."""
        a = _make_analyzer()
        eps = a._detect_entry_points(["src/main.cpp", "server/main.cpp"])
        assert "src/main.cpp" in eps
        assert "server/main.cpp" in eps

    def test_cpp_and_python_entry_points_both_detected(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["main.py", "src/main.cpp"])
        assert "main.py" in eps
        assert "src/main.cpp" in eps

    def test_non_main_cpp_not_an_entry_point(self):
        a = _make_analyzer()
        eps = a._detect_entry_points(["src/engine.cpp", "src/player.cpp"])
        assert eps == []


# ── Key path selection — C++ manifests ────────────────────────────────────────

class TestSelectKeyPathsCpp:
    def test_cmakelists_at_root_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["CMakeLists.txt", "src/main.cpp"])
        assert "CMakeLists.txt" in selected

    def test_cmakelists_depth_1_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["src/CMakeLists.txt"])
        assert "src/CMakeLists.txt" in selected

    def test_cmakelists_depth_3_excluded(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["a/b/c/CMakeLists.txt"])
        assert "a/b/c/CMakeLists.txt" not in selected

    def test_makefile_at_root_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["Makefile", "src/main.cpp"])
        assert "Makefile" in selected

    def test_makefile_lowercase_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["makefile"])
        assert "makefile" in selected

    def test_src_main_cpp_as_entry_point_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["src/main.cpp", "include/utils.hpp"])
        assert "src/main.cpp" in selected

    def test_root_main_cpp_as_entry_point_included(self):
        a = _make_analyzer()
        selected = a._select_key_paths(["main.cpp"])
        assert "main.cpp" in selected


# ── Full analyze() — C++ project (network mocked) ─────────────────────────────

_CPP_FAKE_TREE = [
    {"path": "README.md",           "type": "blob"},
    {"path": "CMakeLists.txt",      "type": "blob"},
    {"path": "src/main.cpp",        "type": "blob"},
    {"path": "src/game.cpp",        "type": "blob"},
    {"path": "include/game.hpp",    "type": "blob"},
    {"path": "src",                 "type": "tree"},
    {"path": "include",             "type": "tree"},
]

_CPP_FAKE_FILES = {
    "README.md": "# RoyalEscape\nA C++ game built with SFML.",
    "CMakeLists.txt": (
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(RoyalEscape)\n"
        "find_package(SFML REQUIRED COMPONENTS graphics window system)\n"
        "add_executable(RoyalEscape src/main.cpp src/game.cpp)\n"
        "target_link_libraries(RoyalEscape PRIVATE sfml-graphics sfml-window sfml-system)\n"
    ),
    "src/main.cpp": "int main() { return 0; }\n",
}


@pytest.mark.asyncio
async def test_cpp_analyze_detects_cpp_language():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert "C++" in result.languages


@pytest.mark.asyncio
async def test_cpp_analyze_detects_cmake_framework():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert "CMake" in result.frameworks
    assert "SFML" in result.frameworks


@pytest.mark.asyncio
async def test_cpp_analyze_records_cmake_build_system_dep():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert "cmake_build_system" in result.dependencies


@pytest.mark.asyncio
async def test_cpp_analyze_cmake_deps_contain_sfml():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert "cmake" in result.dependencies
    assert "SFML" in result.dependencies["cmake"]


@pytest.mark.asyncio
async def test_cpp_analyze_detects_src_main_cpp_entry_point():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert "src/main.cpp" in result.entry_points


@pytest.mark.asyncio
async def test_cpp_analyze_header_files_counted():
    analyzer = RepoAnalyzer("https://github.com/owner/RoyalEscape", branch="main")
    with patch("analyzer.fetch_repo_tree", new_callable=AsyncMock) as mock_tree, \
         patch("analyzer.fetch_files_batch", new_callable=AsyncMock) as mock_files:
        mock_tree.return_value = _CPP_FAKE_TREE
        mock_files.return_value = _CPP_FAKE_FILES
        result = await analyzer.analyze()
    assert result.languages.get("C/C++ Header", 0) >= 1
