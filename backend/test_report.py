"""
test_report.py — unit tests for report.py

Covers:
- ReportGenerator._render_template(): all 7 section titles present,
  content references repo name / branch / language / framework / deps / routes.
- ReportGenerator._parse_sections(): normal parse, missing key fallback,
  malformed JSON returns Raw Output section.
- ReportGenerator.generate(): repo_url and repo_name preserved verbatim
  in the returned OnboardingReport (template path, no OpenAI key).
- SECTION_TITLES constant has exactly the expected values.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from models import AnalysisResult  # noqa: E402
from report import ReportGenerator, SECTION_TITLES  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_result(
    repo_url: str = "https://github.com/owner/myrepo",
    owner: str = "owner",
    repo_name: str = "myrepo",
    branch: str = "main",
) -> AnalysisResult:
    return AnalysisResult(
        repo_url=repo_url,
        repo_name=repo_name,
        owner=owner,
        branch=branch,
        languages={"Python": 10, "TypeScript": 5},
        frameworks=["FastAPI", "React"],
        dependencies={
            "python": ["fastapi>=0.111", "uvicorn"],
            "npm": ["react", "vite"],
        },
        entry_points=["backend/main.py", "src/index.ts"],
        folder_structure={"backend": {}, "src": {}, "docs": {}},
        api_routes=[
            {"method": "GET", "path": "/health", "file": "backend/main.py"},
            {"method": "POST", "path": "/analyze", "file": "backend/main.py"},
        ],
        readme_summary="This project is a DevPilot AI assistant.",
    )


# ── SECTION_TITLES constant ───────────────────────────────────────────────────

def test_section_titles_has_seven_entries():
    assert len(SECTION_TITLES) == 7


def test_section_titles_values():
    expected = {
        "Project Overview",
        "Architecture",
        "Important Files",
        "Setup Instructions",
        "Dependencies",
        "Potential Risks",
        "Recommended First Tasks",
    }
    assert set(SECTION_TITLES) == expected


# ── _render_template ──────────────────────────────────────────────────────────

class TestRenderTemplate:
    def _render(self, result: AnalysisResult | None = None) -> dict:
        r = result or _make_result()
        gen = ReportGenerator(r)
        raw = gen._render_template()
        return json.loads(raw)

    def test_all_section_titles_present(self):
        data = self._render()
        for title in SECTION_TITLES:
            assert title in data, f"Missing section: {title}"

    def test_project_overview_contains_repo_name(self):
        data = self._render()
        assert "myrepo" in data["Project Overview"]

    def test_project_overview_contains_branch(self):
        data = self._render()
        assert "main" in data["Project Overview"]

    def test_project_overview_contains_language(self):
        data = self._render()
        assert "Python" in data["Project Overview"]

    def test_project_overview_contains_framework(self):
        data = self._render()
        assert "FastAPI" in data["Project Overview"]

    def test_project_overview_contains_readme_excerpt(self):
        data = self._render()
        assert "DevPilot" in data["Project Overview"]

    def test_architecture_mentions_entry_points(self):
        data = self._render()
        assert "backend/main.py" in data["Architecture"]

    def test_important_files_shows_routes(self):
        data = self._render()
        assert "/health" in data["Important Files"]

    def test_setup_instructions_contains_clone_command(self):
        data = self._render()
        assert "git clone" in data["Setup Instructions"]
        assert "owner/myrepo" in data["Setup Instructions"]

    def test_dependencies_mentions_python_deps(self):
        data = self._render()
        assert "fastapi>=0.111" in data["Dependencies"]

    def test_dependencies_mentions_npm_deps(self):
        data = self._render()
        assert "react" in data["Dependencies"]

    def test_potential_risks_contains_branch(self):
        data = self._render()
        assert "main" in data["Potential Risks"]

    def test_recommended_first_tasks_is_non_empty(self):
        data = self._render()
        assert len(data["Recommended First Tasks"]) > 0

    def test_no_readme_handled_gracefully(self):
        r = _make_result()
        r.readme_summary = None
        gen = ReportGenerator(r)
        data = json.loads(gen._render_template())
        assert "Project Overview" in data  # should not raise


# ── _parse_sections ───────────────────────────────────────────────────────────

class TestParseSections:
    def _gen(self) -> ReportGenerator:
        return ReportGenerator(_make_result())

    def test_all_titles_parsed(self):
        gen = self._gen()
        raw = json.dumps({t: f"content for {t}" for t in SECTION_TITLES})
        sections = gen._parse_sections(raw)
        titles = [s.title for s in sections]
        assert titles == SECTION_TITLES

    def test_missing_key_uses_placeholder(self):
        gen = self._gen()
        raw = json.dumps({})  # no sections at all
        sections = gen._parse_sections(raw)
        for s in sections:
            assert "no content generated" in s.content

    def test_partial_keys_fallback(self):
        gen = self._gen()
        raw = json.dumps({"Project Overview": "hello"})
        sections = gen._parse_sections(raw)
        po = next(s for s in sections if s.title == "Project Overview")
        assert po.content == "hello"
        arch = next(s for s in sections if s.title == "Architecture")
        assert "no content generated" in arch.content

    def test_malformed_json_raw_output_section(self):
        gen = self._gen()
        sections = gen._parse_sections("NOT JSON {{{{")
        assert len(sections) == 1
        assert sections[0].title == "Raw Output"
        assert "NOT JSON" in sections[0].content


# ── generate() — template path (no OPENAI key) ───────────────────────────────

class TestGenerate:
    @pytest.mark.asyncio
    async def test_repo_url_preserved_in_report(self):
        original_url = "https://github.com/owner/myrepo"
        result = _make_result(repo_url=original_url)
        # Ensure template path is used (no key)
        import report as report_module
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            gen = ReportGenerator(result)
            report = await gen.generate()
        finally:
            report_module._OPENAI_API_KEY = original_key

        assert report.repo_url == original_url

    @pytest.mark.asyncio
    async def test_repo_name_preserved_in_report(self):
        result = _make_result(repo_name="myrepo")
        import report as report_module
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            report = await ReportGenerator(result).generate()
        finally:
            report_module._OPENAI_API_KEY = original_key

        assert report.repo_name == "myrepo"

    @pytest.mark.asyncio
    async def test_report_has_all_sections(self):
        result = _make_result()
        import report as report_module
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            report = await ReportGenerator(result).generate()
        finally:
            report_module._OPENAI_API_KEY = original_key

        assert len(report.sections) == len(SECTION_TITLES)

    @pytest.mark.asyncio
    async def test_generated_at_is_iso8601(self):
        result = _make_result()
        import report as report_module
        from datetime import datetime
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            report = await ReportGenerator(result).generate()
        finally:
            report_module._OPENAI_API_KEY = original_key

        # Should parse without error as ISO-8601
        parsed = datetime.fromisoformat(report.generated_at)
        assert parsed is not None


# ═══════════════════════════════════════════════════════════════════════════════
# C++ / CMake template rendering tests
# ═══════════════════════════════════════════════════════════════════════════════

def _make_cpp_result(
    with_src: bool = True,
    with_include: bool = True,
    with_test: bool = False,
    entry_points: list[str] | None = None,
    cmake_deps: list[str] | None = None,
    frameworks: list[str] | None = None,
) -> AnalysisResult:
    """Build a minimal AnalysisResult that looks like a C++ CMake project."""
    folder_structure: dict = {}
    if with_src:
        folder_structure["src"] = {}
    if with_include:
        folder_structure["include"] = {}
    if with_test:
        folder_structure["tests"] = {}

    deps: dict[str, list[str]] = {"cmake_build_system": ["CMake"]}
    if cmake_deps:
        deps["cmake"] = cmake_deps

    return AnalysisResult(
        repo_url="https://github.com/owner/RoyalEscape",
        repo_name="RoyalEscape",
        owner="owner",
        branch="main",
        languages={"C++": 5, "C/C++ Header": 3},
        frameworks=frameworks if frameworks is not None else ["CMake", "SFML"],
        dependencies=deps,
        entry_points=entry_points if entry_points is not None else ["src/main.cpp"],
        folder_structure=folder_structure,
        api_routes=[],
        readme_summary="A C++ game engine built with SFML.",
    )


def _render_cpp(result: AnalysisResult | None = None, **kwargs) -> dict:
    import json
    r = result if result is not None else _make_cpp_result(**kwargs)
    import report as report_module
    original_key = report_module._OPENAI_API_KEY
    report_module._OPENAI_API_KEY = None
    try:
        gen = ReportGenerator(r)
        raw = gen._render_template()
    finally:
        report_module._OPENAI_API_KEY = original_key
    return json.loads(raw)


class TestCppRenderTemplate:
    # ── Project Overview ───────────────────────────────────────────────────────

    def test_project_overview_mentions_cpp(self):
        data = _render_cpp()
        assert "C++" in data["Project Overview"]

    def test_project_overview_mentions_sfml(self):
        data = _render_cpp()
        assert "SFML" in data["Project Overview"]

    def test_project_overview_mentions_cmake(self):
        data = _render_cpp()
        assert "CMake" in data["Project Overview"]

    # ── Architecture ───────────────────────────────────────────────────────────

    def test_architecture_mentions_cmake_build_system(self):
        data = _render_cpp()
        assert "CMake" in data["Architecture"]

    def test_architecture_mentions_src_directory(self):
        data = _render_cpp(with_src=True)
        assert "src" in data["Architecture"]

    def test_architecture_mentions_include_directory(self):
        data = _render_cpp(with_include=True)
        assert "include" in data["Architecture"]

    def test_architecture_mentions_test_directory_when_present(self):
        data = _render_cpp(with_test=True)
        arch = data["Architecture"]
        assert "test" in arch.lower()

    def test_architecture_no_test_mention_when_absent(self):
        data = _render_cpp(with_test=False)
        # "test" should not appear when there is no test folder
        assert "test" not in data["Architecture"].lower()

    def test_architecture_mentions_entry_point(self):
        data = _render_cpp()
        assert "main.cpp" in data["Architecture"]

    def test_architecture_no_src_note_when_no_src_folder(self):
        # No src/ or include/ folder → no "Directory layout" bullet block
        data = _render_cpp(with_src=False, with_include=False)
        assert "Directory layout" not in data["Architecture"]
        assert "src/` — C++ source files" not in data["Architecture"]

    # ── Setup Instructions ─────────────────────────────────────────────────────

    def test_setup_contains_cmake_configure_command(self):
        data = _render_cpp()
        assert "cmake .." in data["Setup Instructions"]

    def test_setup_contains_cmake_build_command(self):
        data = _render_cpp()
        assert "cmake --build" in data["Setup Instructions"]

    def test_setup_contains_mkdir_build(self):
        data = _render_cpp()
        assert "mkdir build" in data["Setup Instructions"]

    def test_setup_contains_clone_command(self):
        data = _render_cpp()
        assert "git clone" in data["Setup Instructions"]

    def test_setup_contains_repo_name_in_cd(self):
        data = _render_cpp()
        assert "RoyalEscape" in data["Setup Instructions"]

    def test_setup_mentions_find_package_note(self):
        data = _render_cpp()
        assert "find_package" in data["Setup Instructions"]

    def test_setup_no_pip_install_for_cpp(self):
        """The C++ setup path must not contain Python install instructions."""
        data = _render_cpp()
        assert "pip install" not in data["Setup Instructions"]
        assert ".env.example" not in data["Setup Instructions"]

    # ── Dependencies ───────────────────────────────────────────────────────────

    def test_dependencies_mentions_cmake_build_system(self):
        data = _render_cpp()
        assert "CMake" in data["Dependencies"]

    def test_dependencies_mentions_cmake_deps_when_present(self):
        data = _render_cpp(cmake_deps=["SFML", "OpenCV", "Boost"])
        assert "SFML" in data["Dependencies"]
        assert "OpenCV" in data["Dependencies"]

    def test_dependencies_no_not_detected_message(self):
        """When CMake is detected, must NOT say 'No dependency files detected.'"""
        data = _render_cpp()
        assert "No dependency files detected" not in data["Dependencies"]

    def test_dependencies_only_cmake_build_system_still_not_empty(self):
        """Even with no cmake deps list, CMake build system line must appear."""
        result = _make_cpp_result(cmake_deps=None)
        data = _render_cpp(result)
        assert "CMake" in data["Dependencies"]
        assert "No dependency files detected" not in data["Dependencies"]

    # ── Make fallback ──────────────────────────────────────────────────────────

    def test_make_setup_instructions(self):
        """A Makefile-only project should get 'make' build instructions."""
        result = AnalysisResult(
            repo_url="https://github.com/owner/cproject",
            repo_name="cproject",
            owner="owner",
            branch="main",
            languages={"C": 3},
            frameworks=[],
            dependencies={"make_build_system": ["Make"]},
            entry_points=["main.c"],
            folder_structure={"src": {}},
            api_routes=[],
            readme_summary=None,
        )
        import json, report as report_module
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            raw = ReportGenerator(result)._render_template()
        finally:
            report_module._OPENAI_API_KEY = original_key
        data = json.loads(raw)
        assert "make" in data["Setup Instructions"].lower()
        assert "cmake" not in data["Setup Instructions"].lower()

    def test_make_dependencies_mentions_make(self):
        result = AnalysisResult(
            repo_url="https://github.com/owner/cproject",
            repo_name="cproject",
            owner="owner",
            branch="main",
            languages={"C": 3},
            frameworks=[],
            dependencies={"make_build_system": ["Make"]},
            entry_points=[],
            folder_structure={},
            api_routes=[],
            readme_summary=None,
        )
        import json, report as report_module
        original_key = report_module._OPENAI_API_KEY
        report_module._OPENAI_API_KEY = None
        try:
            raw = ReportGenerator(result)._render_template()
        finally:
            report_module._OPENAI_API_KEY = original_key
        data = json.loads(raw)
        assert "Make" in data["Dependencies"]

    # ── Non-regression: Python project unchanged ───────────────────────────────

    def test_python_project_unaffected_by_cpp_changes(self):
        """A regular Python/FastAPI result must still render the old-style setup."""
        import json
        data = json.loads(ReportGenerator(_make_result())._render_template())
        assert "git clone" in data["Setup Instructions"]
        assert ".env.example" in data["Setup Instructions"]
        assert "cmake" not in data["Setup Instructions"].lower()

    def test_python_deps_still_rendered_correctly(self):
        import json
        data = json.loads(ReportGenerator(_make_result())._render_template())
        # Should use old "**python**: ..." format (not cmake format)
        assert "fastapi>=0.111" in data["Dependencies"]
        assert "No dependency files detected" not in data["Dependencies"]

    # ── All 7 sections always present ─────────────────────────────────────────

    def test_all_section_titles_present_for_cpp(self):
        data = _render_cpp()
        for title in SECTION_TITLES:
            assert title in data, f"Missing section: {title}"

    def test_recommended_tasks_mentions_ctest(self):
        data = _render_cpp()
        assert "ctest" in data["Recommended First Tasks"]
