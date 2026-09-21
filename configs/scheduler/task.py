class ScheduledTaskConfig:
    def __init__(
        self,
        task_id,
        queue_name,
        payload,
        next_run_at,
        recurrence=None,
        priority=0,
        max_attempts=None,
        enabled=True,
        metadata=None,
    ):
        if not isinstance(task_id, str) or task_id == "":
            raise ValueError(
                "task_id must be non-empty str"
            )

        if not isinstance(queue_name, str) or queue_name == "":
            raise ValueError(
                "queue_name must be non-empty str"
            )

        if not isinstance(payload, dict):
            raise TypeError(
                "payload must be dict"
            )

        if (
            not isinstance(next_run_at, int)
            or next_run_at < 0
        ):
            raise ValueError(
                "next_run_at must be non-negative int"
            )

        if recurrence is None:
            recurrence = SchedulerRecurrenceConfig()

        if not isinstance(
            recurrence,
            SchedulerRecurrenceConfig,
        ):
            raise TypeError(
                "recurrence must be SchedulerRecurrenceConfig"
            )

        if not isinstance(priority, int):
            raise TypeError(
                "priority must be int"
            )

        if max_attempts is not None and (
            not isinstance(max_attempts, int)
            or max_attempts <= 0
        ):
            raise ValueError(
                "max_attempts must be positive int or None"
            )

        if (
            recurrence.end_at is not None
            and next_run_at > recurrence.end_at
        ):
            raise ValueError(
                "next_run_at exceeds recurrence end_at"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.task_id = task_id
        self.queue_name = queue_name
        self.payload = self._copy(payload)
        self.next_run_at = next_run_at
        self.recurrence = recurrence
        self.priority = priority
        self.max_attempts = max_attempts
        self.enabled = bool(enabled)
        self.metadata = self._copy(metadata)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "queue_name": self.queue_name,
            "payload": self._copy(self.payload),
            "next_run_at": self.next_run_at,
            "recurrence": self.recurrence.to_dict(),
            "priority": self.priority,
            "max_attempts": self.max_attempts,
            "enabled": self.enabled,
            "metadata": self._copy(self.metadata),
        }

    def _copy(self, value):
        if isinstance(value, dict):
            return {
                key: self._copy(value[key])
                for key in value
            }

        if isinstance(value, (list, tuple)):
            return [
                self._copy(item)
                for item in value
            ]

        return value
