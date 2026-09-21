SCHEMA_BASE = "libs/data/schema/"
SERIAL_BASE = "libs/core/serialization/"
TOKENIZER_BASE = "libs/nlp/tokenizer/"
PROTOCOL_BASE = "libs/protocol/"
SERVICE_BASE = "services/conversation_service/"

namespace = {
    "__builtins__": __builtins__,
}

groups = [
    (
        SCHEMA_BASE,
        [
            "message.py",
            "conversation.py",
        ],
    ),
    (
        SERIAL_BASE,
        [
            "binary_writer.py",
            "binary_reader.py",
            "checksum.py",
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
            "validator.py",
            "codec.py",
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
    "session.py",
    "window.py",
    "handoff.py",
    "result.py",
    "manager.py",
    "service.py",
]:
    path = SERVICE_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "conversation_service implementation contains forbidden import: "
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
        + repr(
            actual
        )
        + " expected="
        + repr(
            expected
        )
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

    except Exception as exc:
        raise AssertionError(
            message
            + " | wrong exception="
            + repr(
                exc
            )
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def tokenizer():
    encoder = ByteEncoder()
    specials = SpecialTokens()

    corpus = [
        "USER ASSISTANT SYSTEM conversation history",
        "SireSoft software engineering services clients",
        "What does it build follow up question",
        "It builds web mobile and business systems",
        "first second third fourth fifth message",
        "اردو 中文 multilingual conversation",
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


class FakeRAGService:
    def __init__(
        self,
    ):
        self.requests = []
        self.fail_next = None
        self.block_next = False

    def handle(
        self,
        request,
    ):
        self.requests.append(
            request
        )

        if self.fail_next is not None:
            error = self.fail_next
            self.fail_next = None

            return (
                ServiceResponse
                .error_response(
                    request,
                    error,
                )
            )

        if self.block_next:
            self.block_next = False

            return (
                ServiceResponse
                .success_response(
                    request,
                    data={
                        "answer": {
                            "status": "blocked",
                            "blocked_phase": "input",
                            "answer_text": "",
                            "generated_ids": [],
                            "generated_count": 0,
                            "stop_reason": (
                                "guardrail_input_block"
                            ),
                            "citations": [],
                            "safety": {
                                "input": {
                                    "action": "block",
                                },
                            },
                        },
                    },
                )
            )

        query = request.payload[
            "query"
        ]

        answer_text = (
            "SireSoft builds web, mobile, "
            "and business systems."
        )

        if (
            "CURRENT USER MESSAGE"
            in query
        ):
            answer_text = (
                "It builds web, mobile, "
                "and business systems."
            )

        return (
            ServiceResponse
            .success_response(
                request,
                data={
                    "answer": {
                        "status": "ok",
                        "blocked_phase": None,
                        "answer_text": (
                            answer_text
                        ),
                        "generated_ids": [
                            1,
                            2,
                        ],
                        "generated_count": 2,
                        "stop_reason": (
                            "max_new_tokens"
                        ),
                        "citations": [
                            {
                                "citation_id": "S1",
                                "document_id": (
                                    "siresoft-main"
                                ),
                                "dataset_id": (
                                    "siresoft"
                                ),
                                "text": (
                                    "SireSoft builds systems."
                                ),
                            },
                        ],
                        "safety": {
                            "input": {
                                "action": "allow",
                            },
                            "context": {
                                "action": "allow",
                            },
                            "output": {
                                "action": "allow",
                            },
                        },
                    },
                },
            )
        )


def manager(
    history_tokens=128,
):
    rag = FakeRAGService()

    return (
        build_conversation_manager(
            tokenizer=tokenizer(),
            rag_service=rag,
            max_history_tokens=(
                history_tokens
            ),
        ),
        rag,
    )


def test_session_create_and_messages():
    worker, rag = manager()

    session = worker.create_session(
        "session-1",
        title="SireSoft Chat",
        metadata={
            "channel": "web",
        },
        system_message=(
            "You are a company assistant."
        ),
    )

    eq(
        session.status,
        "open",
        "new session open",
    )

    eq(
        session.message_count(),
        1,
        "system message created",
    )

    eq(
        session.messages()[
            0
        ].role,
        "system",
        "system role preserved",
    )

    user = worker.add_message(
        "session-1",
        "user",
        "Hello",
        metadata={
            "source": "manual",
        },
    )

    eq(
        user.source_index,
        1,
        "message sequence assigned",
    )

    eq(
        session.message_count(),
        2,
        "message appended",
    )

    eq(
        session.metadata[
            "channel"
        ],
        "web",
        "session metadata retained",
    )


def test_session_metadata_update():
    worker, rag = manager()

    worker.create_session(
        "meta",
        metadata={
            "channel": "web",
        },
    )

    worker.update_metadata(
        "meta",
        {
            "language": "en",
        },
    )

    session = worker.get(
        "meta"
    )

    eq(
        session.metadata[
            "channel"
        ],
        "web",
        "metadata merge preserves existing",
    )

    eq(
        session.metadata[
            "language"
        ],
        "en",
        "metadata merge adds value",
    )

    worker.update_metadata(
        "meta",
        {
            "only": True,
        },
        replace=True,
    )

    eq(
        session.metadata,
        {
            "only": True,
        },
        "metadata replace",
    )


def test_close_reopen():
    worker, rag = manager()

    worker.create_session(
        "lifecycle"
    )

    worker.close_session(
        "lifecycle"
    )

    eq(
        worker.get(
            "lifecycle"
        ).status,
        "closed",
        "session closes",
    )

    expect_error(
        RuntimeError,
        lambda: worker.add_message(
            "lifecycle",
            "user",
            "blocked while closed",
        ),
        "closed session rejects append",
    )

    worker.reopen_session(
        "lifecycle"
    )

    worker.add_message(
        "lifecycle",
        "user",
        "works again",
    )

    eq(
        worker.get(
            "lifecycle"
        ).message_count(),
        1,
        "reopened session accepts message",
    )


def test_window_whole_message_trimming():
    tok = tokenizer()
    rag = FakeRAGService()

    window_builder = (
        ConversationWindowBuilder(
            tokenizer=tok,
            default_max_tokens=40,
        )
    )

    handoff = (
        RAGConversationHandoff(
            rag_service=rag,
            window_builder=(
                window_builder
            ),
            max_history_tokens=40,
        )
    )

    worker = ConversationManager(
        Conversation=Conversation,
        Message=Message,
        window_builder=(
            window_builder
        ),
        rag_handoff=handoff,
    )

    worker.create_session(
        "trim"
    )

    worker.add_message(
        "trim",
        "user",
        "first old message about unrelated history",
    )

    worker.add_message(
        "trim",
        "assistant",
        "second response about old history",
    )

    worker.add_message(
        "trim",
        "user",
        "third recent message",
    )

    worker.add_message(
        "trim",
        "assistant",
        "fourth recent response",
    )

    window = worker.context(
        "trim",
        max_tokens=18,
    )

    check(
        window.token_count
        <= 18,
        "history obeys exact token budget",
    )

    check(
        window.dropped_message_count
        > 0,
        "old messages dropped",
    )

    all_messages = (
        worker.get(
            "trim"
        ).messages()
    )

    expected_tail = all_messages[
        len(
            all_messages
        )
        - len(
            window.messages
        ):
    ]

    eq(
        [
            message.source_index
            for message
            in window.messages
        ],
        [
            message.source_index
            for message
            in expected_tail
        ],
        "window is contiguous newest tail",
    )

    for message in window.messages:
        check(
            message.content
            in window.rendered,
            "whole message retained",
        )


def test_chat_first_turn():
    worker, rag = manager()

    worker.create_session(
        "chat"
    )

    result = worker.chat(
        session_id="chat",
        user_text=(
            "What does SireSoft build?"
        ),
        rag_options={
            "top_k": 2,
        },
        trace_id="trace-chat",
        correlation_id="outer-1",
    )

    eq(
        result.answer[
            "status"
        ],
        "ok",
        "chat receives RAG answer",
    )

    eq(
        result.assistant_message.content,
        (
            "SireSoft builds web, mobile, "
            "and business systems."
        ),
        "assistant response stored",
    )

    eq(
        worker.get(
            "chat"
        ).message_count(),
        2,
        "user and assistant stored",
    )

    eq(
        rag.requests[
            0
        ].payload[
            "query"
        ],
        "What does SireSoft build?",
        "first turn sends original query",
    )

    eq(
        rag.requests[
            0
        ].trace_id,
        "trace-chat",
        "trace propagated to RAG",
    )

    eq(
        rag.requests[
            0
        ].correlation_id,
        "outer-1",
        "outer correlation propagated",
    )

    eq(
        result.assistant_message.metadata[
            "citation_ids"
        ],
        [
            "S1",
        ],
        "assistant message tracks citation IDs",
    )


def test_followup_handoff_uses_history():
    worker, rag = manager(
        history_tokens=200
    )

    worker.create_session(
        "follow"
    )

    worker.chat(
        "follow",
        "What does SireSoft build?",
    )

    second = worker.chat(
        "follow",
        "Does it build mobile systems?",
    )

    query = rag.requests[
        1
    ].payload[
        "query"
    ]

    check(
        "Conversation history:"
        in query,
        "follow-up handoff includes history marker",
    )

    check(
        "USER: What does SireSoft build?"
        in query,
        "follow-up includes prior user turn",
    )

    check(
        (
            "ASSISTANT: SireSoft builds web, "
            "mobile, and business systems."
        )
        in query,
        "follow-up includes prior assistant turn",
    )

    check(
        "CURRENT USER MESSAGE:\nDoes it build mobile systems?"
        in query,
        "follow-up distinguishes current message",
    )

    eq(
        second.history_window.message_count
        if hasattr(
            second.history_window,
            "message_count"
        )
        else len(
            second.history_window.messages
        ),
        2,
        "current user message excluded from history prefix",
    )


def test_chat_history_budget():
    worker, rag = manager(
        history_tokens=20
    )

    worker.create_session(
        "budget"
    )

    worker.add_message(
        "budget",
        "user",
        "very old user message with many words",
    )

    worker.add_message(
        "budget",
        "assistant",
        "very old assistant answer with many words",
    )

    worker.add_message(
        "budget",
        "user",
        "recent user",
    )

    worker.add_message(
        "budget",
        "assistant",
        "recent answer",
    )

    result = worker.chat(
        "budget",
        "current question",
    )

    check(
        result.history_window.token_count
        <= 20,
        "RAG handoff history obeys configured token budget",
    )

    check(
        result.history_window.dropped_message_count
        > 0,
        "RAG handoff trims old conversation turns",
    )

    query = rag.requests[
        -1
    ].payload[
        "query"
    ]

    check(
        "current question"
        in query,
        "current query always retained outside trimmed history",
    )


def test_blocked_rag_does_not_add_assistant():
    worker, rag = manager()

    worker.create_session(
        "blocked"
    )

    rag.block_next = True

    result = worker.chat(
        "blocked",
        "",
    )

    eq(
        result.answer[
            "status"
        ],
        "blocked",
        "blocked RAG status preserved",
    )

    eq(
        result.assistant_message,
        None,
        "blocked answer not stored as assistant message",
    )

    eq(
        worker.get(
            "blocked"
        ).message_count(),
        1,
        "user attempt remains in history",
    )

    eq(
        worker.get(
            "blocked"
        ).metadata[
            "last_blocked_phase"
        ],
        "input",
        "session tracks last block phase",
    )


def test_downstream_error():
    worker, rag = manager()

    worker.create_session(
        "downstream"
    )

    rag.fail_next = ProtocolError(
        code="MODEL_NOT_READY",
        message="No model loaded",
        retryable=True,
    )

    expect_error(
        DownstreamRAGError,
        lambda: worker.chat(
            "downstream",
            "hello",
        ),
        "downstream RAG failure surfaced",
    )

    eq(
        worker.get(
            "downstream"
        ).message_count(),
        1,
        "failed downstream call still preserves user turn",
    )


def test_list_delete():
    worker, rag = manager()

    worker.create_session(
        "a"
    )
    worker.create_session(
        "b"
    )

    eq(
        [
            item[
                "session_id"
            ]
            for item
            in worker.list_sessions()
        ],
        [
            "a",
            "b",
        ],
        "session creation order stable",
    )

    deleted = worker.delete_session(
        "a"
    )

    eq(
        deleted.session_id,
        "a",
        "delete returns removed session",
    )

    eq(
        len(
            worker.list_sessions()
        ),
        1,
        "session removed from list",
    )

    expect_error(
        KeyError,
        lambda: worker.get(
            "a"
        ),
        "deleted session unavailable",
    )


def test_service_end_to_end():
    worker, rag = manager()

    service = ConversationService(
        worker
    )

    created = service.handle(
        ServiceRequest(
            "s1",
            "conversation_service",
            "create_session",
            payload={
                "session_id": "service-chat",
                "title": "Chat",
                "metadata": {
                    "channel": "web",
                },
            },
        )
    )

    eq(
        created.success,
        True,
        "service creates session",
    )

    chat = service.handle(
        ServiceRequest(
            "s2",
            "conversation_service",
            "chat",
            payload={
                "session_id": (
                    "service-chat"
                ),
                "text": (
                    "What does SireSoft build?"
                ),
                "rag_options": {
                    "top_k": 1,
                },
            },
            trace_id="trace-service",
        )
    )

    eq(
        chat.success,
        True,
        "service chat succeeds",
    )

    eq(
        chat.data[
            "chat"
        ][
            "assistant_message"
        ][
            "role"
        ],
        "assistant",
        "service returns assistant message",
    )

    context = service.handle(
        ServiceRequest(
            "s3",
            "conversation_service",
            "context",
            payload={
                "session_id": (
                    "service-chat"
                ),
                "max_tokens": 100,
            },
        )
    )

    eq(
        context.success,
        True,
        "service context succeeds",
    )

    check(
        context.data[
            "context"
        ][
            "message_count"
        ] >= 1,
        "service context returns history",
    )


def test_service_downstream_error_mapping():
    worker, rag = manager()

    service = ConversationService(
        worker
    )

    service.handle(
        ServiceRequest(
            "c",
            "conversation_service",
            "create_session",
            payload={
                "session_id": "down",
            },
        )
    )

    rag.fail_next = ProtocolError(
        code="MODEL_NOT_READY",
        message="No model",
        retryable=True,
    )

    response = service.handle(
        ServiceRequest(
            "x",
            "conversation_service",
            "chat",
            payload={
                "session_id": "down",
                "text": "hello",
            },
        )
    )

    eq(
        response.success,
        False,
        "downstream failure maps to conversation service error",
    )

    eq(
        response.error.code,
        "DOWNSTREAM_MODEL_NOT_READY",
        "downstream error code namespaced",
    )

    eq(
        response.error.retryable,
        True,
        "downstream retryability preserved",
    )


def test_protocol_round_trip():
    worker, rag = manager()

    service = ConversationService(
        worker
    )

    codec = ProtocolCodec()

    create_request = ServiceRequest(
        "protocol-create",
        "conversation_service",
        "create_session",
        payload={
            "session_id": (
                "protocol-session"
            ),
            "metadata": {
                "client": "web",
            },
        },
        trace_id="trace-conversation",
    )

    create_request = (
        codec.decode_request(
            codec.encode_request(
                create_request
            )
        )
    )

    create_response = (
        service.handle(
            create_request
        )
    )

    create_response = (
        codec.decode_response(
            codec.encode_response(
                create_response
            )
        )
    )

    eq(
        create_response.success,
        True,
        "session create survives protocol codec",
    )

    chat_request = ServiceRequest(
        "protocol-chat",
        "conversation_service",
        "chat",
        payload={
            "session_id": (
                "protocol-session"
            ),
            "text": (
                "What does SireSoft build?"
            ),
        },
        trace_id="trace-conversation-2",
    )

    chat_request = (
        codec.decode_request(
            codec.encode_request(
                chat_request
            )
        )
    )

    chat_response = (
        service.handle(
            chat_request
        )
    )

    chat_response = (
        codec.decode_response(
            codec.encode_response(
                chat_response
            )
        )
    )

    eq(
        chat_response.success,
        True,
        "chat survives protocol codec",
    )

    eq(
        chat_response.trace_id,
        "trace-conversation-2",
        "conversation trace preserved",
    )

    eq(
        chat_response.data[
            "chat"
        ][
            "answer"
        ][
            "citations"
        ][0][
            "citation_id"
        ],
        "S1",
        "RAG citation survives conversation protocol",
    )


def test_errors():
    worker, rag = manager()

    service = ConversationService(
        worker
    )

    missing = service.handle(
        ServiceRequest(
            "m",
            "conversation_service",
            "get_session",
            payload={
                "session_id": "missing",
            },
        )
    )

    eq(
        missing.error.code,
        "NOT_FOUND",
        "missing session maps to NOT_FOUND",
    )

    wrong = service.handle(
        ServiceRequest(
            "w",
            "rag_service",
            "list_sessions",
        )
    )

    eq(
        wrong.error.code,
        "INVALID_REQUEST",
        "wrong target service rejected",
    )

    unsupported = service.handle(
        ServiceRequest(
            "u",
            "conversation_service",
            "unknown",
        )
    )

    eq(
        unsupported.error.code,
        "INVALID_REQUEST",
        "unsupported operation rejected",
    )

    expect_error(
        TypeError,
        lambda: service.handle(
            {}
        ),
        "non-ServiceRequest rejected",
    )


def test_validation():
    worker, rag = manager()

    expect_error(
        ValueError,
        lambda: worker.create_session(
            ""
        ),
        "empty session ID rejected",
    )

    worker.create_session(
        "dup"
    )

    expect_error(
        ValueError,
        lambda: worker.create_session(
            "dup"
        ),
        "duplicate session rejected",
    )

    expect_error(
        ValueError,
        lambda: ConversationWindowBuilder(
            tokenizer(),
            default_max_tokens=0,
        ),
        "invalid default history budget rejected",
    )


def main():
    test_session_create_and_messages()
    test_session_metadata_update()
    test_close_reopen()
    test_window_whole_message_trimming()
    test_chat_first_turn()
    test_followup_handoff_uses_history()
    test_chat_history_budget()
    test_blocked_rag_does_not_add_assistant()
    test_downstream_error()
    test_list_delete()
    test_service_end_to_end()
    test_service_downstream_error_mapping()
    test_protocol_round_trip()
    test_errors()
    test_validation()

    print(
        "CONVERSATION SERVICE TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Session lifecycle/metadata: VALIDATED"
    )
    print(
        "Ordered user/assistant history: VALIDATED"
    )
    print(
        "Whole-message token-window trimming: VALIDATED"
    )
    print(
        "Bounded conversational RAG handoff: VALIDATED"
    )
    print(
        "RAG citation/trace propagation: VALIDATED"
    )
    print(
        "Blocked-answer persistence policy: VALIDATED"
    )
    print(
        "Downstream error mapping/retryability: VALIDATED"
    )
    print(
        "Protocol service operations: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
