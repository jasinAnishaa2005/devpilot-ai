"""
analyzer.py — inspects a GitHub repository and returns a structured AnalysisResult.

Pipeline:
  1. Fetch the full recursive git tree via github_client.fetch_repo_tree()
  2. Identify which key files (dependency manifests, entry points) to download
  3. Fetch those files concurrently via github_client.fetch_files_batch()
  4. Run all detection passes and return an AnalysisResult
"""
from __future__ import annotations

import json
import re
from typing import Optional

from github_client import fetch_repo_tree, fetch_files_batch, parse_owner_repo
from models import AnalysisResult

# ── Language detection ─────────────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".scala": "Scala",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".sh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".tf": "Terraform",
}

# ── Framework signals ──────────────────────────────────────────────────────────

# Maps a dependency-file name → list of (package_substring, framework_label)
_FRAMEWORK_SIGNALS: dict[str, list[tuple[str, str]]] = {
    "requirements.txt": [
        ("fastapi", "FastAPI"),
        ("django", "Django"),
        ("flask", "Flask"),
        ("starlette", "Starlette"),
        ("sqlalchemy", "SQLAlchemy"),
        ("celery", "Celery"),
        ("pydantic", "Pydantic"),
        ("langchain", "LangChain"),
        ("openai", "OpenAI"),
    ],
    "package.json": [
        ("react", "React"),
        ("next", "Next.js"),
        ("vue", "Vue"),
        ("nuxt", "Nuxt"),
        ("svelte", "Svelte"),
        ("express", "Express"),
        ("fastify", "Fastify"),
        ("nestjs", "NestJS"),
        ("angular", "Angular"),
        ("vite", "Vite"),
        ("tailwindcss", "Tailwind CSS"),
    ],
    "pom.xml": [
        ("spring-boot", "Spring Boot"),
        ("spring-web", "Spring MVC"),
    ],
    "build.gradle": [
        ("spring-boot", "Spring Boot"),
    ],
    "Cargo.toml": [
        ("actix-web", "Actix Web"),
        ("axum", "Axum"),
        ("rocket", "Rocket"),
    ],
    "go.mod": [
        ("gin-gonic", "Gin"),
        ("echo", "Echo"),
        ("fiber", "Fiber"),
    ],
    "Gemfile": [
        ("rails", "Rails"),
        ("sinatra", "Sinatra"),
    ],
}

# ── Entry-point patterns ───────────────────────────────────────────────────────

_ENTRY_POINT_NAMES = {
    "main.py", "app.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "server.js", "server.ts",
    "src/index.ts", "src/index.tsx", "src/main.ts", "src/App.tsx",
    "main.go", "cmd/main.go",
    "main.rs", "src/main.rs",
    "Application.java",
    "Program.cs",
}

# ── API route patterns ─────────────────────────────────────────────────────────

_ROUTE_RE = re.compile(
    r"""
    (?:
        @(?:app|router)\.(get|post|put|patch|delete|options|head)\s*\(\s*["']([^"']+)["']  # FastAPI/Flask
      | router\.(get|post|put|patch|delete)\s*\(\s*["']([^"']+)["']                        # Express
      | @(Get|Post|Put|Patch|Delete)\s*\(\s*["']([^"']+)["']                               # NestJS
      | @(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)  # Spring
        \s*\(\s*(?:value\s*=\s*)?["']([^"']+)["']
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


class RepoAnalyzer:
    """Orchestrates all repo inspection passes."""

    def __init__(self, repo_url: str, branch: str = "main") -> None:
        self.repo_url = repo_url
        self.owner, self.repo_name = parse_owner_repo(repo_url)
        self.branch = branch

    async def analyze(self) -> AnalysisResult:
        # 1. Fetch full tree (blob paths only)
        tree = await fetch_repo_tree(self.owner, self.repo_name, self.branch)
        blobs = [item for item in tree if item.get("type") == "blob"]
        paths = [item["path"] for item in blobs]

        # 2. Determine which files to actually download
        key_paths = self._select_key_paths(paths)

        # 3. Download them concurrently
        files: dict[str, Optional[str]] = {}
        if key_paths:
            files = await fetch_files_batch(
                self.owner, self.repo_name, key_paths, self.branch
            )

        return AnalysisResult(
            repo_url=self.repo_url,
            repo_name=self.repo_name,
            owner=self.owner,
            branch=self.branch,
            languages=self._detect_languages(paths),
            frameworks=self._detect_frameworks(files),
            dependencies=self._extract_dependencies(files),
            entry_points=self._detect_entry_points(paths),
            folder_structure=self._map_folder_structure(paths),
            api_routes=self._detect_api_routes(files),
            readme_summary=self._get_readme(files),
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _select_key_paths(self, paths: list[str]) -> list[str]:
        """Return paths we want to fetch content for."""
        selected: list[str] = []
        # Dependency manifests & lock files (top-level only to avoid sub-packages)
        manifest_names = set(_FRAMEWORK_SIGNALS.keys()) | {
            "package-lock.json",
            "yarn.lock",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "Pipfile",
        }
        for p in paths:
            basename = p.split("/")[-1]
            depth = p.count("/")
            if basename in manifest_names and depth <= 2:
                selected.append(p)
            # README variants
            elif basename.lower() in {"readme.md", "readme.rst", "readme.txt"} and depth == 0:
                selected.append(p)
            # Entry points
            elif p in _ENTRY_POINT_NAMES or basename in _ENTRY_POINT_NAMES:
                selected.append(p)
        # Cap at 30 files to stay well within rate limits
        return selected[:30]

    def _detect_languages(self, paths: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in paths:
            ext = "." + p.rsplit(".", 1)[-1] if "." in p else ""
            lang = _EXT_TO_LANG.get(ext.lower())
            if lang:
                counts[lang] = counts.get(lang, 0) + 1
        # Sort descending by file count
        return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))

    def _detect_frameworks(self, files: dict[str, Optional[str]]) -> list[str]:
        found: list[str] = []
        for path, content in files.items():
            if content is None:
                continue
            basename = path.split("/")[-1]
            signals = _FRAMEWORK_SIGNALS.get(basename, [])
            for pkg, label in signals:
                if pkg.lower() in content.lower() and label not in found:
                    found.append(label)
        return found

    def _extract_dependencies(self, files: dict[str, Optional[str]]) -> dict[str, list[str]]:
        deps: dict[str, list[str]] = {}

        for path, content in files.items():
            if content is None:
                continue
            basename = path.split("/")[-1]

            if basename == "requirements.txt":
                lines = [
                    line.strip()
                    for line in content.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                if lines:
                    deps["python"] = lines

            elif basename == "package.json":
                try:
                    pkg = json.loads(content)
                    all_deps = (
                        list(pkg.get("dependencies", {}).keys())
                        + list(pkg.get("devDependencies", {}).keys())
                    )
                    if all_deps:
                        deps["npm"] = all_deps
                except json.JSONDecodeError:
                    pass

            elif basename == "Cargo.toml":
                section = False
                cargo_deps: list[str] = []
                for line in content.splitlines():
                    if line.strip() == "[dependencies]":
                        section = True
                        continue
                    if section and line.startswith("["):
                        section = False
                    if section and "=" in line:
                        cargo_deps.append(line.split("=")[0].strip())
                if cargo_deps:
                    deps["cargo"] = cargo_deps

            elif basename == "go.mod":
                go_deps: list[str] = []
                in_require_block = False
                for line in content.splitlines():
                    line = line.strip()
                    # Block open: "require (" or "require(" with optional trailing comment
                    if re.match(r"^require\s*\(", line):
                        in_require_block = True
                        continue
                    if in_require_block and line.split("//")[0].strip() == ")":
                        in_require_block = False
                        continue
                    # Single-line: require github.com/foo/bar v1.2.3
                    if line.startswith("require ") and not re.match(r"^require\s*\(", line):
                        parts = line.split()
                        if len(parts) >= 2:
                            go_deps.append(parts[1])
                        continue
                    if in_require_block and line and not line.startswith("//"):
                        go_deps.append(line.split()[0])
                if go_deps:
                    deps["go"] = go_deps

        return deps

    def _detect_entry_points(self, paths: list[str]) -> list[str]:
        result: list[str] = []
        for p in paths:
            basename = p.split("/")[-1]
            if p in _ENTRY_POINT_NAMES or basename in _ENTRY_POINT_NAMES:
                result.append(p)
        return result

    def _map_folder_structure(self, paths: list[str], max_depth: int = 3) -> dict:
        root: dict = {}
        for p in paths:
            parts = p.split("/")
            if len(parts) > max_depth + 1:
                parts = parts[: max_depth + 1]
            node = root
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            # Mark files with None, dirs are dicts
            node[parts[-1]] = None
        return root

    def _detect_api_routes(self, files: dict[str, Optional[str]]) -> list[dict]:
        routes: list[dict] = []
        for path, content in files.items():
            if content is None:
                continue
            for m in _ROUTE_RE.finditer(content):
                groups = [g for g in m.groups() if g is not None]
                if len(groups) >= 2:
                    method = groups[0].upper()
                    route_path = groups[1]
                    routes.append({"method": method, "path": route_path, "file": path})
        return routes

    def _get_readme(self, files: dict[str, Optional[str]]) -> Optional[str]:
        for path, content in files.items():
            if path.split("/")[-1].lower().startswith("readme") and content:
                return content[:600].strip()
        return None
