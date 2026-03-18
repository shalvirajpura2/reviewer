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


def has_any_pattern(pathname: str, patterns: list[str]) -> bool:
    return any(pattern in pathname for pattern in patterns)


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

    if has_any_pattern(pathname, dependency_patterns):
        areas.add("dependency")

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
        or pathname.endswith(".tsx")
        or pathname.endswith(".css")
    ):
        areas.add("frontend")

    if (
        "server/" in pathname
        or "backend/" in pathname
        or pathname.endswith(".py")
        or pathname.endswith(".rb")
        or pathname.endswith(".go")
    ):
        areas.add("backend")

    if has_any_pattern(pathname, sensitive_patterns):
        areas.add("sensitive")

    if not areas:
        areas.add("unknown")

    return list(areas)


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

    return blast_radius_weight


def classify_files(files: list[ChangedFile]) -> list[ClassifiedFile]:
    classified_files: list[ClassifiedFile] = []

    for file in files:
        pathname = file.filename.lower()
        symbol_hints = extract_symbol_hints(file)
        areas = classify_path_areas(pathname)
        classified_files.append(
            ClassifiedFile(
                **file.model_dump(),
                areas=areas,
                tags=build_tags(pathname, areas, symbol_hints),
                is_sensitive="sensitive" in areas or "migration" in areas or bool(symbol_hints),
                blast_radius_weight=compute_blast_radius_weight(pathname, areas, symbol_hints),
                symbol_hints=symbol_hints,
            )
        )

    return classified_files
