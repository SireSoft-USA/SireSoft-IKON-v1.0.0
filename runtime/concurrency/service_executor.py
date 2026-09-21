import threading


class ServiceExecutor:
    """
    Concurrent adapter around a synchronous SireLLM service dispatcher.

    The dispatcher may be a callable(request) or an object exposing handle().
    A local semaphore can impose a stricter per-service concurrency limit than
    the shared worker pool.
    """

    def __init__(
        self,
        worker_pool,
        dispatcher,
        max_in_flight=None,
    ):
        if not isinstance(
            worker_pool,
            WorkerPool,
        ):
            raise TypeError(
                "worker_pool must be WorkerPool"
            )

        if callable(
            dispatcher
        ):
            self._dispatch = (
                dispatcher
            )

        elif hasattr(
            dispatcher,
            "handle",
        ) and callable(
            dispatcher.handle
        ):
            self._dispatch = (
                dispatcher.handle
            )

        else:
            raise TypeError(
                "dispatcher must be callable or expose handle()"
            )

        if max_in_flight is not None:
            if (
                not isinstance(
                    max_in_flight,
                    int,
                )
                or max_in_flight <= 0
            ):
                raise ValueError(
                    "max_in_flight must be positive int or None"
                )

            self._semaphore = (
                CountingSemaphore(
                    max_in_flight
                )
            )

        else:
            self._semaphore = None

        self.worker_pool = worker_pool
        self._lock = threading.Lock()

        self.total_requests = 0
        self.total_succeeded = 0
        self.total_failed = 0

    def submit(
        self,
        request,
        block=True,
        timeout=None,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        with self._lock:
            self.total_requests += 1

        return self.worker_pool.submit(
            self._execute,
            request,
            block=block,
            timeout=timeout,
        )

    def call(
        self,
        request,
        timeout=None,
    ):
        future = self.submit(
            request
        )

        return future.result(
            timeout=timeout
        )

    def status(
        self,
    ):
        with self._lock:
            value = {
                "total_requests": (
                    self.total_requests
                ),
                "total_succeeded": (
                    self.total_succeeded
                ),
                "total_failed": (
                    self.total_failed
                ),
            }

        value[
            "max_in_flight"
        ] = (
            None
            if self._semaphore
            is None
            else self._semaphore
            .permits
        )

        value[
            "in_flight"
        ] = (
            0
            if self._semaphore
            is None
            else self._semaphore
            .in_use()
        )

        return value

    def _execute(
        self,
        request,
    ):
        acquired = False

        try:
            if self._semaphore is not None:
                acquired = (
                    self._semaphore
                    .acquire()
                )

                if not acquired:
                    raise RuntimeError(
                        "service executor could not acquire permit"
                    )

            response = self._dispatch(
                request
            )

            if not isinstance(
                response,
                ServiceResponse,
            ):
                raise TypeError(
                    "service dispatcher must return ServiceResponse"
                )

            with self._lock:
                self.total_succeeded += 1

            return response

        except BaseException:
            with self._lock:
                self.total_failed += 1
            raise

        finally:
            if (
                acquired
                and self._semaphore
                is not None
            ):
                self._semaphore.release()
