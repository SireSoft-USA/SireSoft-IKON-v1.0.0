class JobQueueConfig:
    """
    Queue topology + optional worker bootstrap.

    Job payloads themselves are runtime data and are never serialized here.
    """

    def __init__(
        self,
        queues,
        workers=None,
        attach_event_bus=False,
        state_path=None,
        load_state_on_start=False,
        metadata=None,
    ):
        if not isinstance(
            queues,
            (list, tuple),
        ) or len(
            queues
        ) == 0:
            raise ValueError(
                "queues must be non-empty list/tuple"
            )

        if workers is None:
            workers = []

        if not isinstance(
            workers,
            (list, tuple),
        ):
            raise TypeError(
                "workers must be list/tuple or None"
            )

        queue_items = []
        queue_names = {}

        for queue in queues:
            if not isinstance(
                queue,
                JobQueueDefinitionConfig,
            ):
                raise TypeError(
                    "queue entries must be JobQueueDefinitionConfig"
                )

            if queue.queue_name in queue_names:
                raise ValueError(
                    "duplicate queue_name: "
                    + queue.queue_name
                )

            queue_names[
                queue.queue_name
            ] = True
            queue_items.append(
                queue
            )

        worker_items = []
        worker_ids = {}

        for worker in workers:
            if not isinstance(
                worker,
                JobWorkerConfig,
            ):
                raise TypeError(
                    "worker entries must be JobWorkerConfig"
                )

            if worker.worker_id in worker_ids:
                raise ValueError(
                    "duplicate worker_id: "
                    + worker.worker_id
                )

            worker_ids[
                worker.worker_id
            ] = True
            worker_items.append(
                worker
            )

        if state_path is not None and (
            not isinstance(
                state_path,
                str,
            )
            or state_path == ""
        ):
            raise ValueError(
                "state_path must be non-empty str or None"
            )

        if (
            load_state_on_start
            and state_path is None
        ):
            raise ValueError(
                "load_state_on_start requires state_path"
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

        self.queues = queue_items
        self.workers = worker_items
        self.attach_event_bus = bool(
            attach_event_bus
        )
        self.state_path = state_path
        self.load_state_on_start = bool(
            load_state_on_start
        )
        self.metadata = self._copy(
            metadata
        )

    def enabled_queues(
        self,
    ):
        return [
            queue
            for queue
            in self.queues
            if queue.enabled
        ]

    def enabled_workers(
        self,
    ):
        return [
            worker
            for worker
            in self.workers
            if worker.enabled
        ]

    def queue_map(
        self,
    ):
        return {
            queue.queue_name: queue
            for queue
            in self.queues
        }

    def to_dict(
        self,
    ):
        return {
            "queues": [
                queue.to_dict()
                for queue
                in self.queues
            ],
            "workers": [
                worker.to_dict()
                for worker
                in self.workers
            ],
            "attach_event_bus": (
                self.attach_event_bus
            ),
            "state_path": (
                self.state_path
            ),
            "load_state_on_start": (
                self.load_state_on_start
            ),
            "metadata": self._copy(
                self.metadata
            ),
        }

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            return {
                key: self._copy(
                    value[
                        key
                    ]
                )
                for key
                in value
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                self._copy(
                    item
                )
                for item
                in value
            ]

        return value
