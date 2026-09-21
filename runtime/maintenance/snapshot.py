class MaintenanceSnapshot:
    """
    Remembers pre-maintenance discovery state so exit does not accidentally
    enable or mark healthy instances that were already disabled/unhealthy.
    """

    def __init__(
        self,
        captured_at,
    ):
        if not isinstance(
            captured_at,
            int,
        ) or captured_at < 0:
            raise ValueError(
                "captured_at must be non-negative int"
            )

        self.captured_at = captured_at
        self.instances = {}
        self.order = []

    def capture(
        self,
        descriptor,
    ):
        instance_id = (
            descriptor.instance_id
        )

        if instance_id in self.instances:
            raise ValueError(
                "instance already captured: "
                + instance_id
            )

        self.instances[
            instance_id
        ] = {
            "enabled": bool(
                descriptor.enabled
            ),
            "healthy": bool(
                descriptor.healthy
            ),
        }

        self.order.append(
            instance_id
        )

        return self

    def get(
        self,
        instance_id,
    ):
        if instance_id not in self.instances:
            raise KeyError(
                "maintenance snapshot has no instance: "
                + str(
                    instance_id
                )
            )

        return dict(
            self.instances[
                instance_id
            ]
        )

    def to_dict(
        self,
    ):
        return {
            "captured_at": (
                self.captured_at
            ),
            "instances": {
                instance_id: dict(
                    self.instances[
                        instance_id
                    ]
                )
                for instance_id
                in self.order
            },
            "order": list(
                self.order
            ),
        }
