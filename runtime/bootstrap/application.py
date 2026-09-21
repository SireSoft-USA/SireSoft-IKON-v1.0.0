class RuntimeApplication:
    def __init__(
        self,
        context,
        lifecycle,
    ):
        if not isinstance(context, RuntimeContext):
            raise TypeError("context must be RuntimeContext")

        if not isinstance(lifecycle, LifecycleManager):
            raise TypeError("lifecycle must be LifecycleManager")

        self.context = context
        self.lifecycle = lifecycle
        self._started_once = False
        self._stopped = False

    def start(self):
        if self._stopped:
            raise RuntimeError(
                "runtime application cannot restart after stop"
            )

        if self.lifecycle.phase == "running":
            return self.status()

        self.lifecycle.start_all()
        self._started_once = True

        return self.status()

    def stop(self):
        if not self._started_once:
            self._stopped = True
            return self.status()

        if self._stopped:
            return self.status()

        self.lifecycle.stop_all()
        self._stopped = True

        return self.status()

    def submit(
        self,
        function,
        *args,
        **kwargs
    ):
        if self.lifecycle.phase != "running":
            raise RuntimeError(
                "runtime application is not running"
            )

        return self.context.get(
            "worker_pool"
        ).submit(
            function,
            *args,
            **kwargs
        )

    def storage(self):
        return self.context.get(
            "storage"
        )

    def process_supervisor(self):
        return self.context.get(
            "process_supervisor"
        )

    def status(self):
        lifecycle_status = self.lifecycle.status()

        return {
            "running": (
                lifecycle_status["phase"]
                == "running"
            ),
            "stopped": self._stopped,
            "started_once": self._started_once,
            "context": self.context.summary(),
            "lifecycle": lifecycle_status,
            "worker_pool": self.context.get(
                "worker_pool"
            ).status(),
            "storage": self.context.get(
                "storage"
            ).status(),
            "process_supervisor": self.context.get(
                "process_supervisor"
            ).status(),
        }
