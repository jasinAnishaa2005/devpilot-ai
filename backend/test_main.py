"""
test_main.py — integration tests for the FastAPI application in main.py.

Covers:
- GET /        → 200 with running message.
- GET /health  → 200 {"status": "healthy"}.
- CORS: preflight OPTIONS from allowed origin receives correct headers.
- CORS: preflight from disallowed origin does NOT receive Allow-Origin.
- POST /analyze with invalid body → 422 (Pydantic validation).
- POST /analyze with non-GitHub URL → 400.
- POST /analyze with valid body — happy path with mocked RepoAnalyzer and
  ReportGenerator so no real network calls are made.
- load_dotenv() is called before application imports consume os.getenv().

Uses FastAPI's TestClient (synchronous) for straightforward checks, and
AsyncMock patches for the async analyze/generate methods.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))

# We must call load_dotenv before importing main (mirrors production behaviour).
# In tests we simply ensure it has been called — the real .env may not exist.
from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from main import app  # noqa: E402
from models import AnalysisResult, OnboardingReport, ReportSection  # noqa: E402
from report import SECTION_TITLES  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


# ── Helper: build a minimal OnboardingReport ─────────────────────────────────

def _fake_report(repo_url: str = "https://github.com/owner/repo") -> OnboardingReport:
    return OnboardingReport(
        repo_url=repo_url,
        repo_name="repo",
        sections=[ReportSection(title=t, content=f"Content for {t}") for t in SECTION_TITLES],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _fake_result(repo_url: str = "https://github.com/owner/repo") -> AnalysisResult:
    return AnalysisResult(
        repo_url=repo_url,
        repo_name="repo",
        owner="owner",
        branch="main",
        languages={"Python": 5},
        frameworks=["FastAPI"],
        dependencies={"python": ["fastapi"]},
        entry_points=["main.py"],
        folder_structure={"backend": {}},
        api_routes=[{"method": "GET", "path": "/health", "file": "main.py"}],
        readme_summary="A test repo.",
    )


# ── Basic endpoints ───────────────────────────────────────────────────────────

class TestBasicEndpoints:
    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_message(self):
        resp = client.get("/")
        assert "DevPilot" in resp.json()["message"]

    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_healthy(self):
        resp = client.get("/health")
        assert resp.json() == {"status": "healthy"}


# ── CORS middleware ───────────────────────────────────────────────────────────

class TestCORS:
    def test_allowed_origin_returns_access_control_header(self):
        """Preflight from localhost:3000 should get the header back."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_allowed_origin_127_0_0_1(self):
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"

    def test_disallowed_origin_no_access_control_header(self):
        """Unknown origin must NOT receive the Allow-Origin header."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        header = resp.headers.get("access-control-allow-origin", "")
        assert "evil.example.com" not in header

    def test_allowed_methods_include_get_and_post(self):
        resp = client.options(
            "/analyze",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        # The response may list individual methods or a wildcard
        assert "POST" in allow_methods or allow_methods == "*"


# ── /analyze — request validation ────────────────────────────────────────────

class TestAnalyzeValidation:
    def test_missing_body_returns_422(self):
        resp = client.post("/analyze")
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        resp = client.post("/analyze", json={})
        assert resp.status_code == 422

    def test_non_github_url_returns_422(self):
        """AnalyzeRequest.field_validator rejects non-GitHub URLs via Pydantic → FastAPI → 422."""
        resp = client.post("/analyze", json={"repo_url": "https://gitlab.com/owner/repo"})
        assert resp.status_code == 422

    def test_repo_url_without_repo_returns_400(self):
        resp = client.post("/analyze", json={"repo_url": "https://github.com/onlyowner"})
        assert resp.status_code == 400


# ── /analyze — happy path (mocked) ───────────────────────────────────────────

class TestAnalyzeHappyPath:
    def _post(self, repo_url: str = "https://github.com/owner/repo", branch: str | None = None):
        body = {"repo_url": repo_url}
        if branch:
            body["branch"] = branch
        return client.post("/analyze", json=body)

    def test_returns_200(self):
        fake_result = _fake_result()
        fake_report = _fake_report()

        with patch("main.fetch_default_branch", new_callable=AsyncMock) as mock_branch, \
             patch("main.RepoAnalyzer") as MockAnalyzer, \
             patch("main.ReportGenerator") as MockReport:

            mock_branch.return_value = "main"
            instance_a = MockAnalyzer.return_value
            instance_a.analyze = AsyncMock(return_value=fake_result)
            instance_r = MockReport.return_value
            instance_r.generate = AsyncMock(return_value=fake_report)

            resp = self._post()

        assert resp.status_code == 200

    def test_response_contains_repo_url(self):
        original_url = "https://github.com/owner/repo"
        fake_result = _fake_result(original_url)
        fake_report = _fake_report(original_url)

        with patch("main.fetch_default_branch", new_callable=AsyncMock) as mock_branch, \
             patch("main.RepoAnalyzer") as MockAnalyzer, \
             patch("main.ReportGenerator") as MockReport:

            mock_branch.return_value = "main"
            MockAnalyzer.return_value.analyze = AsyncMock(return_value=fake_result)
            MockReport.return_value.generate = AsyncMock(return_value=fake_report)

            resp = self._post(original_url)

        data = resp.json()
        assert data["repo_url"] == original_url

    def test_explicit_branch_skips_default_branch_fetch(self):
        """When branch is supplied, fetch_default_branch must NOT be called."""
        fake_result = _fake_result()
        fake_report = _fake_report()

        with patch("main.fetch_default_branch", new_callable=AsyncMock) as mock_branch, \
             patch("main.RepoAnalyzer") as MockAnalyzer, \
             patch("main.ReportGenerator") as MockReport:

            mock_branch.return_value = "main"
            MockAnalyzer.return_value.analyze = AsyncMock(return_value=fake_result)
            MockReport.return_value.generate = AsyncMock(return_value=fake_report)

            self._post(branch="develop")

        mock_branch.assert_not_called()

    def test_response_has_all_sections(self):
        fake_result = _fake_result()
        fake_report = _fake_report()

        with patch("main.fetch_default_branch", new_callable=AsyncMock) as mock_branch, \
             patch("main.RepoAnalyzer") as MockAnalyzer, \
             patch("main.ReportGenerator") as MockReport:

            mock_branch.return_value = "main"
            MockAnalyzer.return_value.analyze = AsyncMock(return_value=fake_result)
            MockReport.return_value.generate = AsyncMock(return_value=fake_report)

            resp = self._post()

        data = resp.json()
        assert len(data["sections"]) == len(SECTION_TITLES)


# ── .env loading order ────────────────────────────────────────────────────────

class TestDotEnvLoading:
    def test_load_dotenv_called_before_app_imports(self):
        """
        Verify that the load_dotenv() call in main.py appears before the first
        import that reads os.getenv() at module level.

        We do this by inspecting the source file directly: load_dotenv() must
        appear on a line that comes before the 'from github_client import' line
        and the 'from report import' line, both of which trigger module-level
        os.getenv() calls.
        """
        main_path = os.path.join(os.path.dirname(__file__), "main.py")
        with open(main_path) as f:
            source = f.read()

        lines = source.splitlines()

        def first_line_containing(text: str) -> int:
            for i, line in enumerate(lines, start=1):
                if text in line:
                    return i
            return 999999

        load_dotenv_line = first_line_containing("load_dotenv()")
        github_client_import_line = first_line_containing("from github_client import")
        report_import_line = first_line_containing("from report import")

        assert load_dotenv_line < github_client_import_line, (
            f"load_dotenv() on line {load_dotenv_line} must come before "
            f"'from github_client import' on line {github_client_import_line}"
        )
        assert load_dotenv_line < report_import_line, (
            f"load_dotenv() on line {load_dotenv_line} must come before "
            f"'from report import' on line {report_import_line}"
        )
