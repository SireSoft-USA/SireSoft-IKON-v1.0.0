import threading


class ShutdownCoordinator:
    """
    Thread-safe, idempotent shutdown request coordinator.

    The first request becomes canonical. Later requests are counted but do not
    replace the original event or call the callback again.
    """

    def __init__(
        self,
        callback=None,
    ):
        if callback is not None and not callable(
            callback
        ):
            raise TypeError(
                "callback must be callable or None"
            )

        self.callback = callback
        self._event = threading.Event()
        self._lock = threading.Lock()

        self._shutdown_event = None
        self._request_count = 0
        self._callback_count = 0

    def request(
        self,
        reason,
        signal_name=None,
        signal_number=None,
        metadata=None,
    ):
        callback = None
        event = None

        with self._lock:
            self._request_count += 1

            if self._shutdown_event is None:
                self._shutdown_event = ShutdownSignalEvent(
                    reason=reason,
                    signal_name=signal_name,
                    signal_number=signal_number,
                    request_sequence=(
                        self._request_count
                    ),
                    metadata=metadata,
                )

                self._event.set()
                callback = self.callback

            event = self._shutdown_event

        if callback is not None:
            callback(
                event
            )

            with self._lock:
                self._callback_count += 1

        return event

    def requested(
        self,
    ):
        return self._event.is_set()

    def wait(
        self,
        timeout=None,
    ):
        if timeout is not None and (
            not isinstance(
                timeout,
                (int, float),
            )
            or timeout < 0
        ):
            raise ValueError(
                "timeout must be non-negative or None"
            )

        return self._event.wait(
            timeout
        )

    def event(
        self,
    ):
        with self._lock:
            return self._shutdown_event

    def status(
        self,
    ):
        with self._lock:
            return {
                "requested": (
                    self._event.is_set()
                ),
                "request_count": (
                    self._request_count
                ),
                "callback_count": (
                    self._callback_count
                ),
                "event": (
                    None
                    if self._shutdown_event
                    is None
                    else self._shutdown_event
                    .to_dict()
                ),
            }
