from app.models.analysis import ChangedFile, ClassifiedFile
from app.services.tree_sitter_service import extract_symbol_hints


dependency_patterns = [
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "go.mod",
    "go.sum",
    "cargo.toml",
    "cargo.lock",
]

lockfile_patterns = [
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "go.sum",
    "cargo.lock",
]

config_patterns = [
    ".env",
    ".env.example",
    "next.config",
    "tsconfig",
    "vite.config",
    "webpack",
    "eslint",
    "prettier",
    "docker-compose",
    ".github/workflows",
    "ci/",
    "config/",
]

migration_patterns = ["migrations/", "alembic/", "prisma/migrations/", "schema.sql"]
shared_patterns = ["shared", "core", "common", "utils"]
api_patterns = ["api/", "/api/", "graphql", "rpc"]
middleware_patterns = ["middleware", "interceptor", "guard"]
generated_patterns = ["dist/", "build/", "coverage/", "generated/", ".min."]
asset_patterns = ["assets/", "public/", "static/"]
frontend_extensions = [".tsx", ".ts", ".jsx", ".js", ".css", ".scss", ".sass", ".less"]
backend_extensions = [".py", ".rb", ".go", ".rs", ".java", ".kt", ".cs"]
sensitive_patterns = [
    "auth",
    "login",
    "session",
    "token",
    "payment",
    "billing",
    "checkout",
    "db",
    "database",
    "schema",
    "config",
    "env",
    "permissions",
    "role",
    "admin",
]


def normalize_pathname(pathname: str) -> str:
    return pathname.replace('\\', '/').lower()


def has_any_pattern(pathname: str, patterns: list[str]) -> bool:
    return any(pattern in pathname for pattern in patterns)


def has_any_suffix(pathname: str, suffixes: list[str]) -> bool:
    return any(pathname.endswith(suffix) for suffix in suffixes)


def classify_path_areas(pathname: str) -> list[str]:
    areas: set[str] = set()

    if "docs/" in pathname or pathname.endswith(".md") or pathname.endswith(".mdx"):
        areas.add("docs")

    if (
        "__tests__" in pathname
        or "tests/" in pathname
        or "spec/" in pathname
        or ".test." in pathname
        or ".spec." in pathname
        or "test_" in pathname
    ):
        areas.add("test")

    if has_any_pattern(pathname, generated_patterns):
        areas.add("generated")

    if has_any_pattern(pathname, asset_patterns) or has_any_suffix(pathname, [".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"]):
        areas.add("asset")

    if has_any_pattern(pathname, dependency_patterns):
        areas.add("dependency")

    if has_any_pattern(pathname, lockfile_patterns):
        areas.add("lockfile")

    if has_any_pattern(pathname, config_patterns):
        areas.add("config")
        areas.add("infra")

    if has_any_pattern(pathname, migration_patterns):
        areas.add("migration")
        areas.add("backend")

    if has_any_pattern(pathname, shared_patterns):
        areas.add("shared_core")

    if has_any_pattern(pathname, api_patterns):
        areas.add("api")
        areas.add("backend")

    if has_any_pattern(pathname, middleware_patterns):
        areas.add("middleware")
        areas.add("backend")

    if (
        "app/" in pathname
        or "components/" in pathname
        or "pages/" in pathname
        or pathname.startswith("frontend/")
        or has_any_suffix(pathname, frontend_extensions)
    ):
        areas.add("frontend")

    if (
        "server/" in pathname
        or pathname.startswith("backend/")
        or has_any_suffix(pathname, backend_extensions)
    ):
        areas.add("backend")

    if has_any_pattern(pathname, sensitive_patterns):
        areas.add("sensitive")

    if not areas:
        areas.add("unknown")

    return sorted(areas)


def build_tags(pathname: str, areas: list[str], symbol_hints: list[str]) -> list[str]:
    tags = {area.replace("_", "-") for area in areas if area != "unknown"}

    if "auth" in pathname or "login" in pathname:
        tags.add("auth")

    if "db" in pathname or "database" in pathname:
        tags.add("db")

    if "api" in pathname:
        tags.add("api")

    for symbol_hint in symbol_hints:
        if symbol_hint != "imports_changed":
            tags.add(symbol_hint.replace("_", "-"))

    return sorted(tags)


def compute_blast_radius_weight(pathname: str, areas: list[str], symbol_hints: list[str]) -> int:
    blast_radius_weight = 1

    if "shared_core" in areas:
        blast_radius_weight += 2

    if "middleware" in areas or "api" in areas:
        blast_radius_weight += 1

    if "sensitive" in areas:
        blast_radius_weight += 2

    if len(pathname.split("/")) <= 2:
        blast_radius_weight += 1

    if "imports_changed" in symbol_hints:
        blast_radius_weight += 1

    if any(hint in symbol_hints for hint in {"authorization", "middleware", "database"}):
        blast_radius_weight += 1

    if "generated" in areas or "asset" in areas:
        blast_radius_weight = max(1, blast_radius_weight - 1)

    if "docs" in areas and "backend" not in areas and "frontend" not in areas:
        blast_radius_weight = 1

    return blast_radius_weight


def classify_files(files: list[ChangedFile]) -> list[ClassifiedFile]:
    classified_files: list[ClassifiedFile] = []

    for file in files:
        pathname = normalize_pathname(file.filename)
        symbol_hints = extract_symbol_hints(file)
        areas = classify_path_areas(pathname)
        is_sensitive = (
            "sensitive" in areas
            or "migration" in areas
            or bool(symbol_hints)
            or ("config" in areas and "infra" in areas and "generated" not in areas)
        ) and "docs" not in areas and "asset" not in areas

        classified_files.append(
            ClassifiedFile(
                **file.model_dump(),
                areas=areas,
                tags=build_tags(pathname, areas, symbol_hints),
                is_sensitive=is_sensitive,
                blast_radius_weight=compute_blast_radius_weight(pathname, areas, symbol_hints),
                symbol_hints=symbol_hints,
            )
        )

    return classified_files
