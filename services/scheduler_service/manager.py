class SchedulerManager:
    """
    Deterministic scheduler that dispatches due tasks into JobQueueManager.

    One tick dispatches each due scheduled task at most once. This avoids an
    unbounded catch-up loop when a scheduler has been offline for a long time.
    """

    def __init__(
        self,
        job_queue,
        persistence=None,
        event_bus=None,
    ):
        if job_queue is None or not hasattr(
            job_queue,
            "enqueue",
        ):
            raise TypeError(
                "job_queue must provide enqueue()"
            )

        self.job_queue = (
            job_queue
        )

        self.persistence = (
            SchedulerPersistence()
            if persistence is None
            else persistence
        )

        self.event_bus = event_bus

        self._tasks = {}
        self._order = []
        self._sequence = 0

        self.total_ticks = 0
        self.total_dispatched = 0
        self.total_dispatch_failures = 0

    def create_task(
        self,
        task_id,
        queue_name,
        payload,
        next_run_at,
        recurrence=None,
        priority=0,
        max_attempts=None,
        metadata=None,
        enabled=True,
    ):
        if task_id in self._tasks:
            raise ValueError(
                "scheduled task already exists: "
                + str(
                    task_id
                )
            )

        self.job_queue.get_queue(
            queue_name
        )

        if recurrence is None:
            recurrence = (
                RecurrenceRule(
                    "once"
                )
            )

        self._sequence += 1

        task = ScheduledTask(
            task_id=task_id,
            sequence=self._sequence,
            queue_name=queue_name,
            payload=payload,
            next_run_at=next_run_at,
            recurrence=recurrence,
            priority=priority,
            max_attempts=max_attempts,
            metadata=metadata,
            enabled=enabled,
        )

        self._tasks[
            task_id
        ] = task

        self._order.append(
            task_id
        )

        return task

    def remove_task(
        self,
        task_id,
    ):
        task = self.get_task(
            task_id
        )

        del self._tasks[
            task_id
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != task_id
        ]

        return task

    def get_task(
        self,
        task_id,
    ):
        if task_id not in self._tasks:
            raise KeyError(
                "scheduled task not found: "
                + str(
                    task_id
                )
            )

        return self._tasks[
            task_id
        ]

    def list_tasks(
        self,
        status=None,
        limit=100,
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

        if (
            status is not None
            and status
            not in ScheduledTask.VALID_STATUSES
        ):
            raise ValueError(
                "invalid scheduled-task status"
            )

        result = []

        for task_id in self._order:
            task = self._tasks[
                task_id
            ]

            if (
                status is not None
                and task.status
                != status
            ):
                continue

            result.append(
                task.public_dict()
            )

            if len(
                result
            ) >= limit:
                break

        return result

    def enable_task(
        self,
        task_id,
    ):
        return self.get_task(
            task_id
        ).enable()

    def disable_task(
        self,
        task_id,
    ):
        return self.get_task(
            task_id
        ).disable()

    def reschedule_task(
        self,
        task_id,
        next_run_at,
        reset_completed=False,
    ):
        return self.get_task(
            task_id
        ).reschedule(
            next_run_at=next_run_at,
            reset_completed=(
                reset_completed
            ),
        )

    def tick(
        self,
        now,
        trace_id=None,
        correlation_id=None,
    ):
        self._validate_now(
            now
        )

        self.total_ticks += 1

        due = []

        for task_id in self._order:
            task = self._tasks[
                task_id
            ]

            if task.due(
                now
            ):
                due.append(
                    task
                )

        due.sort(
            key=(
                lambda task: (
                    task.next_run_at,
                    task.sequence,
                )
            )
        )

        dispatched = []
        failures = []

        for task in due:
            try:
                metadata = self._copy(
                    task.metadata
                )

                metadata[
                    "scheduler_task_id"
                ] = task.task_id

                metadata[
                    "scheduler_run_number"
                ] = (
                    task.run_count
                    + 1
                )

                job = self.job_queue.enqueue(
                    queue_name=(
                        task.queue_name
                    ),
                    payload=self._copy(
                        task.payload
                    ),
                    now=now,
                    priority=(
                        task.priority
                    ),
                    max_attempts=(
                        task.max_attempts
                    ),
                    metadata=metadata,
                    trace_id=trace_id,
                    correlation_id=(
                        correlation_id
                    ),
                )

                task.record_dispatch(
                    now=now,
                    job_id=job.job_id,
                )

                self.total_dispatched += 1

                dispatched.append({
                    "task_id": task.task_id,
                    "job_id": job.job_id,
                    "queue_name": (
                        task.queue_name
                    ),
                    "run_count": (
                        task.run_count
                    ),
                    "next_run_at": (
                        task.next_run_at
                    ),
                    "task_status": (
                        task.status
                    ),
                })

                self._publish_event(
                    topic=(
                        "scheduler.dispatched"
                    ),
                    timestamp=now,
                    task=task,
                    extra={
                        "job_id": (
                            job.job_id
                        ),
                    },
                    trace_id=trace_id,
                    correlation_id=(
                        correlation_id
                    ),
                )

            except Exception as error:
                self.total_dispatch_failures += 1

                failures.append({
                    "task_id": (
                        task.task_id
                    ),
                    "error_type": (
                        type(
                            error
                        ).__name__
                    ),
                    "error_message": (
                        str(
                            error
                        )
                    ),
                })

                self._publish_event(
                    topic=(
                        "scheduler.dispatch_failed"
                    ),
                    timestamp=now,
                    task=task,
                    extra={
                        "error_type": (
                            type(
                                error
                            ).__name__
                        ),
                        "error_message": (
                            str(
                                error
                            )
                        ),
                    },
                    trace_id=trace_id,
                    correlation_id=(
                        correlation_id
                    ),
                )

        return {
            "now": now,
            "due_count": len(
                due
            ),
            "dispatched": dispatched,
            "dispatch_count": len(
                dispatched
            ),
            "failures": failures,
            "failure_count": len(
                failures
            ),
        }

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
                "SireLLMSchedulerState"
            ),
            "version": 1,
            "task_sequence": (
                self._sequence
            ),
            "tasks": [
                self._tasks[
                    task_id
                ].public_dict()
                for task_id in self._order
            ],
            "stats": {
                "total_ticks": (
                    self.total_ticks
                ),
                "total_dispatched": (
                    self.total_dispatched
                ),
                "total_dispatch_failures": (
                    self.total_dispatch_failures
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
                "scheduler state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMSchedulerState":
            raise ValueError(
                "invalid scheduler state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported scheduler state version"
            )

        staged = {}
        order = []

        for task_state in state.get(
            "tasks",
            [],
        ):
            task = (
                ScheduledTask
                .from_dict(
                    task_state
                )
            )

            self.job_queue.get_queue(
                task.queue_name
            )

            if task.task_id in staged:
                raise ValueError(
                    "duplicate task in scheduler state"
                )

            staged[
                task.task_id
            ] = task

            order.append(
                task.task_id
            )

        stats = state.get(
            "stats",
            {},
        )

        self._tasks = staged
        self._order = order
        self._sequence = int(
            state.get(
                "task_sequence",
                0,
            )
        )
        self.total_ticks = int(
            stats.get(
                "total_ticks",
                0,
            )
        )
        self.total_dispatched = int(
            stats.get(
                "total_dispatched",
                0,
            )
        )
        self.total_dispatch_failures = int(
            stats.get(
                "total_dispatch_failures",
                0,
            )
        )

        return self

    def status(
        self,
    ):
        counts = {
            "scheduled": 0,
            "disabled": 0,
            "completed": 0,
        }

        for task_id in self._order:
            counts[
                self._tasks[
                    task_id
                ].status
            ] += 1

        return {
            "ready": True,
            "task_count": len(
                self._order
            ),
            "counts": counts,
            "total_ticks": (
                self.total_ticks
            ),
            "total_dispatched": (
                self.total_dispatched
            ),
            "total_dispatch_failures": (
                self.total_dispatch_failures
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
        }

    def _publish_event(
        self,
        topic,
        timestamp,
        task,
        extra,
        trace_id,
        correlation_id,
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

        payload = {
            "task_id": (
                task.task_id
            ),
            "queue_name": (
                task.queue_name
            ),
            "status": (
                task.status
            ),
            "run_count": (
                task.run_count
            ),
        }

        for key in extra:
            payload[
                key
            ] = extra[
                key
            ]

        self.event_bus.publish(
            topic=topic,
            timestamp=timestamp,
            payload=payload,
            source_service=(
                "scheduler_service"
            ),
            trace_id=trace_id,
            correlation_id=(
                correlation_id
            ),
        )

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(
            now,
            int,
        ):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )

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
