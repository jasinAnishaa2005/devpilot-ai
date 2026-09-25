# backend/report.py

SECTION_TITLES = [
    "Project Overview",
    "Architecture",
    "Important Files",
    "Setup Instructions",
    "Dependencies",
    "Potential Risks",
    "Recommended First Tasks",
]

SYSTEM_PROMPT = """
You are a senior engineer producing onboarding documentation for a new developer.
You will receive a structured analysis of a GitHub repository.
Return a JSON object with keys matching these exact section titles: {titles}.
Each value is a markdown string (2–6 sentences or a short list).
Be concrete, use file names and tech names from the analysis.
""".format(titles=", ".join(f'"{t}"' for t in SECTION_TITLES))

class ReportGenerator:

    def __init__(self, result: AnalysisResult):
        self.result = result

    async def generate(self) -> OnboardingReport:
        prompt  = self._build_prompt()
        raw     = await self._call_llm(prompt)
        sections = self._parse_sections(raw)
        return OnboardingReport(
            repo_url     = ...,
            sections     = sections,
            generated_at = datetime.utcnow().isoformat(),
        )

    def _build_prompt(self) -> str:
        # Serialize AnalysisResult fields into a tightly structured
        # plain-text block — languages, frameworks, routes, entry points,
        # folder tree, first 300 chars of README.
        # Keeps token cost low; avoids dumping raw file contents.

    async def _call_llm(self, prompt: str) -> str:
        # openai.AsyncOpenAI().chat.completions.create(
        #     model="gpt-4o-mini",
        #     response_format={"type": "json_object"},
        #     messages=[{"role":"system", ...}, {"role":"user", "content": prompt}]
        # )
        # Falls back to a template-based renderer if LLM_API_KEY not set.

    def _parse_sections(self, raw: str) -> list[ReportSection]:
        # json.loads(raw) → iterate SECTION_TITLES → build ReportSection list
        # Gracefully handles missing keys with a placeholder message.