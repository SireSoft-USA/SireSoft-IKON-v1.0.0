class ScheduledTask:
    VALID_STATUSES = (
        "scheduled",
        "disabled",
        "completed",
    )

    def __init__(
        self,
        task_id,
        sequence,
        queue_name,
        payload,
        next_run_at,
        recurrence,
        priority=0,
        max_attempts=None,
        metadata=None,
        enabled=True,
    ):
        if not isinstance(
            task_id,
            str,
        ) or task_id == "":
            raise ValueError(
                "task_id must be non-empty str"
            )

        if (
            not isinstance(
                sequence,
                int,
            )
            or sequence <= 0
        ):
            raise ValueError(
                "sequence must be positive int"
            )

        if not isinstance(
            queue_name,
            str,
        ) or queue_name == "":
            raise ValueError(
                "queue_name must be non-empty str"
            )

        if not isinstance(
            payload,
            dict,
        ):
            raise TypeError(
                "payload must be dict"
            )

        if (
            not isinstance(
                next_run_at,
                int,
            )
            or next_run_at < 0
        ):
            raise ValueError(
                "next_run_at must be non-negative int"
            )

        if not isinstance(
            recurrence,
            RecurrenceRule,
        ):
            raise TypeError(
                "recurrence must be RecurrenceRule"
            )

        if not isinstance(
            priority,
            int,
        ):
            raise TypeError(
                "priority must be int"
            )

        if max_attempts is not None:
            if (
                not isinstance(
                    max_attempts,
                    int,
                )
                or max_attempts <= 0
            ):
                raise ValueError(
                    "max_attempts must be positive int or None"
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

        if (
            recurrence.end_at
            is not None
            and next_run_at
            > recurrence.end_at
        ):
            raise ValueError(
                "next_run_at exceeds recurrence end_at"
            )

        self.task_id = task_id
        self.sequence = sequence
        self.queue_name = queue_name
        self.payload = self._copy(
            payload
        )
        self.next_run_at = next_run_at
        self.recurrence = recurrence
        self.priority = priority
        self.max_attempts = max_attempts
        self.metadata = self._copy(
            metadata
        )

        self.status = (
            "scheduled"
            if enabled
            else "disabled"
        )

        self.run_count = 0
        self.last_run_at = None
        self.last_job_id = None

    def due(
        self,
        now,
    ):
        self._validate_now(
            now
        )

        return (
            self.status
            == "scheduled"
            and self.next_run_at
            is not None
            and now
            >= self.next_run_at
        )

    def record_dispatch(
        self,
        now,
        job_id,
    ):
        self._validate_now(
            now
        )

        if not self.due(
            now
        ):
            raise RuntimeError(
                "scheduled task is not due"
            )

        scheduled_at = (
            self.next_run_at
        )

        self.run_count += 1
        self.last_run_at = now
        self.last_job_id = job_id

        next_run = (
            self.recurrence
            .next_run(
                previous_scheduled_at=(
                    scheduled_at
                ),
                dispatched_at=now,
                run_count=(
                    self.run_count
                ),
            )
        )

        self.next_run_at = next_run

        if next_run is None:
            self.status = "completed"

        return self

    def enable(
        self,
    ):
        if self.status == "completed":
            raise RuntimeError(
                "completed schedule cannot be enabled"
            )

        self.status = "scheduled"

        return self

    def disable(
        self,
    ):
        if self.status == "completed":
            raise RuntimeError(
                "completed schedule cannot be disabled"
            )

        self.status = "disabled"

        return self

    def reschedule(
        self,
        next_run_at,
        reset_completed=False,
    ):
        if (
            not isinstance(
                next_run_at,
                int,
            )
            or next_run_at < 0
        ):
            raise ValueError(
                "next_run_at must be non-negative int"
            )

        if (
            self.recurrence.end_at
            is not None
            and next_run_at
            > self.recurrence.end_at
        ):
            raise ValueError(
                "next_run_at exceeds recurrence end_at"
            )

        if self.status == "completed":
            if not reset_completed:
                raise RuntimeError(
                    "completed schedule requires reset_completed=True"
                )

            self.status = "scheduled"

        self.next_run_at = (
            next_run_at
        )

        return self

    def public_dict(
        self,
    ):
        return {
            "task_id": self.task_id,
            "sequence": self.sequence,
            "queue_name": (
                self.queue_name
            ),
            "payload": self._copy(
                self.payload
            ),
            "next_run_at": (
                self.next_run_at
            ),
            "recurrence": (
                self.recurrence
                .to_dict()
            ),
            "priority": (
                self.priority
            ),
            "max_attempts": (
                self.max_attempts
            ),
            "metadata": self._copy(
                self.metadata
            ),
            "status": self.status,
            "run_count": (
                self.run_count
            ),
            "last_run_at": (
                self.last_run_at
            ),
            "last_job_id": (
                self.last_job_id
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
                "scheduled task state must be dict"
            )

        task = cls(
            task_id=value[
                "task_id"
            ],
            sequence=int(
                value[
                    "sequence"
                ]
            ),
            queue_name=value[
                "queue_name"
            ],
            payload=value.get(
                "payload",
                {},
            ),
            next_run_at=(
                int(
                    value[
                        "next_run_at"
                    ]
                )
                if value.get(
                    "next_run_at"
                )
                is not None
                else 0
            ),
            recurrence=(
                RecurrenceRule
                .from_dict(
                    value[
                        "recurrence"
                    ]
                )
            ),
            priority=int(
                value.get(
                    "priority",
                    0,
                )
            ),
            max_attempts=value.get(
                "max_attempts"
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
            enabled=(
                value.get(
                    "status",
                    "scheduled",
                )
                == "scheduled"
            ),
        )

        status = value.get(
            "status",
            "scheduled",
        )

        if status not in cls.VALID_STATUSES:
            raise ValueError(
                "invalid persisted schedule status"
            )

        task.status = status

        raw_next = value.get(
            "next_run_at"
        )

        task.next_run_at = (
            None
            if raw_next is None
            else int(
                raw_next
            )
        )

        task.run_count = int(
            value.get(
                "run_count",
                0,
            )
        )

        task.last_run_at = value.get(
            "last_run_at"
        )

        task.last_job_id = value.get(
            "last_job_id"
        )

        return task

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
