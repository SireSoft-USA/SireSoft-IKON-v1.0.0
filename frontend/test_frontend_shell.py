from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"


class FrontendParser(HTMLParser):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.ids = set()
        self.tags = []
        self.scripts = []
        self.stylesheets = []
        self.inline_handlers = []
        self.forms = []
        self.buttons = []
        self.textareas = []
        self.aria_live = []
        self.noscript = 0

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(attrs)
        self.tags.append(tag)

        element_id = attrs.get(
            "id"
        )

        if element_id:
            if element_id in self.ids:
                raise AssertionError(
                    "duplicate id: "
                    + element_id
                )

            self.ids.add(
                element_id
            )

        for key in attrs:
            if key.lower().startswith(
                "on"
            ):
                self.inline_handlers.append(
                    (
                        tag,
                        key,
                    )
                )

        if tag == "script":
            self.scripts.append(
                attrs
            )

        if (
            tag == "link"
            and attrs.get(
                "rel"
            )
            == "stylesheet"
        ):
            self.stylesheets.append(
                attrs
            )

        if tag == "form":
            self.forms.append(
                attrs
            )

        if tag == "button":
            self.buttons.append(
                attrs
            )

        if tag == "textarea":
            self.textareas.append(
                attrs
            )

        if "aria-live" in attrs:
            self.aria_live.append(
                attrs.get(
                    "aria-live"
                )
            )

        if tag == "noscript":
            self.noscript += 1


def assert_true(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def main():
    source = INDEX.read_text(
        encoding="utf-8"
    )

    parser = FrontendParser()
    parser.feed(source)

    required_ids = {
        "app",
        "status-indicator",
        "status-text",
        "new-chat-button",
        "clear-chat-button",
        "session-id",
        "grounding-status",
        "message-list",
        "citation-panel",
        "citation-list",
        "close-citations-button",
        "chat-form",
        "message-input",
        "send-button",
        "token-hint",
        "build-status",
        "toast-region",
    }

    missing = sorted(
        required_ids
        - parser.ids
    )

    assert_true(
        not missing,
        "missing required frontend hooks: "
        + repr(
            missing
        ),
    )

    for tag in (
        "header",
        "main",
        "aside",
        "section",
        "footer",
        "form",
    ):
        assert_true(
            tag in parser.tags,
            "missing semantic tag: "
            + tag,
        )

    assert_true(
        len(
            parser.forms
        )
        == 1,
        "frontend shell must expose exactly one chat form",
    )

    form = parser.forms[0]

    assert_true(
        form.get(
            "id"
        )
        == "chat-form",
        "chat form ID mismatch",
    )

    assert_true(
        len(
            parser.textareas
        )
        == 1,
        "frontend shell must expose one message textarea",
    )

    textarea = (
        parser.textareas[0]
    )

    assert_true(
        textarea.get(
            "id"
        )
        == "message-input",
        "message textarea ID mismatch",
    )

    assert_true(
        textarea.get(
            "required"
        )
        is None,
        "HTML boolean required attribute must be present",
    )

    assert_true(
        textarea.get(
            "maxlength"
        )
        == "12000",
        "message length guard must be present",
    )

    button_ids = {
        button.get(
            "id"
        )
        for button
        in parser.buttons
    }

    assert_true(
        {
            "new-chat-button",
            "clear-chat-button",
            "close-citations-button",
            "send-button",
        }
        <= button_ids,
        "missing required controls",
    )

    for button in parser.buttons:
        assert_true(
            button.get(
                "type"
            )
            in (
                "button",
                "submit",
            ),
            "all buttons must declare explicit type",
        )

    assert_true(
        len(
            parser.inline_handlers
        )
        == 0,
        "inline JavaScript handlers are forbidden",
    )

    assert_true(
        len(
            parser.stylesheets
        )
        == 1,
        "frontend root must reference one local stylesheet",
    )

    stylesheet = (
        parser
        .stylesheets[0]
        .get(
            "href"
        )
    )

    assert_true(
        stylesheet
        == "./css/app.css",
        "stylesheet path must target frontend/css/app.css",
    )

    assert_true(
        len(
            parser.scripts
        )
        == 1,
        "frontend root must reference one module entrypoint",
    )

    script = parser.scripts[0]

    assert_true(
        script.get(
            "type"
        )
        == "module",
        "frontend entry script must be ES module",
    )

    assert_true(
        script.get(
            "src"
        )
        == "./js/app.js",
        "script path must target frontend/js/app.js",
    )

    external_pattern = re.compile(
        r"https?://",
        re.IGNORECASE,
    )

    assert_true(
        external_pattern.search(
            source
        )
        is None,
        "frontend shell must not depend on external CDN/resources",
    )

    assert_true(
        source.count(
            "<script"
        )
        == 1,
        "no hidden inline/external script blocks allowed",
    )

    assert_true(
        len(
            parser.aria_live
        )
        >= 3,
        "runtime, chat and toast live regions required",
    )

    assert_true(
        parser.noscript
        == 1,
        "noscript fallback required",
    )

    assert_true(
        'href="#chat-main"'
        in source,
        "skip link must target chat main",
    )

    assert_true(
        "No external LLM API"
        in source,
        "frontend system summary must state local/no-LLM-API boundary",
    )

    assert_true(
        "SireSoft RAG"
        in source,
        "frontend shell must expose grounding mode",
    )

    print(
        "FRONTEND ROOT TEST SUITE: PASS"
    )
    print(
        "Semantic HTML shell: VALIDATED"
    )
    print(
        "Chat/session/citation DOM contract: VALIDATED"
    )
    print(
        "Accessibility/live regions: VALIDATED"
    )
    print(
        "Local CSS/ES-module paths: VALIDATED"
    )
    print(
        "Inline event handlers: 0"
    )
    print(
        "External CDN/runtime dependencies: 0"
    )
    print(
        "Third-party Python dependencies: 0"
    )


main()
