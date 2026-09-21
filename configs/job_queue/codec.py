class JobQueueConfigCodec:
    def __init__(
        self,
        parser=None,
    ):
        self.parser = (
            JSONParser()
            if parser is None
            else parser
        )

    def decode_text(
        self,
        text,
    ):
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "job queue config text must be str"
            )

        return self.from_dict(
            self.parser.parse(
                text
            )
        )

    def from_dict(
        self,
        value,
    ):
        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "job queue config root must be object"
            )

        raw_queues = value.get(
            "queues"
        )

        raw_workers = value.get(
            "workers",
            [],
        )

        if not isinstance(
            raw_queues,
            list,
        ) or len(
            raw_queues
        ) == 0:
            raise ValueError(
                "queues must be non-empty list"
            )

        if not isinstance(
            raw_workers,
            list,
        ):
            raise ValueError(
                "workers must be list"
            )

        queues = []

        for raw in raw_queues:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "queue config must be object"
                )

            queues.append(
                JobQueueDefinitionConfig(
                    queue_name=(
                        raw.get(
                            "queue_name"
                        )
                    ),
                    default_lease_seconds=(
                        raw.get(
                            "default_lease_seconds",
                            30,
                        )
                    ),
                    default_max_attempts=(
                        raw.get(
                            "default_max_attempts",
                            3,
                        )
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

        workers = []

        for raw in raw_workers:
            if not isinstance(
                raw,
                dict,
            ):
                raise ValueError(
                    "worker config must be object"
                )

            workers.append(
                JobWorkerConfig(
                    worker_id=raw.get(
                        "worker_id"
                    ),
                    queue_name=raw.get(
                        "queue_name"
                    ),
                    handler_key=raw.get(
                        "handler_key"
                    ),
                    lease_seconds=(
                        raw.get(
                            "lease_seconds"
                        )
                    ),
                    retry_delay_seconds=(
                        raw.get(
                            "retry_delay_seconds",
                            0,
                        )
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

        return JobQueueConfig(
            queues=queues,
            workers=workers,
            attach_event_bus=value.get(
                "attach_event_bus",
                False,
            ),
            state_path=value.get(
                "state_path"
            ),
            load_state_on_start=(
                value.get(
                    "load_state_on_start",
                    False,
                )
            ),
            metadata=value.get(
                "metadata",
                {},
            ),
        )
