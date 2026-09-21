class JobWorker:
    """
    Synchronous local worker adapter.

    This does not create threads/processes. Runtime orchestration decides when
    run_once() is called. Worker handlers receive the Job object and may return
    any serializable result.
    """

    def __init__(
        self,
        worker_id,
        queue_name,
        manager,
        handler,
        lease_seconds=None,
        retry_delay_seconds=0,
    ):
        if not isinstance(worker_id, str) or worker_id == "":
            raise ValueError("worker_id must be non-empty str")

        if not isinstance(queue_name, str) or queue_name == "":
            raise ValueError("queue_name must be non-empty str")

        if manager is None or not hasattr(
            manager,
            "claim",
        ):
            raise TypeError(
                "manager must provide queue operations"
            )

        if not callable(handler):
            raise TypeError("handler must be callable")

        if lease_seconds is not None:
            if (
                not isinstance(lease_seconds, int)
                or lease_seconds <= 0
            ):
                raise ValueError(
                    "lease_seconds must be positive int or None"
                )

        if (
            not isinstance(retry_delay_seconds, int)
            or retry_delay_seconds < 0
        ):
            raise ValueError(
                "retry_delay_seconds must be non-negative int"
            )

        self.worker_id = worker_id
        self.queue_name = queue_name
        self.manager = manager
        self.handler = handler
        self.lease_seconds = lease_seconds
        self.retry_delay_seconds = (
            retry_delay_seconds
        )

        self.processed = 0
        self.succeeded = 0
        self.failed = 0

    def run_once(
        self,
        now,
        completion_now=None,
        trace_id=None,
        correlation_id=None,
    ):
        job = self.manager.claim(
            queue_name=self.queue_name,
            worker_id=self.worker_id,
            now=now,
            lease_seconds=(
                self.lease_seconds
            ),
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        if job is None:
            return {
                "claimed": False,
                "job": None,
                "success": None,
                "result": None,
                "error": None,
            }

        if completion_now is None:
            completion_now = now

        self.processed += 1

        try:
            result = self.handler(
                job
            )

            completed = (
                self.manager
                .complete(
                    queue_name=(
                        self.queue_name
                    ),
                    job_id=job.job_id,
                    worker_id=(
                        self.worker_id
                    ),
                    now=completion_now,
                    result=result,
                    trace_id=trace_id,
                    correlation_id=(
                        correlation_id
                    ),
                )
            )

            self.succeeded += 1

            return {
                "claimed": True,
                "job": (
                    completed.public_dict()
                ),
                "success": True,
                "result": completed._copy(
                    completed.result
                ),
                "error": None,
            }

        except Exception as error:
            failed = (
                self.manager
                .fail(
                    queue_name=(
                        self.queue_name
                    ),
                    job_id=job.job_id,
                    worker_id=(
                        self.worker_id
                    ),
                    now=completion_now,
                    error_message=str(
                        error
                    ),
                    retry_delay_seconds=(
                        self.retry_delay_seconds
                    ),
                    trace_id=trace_id,
                    correlation_id=(
                        correlation_id
                    ),
                )
            )

            self.failed += 1

            return {
                "claimed": True,
                "job": (
                    failed.public_dict()
                ),
                "success": False,
                "result": None,
                "error": {
                    "type": (
                        type(error).__name__
                    ),
                    "message": str(
                        error
                    ),
                },
            }

    def status(self):
        return {
            "worker_id": self.worker_id,
            "queue_name": (
                self.queue_name
            ),
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
        }
