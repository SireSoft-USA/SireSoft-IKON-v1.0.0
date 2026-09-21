BASE = "libs/training/batching/"

namespace = {
    "__builtins__": __builtins__,
}

for filename in [
    "padding.py",
    "sequence_packer.py",
    "batch_builder.py",
]:
    path = BASE + filename
    source = open(
        path,
        "r",
        encoding="utf-8",
    ).read()

    if "import " in source:
        raise AssertionError(
            "batching implementation contains forbidden import: "
            + filename
        )

    exec(
        compile(source, path, "exec"),
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


def expect_error(error_type, fn, message):
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


def test_right_padding():
    padder = Padder(
        pad_token_id=0,
        side="right",
    )

    result = padder.pad(
        [
            [1, 2, 3],
            [4, 5],
        ]
    )

    eq(
        result.sequences,
        [
            [1, 2, 3],
            [4, 5, 0],
        ],
        "right padding",
    )

    eq(
        result.attention_mask,
        [
            [1, 1, 1],
            [1, 1, 0],
        ],
        "right attention mask",
    )

    eq(
        result.lengths,
        [3, 2],
        "padding lengths",
    )


def test_left_padding():
    result = Padder(
        99,
        side="left",
    ).pad(
        [
            [1],
            [2, 3],
        ],
        target_length=3,
    )

    eq(
        result.sequences,
        [
            [99, 99, 1],
            [99, 2, 3],
        ],
        "left padding",
    )

    eq(
        result.attention_mask,
        [
            [0, 0, 1],
            [0, 1, 1],
        ],
        "left padding mask",
    )


def test_padding_truncation():
    padder = Padder(
        0,
        side="right",
    )

    expect_error(
        ValueError,
        lambda: padder.pad(
            [[1, 2, 3]],
            target_length=2,
            truncate=False,
        ),
        "padding refuses silent truncation",
    )

    result = padder.pad(
        [[1, 2, 3]],
        target_length=2,
        truncate=True,
    )

    eq(
        result.sequences,
        [[1, 2]],
        "explicit truncation",
    )


def test_sequence_packing():
    packer = SequencePacker(
        max_tokens=6,
        separator_token_id=99,
    )

    packed = packer.pack(
        [
            [1, 2],
            [3, 4],
            [5, 6, 7],
        ]
    )

    eq(
        len(packed),
        2,
        "packer block count",
    )

    eq(
        packed[0].tokens,
        [1, 2, 99, 3, 4],
        "first packed block",
    )

    eq(
        packed[1].tokens,
        [5, 6, 7],
        "second packed block",
    )

    eq(
        packed[0].sample_count(),
        2,
        "packed provenance count",
    )

    eq(
        packed[0].sample_spans[1]["start"],
        3,
        "second sample start",
    )


def test_long_sequence_split():
    packer = SequencePacker(
        max_tokens=4,
        separator_token_id=99,
        split_long_sequences=True,
    )

    packed = packer.pack(
        [
            [1, 2, 3, 4, 5, 6, 7],
        ]
    )

    eq(
        len(packed),
        2,
        "long sequence chunk count",
    )

    eq(
        packed[0].tokens,
        [1, 2, 3, 4],
        "long sequence first chunk",
    )

    eq(
        packed[1].tokens,
        [5, 6, 7],
        "long sequence remainder",
    )

    eq(
        packed[1].sample_spans[0]["sample_index"],
        0,
        "split chunk retains source sample",
    )

    eq(
        packed[1].sample_spans[0]["chunk_index"],
        1,
        "split chunk index",
    )


def test_packing_disabled_split():
    packer = SequencePacker(
        max_tokens=3,
        split_long_sequences=False,
    )

    expect_error(
        ValueError,
        lambda: packer.pack(
            [[1, 2, 3, 4]]
        ),
        "oversized sequence rejected when splitting disabled",
    )


def test_next_token_batch():
    builder = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
    )

    batch = builder.build(
        [
            [10, 11, 12, 13],
            [20, 21, 22],
        ]
    )

    eq(
        batch.input_ids,
        [
            [10, 11, 12],
            [20, 21, 0],
        ],
        "shifted causal inputs",
    )

    eq(
        batch.labels,
        [
            [11, 12, 13],
            [21, 22, -100],
        ],
        "shifted causal labels",
    )

    eq(
        batch.attention_mask,
        [
            [1, 1, 1],
            [1, 1, 0],
        ],
        "batch attention mask",
    )

    eq(
        batch.loss_mask,
        [
            [1, 1, 1],
            [1, 1, 0],
        ],
        "batch loss mask",
    )

    eq(
        batch.lengths,
        [3, 2],
        "batch real lengths",
    )

    eq(
        batch.active_target_count(),
        5,
        "active target count",
    )


def test_packed_boundary_mask():
    packer = SequencePacker(
        max_tokens=10,
        separator_token_id=99,
    )

    packed = packer.pack(
        [
            [1, 2],
            [3, 4],
        ]
    )

    eq(
        packed[0].tokens,
        [1, 2, 99, 3, 4],
        "boundary test packed tokens",
    )

    batch = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
    ).build(packed)

    # input:  [1,2,99,3]
    # labels: [2,99,3,4]
    # transition 99 -> 3 is artificial and must be ignored.
    eq(
        batch.input_ids[0],
        [1, 2, 99, 3],
        "packed input row",
    )

    eq(
        batch.labels[0],
        [2, 99, -100, 4],
        "cross-sample target ignored",
    )

    eq(
        batch.loss_mask[0],
        [1, 1, 0, 1],
        "cross-sample loss mask",
    )

    eq(
        batch.active_target_count(),
        3,
        "packed active targets",
    )


def test_without_separator_boundary_mask():
    packer = SequencePacker(
        max_tokens=10,
        separator_token_id=None,
    )

    packed = packer.pack(
        [
            [1, 2],
            [3, 4],
        ]
    )

    eq(
        packed[0].tokens,
        [1, 2, 3, 4],
        "packing without separator",
    )

    batch = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
    ).build(packed)

    eq(
        batch.labels[0],
        [2, -100, 4],
        "direct cross-document target ignored",
    )


def test_max_sequence_length():
    builder = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
        max_sequence_length=3,
    )

    batch = builder.build(
        [
            [1, 2, 3, 4, 5, 6],
        ]
    )

    eq(
        batch.input_ids,
        [[1, 2, 3]],
        "max sequence input truncation",
    )

    eq(
        batch.labels,
        [[2, 3, 4]],
        "max sequence label truncation",
    )

    eq(
        batch.sequence_length(),
        3,
        "configured training sequence length",
    )


def test_left_padded_training_batch():
    builder = BatchBuilder(
        pad_token_id=0,
        ignore_index=-100,
        padding_side="left",
    )

    batch = builder.build(
        [
            [1, 2, 3, 4],
            [7, 8],
        ]
    )

    eq(
        batch.input_ids,
        [
            [1, 2, 3],
            [0, 0, 7],
        ],
        "left padded input batch",
    )

    eq(
        batch.labels,
        [
            [2, 3, 4],
            [-100, -100, 8],
        ],
        "left padded labels",
    )

    eq(
        batch.attention_mask,
        [
            [1, 1, 1],
            [0, 0, 1],
        ],
        "left padded attention",
    )


def test_source_not_mutated():
    source = [
        [1, 2, 3],
        [4, 5],
    ]

    original = [
        list(source[0]),
        list(source[1]),
    ]

    SequencePacker(
        max_tokens=8,
        separator_token_id=99,
    ).pack(source)

    BatchBuilder(
        pad_token_id=0,
    ).build(source)

    eq(
        source,
        original,
        "batching never mutates source token sequences",
    )


def test_empty_and_short_sequences():
    builder = BatchBuilder(
        pad_token_id=0,
    )

    batch = builder.build(
        [
            [],
            [1],
            [2, 3],
        ]
    )

    eq(
        batch.input_ids,
        [[2]],
        "short sequences skipped safely",
    )

    eq(
        batch.labels,
        [[3]],
        "remaining valid label",
    )

    expect_error(
        ValueError,
        lambda: builder.build(
            [
                [],
                [1],
            ]
        ),
        "no trainable targets rejected",
    )


def test_drop_last():
    packer = SequencePacker(
        max_tokens=5,
        drop_last=True,
    )

    packed = packer.pack(
        [
            [1, 2, 3],
        ]
    )

    eq(
        packed,
        [],
        "drop_last removes incomplete final block",
    )

    full = packer.pack(
        [
            [1, 2, 3, 4, 5],
        ]
    )

    eq(
        len(full),
        1,
        "drop_last keeps complete block",
    )


def test_validation():
    expect_error(
        ValueError,
        lambda: SequencePacker(
            max_tokens=1,
        ),
        "invalid pack size",
    )

    expect_error(
        TypeError,
        lambda: Padder(
            "PAD"
        ),
        "pad token must be int",
    )

    expect_error(
        ValueError,
        lambda: BatchBuilder(
            pad_token_id=0,
            max_sequence_length=0,
        ),
        "invalid training sequence length",
    )

    expect_error(
        TypeError,
        lambda: BatchBuilder(
            pad_token_id=0,
        ).build(
            [
                [1, "2", 3],
            ]
        ),
        "non-integer token rejected",
    )


def main():
    test_right_padding()
    test_left_padding()
    test_padding_truncation()
    test_sequence_packing()
    test_long_sequence_split()
    test_packing_disabled_split()
    test_next_token_batch()
    test_packed_boundary_mask()
    test_without_separator_boundary_mask()
    test_max_sequence_length()
    test_left_padded_training_batch()
    test_source_not_mutated()
    test_empty_and_short_sequences()
    test_drop_last()
    test_validation()

    print(
        "BATCHING TEST SUITE: PASS"
    )
    print(
        "Assertions passed:",
        ASSERTIONS,
    )
    print(
        "Files validated: 3/3"
    )
    print(
        "Padding + attention masks: VALIDATED"
    )
    print(
        "Sequence packing + provenance: VALIDATED"
    )
    print(
        "Next-token input/label shifting: VALIDATED"
    )
    print(
        "Cross-document loss masking: VALIDATED"
    )
    print(
        "Length limiting + source immutability: VALIDATED"
    )
    print(
        "Third-party dependencies: 0"
    )


main()
