"""
main.py — DevPilot AI FastAPI application entry point.
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # load GITHUB_TOKEN / OPENAI_API_KEY from .env before any other import reads os.getenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import AnalyzeRequest, OnboardingReport
from analyzer import RepoAnalyzer
from report import ReportGenerator
from github_client import parse_owner_repo, fetch_default_branch

app = FastAPI(
    title="DevPilot AI",
    description="AI Developer Assistant for GitHub repositories",
    version="1.0.0",
)

# Allow the Next.js dev server (port 3000) and any same-origin production deploy.
# Adjust origins / methods as needed when the frontend URL is finalised.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
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
