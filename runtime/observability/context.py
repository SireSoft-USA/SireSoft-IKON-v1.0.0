class ObservationContext:
    """
    Per-request state shared across logs, metrics, and tracing.
    """

    def __init__(
        self,
        request_id,
        service,
        operation,
        trace_id,
        correlation_id,
        start_time,
        span_id=None,
        sampled=True,
    ):
        for field_name, value in (
            ("request_id", request_id),
            ("service", service),
            ("operation", operation),
            ("trace_id", trace_id),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if correlation_id is not None and not isinstance(
            correlation_id,
            str,
        ):
            raise TypeError(
                "correlation_id must be str or None"
            )

        if not isinstance(start_time, int) or start_time < 0:
            raise ValueError(
                "start_time must be non-negative int"
            )

        if span_id is not None and not isinstance(
            span_id,
            str,
        ):
            raise TypeError(
                "span_id must be str or None"
            )

        self.request_id = request_id
        self.service = service
        self.operation = operation
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.start_time = start_time
        self.span_id = span_id
        self.sampled = bool(sampled)

        self.finished = False
        self.outcome = None
        self.end_time = None

    def finish(
        self,
        outcome,
        end_time,
    ):
        if self.finished:
            raise RuntimeError(
                "observation context already finished"
            )

        if not isinstance(outcome, str) or outcome == "":
            raise ValueError(
                "outcome must be non-empty str"
            )

        if not isinstance(end_time, int) or end_time < 0:
            raise ValueError(
                "end_time must be non-negative int"
            )

        if end_time < self.start_time:
            raise ValueError(
                "end_time cannot precede start_time"
            )

        self.finished = True
        self.outcome = outcome
        self.end_time = end_time

        return self

    def duration(
        self,
    ):
        if not self.finished:
            return None

        return self.end_time - self.start_time

    def to_dict(
        self,
    ):
        return {
            "request_id": self.request_id,
            "service": self.service,
            "operation": self.operation,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "start_time": self.start_time,
            "span_id": self.span_id,
            "sampled": self.sampled,
            "finished": self.finished,
            "outcome": self.outcome,
            "end_time": self.end_time,
            "duration": self.duration(),
        }
