import threading


class WorkerTask:
    def __init__(
        self,
        task_id,
        future,
        function,
        args,
        kwargs,
    ):
        self.task_id = task_id
        self.future = future
        self.function = function
        self.args = args
        self.kwargs = kwargs


class WorkerPool:
    """
    Fixed-size handwritten worker pool.

    No concurrent.futures and no queue.Queue are used. Task scheduling relies
    on BoundedTaskQueue and TaskFuture from this folder.
    """

    def __init__(
        self,
        worker_count=4,
        queue_capacity=128,
        thread_name_prefix="sirellm-worker",
        daemon=True,
    ):
        if (
            not isinstance(
                worker_count,
                int,
            )
            or worker_count <= 0
        ):
            raise ValueError(
                "worker_count must be positive int"
            )

        if not isinstance(
            thread_name_prefix,
            str,
        ) or thread_name_prefix == "":
            raise ValueError(
                "thread_name_prefix must be non-empty str"
            )

        self.worker_count = (
            worker_count
        )

        self.queue = (
            BoundedTaskQueue(
                queue_capacity
            )
        )

        self.thread_name_prefix = (
            thread_name_prefix
        )
        self.daemon = bool(
            daemon
        )

        self._threads = []
        self._lock = threading.RLock()

        self._started = False
        self._shutdown = False
        self._task_sequence = 0
        self._active = 0

        self.total_submitted = 0
        self.total_started = 0
        self.total_succeeded = 0
        self.total_failed = 0
        self.total_cancelled = 0

    def start(
        self,
    ):
        with self._lock:
            if self._shutdown:
                raise RuntimeError(
                    "worker pool has been shut down"
                )

            if self._started:
                return self

            self._started = True

            index = 0

            while index < self.worker_count:
                thread = threading.Thread(
                    target=self._worker_loop,
                    name=(
                        self.thread_name_prefix
                        + "-"
                        + str(
                            index + 1
                        )
                    ),
                    daemon=self.daemon,
                )

                self._threads.append(
                    thread
                )

                thread.start()

                index += 1

        return self

    def submit(
        self,
        function,
        *args,
        block=True,
        timeout=None,
        **kwargs
    ):
        if not callable(
            function
        ):
            raise TypeError(
                "function must be callable"
            )

        with self._lock:
            if self._shutdown:
                raise RuntimeError(
                    "worker pool is shut down"
                )

            if not self._started:
                self.start()

            self._task_sequence += 1

            task_id = (
                "task-"
                + str(
                    self._task_sequence
                )
            )

            future = TaskFuture(
                task_id
            )

            task = WorkerTask(
                task_id=task_id,
                future=future,
                function=function,
                args=args,
                kwargs=kwargs,
            )

            self.total_submitted += 1

        try:
            self.queue.put(
                task,
                block=block,
                timeout=timeout,
            )

        except Exception:
            with self._lock:
                self.total_submitted -= 1
            raise

        return future

    def shutdown(
        self,
        wait=True,
        cancel_pending=False,
    ):
        with self._lock:
            if self._shutdown:
                threads = list(
                    self._threads
                )
            else:
                self._shutdown = True

                if cancel_pending:
                    pending = self.queue.drain()

                    for task in pending:
                        if task.future.cancel():
                            self.total_cancelled += 1

                self.queue.close()

                threads = list(
                    self._threads
                )

        if wait:
            for thread in threads:
                thread.join()

        return self

    def status(
        self,
    ):
        with self._lock:
            alive = 0

            for thread in self._threads:
                if thread.is_alive():
                    alive += 1

            return {
                "worker_count": (
                    self.worker_count
                ),
                "started": self._started,
                "shutdown": self._shutdown,
                "alive_workers": alive,
                "active_tasks": (
                    self._active
                ),
                "queued_tasks": (
                    self.queue.size()
                ),
                "total_submitted": (
                    self.total_submitted
                ),
                "total_started": (
                    self.total_started
                ),
                "total_succeeded": (
                    self.total_succeeded
                ),
                "total_failed": (
                    self.total_failed
                ),
                "total_cancelled": (
                    self.total_cancelled
                ),
            }

    def _worker_loop(
        self,
    ):
        while True:
            task = self.queue.get()

            if task is None:
                break

            if task.future.cancelled():
                with self._lock:
                    self.total_cancelled += 1
                continue

            if not task.future.set_running():
                with self._lock:
                    self.total_cancelled += 1
                continue

            with self._lock:
                self._active += 1
                self.total_started += 1

            try:
                result = task.function(
                    *task.args,
                    **task.kwargs
                )

                task.future.set_result(
                    result
                )

                with self._lock:
                    self.total_succeeded += 1

            except BaseException as error:
                task.future.set_exception(
                    error
                )

                with self._lock:
                    self.total_failed += 1

            finally:
                with self._lock:
                    self._active -= 1
