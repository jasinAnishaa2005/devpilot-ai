# backend/analyzer.py

class RepoAnalyzer:
    """Orchestrates all repo inspection steps."""

    LANG_MAP = {".py": "Python", ".ts": "TypeScript", ".js": "JavaScript",
                ".java": "Java", ".go": "Go", ".rs": "Rust", ...}

    FRAMEWORK_SIGNALS = {
        "requirements.txt": ["fastapi", "django", "flask", "sqlalchemy"],
        "package.json":     ["react", "vue", "next", "express", "nestjs"],
        "pom.xml":          ["spring-boot"],
        "build.gradle":     ["spring"],
        "Cargo.toml":       ["actix", "axum"],
    }

    ENTRY_POINT_PATTERNS = [
        "main.py", "app.py", "index.js", "index.ts",
        "src/main.ts", "src/index.tsx", "App.tsx",
    ]

    def __init__(self, repo_url: str, branch: str = "main"):
        # parse owner/repo from URL
        # initialise github_client

    async def analyze(self) -> AnalysisResult:
        tree   = await self._fetch_tree()       # flat file list
        files  = await self._fetch_key_files()  # content of dep + entry files

        return AnalysisResult(
            repo_name        = ...,
            languages        = self._detect_languages(tree),
            frameworks       = self._detect_frameworks(files),
            dependencies     = self._extract_dependencies(files),
            entry_points     = self._detect_entry_points(tree),
            folder_structure = self._map_folder_structure(tree),
            api_routes       = self._detect_api_routes(files),
            readme_summary   = self._get_readme(files),
        )

    def _detect_languages(self, tree) -> dict[str, int]:
        # count file extensions → map to language names

    def _detect_frameworks(self, files) -> list[str]:
        # scan FRAMEWORK_SIGNALS files for known package names

    def _extract_dependencies(self, files) -> dict[str, list[str]]:
        # parse requirements.txt (line-by-line), package.json (.dependencies),
        # pom.xml (<dependency>), Cargo.toml ([dependencies])

    def _detect_entry_points(self, tree) -> list[str]:
        # match tree paths against ENTRY_POINT_PATTERNS

    def _map_folder_structure(self, tree) -> dict:
        # build nested dict from paths, max depth 3

    def _detect_api_routes(self, files) -> list[dict]:
        # regex scan for:
        #   @app.(get|post|put|delete)\("([^"]+)"\)      — FastAPI/Flask
        #   router.(get|post)\("([^"]+)"                 — Express
        #   @(Get|Post|Put|Delete)\("([^"]+)"\)          — NestJS / Spring