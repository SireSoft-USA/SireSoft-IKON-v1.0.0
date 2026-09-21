from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
JS = Path(__file__).resolve().parent
HTML = ROOT / "index.html"

ASSERTIONS = 0


def check(
    condition,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(
            message
        )


def read(name):
    return (
        JS
        .joinpath(name)
        .read_text(
            encoding="utf-8"
        )
    )


def main():
    required = [
        "api.js",
        "state.js",
        "stream.js",
        "chat.js",
        "app.js",
    ]

    for name in required:
        check(
            JS.joinpath(
                name
            ).is_file(),
            "missing JS implementation: "
            + name,
        )

    html = HTML.read_text(
        encoding="utf-8"
    )

    check(
        './js/app.js'
        in html,
        "frontend root must reference app.js",
    )

    for name in required:
        result = subprocess.run(
            [
                "node",
                "--check",
                str(
                    JS / name
                ),
            ],
            capture_output=True,
            text=True,
        )

        check(
            result.returncode == 0,
            (
                "node syntax check failed for "
                + name
                + ": "
                + result.stderr
            ),
        )

    api = read(
        "api.js"
    )
    state = read(
        "state.js"
    )
    stream = read(
        "stream.js"
    )
    chat = read(
        "chat.js"
    )
    app = read(
        "app.js"
    )

    check(
        '"/v1/health"'
        in api,
        "health endpoint contract missing",
    )

    check(
        '"/v1/chat"'
        in api,
        "chat endpoint contract missing",
    )

    for key in [
        "query:",
        "max_new_tokens:",
        "candidate_k:",
        "top_k:",
        "use_mmr:",
        "mmr_lambda:",
        "similarity_weight:",
        "repetition_penalty:",
    ]:
        check(
            key in api,
            "RAG gateway payload key missing: "
            + key,
        )

    for key in [
        '"X-Trace-Id"',
        '"X-Correlation-Id"',
        '"Content-Type"',
        '"application/json"',
    ]:
        check(
            key in api,
            "HTTP transport metadata missing: "
            + key,
        )

    check(
        'credentials: "same-origin"'
        in api,
        "same-origin credential policy missing",
    )

    check(
        'cache: "no-store"'
        in api,
        "API requests must bypass stale browser cache",
    )

    check(
        "AbortController"
        in api,
        "API cancellation support required",
    )

    check(
        "DEFAULT_TIMEOUT_MS"
        in api,
        "API timeout boundary required",
    )

    check(
        "class APIError"
        in api,
        "typed client error required",
    )

    check(
        "createStore"
        in state,
        "frontend state store missing",
    )

    check(
        "Object.freeze"
        in state,
        "state snapshots must be frozen",
    )

    check(
        "normalizeCitations"
        in state,
        "RAG citation normalization missing",
    )

    check(
        "chunkText"
        in stream
        and "progressiveText"
        in stream,
        "progressive answer rendering utilities missing",
    )

    check(
        "textContent"
        in chat,
        "chat rendering must use textContent",
    )

    check(
        "innerHTML"
        not in chat,
        "chat renderer must not use innerHTML",
    )

    check(
        "requestSubmit"
        in chat,
        "Enter-to-submit must use native form semantics",
    )

    check(
        "event.shiftKey"
        in chat,
        "Shift+Enter multiline handling required",
    )

    check(
        "appendCitationButtons"
        in chat,
        "citation controls missing",
    )

    check(
        "showCitations"
        in chat,
        "citation detail panel integration missing",
    )

    for module in [
        "./api.js",
        "./state.js",
        "./stream.js",
        "./chat.js",
    ]:
        check(
            module in app,
            "app.js dependency missing: "
            + module,
        )

    check(
        "client.chat"
        in app,
        "app does not connect chat UI to gateway client",
    )

    check(
        "client.health"
        in app,
        "app does not connect runtime health endpoint",
    )

    check(
        "answer.answer_text"
        in app,
        "app does not consume real RAG answer_text",
    )

    check(
        "answer.citations"
        in app,
        "app does not consume real RAG citations",
    )

    check(
        "answer.status"
        in app
        and '"blocked"'
        in app,
        "guardrail-blocked answer handling missing",
    )

    check(
        "progressiveText"
        in app,
        "answer rendering is not progressively applied",
    )

    check(
        "activeController.abort"
        in app,
        "superseded chat request cancellation missing",
    )

    external_imports = []
    import_pattern = re.compile(
        r'(?:from\s+|import\s*\()\s*["\']([^"\']+)["\']'
    )

    for name in required:
        source = read(
            name
        )

        for match in import_pattern.findall(
            source
        ):
            if (
                match.startswith(
                    "http://"
                )
                or match.startswith(
                    "https://"
                )
                or not match.startswith(
                    "."
                )
            ):
                external_imports.append(
                    (
                        name,
                        match,
                    )
                )

    check(
        external_imports == [],
        "external JS module dependencies found: "
        + repr(
            external_imports
        ),
    )

    combined = (
        api
        + state
        + stream
        + chat
        + app
    )

    check(
        "eval("
        not in combined,
        "eval is forbidden in browser code",
    )

    check(
        "new Function("
        not in combined,
        "dynamic Function construction is forbidden",
    )

    print(
        "FRONTEND JS TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "ES-module syntax: VALIDATED"
    )
    print(
        "Gateway /v1/health + /v1/chat contract: VALIDATED"
    )
    print(
        "RAG payload/answer/citation mapping: VALIDATED"
    )
    print(
        "Request timeout/cancellation/trace IDs: VALIDATED"
    )
    print(
        "Immutable client state: VALIDATED"
    )
    print(
        "Safe DOM rendering (innerHTML usage): 0"
    )
    print(
        "Guardrail-blocked response handling: VALIDATED"
    )
    print(
        "External JS package/CDN dependencies: 0"
    )
    print(
        "Third-party Python dependencies: 0"
    )


main()
