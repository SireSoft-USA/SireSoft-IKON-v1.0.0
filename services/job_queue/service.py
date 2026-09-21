class JobQueueService:
    """
    Protocol-facing job queue.

    Supported operations:
      create_queue
      remove_queue
      list_queues
      enqueue
      claim
      complete
      fail
      retry
      cancel
      recover_expired
      get_job
      list_jobs
      purge_terminal
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager=None,
    ):
        self.manager = (
            JobQueueManager()
            if manager is None
            else manager
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "job_queue":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = request.operation

            if operation == "create_queue":
                queue = self.manager.create_queue(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    default_lease_seconds=request.payload.get(
                        "default_lease_seconds",
                        30,
                    ),
                    default_max_attempts=request.payload.get(
                        "default_max_attempts",
                        3,
                    ),
                )

                return self._success(
                    request,
                    {
                        "queue": (
                            queue.status()
                        ),
                    },
                )

            if operation == "remove_queue":
                queue = self.manager.remove_queue(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    require_empty=request.payload.get(
                        "require_empty",
                        True,
                    ),
                )

                return self._success(
                    request,
                    {
                        "removed_queue_name": (
                            queue.queue_name
                        ),
                    },
                )

            if operation == "list_queues":
                queues = self.manager.list_queues()

                return self._success(
                    request,
                    {
                        "queues": queues,
                        "count": len(queues),
                    },
                )

            if operation == "enqueue":
                job = self.manager.enqueue(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    payload=self._required(
                        request.payload,
                        "payload",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    priority=request.payload.get(
                        "priority",
                        0,
                    ),
                    available_at=request.payload.get(
                        "available_at"
                    ),
                    max_attempts=request.payload.get(
                        "max_attempts"
                    ),
                    metadata=request.payload.get(
                        "metadata"
                    ),
                    job_id=request.payload.get(
                        "job_id"
                    ),
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id,
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "claim":
                job = self.manager.claim(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    worker_id=self._required(
                        request.payload,
                        "worker_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    lease_seconds=request.payload.get(
                        "lease_seconds"
                    ),
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id,
                )

                return self._success(
                    request,
                    {
                        "job": (
                            None
                            if job is None
                            else job.public_dict()
                        ),
                    },
                )

            if operation == "complete":
                job = self.manager.complete(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    job_id=self._required(
                        request.payload,
                        "job_id",
                    ),
                    worker_id=self._required(
                        request.payload,
                        "worker_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    result=request.payload.get(
                        "result"
                    ),
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id,
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "fail":
                job = self.manager.fail(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    job_id=self._required(
                        request.payload,
                        "job_id",
                    ),
                    worker_id=self._required(
                        request.payload,
                        "worker_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    error_message=self._required(
                        request.payload,
                        "error_message",
                    ),
                    retry_delay_seconds=request.payload.get(
                        "retry_delay_seconds",
                        0,
                    ),
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id,
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "retry":
                job = self.manager.retry(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    job_id=self._required(
                        request.payload,
                        "job_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    delay_seconds=request.payload.get(
                        "delay_seconds",
                        0,
                    ),
                    reset_attempts=request.payload.get(
                        "reset_attempts",
                        False,
                    ),
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "cancel":
                job = self.manager.cancel(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    job_id=self._required(
                        request.payload,
                        "job_id",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    trace_id=request.trace_id,
                    correlation_id=request.correlation_id,
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "recover_expired":
                result = self.manager.recover_expired(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    now=self._required(
                        request.payload,
                        "now",
                    ),
                    retry_delay_seconds=request.payload.get(
                        "retry_delay_seconds",
                        0,
                    ),
                )

                return self._success(
                    request,
                    result,
                )

            if operation == "get_job":
                job = self.manager.get_job(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    job_id=self._required(
                        request.payload,
                        "job_id",
                    ),
                )

                return self._success(
                    request,
                    {
                        "job": (
                            job.public_dict()
                        ),
                    },
                )

            if operation == "list_jobs":
                jobs = self.manager.list_jobs(
                    queue_name=self._required(
                        request.payload,
                        "queue_name",
                    ),
                    status=request.payload.get(
                        "status"
                    ),
                    limit=request.payload.get(
                        "limit",
                        100,
                    ),
                    newest_first=request.payload.get(
                        "newest_first",
                        False,
                    ),
                )

                return self._success(
                    request,
                    {
                        "jobs": jobs,
                        "count": len(jobs),
                    },
                )

            if operation == "purge_terminal":
                return self._success(
                    request,
                    self.manager.purge_terminal(
                        self._required(
                            request.payload,
                            "queue_name",
                        )
                    ),
                )

            if operation == "save_state":
                info = self.manager.save_state(
                    self._required(
                        request.payload,
                        "path",
                    )
                )

                return self._success(
                    request,
                    {
                        "artifact": info,
                    },
                )

            if operation == "load_state":
                info = self.manager.load_state_file(
                    self._required(
                        request.payload,
                        "path",
                    )
                )

                return self._success(
                    request,
                    {
                        "status": info,
                    },
                )

            if operation == "status":
                return self._success(
                    request,
                    {
                        "status": (
                            self.manager.status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported job-queue operation",
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except PermissionError as error:
            return self._error(
                request,
                "FORBIDDEN",
                str(error),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(error),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(error),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(error),
            )

    def _required(
        self,
        payload,
        key,
    ):
        if key not in payload:
            raise ValueError(
                "payload requires "
                + key
            )

        return payload[key]

    def _success(
        self,
        request,
        data,
    ):
        return (
            ServiceResponse
            .success_response(
                request,
                data=data,
            )
        )

    def _error(
        self,
        request,
        code,
        message,
    ):
        return (
            ServiceResponse
            .error_response(
                request,
                ProtocolError(
                    code=code,
                    message=message,
                    retryable=False,
                ),
            )
        )
