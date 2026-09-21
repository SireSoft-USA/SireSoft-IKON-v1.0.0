class TraceRecord:
    """
    Ordered span collection for one trace.
    """

    def __init__(
        self,
        trace_id,
        sampled=True,
        correlation_id=None,
        metadata=None,
    ):
        if not isinstance(
            trace_id,
            str,
        ) or trace_id == "":
            raise ValueError(
                "trace_id must be non-empty str"
            )

        if correlation_id is not None and not isinstance(
            correlation_id,
            str,
        ):
            raise TypeError(
                "correlation_id must be str or None"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(
            metadata,
            dict,
        ):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.trace_id = trace_id
        self.sampled = bool(
            sampled
        )
        self.correlation_id = correlation_id
        self.metadata = self._copy(
            metadata
        )

        self._spans = {}
        self._order = []

    def add_span(
        self,
        span,
    ):
        if not isinstance(
            span,
            TraceSpan,
        ):
            raise TypeError(
                "span must be TraceSpan"
            )

        if span.trace_id != self.trace_id:
            raise ValueError(
                "span trace_id mismatch"
            )

        if span.span_id in self._spans:
            raise ValueError(
                "duplicate span_id in trace"
            )

        if (
            span.parent_span_id is not None
            and span.parent_span_id
            not in self._spans
        ):
            raise ValueError(
                "parent span must exist before child span"
            )

        self._spans[
            span.span_id
        ] = span

        self._order.append(
            span.span_id
        )

        return span

    def get_span(
        self,
        span_id,
    ):
        if span_id not in self._spans:
            raise KeyError(
                "span not found: "
                + str(
                    span_id
                )
            )

        return self._spans[
            span_id
        ]

    def spans(
        self,
    ):
        return [
            self._spans[
                span_id
            ]
            for span_id in self._order
        ]

    def roots(
        self,
    ):
        return [
            span
            for span in self.spans()
            if span.parent_span_id
            is None
        ]

    def running_count(
        self,
    ):
        count = 0

        for span in self.spans():
            if span.status == "running":
                count += 1

        return count

    def public_dict(
        self,
    ):
        spans = [
            span.public_dict()
            for span in self.spans()
        ]

        return {
            "trace_id": self.trace_id,
            "sampled": self.sampled,
            "correlation_id": (
                self.correlation_id
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "span_count": len(
                spans
            ),
            "running_span_count": (
                self.running_count()
            ),
            "spans": spans,
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "trace state must be dict"
            )

        trace = cls(
            trace_id=value[
                "trace_id"
            ],
            sampled=value.get(
                "sampled",
                True,
            ),
            correlation_id=value.get(
                "correlation_id"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )

        for span_state in value.get(
            "spans",
            [],
        ):
            trace.add_span(
                TraceSpan.from_dict(
                    span_state
                )
            )

        return trace

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
