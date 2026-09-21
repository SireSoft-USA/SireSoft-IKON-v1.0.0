class ServiceDrainManager:
    """
    Stops new ServiceHost traffic while allowing already-active handlers to
    finish. Existing discovery enabled/healthy state is preserved for restore.
    """

    def __init__(
        self,
        host,
    ):
        if not isinstance(
            host,
            ServiceHost,
        ):
            raise TypeError(
                "host must be ServiceHost"
            )

        self.host = host
        self.snapshot = None
        self.draining = False

    def begin(
        self,
        now,
    ):
        if not self.host.running:
            raise RuntimeError(
                "service host must be running before drain"
            )

        if self.draining:
            return self.status()

        snapshot = MaintenanceSnapshot(
            now
        )

        changed = []

        try:
            for binding in self.host.bindings.bindings():
                descriptor = (
                    self.host.discovery
                    .registry
                    .get(
                        binding.instance_id
                    )
                )

                snapshot.capture(
                    descriptor
                )

                if descriptor.enabled:
                    self.host.disable(
                        binding.instance_id
                    )
                    changed.append(
                        binding.instance_id
                    )

        except BaseException:
            index = len(
                changed
            ) - 1

            while index >= 0:
                instance_id = changed[
                    index
                ]

                original = snapshot.get(
                    instance_id
                )

                if original[
                    "enabled"
                ]:
                    self.host.enable(
                        instance_id
                    )

                if original[
                    "healthy"
                ]:
                    self.host.mark_healthy(
                        instance_id
                    )
                else:
                    self.host.mark_unhealthy(
                        instance_id
                    )

                index -= 1

            raise

        self.snapshot = snapshot
        self.draining = True

        return self.status()

    def active_requests(
        self,
    ):
        total = 0
        by_instance = {}

        for binding in self.host.bindings.bindings():
            instance = (
                self.host.load_balancer
                .registry
                .get(
                    binding.instance_id
                )
            )

            count = (
                instance.active_requests
            )

            by_instance[
                binding.instance_id
            ] = count

            total += count

        return {
            "total": total,
            "by_instance": (
                by_instance
            ),
        }

    def drained(
        self,
    ):
        return (
            self.active_requests()[
                "total"
            ]
            == 0
        )

    def restore(
        self,
    ):
        if not self.draining:
            return {
                "restored": False,
                "instances": [],
            }

        restored = []

        for instance_id in self.snapshot.order:
            original = (
                self.snapshot.get(
                    instance_id
                )
            )

            if original[
                "enabled"
            ]:
                self.host.enable(
                    instance_id
                )
            else:
                self.host.disable(
                    instance_id
                )

            if original[
                "healthy"
            ]:
                self.host.mark_healthy(
                    instance_id
                )
            else:
                self.host.mark_unhealthy(
                    instance_id
                )

            restored.append(
                instance_id
            )

        self.draining = False
        self.snapshot = None

        return {
            "restored": True,
            "instances": restored,
        }

    def status(
        self,
    ):
        active = (
            self.active_requests()
            if self.host.running
            else {
                "total": 0,
                "by_instance": {},
            }
        )

        return {
            "draining": (
                self.draining
            ),
            "drained": (
                active[
                    "total"
                ]
                == 0
            ),
            "active_requests": (
                active
            ),
            "snapshot": (
                None
                if self.snapshot
                is None
                else self.snapshot
                .to_dict()
            ),
        }
