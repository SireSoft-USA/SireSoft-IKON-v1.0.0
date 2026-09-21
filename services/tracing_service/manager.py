class TracingManager:
    """
    In-memory distributed-tracing core with deterministic IDs supplied by a
    sequence, optional deterministic sampling, MetricsService integration, and
    EventBus lifecycle publication.
    """

    def __init__(
        self,
        sampler=None,
        persistence=None,
        metrics_manager=None,
        event_bus=None,
    ):
        self.sampler = (
            DeterministicTraceSampler()
            if sampler is None
            else sampler
        )

        self.persistence = (
            TracingPersistence()
            if persistence is None
            else persistence
        )

        self.metrics_manager = (
            metrics_manager
        )

        self.event_bus = event_bus

        self._traces = {}
        self._trace_order = []
        self._span_sequence = 0

        self.total_started = 0
        self.total_finished = 0
        self.total_errors = 0
        self.total_dropped = 0

        self._ensure_metrics()

    def start_span(
        self,
        trace_id,
        name,
        service_name,
        start_time,
        parent_span_id=None,
        operation=None,
        correlation_id=None,
        attributes=None,
        trace_metadata=None,
    ):
        if trace_id not in self._traces:
            sampled = self.sampler.should_sample(
                trace_id
            )

            trace = TraceRecord(
                trace_id=trace_id,
                sampled=sampled,
                correlation_id=(
                    correlation_id
                ),
                metadata=trace_metadata,
            )

            self._traces[
                trace_id
            ] = trace

            self._trace_order.append(
                trace_id
            )

            if not sampled:
                self.total_dropped += 1

        trace = self._traces[
            trace_id
        ]

        if (
            correlation_id is not None
            and trace.correlation_id
            is None
        ):
            trace.correlation_id = (
                correlation_id
            )

        if not trace.sampled:
            return {
                "sampled": False,
                "trace_id": trace_id,
                "span": None,
            }

        if parent_span_id is not None:
            trace.get_span(
                parent_span_id
            )

        self._span_sequence += 1

        span = TraceSpan(
            span_id=(
                "span-"
                + str(
                    self._span_sequence
                )
            ),
            trace_id=trace_id,
            name=name,
            service_name=service_name,
            start_time=start_time,
            parent_span_id=(
                parent_span_id
            ),
            operation=operation,
            correlation_id=(
                correlation_id
                if correlation_id
                is not None
                else trace.correlation_id
            ),
            attributes=attributes,
        )

        trace.add_span(
            span
        )

        self.total_started += 1

        self._metric_increment(
            "trace_spans_started_total",
            timestamp=start_time,
            labels={
                "service": service_name,
            },
        )

        self._publish_event(
            "tracing.span_started",
            start_time,
            span,
        )

        return {
            "sampled": True,
            "trace_id": trace_id,
            "span": (
                span.public_dict()
            ),
        }

    def finish_span(
        self,
        trace_id,
        span_id,
        end_time,
        status="ok",
        error_type=None,
        error_message=None,
    ):
        trace = self.get_trace(
            trace_id
        )

        if not trace.sampled:
            return {
                "sampled": False,
                "trace_id": trace_id,
                "span": None,
            }

        span = trace.get_span(
            span_id
        )

        span.finish(
            end_time=end_time,
            status=status,
            error_type=error_type,
            error_message=error_message,
        )

        self.total_finished += 1

        if status == "error":
            self.total_errors += 1

        self._metric_increment(
            "trace_spans_finished_total",
            timestamp=end_time,
            labels={
                "service": (
                    span.service_name
                ),
                "status": status,
            },
        )

        duration = span.duration()

        self._metric_observe(
            "trace_span_duration_seconds",
            value=float(
                duration
            ),
            timestamp=end_time,
            labels={
                "service": (
                    span.service_name
                ),
                "operation": (
                    span.operation
                    if span.operation
                    is not None
                    else span.name
                ),
            },
        )

        self._publish_event(
            "tracing.span_finished",
            end_time,
            span,
        )

        return {
            "sampled": True,
            "trace_id": trace_id,
            "span": (
                span.public_dict()
            ),
        }

    def add_event(
        self,
        trace_id,
        span_id,
        name,
        timestamp,
        attributes=None,
    ):
        span = (
            self.get_trace(
                trace_id
            )
            .get_span(
                span_id
            )
        )

        span.add_event(
            name=name,
            timestamp=timestamp,
            attributes=attributes,
        )

        return span.public_dict()

    def set_attribute(
        self,
        trace_id,
        span_id,
        key,
        value,
    ):
        span = (
            self.get_trace(
                trace_id
            )
            .get_span(
                span_id
            )
        )

        span.set_attribute(
            key,
            value,
        )

        return span.public_dict()

    def get_trace(
        self,
        trace_id,
    ):
        if trace_id not in self._traces:
            raise KeyError(
                "trace not found: "
                + str(
                    trace_id
                )
            )

        return self._traces[
            trace_id
        ]

    def list_traces(
        self,
        sampled=None,
        limit=100,
        newest_first=False,
    ):
        if (
            not isinstance(
                limit,
                int,
            )
            or limit <= 0
        ):
            raise ValueError(
                "limit must be positive int"
            )

        ids = list(
            self._trace_order
        )

        if newest_first:
            ids.reverse()

        result = []

        for trace_id in ids:
            trace = self._traces[
                trace_id
            ]

            if (
                sampled is not None
                and trace.sampled
                != bool(
                    sampled
                )
            ):
                continue

            result.append(
                trace.public_dict()
            )

            if len(
                result
            ) >= limit:
                break

        return result

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMTracingState"
            ),
            "version": 1,
            "span_sequence": (
                self._span_sequence
            ),
            "sampler": (
                self.sampler.to_dict()
            ),
            "traces": [
                self._traces[
                    trace_id
                ].public_dict()
                for trace_id
                in self._trace_order
            ],
            "stats": {
                "total_started": (
                    self.total_started
                ),
                "total_finished": (
                    self.total_finished
                ),
                "total_errors": (
                    self.total_errors
                ),
                "total_dropped": (
                    self.total_dropped
                ),
            },
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "tracing state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMTracingState":
            raise ValueError(
                "invalid tracing state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported tracing state version"
            )

        sampler_state = state.get(
            "sampler",
            {
                "numerator": 1,
                "denominator": 1,
            },
        )

        staged_sampler = (
            DeterministicTraceSampler(
                numerator=int(
                    sampler_state[
                        "numerator"
                    ]
                ),
                denominator=int(
                    sampler_state[
                        "denominator"
                    ]
                ),
            )
        )

        traces = {}
        order = []

        for trace_state in state.get(
            "traces",
            [],
        ):
            trace = TraceRecord.from_dict(
                trace_state
            )

            if trace.trace_id in traces:
                raise ValueError(
                    "duplicate trace in state"
                )

            traces[
                trace.trace_id
            ] = trace

            order.append(
                trace.trace_id
            )

        stats = state.get(
            "stats",
            {},
        )

        self.sampler = staged_sampler
        self._traces = traces
        self._trace_order = order
        self._span_sequence = int(
            state.get(
                "span_sequence",
                0,
            )
        )
        self.total_started = int(
            stats.get(
                "total_started",
                0,
            )
        )
        self.total_finished = int(
            stats.get(
                "total_finished",
                0,
            )
        )
        self.total_errors = int(
            stats.get(
                "total_errors",
                0,
            )
        )
        self.total_dropped = int(
            stats.get(
                "total_dropped",
                0,
            )
        )

        return self

    def status(
        self,
    ):
        sampled = 0
        dropped = 0
        running = 0

        for trace_id in self._trace_order:
            trace = self._traces[
                trace_id
            ]

            if trace.sampled:
                sampled += 1
            else:
                dropped += 1

            running += (
                trace.running_count()
            )

        return {
            "ready": True,
            "trace_count": len(
                self._trace_order
            ),
            "sampled_trace_count": (
                sampled
            ),
            "dropped_trace_count": (
                dropped
            ),
            "running_span_count": (
                running
            ),
            "total_started": (
                self.total_started
            ),
            "total_finished": (
                self.total_finished
            ),
            "total_errors": (
                self.total_errors
            ),
            "total_dropped": (
                self.total_dropped
            ),
            "sampler": (
                self.sampler.to_dict()
            ),
            "metrics_attached": (
                self.metrics_manager
                is not None
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
        }

    def _ensure_metrics(
        self,
    ):
        if self.metrics_manager is None:
            return

        definitions = (
            self.metrics_manager
            .registry
        )

        try:
            definitions.get_definition(
                "trace_spans_started_total"
            )
        except KeyError:
            self.metrics_manager.define(
                "trace_spans_started_total",
                "counter",
                description=(
                    "Started trace spans"
                ),
                label_names=[
                    "service",
                ],
            )

        try:
            definitions.get_definition(
                "trace_spans_finished_total"
            )
        except KeyError:
            self.metrics_manager.define(
                "trace_spans_finished_total",
                "counter",
                description=(
                    "Finished trace spans"
                ),
                label_names=[
                    "service",
                    "status",
                ],
            )

        try:
            definitions.get_definition(
                "trace_span_duration_seconds"
            )
        except KeyError:
            self.metrics_manager.define(
                "trace_span_duration_seconds",
                "histogram",
                description=(
                    "Trace span duration in seconds"
                ),
                unit="seconds",
                label_names=[
                    "service",
                    "operation",
                ],
                buckets=[
                    1.0,
                    2.0,
                    5.0,
                    10.0,
                    30.0,
                    60.0,
                    120.0,
                    300.0,
                ],
            )

    def _metric_increment(
        self,
        name,
        timestamp,
        labels,
    ):
        if self.metrics_manager is None:
            return

        self.metrics_manager.increment(
            name=name,
            timestamp=timestamp,
            labels=labels,
        )

    def _metric_observe(
        self,
        name,
        value,
        timestamp,
        labels,
    ):
        if self.metrics_manager is None:
            return

        self.metrics_manager.observe(
            name=name,
            value=value,
            timestamp=timestamp,
            labels=labels,
        )

    def _publish_event(
        self,
        topic,
        timestamp,
        span,
    ):
        if self.event_bus is None:
            return

        if not hasattr(
            self.event_bus,
            "publish",
        ):
            raise TypeError(
                "event_bus must provide publish()"
            )

        self.event_bus.publish(
            topic=topic,
            timestamp=timestamp,
            payload={
                "trace_id": (
                    span.trace_id
                ),
                "span_id": (
                    span.span_id
                ),
                "parent_span_id": (
                    span.parent_span_id
                ),
                "service_name": (
                    span.service_name
                ),
                "operation": (
                    span.operation
                ),
                "status": (
                    span.status
                ),
                "duration": (
                    span.duration()
                ),
            },
            source_service=(
                "tracing_service"
            ),
            trace_id=(
                span.trace_id
            ),
            correlation_id=(
                span.correlation_id
            ),
        )
