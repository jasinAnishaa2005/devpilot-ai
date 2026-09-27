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
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C/C++ Header",
    ".hxx": "C/C++ Header",
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

# ── C++ detection helpers ──────────────────────────────────────────────────────

# Extensions that identify a C++ source file (not headers)
_CPP_SOURCE_EXTS = {".cpp", ".cc", ".cxx"}
# Extensions that identify a C/C++ header
_CPP_HEADER_EXTS = {".h", ".hpp", ".hxx"}

# CMake find_package() — captures the package name (first token after the command)
_CMAKE_FIND_PACKAGE_RE = re.compile(
    r"^\s*find_package\s*\(\s*([A-Za-z0-9_\-]+)", re.MULTILINE | re.IGNORECASE
)
# target_link_libraries() — captures each library token (non-whitespace, non-paren)
_CMAKE_LINK_LIBS_RE = re.compile(
    r"^\s*target_link_libraries\s*\([^)]*\)", re.MULTILINE | re.IGNORECASE | re.DOTALL
)
# pkg_check_modules() — captures the module list after the target name
_CMAKE_PKG_CHECK_RE = re.compile(
    r"^\s*pkg_check_modules\s*\(\s*\S+\s+([^)]+)\)", re.MULTILINE | re.IGNORECASE
)
# add_subdirectory() — captures the directory name
_CMAKE_SUBDIR_RE = re.compile(
    r"^\s*add_subdirectory\s*\(\s*([A-Za-z0-9_.\-/]+)", re.MULTILINE | re.IGNORECASE
)

# Known CMake package names → human-readable framework label
_CMAKE_KNOWN_FRAMEWORKS: dict[str, str] = {
    "qt5": "Qt5",
    "qt6": "Qt6",
    "qt": "Qt",
    "boost": "Boost",
    "openssl": "OpenSSL",
    "opengl": "OpenGL",
    "glfw3": "GLFW",
    "glfw": "GLFW",
    "glew": "GLEW",
    "glm": "GLM",
    "sfml": "SFML",
    "sdl2": "SDL2",
    "sdl": "SDL",
    "wxwidgets": "wxWidgets",
    "gtk": "GTK",
    "gtkmm": "GTKmm",
    "opencv": "OpenCV",
    "eigen3": "Eigen",
    "eigen": "Eigen",
    "protobuf": "Protobuf",
    "grpc": "gRPC",
    "zlib": "zlib",
    "curl": "libcurl",
    "libcurl": "libcurl",
    "sqlite3": "SQLite",
    "sqlite": "SQLite",
    "gtest": "Google Test",
    "googletest": "Google Test",
    "catch2": "Catch2",
    "fmt": "fmtlib",
    "spdlog": "spdlog",
    "nlohmannjson": "nlohmann/json",
    "abseil": "Abseil",
    "tbb": "Intel TBB",
    "openmp": "OpenMP",
    "mpi": "MPI",
    "cuda": "CUDA",
    "vulkan": "Vulkan",
    "directx": "DirectX",
    "assimp": "Assimp",
    "bullet": "Bullet Physics",
    "box2d": "Box2D",
    "yaml-cpp": "yaml-cpp",
    "yamlcpp": "yaml-cpp",
}


def _is_cpp_project(paths: list[str]) -> bool:
    """Return True if the file tree contains C++ source files."""
    for p in paths:
        ext = "." + p.rsplit(".", 1)[-1].lower() if "." in p else ""
        if ext in _CPP_SOURCE_EXTS or ext in _CPP_HEADER_EXTS:
            return True
    return False


def _parse_cmake_deps(content: str) -> list[str]:
    """
    Extract external dependency names from CMakeLists.txt content.

    Recognises:
      - find_package(PkgName ...)
      - target_link_libraries(... libname ...)   (keyword-filtered)
      - pkg_check_modules(TARGET lib1 lib2 ...)
      - add_subdirectory(name)                   (only top-level names w/o '/')
    """
    deps: list[str] = []
    seen: set[str] = set()

    def _add(name: str) -> None:
        key = name.lower().strip()
        if key and key not in seen:
            seen.add(key)
            deps.append(name.strip())

    # find_package() calls
    for m in _CMAKE_FIND_PACKAGE_RE.finditer(content):
        _add(m.group(1))

    # target_link_libraries() — extract token-by-token, skip CMake keywords
    _CMAKE_LINK_KW = {
        "public", "private", "interface", "target_link_libraries",
        "target_link_options", "keywords_missing_values",
    }
    for block_m in _CMAKE_LINK_LIBS_RE.finditer(content):
        block = block_m.group(0)
        # Strip outer parens content
        inner = re.search(r"\(([^)]*)\)", block, re.DOTALL)
        if inner:
            tokens = inner.group(1).split()
            # First token is always the target name — skip it
            for tok in tokens[1:]:
                clean = tok.strip("()")
                if clean and not clean.startswith("$") and clean.lower() not in _CMAKE_LINK_KW:
                    _add(clean)

    # pkg_check_modules() — everything after the first arg
    for m in _CMAKE_PKG_CHECK_RE.finditer(content):
        for mod in m.group(1).split():
            _add(mod.strip())

    # add_subdirectory() — only direct children (no '/' in name)
    for m in _CMAKE_SUBDIR_RE.finditer(content):
        name = m.group(1).strip()
        if "/" not in name:
            _add(name)

    return deps


def _cmake_framework_labels(dep_names: list[str]) -> list[str]:
    """Map raw CMake dependency names to human-readable framework labels."""
    labels: list[str] = []
    for name in dep_names:
        key = name.lower().replace("-", "").replace("_", "").replace("::", "")
        label = _CMAKE_KNOWN_FRAMEWORKS.get(key) or _CMAKE_KNOWN_FRAMEWORKS.get(name.lower())
        if label and label not in labels:
            labels.append(label)
    return labels


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
    # C/C++ entry points — prefer src/ first, then root
    "src/main.cpp", "src/main.cc", "src/main.cxx",
    "main.cpp", "main.cc", "main.cxx",
}

# C++ entry point basename set for fast lookup
_CPP_MAIN_BASENAMES = {"main.cpp", "main.cc", "main.cxx", "main.c"}

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
            # C++ build system manifests
            "CMakeLists.txt",
            "Makefile",
            "makefile",
            "GNUmakefile",
            "meson.build",
            "conanfile.txt",
            "conanfile.py",
            "vcpkg.json",
        }
        for p in paths:
            basename = p.split("/")[-1]
            depth = p.count("/")
            if basename in manifest_names and depth <= 2:
                selected.append(p)
            # README variants
            elif basename.lower() in {"readme.md", "readme.rst", "readme.txt"} and depth == 0:
                selected.append(p)
            # Entry points (covers both scripted and C++ mains)
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
            # Existing signal-based detection (Python, JS, Java, Rust, Go, Ruby)
            signals = _FRAMEWORK_SIGNALS.get(basename, [])
            for pkg, label in signals:
                if pkg.lower() in content.lower() and label not in found:
                    found.append(label)
            # CMake-specific framework detection
            if basename == "CMakeLists.txt":
                cmake_deps = _parse_cmake_deps(content)
                for label in _cmake_framework_labels(cmake_deps):
                    if label not in found:
                        found.append(label)
                # Always annotate CMake itself as the build system
                if "CMake" not in found:
                    found.insert(0, "CMake")
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

            elif basename == "CMakeLists.txt":
                cmake_deps = _parse_cmake_deps(content)
                if cmake_deps:
                    # Merge across multiple CMakeLists.txt files in the repo
                    existing = deps.get("cmake", [])
                    seen = set(existing)
                    merged = list(existing)
                    for d in cmake_deps:
                        if d not in seen:
                            seen.add(d)
                            merged.append(d)
                    deps["cmake"] = merged
                # Always record CMake itself as the build system
                if "cmake_build_system" not in deps:
                    deps["cmake_build_system"] = ["CMake"]

            elif basename in {"Makefile", "makefile", "GNUmakefile"}:
                if "make_build_system" not in deps:
                    deps["make_build_system"] = ["Make"]

        return deps

    def _detect_entry_points(self, paths: list[str]) -> list[str]:
        """
        Return likely entry point files.

        For C++ projects:
          - Prefer src/main.cpp (and .cc/.cxx variants) over root-level main.cpp.
          - If multiple candidates exist at the same priority level, report all.
          - For other ecosystems the existing set-membership logic is unchanged.
        """
        result: list[str] = []
        cpp_src_mains: list[str] = []   # paths like src/main.cpp, game/main.cc
        cpp_root_mains: list[str] = []  # paths like main.cpp at depth 0

        for p in paths:
            basename = p.split("/")[-1]
            depth = p.count("/")

            if basename in _CPP_MAIN_BASENAMES:
                if depth == 0:
                    cpp_root_mains.append(p)
                else:
                    cpp_src_mains.append(p)
                continue  # handled separately below

            if p in _ENTRY_POINT_NAMES or basename in _ENTRY_POINT_NAMES:
                result.append(p)

        # C++ entry point strategy: prefer src-level, fall back to root-level.
        # Report all candidates so the developer can choose.
        if cpp_src_mains:
            result.extend(cpp_src_mains)
        elif cpp_root_mains:
            result.extend(cpp_root_mains)

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
