class ProcessRegistry:
    """
    Deterministic registry of process specifications and current process runs.
    """

    def __init__(
        self,
    ):
        self._specs = {}
        self._processes = {}
        self._order = []

    def register(
        self,
        spec,
    ):
        if not isinstance(
            spec,
            ProcessSpec,
        ):
            raise TypeError(
                "spec must be ProcessSpec"
            )

        if spec.name in self._specs:
            raise ValueError(
                "process spec already registered: "
                + spec.name
            )

        self._specs[
            spec.name
        ] = spec

        self._processes[
            spec.name
        ] = None

        self._order.append(
            spec.name
        )

        return spec

    def get_spec(
        self,
        name,
    ):
        if name not in self._specs:
            raise KeyError(
                "process spec not found: "
                + str(
                    name
                )
            )

        return self._specs[
            name
        ]

    def set_process(
        self,
        name,
        process,
    ):
        self.get_spec(
            name
        )

        if not isinstance(
            process,
            ManagedProcess,
        ):
            raise TypeError(
                "process must be ManagedProcess"
            )

        self._processes[
            name
        ] = process

        return process

    def get_process(
        self,
        name,
    ):
        self.get_spec(
            name
        )

        return self._processes[
            name
        ]

    def list(
        self,
    ):
        rows = []

        for name in self._order:
            process = self._processes[
                name
            ]

            rows.append({
                "spec": (
                    self._specs[
                        name
                    ].public_dict()
                ),
                "process": (
                    None
                    if process
                    is None
                    else process.status()
                ),
            })

        return rows

    def names(
        self,
    ):
        return list(
            self._order
        )
