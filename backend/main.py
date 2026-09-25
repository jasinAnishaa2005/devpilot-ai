from fastapi import FastAPI

app = FastAPI(
    title="DevPilot AI",
    description="AI Developer Assistant for GitHub repositories",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "DevPilot AI Backend is running 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }