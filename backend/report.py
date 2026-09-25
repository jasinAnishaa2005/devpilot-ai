"""
report.py — converts an AnalysisResult into a structured OnboardingReport.

LLM strategy:
  - If OPENAI_API_KEY is set: calls GPT-4o-mini with JSON response_format.
  - Otherwise: falls back to a deterministic template renderer so the app
    is fully usable without any API key.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from models import AnalysisResult, OnboardingReport, ReportSection

_OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

SECTION_TITLES = [
    "Project Overview",
    "Architecture",
    "Important Files",
    "Setup Instructions",
    "Dependencies",
    "Potential Risks",
    "Recommended First Tasks",
]

_SYSTEM_PROMPT = (
    "You are a senior software engineer writing onboarding documentation for a new developer. "
    "You will receive a structured JSON analysis of a GitHub repository. "
    "Return a JSON object whose keys are EXACTLY these section titles (no extras, no renaming):\n"
    + "\n".join(f'  "{t}"' for t in SECTION_TITLES)
    + "\n\nEach value must be a concise markdown string (2–6 sentences or a short bullet list). "
    "Be concrete: reference actual file names, package names, and technology names from the analysis. "
    "Do NOT wrap your response in a markdown fence — return raw JSON only."
)


class ReportGenerator:
    """Generates an OnboardingReport from an AnalysisResult."""

    def __init__(self, result: AnalysisResult) -> None:
        self.result = result

    async def generate(self) -> OnboardingReport:
        if _OPENAI_API_KEY:
            raw = await self._call_openai()
        else:
            raw = self._render_template()

        sections = self._parse_sections(raw)
        return OnboardingReport(
            repo_url=self.result.owner + "/" + self.result.repo_name,
            repo_name=self.result.repo_name,
            sections=sections,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ── LLM path ──────────────────────────────────────────────────────────────

    def _build_prompt(self) -> str:
        r = self.result
        routes_preview = r.api_routes[:10]  # keep prompt compact
        payload = {
            "repo": f"{r.owner}/{r.repo_name}",
            "branch": r.branch,
            "languages": r.languages,
            "frameworks": r.frameworks,
            "dependencies": {
                ecosystem: pkgs[:20] for ecosystem, pkgs in r.dependencies.items()
            },
            "entry_points": r.entry_points,
            "top_level_folders": list(r.folder_structure.keys()),
            "api_routes": routes_preview,
            "readme_excerpt": r.readme_summary or "(none)",
        }
        return json.dumps(payload, indent=2)

    async def _call_openai(self) -> str:
        try:
            import openai  # type: ignore[import-untyped]  # optional dependency
        except ImportError as exc:
            raise RuntimeError(
                "openai package is not installed. "
                "Run: pip install openai  or unset OPENAI_API_KEY to use the template renderer."
            ) from exc

        client = openai.AsyncOpenAI(api_key=_OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": self._build_prompt()},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content or "{}"

    # ── Template fallback ──────────────────────────────────────────────────────

    def _render_template(self) -> str:
        r = self.result
        langs = ", ".join(r.languages.keys()) or "unknown"
        frameworks = ", ".join(r.frameworks) or "none detected"
        entry_points = "\n".join(f"- `{e}`" for e in r.entry_points) or "- Not detected"
        dep_lines: list[str] = []
        for eco, pkgs in r.dependencies.items():
            dep_lines.append(f"**{eco}**: {', '.join(pkgs[:10])}")
        deps_text = "\n".join(dep_lines) or "No dependency files detected."
        routes = r.api_routes[:8]
        routes_text = (
            "\n".join(f"- `{rt['method']} {rt['path']}`" for rt in routes)
            if routes
            else "- No routes detected automatically."
        )
        readme = r.readme_summary or "No README found."

        sections: dict[str, str] = {
            "Project Overview": (
                f"`{r.owner}/{r.repo_name}` (branch: `{r.branch}`).\n\n"
                f"**Languages:** {langs}\n\n"
                f"**Frameworks/Libraries:** {frameworks}\n\n"
                f"{readme[:300]}"
            ),
            "Architecture": (
                f"Top-level folders: {', '.join(f'`{k}`' for k in r.folder_structure.keys()) or 'N/A'}.\n\n"
                f"Detected frameworks suggest the following stack: {frameworks}.\n\n"
                f"Entry points indicate the application starts from:\n{entry_points}"
            ),
            "Important Files": (
                f"**Entry points:**\n{entry_points}\n\n"
                f"**Detected API routes:**\n{routes_text}"
            ),
            "Setup Instructions": (
                "1. Clone the repository: `git clone https://github.com/"
                f"{r.owner}/{r.repo_name}.git`\n"
                "2. Install dependencies (see Dependencies section).\n"
                "3. Copy `.env.example` to `.env` and fill in required variables (if present).\n"
                "4. Run the application via the detected entry point."
            ),
            "Dependencies": deps_text,
            "Potential Risks": (
                "- Verify all environment variables and secrets are configured before running.\n"
                "- Check for outdated dependencies with known CVEs.\n"
                "- Review any hard-coded configuration values in the codebase.\n"
                "- Confirm the correct branch (`"
                + r.branch
                + "`) is being used for development."
            ),
            "Recommended First Tasks": (
                "1. Read the README and any docs/ folder thoroughly.\n"
                "2. Get the application running locally end-to-end.\n"
                "3. Explore the entry points and trace one request through the codebase.\n"
                "4. Run the existing test suite (look for `pytest`, `jest`, `go test`, etc.).\n"
                "5. Pick a small open issue or TODO to familiarise yourself with the PR workflow."
            ),
        }
        return json.dumps(sections)

    # ── Parsing ────────────────────────────────────────────────────────────────

    def _parse_sections(self, raw: str) -> list[ReportSection]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # If the LLM returns malformed JSON, surface it as a single section
            return [ReportSection(title="Raw Output", content=raw)]

        sections: list[ReportSection] = []
        for title in SECTION_TITLES:
            content = data.get(title, f"*{title} — no content generated.*")
            sections.append(ReportSection(title=title, content=str(content)))
        return sections
