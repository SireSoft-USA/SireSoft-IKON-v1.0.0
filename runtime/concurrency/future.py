import threading


class TaskFuture:
    """
    Handwritten future used by the SireLLM worker pool.

    State transitions:
      pending -> running -> succeeded
      pending -> running -> failed
      pending -> cancelled
    """

    TERMINAL = (
        "succeeded",
        "failed",
        "cancelled",
    )

    def __init__(
        self,
        task_id,
    ):
        if not isinstance(
            task_id,
            str,
        ) or task_id == "":
            raise ValueError(
                "task_id must be non-empty str"
            )

        self.task_id = task_id
        self._state = "pending"
        self._result = None
        self._exception = None
        self._condition = (
            threading.Condition()
        )

    def state(
        self,
    ):
        with self._condition:
            return self._state

    def done(
        self,
    ):
        with self._condition:
            return (
                self._state
                in self.TERMINAL
            )

    def running(
        self,
    ):
        with self._condition:
            return (
                self._state
                == "running"
            )

    def cancelled(
        self,
    ):
        with self._condition:
            return (
                self._state
                == "cancelled"
            )

    def cancel(
        self,
    ):
        with self._condition:
            if self._state != "pending":
                return False

            self._state = "cancelled"
            self._condition.notify_all()

            return True

    def set_running(
        self,
    ):
        with self._condition:
            if self._state == "cancelled":
                return False

            if self._state != "pending":
                raise RuntimeError(
                    "future can only enter running from pending"
                )

            self._state = "running"
            self._condition.notify_all()

            return True

    def set_result(
        self,
        value,
    ):
        with self._condition:
            if self._state != "running":
                raise RuntimeError(
                    "future result requires running state"
                )

            self._result = value
            self._state = "succeeded"
            self._condition.notify_all()

            return self

    def set_exception(
        self,
        error,
    ):
        if not isinstance(
            error,
            BaseException,
        ):
            raise TypeError(
                "error must be BaseException"
            )

        with self._condition:
            if self._state != "running":
                raise RuntimeError(
                    "future exception requires running state"
                )

            self._exception = error
            self._state = "failed"
            self._condition.notify_all()

            return self

    def result(
        self,
        timeout=None,
    ):
        with self._condition:
            self._wait_terminal(
                timeout
            )

            if self._state == "cancelled":
                raise RuntimeError(
                    "future was cancelled"
                )

            if self._state == "failed":
                raise self._exception

            return self._result

    def exception(
        self,
        timeout=None,
    ):
        with self._condition:
            self._wait_terminal(
                timeout
            )

            if self._state == "cancelled":
                raise RuntimeError(
                    "future was cancelled"
                )

            return self._exception

    def _wait_terminal(
        self,
        timeout,
    ):
        if timeout is not None:
            if (
                not isinstance(
                    timeout,
                    (int, float),
                )
                or timeout < 0
            ):
                raise ValueError(
                    "timeout must be non-negative or None"
                )

        if self._state in self.TERMINAL:
            return

        if timeout is None:
            while self._state not in self.TERMINAL:
                self._condition.wait()

            return

        # Condition.wait(timeout) can wake spuriously. Track elapsed time
        # without depending on concurrent.futures.
        import time

        deadline = (
            time.monotonic()
            + float(
                timeout
            )
        )

        while self._state not in self.TERMINAL:
            remaining = (
                deadline
                - time.monotonic()
            )

            if remaining <= 0:
                raise TimeoutError(
                    "future result timed out"
                )

            self._condition.wait(
                remaining
            )
