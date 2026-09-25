# DevPilot AI — Backend API Contract

Base URL (local dev): `http://127.0.0.1:8000`

---

## 1. Health Check

**`GET /health`**

Quick check that the backend is up.

**Response `200 OK`**
```json
{"status": "healthy"}
```

---

## 2. Analyze a Repository

**`POST /analyze`**

Analyzes a public GitHub repository and returns a structured onboarding report.

### Request

**Headers**
```
Content-Type: application/json
```

**Body**
| Field      | Type   | Required | Default | Notes                                                                 |
|------------|--------|----------|---------|------------------------------------------------------------------------|
| `repo_url` | string | ✅ yes   | —       | Must be a GitHub URL, e.g. `https://github.com/owner/repo`            |
| `branch`   | string | ❌ no    | `null`  | If omitted, backend auto-detects the repo's actual default branch     |

**Example**
```json
{
  "repo_url": "https://github.com/tiangolo/fastapi"
}
```

You normally do **not** need to send `branch` — the backend looks it up automatically via GitHub. Only pass it if you want to force analysis of a specific non-default branch.

### Response — Success `200 OK`

```json
{
  "repo_url": "tiangolo/fastapi",
  "repo_name": "fastapi",
  "sections": [
    { "title": "Project Overview", "content": "..." },
    { "title": "Architecture", "content": "..." },
    { "title": "Important Files", "content": "..." },
    { "title": "Setup Instructions", "content": "..." },
    { "title": "Dependencies", "content": "..." },
    { "title": "Potential Risks", "content": "..." },
    { "title": "Recommended First Tasks", "content": "..." }
  ],
  "generated_at": "2026-09-25T17:51:19.207432+00:00"
}
```

- `sections` is always an array of exactly these 7 report sections, in this order.
- `content` for each section is a **Markdown string** — render it with a Markdown component on the frontend (don't treat it as plain text or HTML).
- `generated_at` is ISO-8601 UTC.

### Response — Errors

**`400 Bad Request`** — invalid input (bad URL, repo not found/private, branch doesn't exist)
```json
{ "detail": "repo_url must be a GitHub repository URL (e.g. https://github.com/owner/repo)" }
```
```json
{ "detail": "Repository 'owner/repo' not found or is private. Set GITHUB_TOKEN to access private repos." }
```

**`500 Internal Server Error`** — unexpected failure during analysis
```json
{ "detail": "Analysis failed: <error message>" }
```

👉 In both error cases, show `detail` directly to the user as the error message — it's already human-readable.

### Timing
Analysis calls GitHub's API and can take a few seconds (sometimes 10-20s for large repos). Show a loading state on the frontend while waiting.

---

## Example (curl)

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/fastapi"}'
```
