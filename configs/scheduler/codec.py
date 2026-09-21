class SchedulerConfigCodec:
    def __init__(self, parser=None):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(self, text):
        if not isinstance(text, str):
            raise TypeError(
                "scheduler config text must be str"
            )

        return self.from_dict(
            self.parser.parse(text)
        )

    def from_dict(self, value):
        if not isinstance(value, dict):
            raise ValueError(
                "scheduler config root must be object"
            )

        raw_tasks = value.get(
            "tasks",
            [],
        )

        if not isinstance(raw_tasks, list):
            raise ValueError(
                "tasks must be list"
            )

        tasks = []

        for raw in raw_tasks:
            if not isinstance(raw, dict):
                raise ValueError(
                    "scheduled task config must be object"
                )

            recurrence = raw.get(
                "recurrence",
                {},
            )

            if not isinstance(recurrence, dict):
                raise ValueError(
                    "recurrence must be object"
                )

            tasks.append(
                ScheduledTaskConfig(
                    task_id=raw.get("task_id"),
                    queue_name=raw.get("queue_name"),
                    payload=raw.get(
                        "payload",
                        {},
                    ),
                    next_run_at=raw.get(
                        "next_run_at"
                    ),
                    recurrence=SchedulerRecurrenceConfig(
                        mode=recurrence.get(
                            "mode",
                            "once",
                        ),
                        interval_seconds=recurrence.get(
                            "interval_seconds"
                        ),
                        max_runs=recurrence.get(
                            "max_runs"
                        ),
                        end_at=recurrence.get(
                            "end_at"
                        ),
                        catch_up=recurrence.get(
                            "catch_up",
                            False,
                        ),
                    ),
                    priority=raw.get(
                        "priority",
                        0,
                    ),
                    max_attempts=raw.get(
                        "max_attempts"
                    ),
                    enabled=raw.get(
                        "enabled",
                        True,
                    ),
                    metadata=raw.get(
                        "metadata",
                        {},
                    ),
                )
            )

        return SchedulerConfig(
            tasks=tasks,
            attach_event_bus=value.get(
                "attach_event_bus",
                False,
            ),
            state_path=value.get(
                "state_path"
            ),
            load_state_on_start=value.get(
                "load_state_on_start",
                False,
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
