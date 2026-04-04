from __future__ import annotations

from functools import lru_cache

from app.models.analysis import ChangedFile

try:
    from tree_sitter import Language, Parser
    from tree_sitter_javascript import language as javascript_language
    from tree_sitter_python import language as python_language
except ImportError:
    Language = None
    Parser = None
    javascript_language = None
    python_language = None


high_signal_terms = {
    "authenticate",
    "authorization",
    "permission",
    "middleware",
    "session",
    "token",
    "database",
    "migration",
    "config",
    "admin",
}

language_by_extension = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".py": "python",
}


@lru_cache(maxsize=2)
def build_parser(language_name: str) -> Parser | None:
    if not Parser or not Language:
        return None

    parser = Parser()

    if language_name == "javascript" and javascript_language:
        parser.language = Language(javascript_language())
        return parser

    if language_name == "python" and python_language:
        parser.language = Language(python_language())
        return parser

    return None


def detect_language_name(filename: str) -> str | None:
    lowered_name = filename.lower()

    for extension, language_name in language_by_extension.items():
        if lowered_name.endswith(extension):
            return language_name

    return None


def build_parseable_patch_source(patch_text: str) -> str:
    source_lines: list[str] = []

    for patch_line in patch_text.splitlines():
        if patch_line.startswith(("@@", "+++", "---")):
            continue

        if patch_line.startswith("+"):
            source_lines.append(patch_line[1:])
            continue

        if patch_line.startswith("-"):
            continue

        if patch_line.startswith(" "):
            source_lines.append(patch_line[1:])
            continue

        if patch_line.startswith("\\ No newline at end of file"):
            continue

        source_lines.append(patch_line)

    return "\n".join(source_lines).strip()


def extract_tree_sitter_hints(file: ChangedFile) -> list[str]:
    if not file.patch:
        return []

    language_name = detect_language_name(file.filename)
    if not language_name:
        return []

    parser = build_parser(language_name)
    if not parser:
        return []

    parseable_source = build_parseable_patch_source(file.patch)
    if not parseable_source:
        return []

    try:
        tree = parser.parse(parseable_source.encode("utf-8"))
    except Exception:
        return []

    root_type = tree.root_node.type.lower()
    hints: list[str] = []

    if root_type and root_type != "error":
        hints.append("patch_structure_detected")

    if any(keyword in parseable_source.lower() for keyword in {"import ", "from ", "require("}):
        hints.append("imports_changed")

    return hints


def extract_symbol_hints(file: ChangedFile) -> list[str]:
    if not file.patch:
        return []

    parseable_source = build_parseable_patch_source(file.patch)
    lowered_patch = parseable_source.lower() if parseable_source else file.patch.lower()
    symbol_hints = [term for term in high_signal_terms if term in lowered_patch]
    symbol_hints.extend(extract_tree_sitter_hints(file))

    return sorted(set(symbol_hints))