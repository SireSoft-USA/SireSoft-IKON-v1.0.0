class JobQueueManager:
    """
    Multi-queue orchestration with optional EventBus lifecycle publication.
    """

    def __init__(
        self,
        persistence=None,
        event_bus=None,
    ):
        self.persistence = (
            JobQueuePersistence()
            if persistence is None
            else persistence
        )

        self.event_bus = event_bus

        self._queues = {}
        self._order = []
        self._job_sequence = 0

    def create_queue(
        self,
        queue_name,
        default_lease_seconds=30,
        default_max_attempts=3,
    ):
        if queue_name in self._queues:
            raise ValueError(
                "queue already exists: "
                + str(queue_name)
            )

        queue = JobQueue(
            queue_name=queue_name,
            default_lease_seconds=(
                default_lease_seconds
            ),
            default_max_attempts=(
                default_max_attempts
            ),
        )

        self._queues[
            queue_name
        ] = queue

        self._order.append(
            queue_name
        )

        return queue

    def remove_queue(
        self,
        queue_name,
        require_empty=True,
    ):
        queue = self.get_queue(
            queue_name
        )

        if (
            require_empty
            and queue.status()[
                "job_count"
            ] > 0
        ):
            raise RuntimeError(
                "cannot remove non-empty queue"
            )

        del self._queues[
            queue_name
        ]

        self._order = [
            existing
            for existing in self._order
            if existing != queue_name
        ]

        return queue

    def get_queue(
        self,
        queue_name,
    ):
        if queue_name not in self._queues:
            raise KeyError(
                "queue not found: "
                + str(queue_name)
            )

        return self._queues[
            queue_name
        ]

    def list_queues(self):
        return [
            self._queues[
                queue_name
            ].status()
            for queue_name in self._order
        ]

    def enqueue(
        self,
        queue_name,
        payload,
        now,
        priority=0,
        available_at=None,
        max_attempts=None,
        metadata=None,
        job_id=None,
        trace_id=None,
        correlation_id=None,
    ):
        queue = self.get_queue(
            queue_name
        )

        self._validate_now(now)

        self._job_sequence += 1

        sequence = self._job_sequence

        if job_id is None:
            job_id = (
                "job-"
                + str(sequence)
            )

        if max_attempts is None:
            max_attempts = (
                queue.default_max_attempts
            )

        job = Job(
            job_id=job_id,
            queue_name=queue_name,
            payload=payload,
            sequence=sequence,
            created_at=now,
            priority=priority,
            available_at=available_at,
            max_attempts=max_attempts,
            metadata=metadata,
        )

        queue.add_job(
            job
        )

        self._publish_event(
            topic="job.enqueued",
            timestamp=now,
            job=job,
            extra={},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        return job

    def claim(
        self,
        queue_name,
        worker_id,
        now,
        lease_seconds=None,
        trace_id=None,
        correlation_id=None,
    ):
        queue = self.get_queue(
            queue_name
        )

        job = queue.claim(
            worker_id=worker_id,
            now=now,
            lease_seconds=(
                lease_seconds
            ),
        )

        if job is not None:
            self._publish_event(
                topic="job.claimed",
                timestamp=now,
                job=job,
                extra={
                    "worker_id": worker_id,
                },
                trace_id=trace_id,
                correlation_id=(
                    correlation_id
                ),
            )

        return job

    def complete(
        self,
        queue_name,
        job_id,
        worker_id,
        now,
        result=None,
        trace_id=None,
        correlation_id=None,
    ):
        queue = self.get_queue(
            queue_name
        )

        job = queue.complete(
            job_id=job_id,
            worker_id=worker_id,
            now=now,
            result=result,
        )

        self._publish_event(
            topic="job.completed",
            timestamp=now,
            job=job,
            extra={
                "worker_id": worker_id,
            },
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        return job

    def fail(
        self,
        queue_name,
        job_id,
        worker_id,
        now,
        error_message,
        retry_delay_seconds=0,
        trace_id=None,
        correlation_id=None,
    ):
        queue = self.get_queue(
            queue_name
        )

        job = queue.fail(
            job_id=job_id,
            worker_id=worker_id,
            now=now,
            error_message=error_message,
            retry_delay_seconds=(
                retry_delay_seconds
            ),
        )

        topic = (
            "job.dead_letter"
            if job.status == "dead_letter"
            else "job.retry_scheduled"
        )

        self._publish_event(
            topic=topic,
            timestamp=now,
            job=job,
            extra={
                "worker_id": worker_id,
                "error_message": (
                    error_message
                ),
            },
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        return job

    def retry(
        self,
        queue_name,
        job_id,
        now,
        delay_seconds=0,
        reset_attempts=False,
    ):
        return self.get_queue(
            queue_name
        ).retry(
            job_id=job_id,
            now=now,
            delay_seconds=delay_seconds,
            reset_attempts=reset_attempts,
        )

    def cancel(
        self,
        queue_name,
        job_id,
        now,
        trace_id=None,
        correlation_id=None,
    ):
        job = self.get_queue(
            queue_name
        ).cancel(
            job_id=job_id,
            now=now,
        )

        self._publish_event(
            topic="job.cancelled",
            timestamp=now,
            job=job,
            extra={},
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        return job

    def recover_expired(
        self,
        queue_name,
        now,
        retry_delay_seconds=0,
    ):
        return self.get_queue(
            queue_name
        ).recover_expired(
            now=now,
            retry_delay_seconds=(
                retry_delay_seconds
            ),
        )

    def get_job(
        self,
        queue_name,
        job_id,
    ):
        return self.get_queue(
            queue_name
        ).get(
            job_id
        )

    def list_jobs(
        self,
        queue_name,
        status=None,
        limit=100,
        newest_first=False,
    ):
        return self.get_queue(
            queue_name
        ).list_jobs(
            status=status,
            limit=limit,
            newest_first=newest_first,
        )

    def purge_terminal(
        self,
        queue_name,
    ):
        return self.get_queue(
            queue_name
        ).purge_terminal()

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

    def export_state(self):
        return {
            "format": "SireLLMJobQueueState",
            "version": 1,
            "job_sequence": (
                self._job_sequence
            ),
            "queues": [
                self._queues[
                    queue_name
                ].export_state()
                for queue_name in self._order
            ],
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(state, dict):
            raise TypeError(
                "job-queue manager state must be dict"
            )

        if state.get("format") != "SireLLMJobQueueState":
            raise ValueError(
                "invalid job-queue manager state format"
            )

        if int(state.get("version", 0)) != 1:
            raise ValueError(
                "unsupported job-queue manager state version"
            )

        staged = {}
        order = []

        for queue_state in state.get("queues", []):
            queue = JobQueue.from_state(
                queue_state
            )

            if queue.queue_name in staged:
                raise ValueError(
                    "duplicate queue in persisted state"
                )

            staged[
                queue.queue_name
            ] = queue

            order.append(
                queue.queue_name
            )

        self._queues = staged
        self._order = order
        self._job_sequence = int(
            state.get(
                "job_sequence",
                0,
            )
        )

        return self

    def status(self):
        queues = self.list_queues()

        total_jobs = 0

        aggregate = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "dead_letter": 0,
            "cancelled": 0,
        }

        for queue in queues:
            total_jobs += queue[
                "job_count"
            ]

            for key in aggregate:
                aggregate[
                    key
                ] += queue[
                    "counts"
                ][
                    key
                ]

        return {
            "ready": True,
            "queue_count": len(
                queues
            ),
            "total_jobs": total_jobs,
            "counts": aggregate,
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
            "queues": queues,
        }

    def _publish_event(
        self,
        topic,
        timestamp,
        job,
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
            "job_id": job.job_id,
            "queue_name": (
                job.queue_name
            ),
            "status": job.status,
            "attempts": job.attempts,
            "priority": job.priority,
        }

        for key in extra:
            payload[
                key
            ] = extra[key]

        self.event_bus.publish(
            topic=topic,
            timestamp=timestamp,
            payload=payload,
            source_service="job_queue",
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(now, int):
            raise TypeError(
                "now must be integer seconds"
            )

        if now < 0:
            raise ValueError(
                "now must be non-negative"
            )
