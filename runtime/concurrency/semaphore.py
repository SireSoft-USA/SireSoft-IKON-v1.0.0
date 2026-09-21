import threading
import time


class CountingSemaphore:
    """
    Handwritten counting semaphore with timeout support and visibility into
    current permit usage.
    """

    def __init__(
        self,
        permits,
    ):
        if (
            not isinstance(
                permits,
                int,
            )
            or permits <= 0
        ):
            raise ValueError(
                "permits must be positive int"
            )

        self.permits = permits
        self._available = permits
        self._condition = (
            threading.Condition()
        )

        self.total_acquires = 0
        self.total_releases = 0

    def acquire(
        self,
        block=True,
        timeout=None,
    ):
        with self._condition:
            if not block:
                if self._available <= 0:
                    return False

            else:
                deadline = None

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

                    deadline = (
                        time.monotonic()
                        + float(
                            timeout
                        )
                    )

                while self._available <= 0:
                    if deadline is None:
                        self._condition.wait()
                    else:
                        remaining = (
                            deadline
                            - time.monotonic()
                        )

                        if remaining <= 0:
                            return False

                        self._condition.wait(
                            remaining
                        )

            if self._available <= 0:
                return False

            self._available -= 1
            self.total_acquires += 1

            return True

    def release(
        self,
    ):
        with self._condition:
            if self._available >= self.permits:
                raise RuntimeError(
                    "semaphore release would exceed permit count"
                )

            self._available += 1
            self.total_releases += 1
            self._condition.notify()

            return True

    def available(
        self,
    ):
        with self._condition:
            return self._available

    def in_use(
        self,
    ):
        with self._condition:
            return (
                self.permits
                - self._available
            )

    def status(
        self,
    ):
        with self._condition:
            return {
                "permits": self.permits,
                "available": (
                    self._available
                ),
                "in_use": (
                    self.permits
                    - self._available
                ),
                "total_acquires": (
                    self.total_acquires
                ),
                "total_releases": (
                    self.total_releases
                ),
            }
