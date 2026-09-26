"""
main.py — DevPilot AI FastAPI application entry point.
"""
from __future__ import annotations

<<<<<<< HEAD
from dotenv import load_dotenv
load_dotenv()  # load GITHUB_TOKEN / OPENAI_API_KEY from .env before any other import reads os.getenv
=======
import os
>>>>>>> origin/frontend

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

<<<<<<< HEAD
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
=======
# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow the frontend dev server (and any origin configured via CORS_ORIGINS env
# var) to call the backend.  In production, set CORS_ORIGINS to the exact
# frontend domain instead of "*".
_cors_origins_env = os.getenv("CORS_ORIGINS", "")
_allowed_origins: list[str] = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["http://localhost:3000", "http://127.0.0.1:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
>>>>>>> origin/frontend
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
