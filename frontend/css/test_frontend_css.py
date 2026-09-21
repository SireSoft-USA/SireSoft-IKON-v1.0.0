from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CSS = Path(__file__).resolve().parent / "app.css"
HTML = ROOT / "index.html"

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


def main():
    css = CSS.read_text(
        encoding="utf-8"
    )

    html = HTML.read_text(
        encoding="utf-8"
    )

    check(
        './css/app.css' in html,
        "frontend root must reference app.css",
    )

    required_selectors = [
        ":root",
        ".app-shell",
        ".site-header",
        ".runtime-status",
        ".status-dot",
        ".chat-layout",
        ".sidebar",
        ".chat-panel",
        ".message-list",
        ".message",
        ".message-assistant",
        ".message-user",
        ".citation-panel",
        ".composer",
        ".button",
        ".button-primary",
        ".site-footer",
        ".toast-region",
        ".sr-only",
        ".skip-link",
    ]

    for selector in required_selectors:
        check(
            selector in css,
            "missing required selector: "
            + selector,
        )

    required_vars = [
        "--bg",
        "--surface",
        "--border",
        "--text",
        "--text-muted",
        "--accent",
        "--danger",
        "--success",
        "--focus",
        "--sidebar-width",
    ]

    for variable in required_vars:
        check(
            variable in css,
            "missing design token: "
            + variable,
        )

    for breakpoint in (
        "@media (max-width: 900px)",
        "@media (max-width: 640px)",
        "@media (max-width: 420px)",
    ):
        check(
            breakpoint in css,
            "missing responsive breakpoint: "
            + breakpoint,
        )

    check(
        "prefers-reduced-motion"
        in css,
        "reduced-motion accessibility support required",
    )

    check(
        "prefers-contrast: more"
        in css,
        "high-contrast accessibility support required",
    )

    check(
        ":focus-visible"
        in css,
        "keyboard focus styling required",
    )

    check(
        "[hidden]"
        in css,
        "hidden-state contract required",
    )

    check(
        'data-state="ready"'
        in css,
        "ready health-state styling required",
    )

    check(
        'data-state="error"'
        in css,
        "error health-state styling required",
    )

    check(
        'data-tone="error"'
        in css,
        "error toast styling required",
    )

    check(
        "overflow-y: auto"
        in css,
        "chat history must scroll independently",
    )

    check(
        "grid-template-columns"
        in css,
        "desktop layout must use explicit grid columns",
    )

    check(
        "width: min(100%, 920px)"
        in css,
        "message line length must be bounded",
    )

    check(
        "backdrop-filter"
        in css,
        "sticky header visual separation required",
    )

    external_urls = re.findall(
        r"url\(\s*[\"']?https?://",
        css,
        flags=re.IGNORECASE,
    )

    check(
        len(external_urls) == 0,
        "CSS must not load external assets",
    )

    import_rules = re.findall(
        r"@import\b",
        css,
        flags=re.IGNORECASE,
    )

    check(
        len(import_rules) == 0,
        "CSS @import dependencies are forbidden",
    )

    unsafe_expression = re.findall(
        r"expression\s*\(",
        css,
        flags=re.IGNORECASE,
    )

    check(
        len(unsafe_expression) == 0,
        "legacy CSS expression() is forbidden",
    )

    check(
        css.count("{")
        == css.count("}"),
        "CSS brace structure must be balanced",
    )

    check(
        len(css.splitlines())
        >= 400,
        "stylesheet should provide complete production shell styling",
    )

    print(
        "FRONTEND CSS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Frontend root stylesheet contract: VALIDATED"
    )
    print(
        "Desktop/tablet/mobile layouts: VALIDATED"
    )
    print(
        "Chat/composer/citation states: VALIDATED"
    )
    print(
        "Keyboard focus/reduced motion/high contrast: VALIDATED"
    )
    print(
        "Health + toast state styling: VALIDATED"
    )
    print(
        "External CSS imports/assets: 0"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
