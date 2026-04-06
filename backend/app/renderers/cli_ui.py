newline = "\n"
ansi_reset = "\033[0m"
ansi_green = "\033[38;5;120m"
ansi_green_soft = "\033[38;5;114m"
ansi_muted = "\033[38;5;145m"
ansi_white = "\033[38;5;255m"
ansi_bold = "\033[1m"


reviewer_banner_lines = [
    "RRRRR   EEEEE  V   V  III  EEEEE  W   W  EEEEE  RRRRR",
    "R   RR  E      V   V   I   E      W   W  E      R   RR",
    "RRRRR   EEEE   V   V   I   EEEE   W W W  EEEE   RRRRR",
    "R  RR   E       V V    I   E      WW WW  E      R  RR",
    "R   RR  EEEEE    V    III  EEEEE  W   W  EEEEE  R   RR",
]


def colorize(value: str, color: str, bold: bool = False) -> str:
    prefix = f"{ansi_bold}{color}" if bold else color
    return f"{prefix}{value}{ansi_reset}"


def join_blocks(*blocks: str) -> str:
    normalized_blocks = [block.strip("\n") for block in blocks if block and block.strip()]
    return f"{newline}{newline}".join(normalized_blocks)


def render_banner() -> str:
    colored_lines = []
    palette = [ansi_green_soft, ansi_green, ansi_green_soft, ansi_green, ansi_green_soft]
    for line, color in zip(reviewer_banner_lines, palette):
        colored_lines.append(colorize(line, color, bold=True))
    return newline.join(colored_lines)


def render_welcome() -> str:
    return join_blocks(
        render_banner(),
        colorize("REVIEWER CLI", ansi_white, bold=True) + newline + colorize("Deterministic pull request review for GitHub", ansi_muted),
        render_section(
            "Start Here",
            [
                colorize("1. Run `reviewer login`", ansi_green_soft),
                colorize("2. Run `reviewer analyze <pr-url>`", ansi_green_soft),
                colorize("3. Run `reviewer publish-summary <pr-url>`", ansi_green_soft),
            ],
        ),
        render_section(
            "Helpful Commands",
            [
                colorize("reviewer whoami", ansi_muted),
                colorize("reviewer logout", ansi_muted),
                colorize("reviewer --help", ansi_muted),
            ],
        ),
    )


def render_title(title: str, subtitle: str | None = None) -> str:
    lines = [colorize(title, ansi_white, bold=True)]
    if subtitle:
        lines.append(colorize(subtitle, ansi_muted))
    lines.append(colorize("=" * max(len(title), 16), ansi_green_soft))
    return newline.join(lines)


def render_section(title: str, lines: list[str]) -> str:
    body = newline.join(lines) if lines else "(none)"
    return newline.join([colorize(title, ansi_green, bold=True), colorize("-" * len(title), ansi_green_soft), body])


def render_key_values(items: list[tuple[str, str]]) -> list[str]:
    if not items:
        return []

    width = max(len(label) for label, _ in items)
    return [f"{colorize(label.ljust(width), ansi_green_soft)} : {value}" for label, value in items]


def render_bullets(items: list[str], empty_copy: str) -> list[str]:
    if not items:
        return [f"- {empty_copy}"]
    return [f"- {item}" for item in items]


def render_steps(items: list[str], empty_copy: str) -> list[str]:
    if not items:
        return [f"1. {empty_copy}"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def render_status(label: str, message: str) -> str:
    palette = {
        "ok": ansi_green,
        "next": ansi_green_soft,
        "info": ansi_muted,
        "wait": ansi_white,
        "error": "\033[38;5;203m",
    }
    color = palette.get(label, ansi_muted)
    return f"{colorize(f'[{label}]', color, bold=True)} {message}"

