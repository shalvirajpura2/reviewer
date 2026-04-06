newline = "\n"
ansi_reset = "\033[0m"
ansi_green = "\033[38;5;120m"
ansi_green_soft = "\033[38;5;114m"
ansi_muted = "\033[38;5;145m"
ansi_white = "\033[38;5;255m"
ansi_bold = "\033[1m"
panel_width = 78


reviewer_wordmark = "r e v i e w e r"


def colorize(value: str, color: str, bold: bool = False) -> str:
    prefix = f"{ansi_bold}{color}" if bold else color
    return f"{prefix}{value}{ansi_reset}"


def join_blocks(*blocks: str) -> str:
    normalized_blocks = [block.strip("\n") for block in blocks if block and block.strip()]
    return f"{newline}{newline}".join(normalized_blocks)


def pad_plain(value: str, width: int) -> str:
    visible = len(value)
    if visible >= width:
        return value[:width]
    return f"{value}{' ' * (width - visible)}"


def render_panel(title: str, lines: list[str], footer: str | None = None) -> str:
    inner_width = panel_width - 4
    top = colorize(f"┌{'─' * (panel_width - 2)}┐", ansi_green_soft)
    title_line = colorize("│ ", ansi_green_soft) + colorize(pad_plain(title, inner_width), ansi_white, bold=True) + colorize(" │", ansi_green_soft)
    divider = colorize(f"├{'─' * (panel_width - 2)}┤", ansi_green_soft)
    body_lines = []
    for line in lines:
        body_lines.append(
            colorize("│ ", ansi_green_soft)
            + pad_plain(line, inner_width)
            + colorize(" │", ansi_green_soft)
        )
    footer_block = []
    if footer:
        footer_block.append(divider)
        footer_block.append(
            colorize("│ ", ansi_green_soft)
            + pad_plain(footer, inner_width)
            + colorize(" │", ansi_green_soft)
        )
    bottom = colorize(f"└{'─' * (panel_width - 2)}┘", ansi_green_soft)
    return newline.join([top, title_line, divider, *body_lines, *footer_block, bottom])


def render_banner() -> str:
    eyebrow = colorize("deterministic github review", ansi_muted)
    wordmark = colorize(reviewer_wordmark, ansi_green, bold=True)
    subtitle = colorize("professional pull request analysis in your terminal", ansi_white)
    return newline.join([eyebrow, wordmark, subtitle])


def render_welcome() -> str:
    return join_blocks(
        render_banner(),
        render_panel(
            "Start Here",
            [
                f"{colorize('1.', ansi_green, bold=True)} Sign in with {colorize('reviewer login', ansi_white, bold=True)}",
                f"{colorize('2.', ansi_green, bold=True)} Analyze a pull request with {colorize('reviewer analyze <pr-url>', ansi_white, bold=True)}",
                f"{colorize('3.', ansi_green, bold=True)} Post a GitHub summary with {colorize('reviewer publish-summary <pr-url>', ansi_white, bold=True)}",
            ],
            footer="Use reviewer --help for the full command reference.",
        ),
        render_panel(
            "Session",
            [
                f"{colorize('reviewer whoami', ansi_white, bold=True)}   View the active GitHub account",
                f"{colorize('reviewer logout', ansi_white, bold=True)}   Clear the saved Reviewer session",
            ],
            footer="Your CLI stays signed in until you log out or your token expires.",
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

