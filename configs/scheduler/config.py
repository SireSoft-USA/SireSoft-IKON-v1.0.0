class SchedulerConfig:
    def __init__(
        self,
        tasks=None,
        attach_event_bus=False,
        state_path=None,
        load_state_on_start=False,
        metadata=None,
    ):
        if tasks is None:
            tasks = []

        if not isinstance(tasks, (list, tuple)):
            raise TypeError(
                "tasks must be list/tuple or None"
            )

        normalized = []
        seen = {}

        for task in tasks:
            if not isinstance(
                task,
                ScheduledTaskConfig,
            ):
                raise TypeError(
                    "task entries must be ScheduledTaskConfig"
                )

            if task.task_id in seen:
                raise ValueError(
                    "duplicate scheduler task_id: "
                    + task.task_id
                )

            seen[task.task_id] = True
            normalized.append(task)

        if state_path is not None and (
            not isinstance(state_path, str)
            or state_path == ""
        ):
            raise ValueError(
                "state_path must be non-empty str or None"
            )

        if load_state_on_start and state_path is None:
            raise ValueError(
                "load_state_on_start requires state_path"
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError(
                "metadata must be dict or None"
            )

        self.tasks = normalized
        self.attach_event_bus = bool(
            attach_event_bus
        )
        self.state_path = state_path
        self.load_state_on_start = bool(
            load_state_on_start
        )
        self.metadata = self._copy(metadata)

    def enabled_tasks(self):
        return [
            task
            for task in self.tasks
            if task.enabled
        ]

    def to_dict(self):
        return {
            "tasks": [
                task.to_dict()
                for task in self.tasks
            ],
            "attach_event_bus": self.attach_event_bus,
            "state_path": self.state_path,
            "load_state_on_start": self.load_state_on_start,
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
