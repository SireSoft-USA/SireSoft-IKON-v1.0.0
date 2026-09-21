class RuntimeHealthManager:
    """
    Aggregates runtime liveness/readiness from independently executable probes.
    """

    def __init__(
        self,
    ):
        self._probes = {}
        self._order = []
        self.total_checks = 0

    def register(
        self,
        probe,
    ):
        if not isinstance(
            probe,
            RuntimeProbe,
        ):
            raise TypeError(
                "probe must be RuntimeProbe"
            )

        if probe.name in self._probes:
            raise ValueError(
                "duplicate runtime health probe: "
                + probe.name
            )

        self._probes[
            probe.name
        ] = probe

        self._order.append(
            probe.name
        )

        return probe

    def check(
        self,
    ):
        results = []

        for name in self._order:
            result = (
                self._probes[
                    name
                ]
                .execute()
            )

            results.append(
                result
            )

        self.total_checks += 1

        return self._aggregate(
            results
        )

    def check_one(
        self,
        name,
    ):
        if name not in self._probes:
            raise KeyError(
                "runtime health probe not found: "
                + str(
                    name
                )
            )

        self.total_checks += 1

        return (
            self._probes[
                name
            ]
            .execute()
            .to_dict()
        )

    def list_probes(
        self,
    ):
        return [
            {
                "name": name,
                "required": (
                    self._probes[
                        name
                    ].required
                ),
            }
            for name
            in self._order
        ]

    def status(
        self,
    ):
        return {
            "probe_count": len(
                self._order
            ),
            "probes": (
                self.list_probes()
            ),
            "total_checks": (
                self.total_checks
            ),
        }

    def _aggregate(
        self,
        results,
    ):
        overall_status = "healthy"
        ready = True
        live = True

        required_unhealthy = False
        optional_unhealthy = False
        any_degraded = False

        public = []

        for result in results:
            public.append(
                result.to_dict()
            )

            probe = self._probes[
                result.name
            ]

            if result.status == "unhealthy":
                if probe.required:
                    required_unhealthy = True
                else:
                    optional_unhealthy = True

            if result.status == "degraded":
                any_degraded = True

            if probe.required and not result.ready:
                ready = False

        if required_unhealthy:
            overall_status = "unhealthy"
            live = False

        elif (
            optional_unhealthy
            or any_degraded
        ):
            overall_status = "degraded"

        return {
            "status": overall_status,
            "ready": ready,
            "live": live,
            "probes": public,
            "probe_count": len(
                public
            ),
        }
