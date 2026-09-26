from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator


# ── Request ────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = None

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if "github.com" not in v:
            raise ValueError("repo_url must be a GitHub repository URL")
        return v


# ── Analyzer output ────────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    repo_url: str                       # original full URL e.g. "https://github.com/owner/repo"
    repo_name: str
    owner: str
    branch: str
    languages: dict[str, int]           # {"Python": 42, "TypeScript": 18}
    frameworks: list[str]               # ["FastAPI", "React"]
    dependencies: dict[str, list[str]]  # {"python": [...], "npm": [...]}
    entry_points: list[str]             # ["backend/main.py"]
    folder_structure: dict              # nested dict, depth ≤ 3
    api_routes: list[dict]              # [{"method": "GET", "path": "/health"}]
    readme_summary: Optional[str] = None


# ── Report output ──────────────────────────────────────────────────────────────

class ReportSection(BaseModel):
    title: str
    content: str


class OnboardingReport(BaseModel):
    repo_url: str
    repo_name: str
    sections: list[ReportSection]
    generated_at: str  # ISO-8601
