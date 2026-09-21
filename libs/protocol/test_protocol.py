SERIAL_BASE = "libs/core/serialization/"
PROTOCOL_BASE = "libs/protocol/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "binary_writer.py",
    "binary_reader.py",
    "checksum.py",
]:
    path = SERIAL_BASE + filename

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
    "error.py",
    "message.py",
    "request.py",
    "response.py",
    "validator.py",
    "codec.py",
]:
    path = PROTOCOL_BASE + filename

    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "protocol implementation contains forbidden import: "
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

globals().update(namespace)

ASSERTIONS = 0


def check(condition, message):
    global ASSERTIONS
    ASSERTIONS += 1

    if not condition:
        raise AssertionError(message)


def eq(actual, expected, message):
    check(
        actual == expected,
        message
        + " | got="
        + repr(actual)
        + " expected="
        + repr(expected)
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
            + repr(exc)
        )

    raise AssertionError(
        message
        + " | expected exception was not raised"
    )


def test_protocol_error():
    error = ProtocolError(
        code="MODEL_NOT_READY",
        message="Model is not loaded",
        details={
            "model": "sirellm",
            "attempt": 2,
        },
        retryable=True,
    )

    restored = ProtocolError.from_dict(
        error.to_dict()
    )

    eq(
        restored.code,
        "MODEL_NOT_READY",
        "error code round trip",
    )

    eq(
        restored.retryable,
        True,
        "error retryable flag",
    )

    eq(
        restored.details["attempt"],
        2,
        "error details",
    )


def test_message_copy_and_round_trip():
    payload = {
        "nested": {
            "value": 1,
        },
    }

    message = ProtocolMessage(
        message_id="m-1",
        message_type="event",
        service="monitoring_service",
        payload=payload,
        headers={
            "priority": "normal",
        },
        correlation_id="c-1",
        trace_id="t-1",
    )

    payload["nested"]["value"] = 999

    eq(
        message.payload["nested"]["value"],
        1,
        "message deep-copies payload",
    )

    restored = ProtocolMessage.from_dict(
        message.to_dict()
    )

    eq(
        restored.to_dict(),
        message.to_dict(),
        "message dict round trip",
    )


def test_request_message_contract():
    request = ServiceRequest(
        request_id="req-100",
        service="inference_service",
        operation="generate",
        payload={
            "prompt_ids": [
                1,
                2,
                3,
            ],
            "max_new_tokens": 20,
        },
        metadata={
            "user_visible": True,
        },
        trace_id="trace-42",
    )

    message = request.to_message()

    eq(
        message.message_type,
        "request",
        "request message type",
    )

    eq(
        message.service,
        "inference_service",
        "request service",
    )

    restored = ServiceRequest.from_message(
        message
    )

    eq(
        restored.to_dict(),
        request.to_dict(),
        "request message round trip",
    )


def test_success_response_contract():
    request = ServiceRequest(
        "req-1",
        "retrieval_service",
        "search",
        payload={
            "query": "software engineering",
        },
        trace_id="trace-1",
    )

    response = (
        ServiceResponse
        .success_response(
            request,
            data={
                "results": [
                    "chunk-1",
                    "chunk-2",
                ],
            },
        )
    )

    message = response.to_message()

    eq(
        message.message_type,
        "response",
        "successful response message type",
    )

    eq(
        message.correlation_id,
        "req-1",
        "response correlated to request",
    )

    eq(
        message.trace_id,
        "trace-1",
        "trace ID propagated",
    )

    restored = ServiceResponse.from_message(
        message
    )

    eq(
        restored.data["results"],
        [
            "chunk-1",
            "chunk-2",
        ],
        "success response data",
    )

    eq(
        restored.success,
        True,
        "success flag restored",
    )


def test_error_response_contract():
    request = ServiceRequest(
        "req-2",
        "model_registry",
        "load_model",
    )

    error = ProtocolError(
        code="MODEL_NOT_FOUND",
        message="Requested model does not exist",
        details={
            "model_id": "missing",
        },
        retryable=False,
    )

    response = (
        ServiceResponse
        .error_response(
            request,
            error,
        )
    )

    message = response.to_message()

    eq(
        message.message_type,
        "error",
        "failed response message type",
    )

    restored = ServiceResponse.from_message(
        message
    )

    eq(
        restored.success,
        False,
        "failed response success flag",
    )

    eq(
        restored.error.code,
        "MODEL_NOT_FOUND",
        "failed response error code",
    )


def test_validator():
    validator = ProtocolValidator()

    valid = ServiceRequest(
        "r",
        "dataset_service",
        "status",
    ).to_message()

    eq(
        validator.validate_message(
            valid
        ),
        [],
        "valid request message",
    )

    invalid = ProtocolMessage(
        message_id="bad",
        message_type="request",
        service="x",
        payload={},
    )

    errors = validator.validate_message(
        invalid
    )

    check(
        "request payload missing operation"
        in errors,
        "validator detects missing operation",
    )

    expect_error(
        ValueError,
        lambda: validator.require_valid_message(
            invalid
        ),
        "validator raises for invalid message",
    )


def test_codec_request_round_trip():
    codec = ProtocolCodec()

    request = ServiceRequest(
        request_id="req-unicode",
        service="rag_service",
        operation="answer",
        payload={
            "query": "SireSoft کیا کرتا ہے؟",
            "filters": {
                "dataset_id": "siresoft",
            },
            "numbers": [
                1,
                -2,
                3.5,
            ],
            "blob": b"\x00\x01\xff",
        },
        metadata={
            "language": "ur-en",
        },
        correlation_id="conversation-9",
        trace_id="trace-9",
    )

    encoded = codec.encode_request(
        request
    )

    check(
        isinstance(
            encoded,
            bytes,
        ),
        "request encoded to bytes",
    )

    restored = codec.decode_request(
        encoded
    )

    eq(
        restored.to_dict(),
        request.to_dict(),
        "binary request round trip",
    )


def test_codec_response_round_trip():
    codec = ProtocolCodec()

    request = ServiceRequest(
        "req-44",
        "guardrail_service",
        "inspect",
        trace_id="trace-44",
    )

    response = ServiceResponse.success_response(
        request,
        data={
            "action": "allow",
            "risk": 0,
        },
        metadata={
            "phase": "input",
        },
    )

    restored = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        restored.to_dict(),
        response.to_dict(),
        "binary response round trip",
    )


def test_error_codec_round_trip():
    codec = ProtocolCodec()

    request = ServiceRequest(
        "req-45",
        "training_service",
        "start",
    )

    response = ServiceResponse.error_response(
        request,
        ProtocolError(
            "BUSY",
            "Training is already running",
            details={
                "job_id": "train-1",
            },
            retryable=True,
        ),
    )

    restored = codec.decode_response(
        codec.encode_response(
            response
        )
    )

    eq(
        restored.error.code,
        "BUSY",
        "encoded error code",
    )

    eq(
        restored.error.retryable,
        True,
        "encoded retry flag",
    )


def test_codec_determinism():
    codec = ProtocolCodec()

    message = ServiceRequest(
        "req-d",
        "embedding_service",
        "embed",
        payload={
            "b": 2,
            "a": 1,
        },
    )

    first = codec.encode_request(
        message
    )

    second = codec.encode_request(
        message
    )

    eq(
        first,
        second,
        "protocol encoding deterministic",
    )


def test_corruption_detection():
    codec = ProtocolCodec()

    encoded = bytearray(
        codec.encode_request(
            ServiceRequest(
                "req-corrupt",
                "inference_service",
                "generate",
            )
        )
    )

    encoded[-1] ^= 0x01

    expect_error(
        ValueError,
        lambda: codec.decode_request(
            bytes(encoded)
        ),
        "checksum detects protocol corruption",
    )


def test_frame_limit():
    codec = ProtocolCodec(
        max_frame_bytes=80,
    )

    request = ServiceRequest(
        "req-big",
        "dataset_service",
        "ingest",
        payload={
            "text": "x" * 500,
        },
    )

    expect_error(
        ValueError,
        lambda: codec.encode_request(
            request
        ),
        "frame size limit enforced",
    )


def test_service_examples():
    codec = ProtocolCodec()

    examples = [
        ServiceRequest(
            "r1",
            "dataset_service",
            "ingest",
            payload={
                "dataset": "siresoft",
            },
        ),
        ServiceRequest(
            "r2",
            "training_service",
            "train",
            payload={
                "steps": 100,
            },
        ),
        ServiceRequest(
            "r3",
            "retrieval_service",
            "search",
            payload={
                "query": "software",
            },
        ),
        ServiceRequest(
            "r4",
            "rag_service",
            "answer",
            payload={
                "query": "What does SireSoft do?",
            },
        ),
        ServiceRequest(
            "r5",
            "guardrail_service",
            "inspect",
            payload={
                "text": "hello",
            },
        ),
    ]

    for request in examples:
        restored = codec.decode_request(
            codec.encode_request(
                request
            )
        )

        eq(
            restored.service,
            request.service,
            "service request round trip: "
            + request.service,
        )

        eq(
            restored.operation,
            request.operation,
            "service operation round trip: "
            + request.operation,
        )


def test_validation():
    expect_error(
        ValueError,
        lambda: ProtocolMessage(
            "x",
            "invalid",
            "service",
        ),
        "invalid message type",
    )

    expect_error(
        ValueError,
        lambda: ServiceResponse(
            "r",
            "service",
            success=False,
        ),
        "failed response requires error",
    )

    expect_error(
        ValueError,
        lambda: ProtocolCodec(
            max_frame_bytes=0
        ),
        "invalid frame limit",
    )

    expect_error(
        TypeError,
        lambda: ProtocolCodec().decode_message(
            "not bytes"
        ),
        "non-bytes frame rejected",
    )


def main():
    test_protocol_error()
    test_message_copy_and_round_trip()
    test_request_message_contract()
    test_success_response_contract()
    test_error_response_contract()
    test_validator()
    test_codec_request_round_trip()
    test_codec_response_round_trip()
    test_error_codec_round_trip()
    test_codec_determinism()
    test_corruption_detection()
    test_frame_limit()
    test_service_examples()
    test_validation()

    print(
        "PROTOCOL TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 6/6"
    )
    print(
        "Message/request/response contracts: VALIDATED"
    )
    print(
        "Correlation + trace propagation: VALIDATED"
    )
    print(
        "Structured protocol errors: VALIDATED"
    )
    print(
        "Binary framing + deterministic codec: VALIDATED"
    )
    print(
        "Frame checksum/corruption detection: VALIDATED"
    )
    print(
        "Schema validation + frame limits: VALIDATED"
    )
    print(
        "Microservice contract examples: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
