import threading
import time


class QueueClosedError(RuntimeError):
    pass


class BoundedTaskQueue:
    """
    Bounded blocking FIFO queue implemented directly with Condition.

    This keeps queue semantics under SireLLM control instead of delegating task
    scheduling to queue.Queue or concurrent.futures.
    """

    def __init__(
        self,
        capacity,
    ):
        if (
            not isinstance(
                capacity,
                int,
            )
            or capacity <= 0
        ):
            raise ValueError(
                "capacity must be positive int"
            )

        self.capacity = capacity
        self._items = []
        self._head = 0
        self._closed = False
        self._condition = (
            threading.Condition()
        )

        self.total_put = 0
        self.total_get = 0

    def put(
        self,
        item,
        block=True,
        timeout=None,
    ):
        with self._condition:
            if self._closed:
                raise QueueClosedError(
                    "task queue is closed"
                )

            if not block:
                if self._size_unlocked() >= self.capacity:
                    raise RuntimeError(
                        "task queue is full"
                    )

            else:
                deadline = self._deadline(
                    timeout
                )

                while (
                    self._size_unlocked()
                    >= self.capacity
                ):
                    if self._closed:
                        raise QueueClosedError(
                            "task queue is closed"
                        )

                    self._wait(
                        deadline,
                        "task queue put timed out",
                    )

            self._items.append(
                item
            )
            self.total_put += 1
            self._condition.notify_all()

            return True

    def get(
        self,
        block=True,
        timeout=None,
    ):
        with self._condition:
            if not block:
                if self._size_unlocked() == 0:
                    if self._closed:
                        return None

                    raise RuntimeError(
                        "task queue is empty"
                    )

            else:
                deadline = self._deadline(
                    timeout
                )

                while self._size_unlocked() == 0:
                    if self._closed:
                        return None

                    self._wait(
                        deadline,
                        "task queue get timed out",
                    )

            if self._size_unlocked() == 0:
                return None

            item = self._items[
                self._head
            ]

            self._head += 1
            self.total_get += 1

            self._compact_unlocked()

            self._condition.notify_all()

            return item

    def close(
        self,
    ):
        with self._condition:
            self._closed = True
            self._condition.notify_all()

        return self

    def drain(
        self,
    ):
        with self._condition:
            result = []

            while self._size_unlocked() > 0:
                result.append(
                    self._items[
                        self._head
                    ]
                )
                self._head += 1
                self.total_get += 1

            self._compact_unlocked(
                force=True
            )

            self._condition.notify_all()

            return result

    def size(
        self,
    ):
        with self._condition:
            return self._size_unlocked()

    def closed(
        self,
    ):
        with self._condition:
            return self._closed

    def status(
        self,
    ):
        with self._condition:
            return {
                "capacity": self.capacity,
                "size": (
                    self._size_unlocked()
                ),
                "closed": self._closed,
                "total_put": (
                    self.total_put
                ),
                "total_get": (
                    self.total_get
                ),
            }

    def _size_unlocked(
        self,
    ):
        return (
            len(
                self._items
            )
            - self._head
        )

    def _compact_unlocked(
        self,
        force=False,
    ):
        if self._head == 0:
            return

        if (
            force
            or self._head >= 128
            or self._head * 2 >= len(
                self._items
            )
        ):
            self._items = self._items[
                self._head:
            ]
            self._head = 0

    def _deadline(
        self,
        timeout,
    ):
        if timeout is None:
            return None

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

        return (
            time.monotonic()
            + float(
                timeout
            )
        )

    def _wait(
        self,
        deadline,
        message,
    ):
        if deadline is None:
            self._condition.wait()
            return

        remaining = (
            deadline
            - time.monotonic()
        )

        if remaining <= 0:
            raise TimeoutError(
                message
            )

        self._condition.wait(
            remaining
        )
