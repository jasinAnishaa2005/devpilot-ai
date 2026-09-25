# backend/main.py  (additions)
from fastapi import FastAPI, HTTPException
from models import AnalyzeRequest, OnboardingReport
from analyzer import RepoAnalyzer
from report import ReportGenerator

@app.post("/analyze", response_model=OnboardingReport)
async def analyze_repo(body: AnalyzeRequest):
    try:
        result = await RepoAnalyzer(body.repo_url, body.branch).analyze()
        report = await ReportGenerator(result).generate()
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Analysis failed")