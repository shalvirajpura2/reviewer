newline = "\n"


def join_blocks(*blocks: str) -> str:
    normalized_blocks = [block.strip("\n") for block in blocks if block and block.strip()]
    return f"{newline}{newline}".join(normalized_blocks)


def render_title(title: str, subtitle: str | None = None) -> str:
    lines = [title]
    if subtitle:
        lines.append(subtitle)
    lines.append("=" * max(len(title), 16))
    return newline.join(lines)


def render_section(title: str, lines: list[str]) -> str:
    body = newline.join(lines) if lines else "(none)"
    return newline.join([title, "-" * len(title), body])


def render_key_values(items: list[tuple[str, str]]) -> list[str]:
    if not items:
        return []

    width = max(len(label) for label, _ in items)
    return [f"{label.ljust(width)} : {value}" for label, value in items]


def render_bullets(items: list[str], empty_copy: str) -> list[str]:
    if not items:
        return [f"- {empty_copy}"]
    return [f"- {item}" for item in items]


def render_steps(items: list[str], empty_copy: str) -> list[str]:
    if not items:
        return [f"1. {empty_copy}"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def render_status(label: str, message: str) -> str:
    return f"[{label}] {message}"
