class TraceSpan:
    VALID_STATUSES = (
        "running",
        "ok",
        "error",
        "cancelled",
    )

    def __init__(
        self,
        span_id,
        trace_id,
        name,
        service_name,
        start_time,
        parent_span_id=None,
        operation=None,
        correlation_id=None,
        attributes=None,
    ):
        for field_name, value in (
            ("span_id", span_id),
            ("trace_id", trace_id),
            ("name", name),
            ("service_name", service_name),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    field_name + " must be non-empty str"
                )

        if parent_span_id is not None and not isinstance(
            parent_span_id,
            str,
        ):
            raise TypeError(
                "parent_span_id must be str or None"
            )

        if operation is not None and not isinstance(
            operation,
            str,
        ):
            raise TypeError(
                "operation must be str or None"
            )

        if correlation_id is not None and not isinstance(
            correlation_id,
            str,
        ):
            raise TypeError(
                "correlation_id must be str or None"
            )

        if not isinstance(
            start_time,
            int,
        ) or start_time < 0:
            raise ValueError(
                "start_time must be non-negative int"
            )

        if attributes is None:
            attributes = {}

        if not isinstance(
            attributes,
            dict,
        ):
            raise TypeError(
                "attributes must be dict or None"
            )

        self.span_id = span_id
        self.trace_id = trace_id
        self.name = name
        self.service_name = service_name
        self.start_time = start_time
        self.parent_span_id = parent_span_id
        self.operation = operation
        self.correlation_id = correlation_id
        self.attributes = self._copy(
            attributes
        )

        self.status = "running"
        self.end_time = None
        self.error_type = None
        self.error_message = None
        self.events = []

    def finish(
        self,
        end_time,
        status="ok",
        error_type=None,
        error_message=None,
    ):
        if self.status != "running":
            raise RuntimeError(
                "span has already finished"
            )

        if status not in (
            "ok",
            "error",
            "cancelled",
        ):
            raise ValueError(
                "invalid terminal span status"
            )

        if not isinstance(
            end_time,
            int,
        ) or end_time < self.start_time:
            raise ValueError(
                "end_time must be int >= start_time"
            )

        if error_type is not None and not isinstance(
            error_type,
            str,
        ):
            raise TypeError(
                "error_type must be str or None"
            )

        if error_message is not None and not isinstance(
            error_message,
            str,
        ):
            raise TypeError(
                "error_message must be str or None"
            )

        self.status = status
        self.end_time = end_time
        self.error_type = error_type
        self.error_message = error_message

        return self

    def add_event(
        self,
        name,
        timestamp,
        attributes=None,
    ):
        if not isinstance(
            name,
            str,
        ) or name == "":
            raise ValueError(
                "event name must be non-empty str"
            )

        if not isinstance(
            timestamp,
            int,
        ) or timestamp < self.start_time:
            raise ValueError(
                "event timestamp must be int >= span start"
            )

        if (
            self.end_time is not None
            and timestamp > self.end_time
        ):
            raise ValueError(
                "event timestamp cannot exceed span end"
            )

        if attributes is None:
            attributes = {}

        if not isinstance(
            attributes,
            dict,
        ):
            raise TypeError(
                "event attributes must be dict or None"
            )

        self.events.append({
            "name": name,
            "timestamp": timestamp,
            "attributes": self._copy(
                attributes
            ),
        })

        return self

    def set_attribute(
        self,
        key,
        value,
    ):
        if not isinstance(
            key,
            str,
        ) or key == "":
            raise ValueError(
                "attribute key must be non-empty str"
            )

        self.attributes[
            key
        ] = self._copy(
            value
        )

        return self

    def duration(
        self,
    ):
        if self.end_time is None:
            return None

        return (
            self.end_time
            - self.start_time
        )

    def public_dict(
        self,
    ):
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "service_name": self.service_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration(),
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "attributes": self._copy(
                self.attributes
            ),
            "status": self.status,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "events": self._copy(
                self.events
            ),
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
                "span state must be dict"
            )

        span = cls(
            span_id=value[
                "span_id"
            ],
            trace_id=value[
                "trace_id"
            ],
            name=value[
                "name"
            ],
            service_name=value[
                "service_name"
            ],
            start_time=int(
                value[
                    "start_time"
                ]
            ),
            parent_span_id=value.get(
                "parent_span_id"
            ),
            operation=value.get(
                "operation"
            ),
            correlation_id=value.get(
                "correlation_id"
            ),
            attributes=value.get(
                "attributes",
                {},
            ),
        )

        status = value.get(
            "status",
            "running",
        )

        if status not in cls.VALID_STATUSES:
            raise ValueError(
                "invalid persisted span status"
            )

        span.status = status
        span.end_time = value.get(
            "end_time"
        )
        span.error_type = value.get(
            "error_type"
        )
        span.error_message = value.get(
            "error_message"
        )
        span.events = span._copy(
            value.get(
                "events",
                [],
            )
        )

        return span

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
