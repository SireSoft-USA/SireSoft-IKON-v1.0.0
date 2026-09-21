class SchedulerService:
    """
    Protocol-facing scheduler.

    Supported operations:
      create_task
      remove_task
      get_task
      list_tasks
      enable_task
      disable_task
      reschedule_task
      tick
      save_state
      load_state
      status
    """

    def __init__(
        self,
        manager,
    ):
        if manager is None or not hasattr(
            manager,
            "tick",
        ):
            raise TypeError(
                "manager must provide scheduler operations"
            )

        self.manager = manager

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

        if request.service != (
            "scheduler_service"
        ):
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            operation = (
                request.operation
            )

            if operation == "create_task":
                recurrence = (
                    RecurrenceRule(
                        mode=request.payload.get(
                            "mode",
                            "once",
                        ),
                        interval_seconds=request.payload.get(
                            "interval_seconds"
                        ),
                        max_runs=request.payload.get(
                            "max_runs"
                        ),
                        end_at=request.payload.get(
                            "end_at"
                        ),
                        catch_up=request.payload.get(
                            "catch_up",
                            False,
                        ),
                    )
                )

                task = (
                    self.manager
                    .create_task(
                        task_id=self._required(
                            request.payload,
                            "task_id",
                        ),
                        queue_name=self._required(
                            request.payload,
                            "queue_name",
                        ),
                        payload=self._required(
                            request.payload,
                            "payload",
                        ),
                        next_run_at=self._required(
                            request.payload,
                            "next_run_at",
                        ),
                        recurrence=recurrence,
                        priority=request.payload.get(
                            "priority",
                            0,
                        ),
                        max_attempts=request.payload.get(
                            "max_attempts"
                        ),
                        metadata=request.payload.get(
                            "metadata"
                        ),
                        enabled=request.payload.get(
                            "enabled",
                            True,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "task": (
                            task.public_dict()
                        ),
                    },
                )

            if operation == "remove_task":
                task = (
                    self.manager
                    .remove_task(
                        self._required(
                            request.payload,
                            "task_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "removed_task_id": (
                            task.task_id
                        ),
                    },
                )

            if operation == "get_task":
                task = (
                    self.manager
                    .get_task(
                        self._required(
                            request.payload,
                            "task_id",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "task": (
                            task.public_dict()
                        ),
                    },
                )

            if operation == "list_tasks":
                tasks = (
                    self.manager
                    .list_tasks(
                        status=request.payload.get(
                            "status"
                        ),
                        limit=request.payload.get(
                            "limit",
                            100,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "tasks": tasks,
                        "count": len(
                            tasks
                        ),
                    },
                )

            if operation in (
                "enable_task",
                "disable_task",
            ):
                method = (
                    self.manager.enable_task
                    if operation
                    == "enable_task"
                    else self.manager.disable_task
                )

                task = method(
                    self._required(
                        request.payload,
                        "task_id",
                    )
                )

                return self._success(
                    request,
                    {
                        "task": (
                            task.public_dict()
                        ),
                    },
                )

            if operation == "reschedule_task":
                task = (
                    self.manager
                    .reschedule_task(
                        task_id=self._required(
                            request.payload,
                            "task_id",
                        ),
                        next_run_at=self._required(
                            request.payload,
                            "next_run_at",
                        ),
                        reset_completed=request.payload.get(
                            "reset_completed",
                            False,
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "task": (
                            task.public_dict()
                        ),
                    },
                )

            if operation == "tick":
                result = (
                    self.manager
                    .tick(
                        now=self._required(
                            request.payload,
                            "now",
                        ),
                        trace_id=request.trace_id,
                        correlation_id=(
                            request.correlation_id
                        ),
                    )
                )

                return self._success(
                    request,
                    {
                        "tick": result,
                    },
                )

            if operation == "save_state":
                info = (
                    self.manager
                    .save_state(
                        self._required(
                            request.payload,
                            "path",
                        )
                    )
                )

                return self._success(
                    request,
                    {
                        "artifact": info,
                    },
                )

            if operation == "load_state":
                info = (
                    self.manager
                    .load_state_file(
                        self._required(
                            request.payload,
                            "path",
                        )
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
                            self.manager
                            .status()
                        ),
                    },
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                (
                    "Unsupported scheduler service operation"
                ),
            )

        except KeyError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except RuntimeError as error:
            return self._error(
                request,
                "CONFLICT",
                str(
                    error
                ),
            )

        except FileNotFoundError as error:
            return self._error(
                request,
                "NOT_FOUND",
                str(
                    error
                ),
            )

        except (
            ValueError,
            TypeError,
            IndexError,
        ) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(
                    error
                ),
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

        return payload[
            key
        ]

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
