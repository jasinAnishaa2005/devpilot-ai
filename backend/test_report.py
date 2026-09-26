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
