"""
main.py — DevPilot AI FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from models import AnalyzeRequest, OnboardingReport
from analyzer import RepoAnalyzer
from report import ReportGenerator
from github_client import parse_owner_repo, fetch_default_branch

app = FastAPI(
    title="DevPilot AI",
    description="AI Developer Assistant for GitHub repositories",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"message": "DevPilot AI Backend is running 🚀"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze", response_model=OnboardingReport)
async def analyze_repo(body: AnalyzeRequest):
    try:
        branch = body.branch
        if not branch:
            owner, repo = parse_owner_repo(body.repo_url)
            branch = await fetch_default_branch(owner, repo)
        result = await RepoAnalyzer(body.repo_url, branch).analyze()
        report = await ReportGenerator(result).generate()
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e
