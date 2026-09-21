PARSER_BASE = "libs/data/parsers/"
SCHEMA_BASE = "libs/data/schema/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/conversation_service/"
CONFIG_BASE = "configs/conversation/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        PARSER_BASE,
        [
            "json_parser.py",
        ],
    ),
    (
        SCHEMA_BASE,
        [
            "message.py",
            "conversation.py",
        ],
    ),
    (
        TOKENIZER_BASE,
        [
            "special_tokens.py",
            "byte_encoder.py",
            "pair_counter.py",
            "vocabulary.py",
            "bpe_trainer.py",
            "bpe_tokenizer.py",
        ],
    ),
    (
        PROTOCOL_BASE,
        [
            "error.py",
            "message.py",
            "request.py",
            "response.py",
        ],
    ),
    (
        SERVICE_BASE,
        [
            "handoff.py",
            "session.py",
            "window.py",
            "result.py",
            "manager.py",
            "service.py",
        ],
    ),
]

for base, filenames in groups:
    for filename in filenames:
        path = base + filename

        source = open(
            path,
            "r",
            encoding="utf-8",
        ).read()

        exec(
            compile(
                source,
                path,
                "exec",
            ),
            namespace,
        )

for filename in [
    "window.py",
    "defaults.py",
    "config.py",
    "codec.py",
    "validator.py",
    "factory.py",
]:
    path = CONFIG_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "conversation config implementation contains forbidden import: "
            + filename
        )

    exec(
        compile(
            source,
            path,
            "exec",
        ),
        namespace,
    )

globals().update(
    namespace
)

ASSERTIONS = 0


class FakeRAGService:
    def __init__(
        self,
    ):
        self.requests = []

    def handle(
        self,
        request,
    ):
        self.requests.append(
            request
        )

        query = request.payload.get(
            "query",
            "",
        )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "answer": {
                        "status": "ok",
                        "answer_text": (
                            "Configured answer for: "
                            + query.split(
                                "\n"
                            )[-1]
                        ),
                        "citations": [
                            {
                                "citation_id": (
                                    "S1"
                                ),
                            },
                        ],
                        "stop_reason": (
                            "max_new_tokens"
                        ),
                    },
                },
            )
        )


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


def eq(
    actual,
    expected,
    message,
):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected),
    )


def expect_error(
    error_type,
    fn,
    message,
):
    global ASSERTIONS
    ASSERTIONS += 1

    try:
        fn()

    except error_type:
        return

    except Exception as error:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(error)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def tokenizer():
    encoder = ByteEncoder()
    specials = SpecialTokens()

    corpus = [
        (
            "SYSTEM USER ASSISTANT "
            "conversation history"
        ),
        (
            "SireSoft software engineering "
            "services clients applications"
        ),
        (
            "What does SireSoft build?"
        ),
        (
            "It builds professional software systems."
        ),
    ]

    model = (
        BPETrainer(
            byte_encoder=encoder,
            pair_counter=PairCounter(),
            vocabulary_factory=Vocabulary,
            special_tokens=specials,
        )
        .train(
            corpus,
            vocab_size=320,
            min_frequency=2,
        )
    )

    return BPETokenizer(
        model,
        encoder,
        specials,
    )


def sample_config():
    return ConversationConfig(
        window=(
            ConversationWindowConfig(
                context_max_tokens=100,
                rag_history_tokens=60,
            )
        ),
        defaults=(
            ConversationDefaultsConfig(
                system_message=(
                    "Answer using grounded company information."
                ),
                title_prefix="Chat",
                metadata={
                    "channel": "web",
                },
            )
        ),
        metadata={
            "profile": "default",
        },
    )


def test_window_config():
    config = (
        ConversationWindowConfig(
            context_max_tokens=200,
            rag_history_tokens=80,
        )
    )

    eq(
        config.context_max_tokens,
        200,
        "context token budget stored",
    )

    expect_error(
        ValueError,
        lambda: (
            ConversationWindowConfig(
                context_max_tokens=0
            )
        ),
        "zero conversation window rejected",
    )


def test_codec():
    text = (
        '{"window":{'
        '"context_max_tokens":300,'
        '"rag_history_tokens":120'
        '},'
        '"defaults":{'
        '"system_message":"Use grounded context.",'
        '"title_prefix":"Support",'
        '"metadata":{"channel":"site"}'
        '},'
        '"metadata":{"profile":"prod"}'
        '}'
    )

    config = (
        ConversationConfigCodec()
        .decode_text(
            text
        )
    )

    eq(
        config.window.context_max_tokens,
        300,
        "codec context budget",
    )

    eq(
        config.defaults.title_prefix,
        "Support",
        "codec title prefix",
    )

    eq(
        config.defaults.metadata[
            "channel"
        ],
        "site",
        "codec default metadata",
    )


def test_validator():
    config = ConversationConfig(
        window=(
            ConversationWindowConfig(
                context_max_tokens=50,
                rag_history_tokens=100,
            )
        )
    )

    result = (
        ConversationConfigValidator()
        .validate(
            config
        )
    )

    codes = [
        item[
            "code"
        ]
        for item
        in result[
            "warnings"
        ]
    ]

    check(
        "RAG_HISTORY_EXCEEDS_CONTEXT_DEFAULT"
        in codes,
        "history/context budget mismatch warned",
    )


def test_manager_generation():
    manager = (
        ConversationConfigFactory()
        .build_manager(
            sample_config(),
            tokenizer(),
            FakeRAGService(),
        )
    )

    check(
        isinstance(
            manager,
            ConversationManager,
        ),
        "factory creates real ConversationManager",
    )

    eq(
        manager
        .window_builder
        .default_max_tokens,
        100,
        "configured direct context budget applied",
    )

    eq(
        manager
        .rag_handoff
        .max_history_tokens,
        60,
        "configured RAG history budget applied",
    )


def test_session_defaults():
    manager = (
        ConversationConfigFactory()
        .build_manager(
            sample_config(),
            tokenizer(),
            FakeRAGService(),
        )
    )

    session = (
        ConversationConfigFactory()
        .create_session(
            manager,
            sample_config(),
            "abc",
            metadata={
                "user_tier": "test",
            },
        )
    )

    eq(
        session.title,
        "Chat abc",
        "default title prefix applied",
    )

    eq(
        session.metadata[
            "channel"
        ],
        "web",
        "default metadata applied",
    )

    eq(
        session.metadata[
            "user_tier"
        ],
        "test",
        "per-session metadata merged",
    )

    eq(
        session.message_count(),
        1,
        "default system message inserted",
    )

    eq(
        session.messages()[
            0
        ].role,
        "system",
        "default first message is system",
    )


def test_real_chat_handoff():
    rag = FakeRAGService()
    tok = tokenizer()
    config = sample_config()

    manager = (
        ConversationConfigFactory()
        .build_manager(
            config,
            tok,
            rag,
        )
    )

    factory = (
        ConversationConfigFactory()
    )

    factory.create_session(
        manager,
        config,
        "chat-1",
    )

    first = manager.chat(
        "chat-1",
        "What does SireSoft build?",
        rag_options={
            "top_k": 3,
        },
    )

    eq(
        first.answer[
            "status"
        ],
        "ok",
        "configured conversation produces successful RAG handoff",
    )

    eq(
        manager.get(
            "chat-1"
        ).message_count(),
        3,
        "system + user + assistant stored after first chat",
    )

    eq(
        rag.requests[
            0
        ].payload[
            "top_k"
        ],
        3,
        "RAG options preserved through conversation handoff",
    )

    second = manager.chat(
        "chat-1",
        "And who is that for?",
    )

    check(
        second
        .history_window
        .token_count
        <= 60,
        "conversation history respects configured RAG token budget",
    )

    check(
        "Conversation history:"
        in rag.requests[
            1
        ].payload[
            "query"
        ],
        "follow-up query includes bounded conversation history",
    )

    check(
        "CURRENT USER MESSAGE:"
        in rag.requests[
            1
        ].payload[
            "query"
        ],
        "handoff separates history from current user message",
    )


def test_context_window():
    manager = (
        ConversationConfigFactory()
        .build_manager(
            sample_config(),
            tokenizer(),
            FakeRAGService(),
        )
    )

    factory = (
        ConversationConfigFactory()
    )

    factory.create_session(
        manager,
        sample_config(),
        "window",
        system_message=(
            "Short system."
        ),
    )

    manager.add_message(
        "window",
        "user",
        "One",
    )

    manager.add_message(
        "window",
        "assistant",
        "Two",
    )

    context = manager.context(
        "window"
    )

    check(
        context.token_count
        <= 100,
        "direct session context obeys configured default budget",
    )

    eq(
        context.max_tokens,
        100,
        "direct context reports configured budget",
    )


def test_closed_session_boundary():
    manager = (
        ConversationConfigFactory()
        .build_manager(
            sample_config(),
            tokenizer(),
            FakeRAGService(),
        )
    )

    ConversationConfigFactory().create_session(
        manager,
        sample_config(),
        "closed",
    )

    manager.close_session(
        "closed"
    )

    expect_error(
        RuntimeError,
        lambda: manager.add_message(
            "closed",
            "user",
            "blocked",
        ),
        "closed configured session rejects new messages",
    )

    manager.reopen_session(
        "closed"
    )

    message = manager.add_message(
        "closed",
        "user",
        "allowed",
    )

    eq(
        message.content,
        "allowed",
        "reopened configured session accepts messages",
    )


def test_service_creation():
    rag = FakeRAGService()

    service = (
        ConversationConfigFactory()
        .build_service(
            sample_config(),
            tokenizer(),
            rag,
        )
    )

    check(
        isinstance(
            service,
            ConversationService,
        ),
        "factory creates ConversationService",
    )

    create = service.handle(
        ServiceRequest(
            "conv-create",
            "conversation_service",
            "create_session",
            payload={
                "session_id": "svc",
            },
        )
    )

    eq(
        create.success,
        True,
        "configured conversation service creates session",
    )

    chat = service.handle(
        ServiceRequest(
            "conv-chat",
            "conversation_service",
            "chat",
            payload={
                "session_id": "svc",
                "text": "Hello",
            },
        )
    )

    eq(
        chat.success,
        True,
        "configured conversation service chats",
    )

    eq(
        chat.data[
            "chat"
        ][
            "answer"
        ][
            "status"
        ],
        "ok",
        "conversation service exposes successful downstream answer",
    )


def main():
    test_window_config()
    test_codec()
    test_validator()
    test_manager_generation()
    test_session_defaults()
    test_real_chat_handoff()
    test_context_window()
    test_closed_session_boundary()
    test_service_creation()

    print(
        "CONVERSATION CONFIG TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Typed conversation/window defaults: VALIDATED"
    )
    print(
        "Handwritten JSON decoding: VALIDATED"
    )
    print(
        "ConversationManager generation: VALIDATED"
    )
    print(
        "Default system/title/metadata application: VALIDATED"
    )
    print(
        "Bounded history handoff to RAG service: VALIDATED"
    )
    print(
        "Session lifecycle boundaries: VALIDATED"
    )
    print(
        "Protocol-level chat integration: VALIDATED"
    )
    print(
        "ConversationService generation: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
