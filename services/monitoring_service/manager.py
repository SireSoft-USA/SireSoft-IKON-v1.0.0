class MonitoringManager:
    """
    Aggregates active service probes and load-balancer instance health.

    Overall state:
      unhealthy - a required probe is unhealthy, or an LB service has no
                  available instances.
      degraded  - optional probe failure, readiness degradation, or partial
                  LB instance availability.
      healthy   - all registered checks are healthy.
    """

    def __init__(
        self,
        load_balancer=None,
    ):
        self.load_balancer = load_balancer

        self._probes = {}
        self._order = []
        self._sequence = 0
        self._last_results = {}

    def register_probe(
        self,
        probe,
    ):
        if not isinstance(
            probe,
            ServiceProbe,
        ):
            raise TypeError(
                "probe must be ServiceProbe"
            )

        if probe.probe_id in self._probes:
            raise ValueError(
                "duplicate probe_id: "
                + probe.probe_id
            )

        self._probes[
            probe.probe_id
        ] = probe

        self._order.append(
            probe.probe_id
        )

        return self

    def deregister_probe(
        self,
        probe_id,
    ):
        if probe_id not in self._probes:
            raise KeyError(
                "probe not registered: "
                + str(probe_id)
            )

        probe = self._probes.pop(
            probe_id
        )

        self._order = [
            existing
            for existing in self._order
            if existing != probe_id
        ]

        if probe_id in self._last_results:
            del self._last_results[
                probe_id
            ]

        return probe

    def get_probe(
        self,
        probe_id,
    ):
        if probe_id not in self._probes:
            raise KeyError(
                "probe not registered: "
                + str(probe_id)
            )

        return self._probes[
            probe_id
        ]

    def list_probes(
        self,
    ):
        return [
            self._probes[
                probe_id
            ].summary()
            for probe_id in self._order
        ]

    def run_probe(
        self,
        probe_id,
        trace_id=None,
    ):
        probe = self.get_probe(
            probe_id
        )

        self._sequence += 1

        result = probe.execute(
            request_id=(
                "monitor-"
                + str(
                    self._sequence
                )
            ),
            trace_id=trace_id,
        )

        self._last_results[
            probe_id
        ] = result

        return result

    def run_all(
        self,
        trace_id=None,
    ):
        results = []

        for probe_id in self._order:
            results.append(
                self.run_probe(
                    probe_id,
                    trace_id=trace_id,
                )
            )

        return results

    def load_balancer_status(
        self,
    ):
        if self.load_balancer is None:
            return {
                "attached": False,
                "status": "not_attached",
                "services": {},
                "total_instances": 0,
                "available_instances": 0,
                "unhealthy_instances": 0,
                "paused_instances": 0,
                "active_requests": 0,
                "total_requests": 0,
                "failed_requests": 0,
            }

        if not hasattr(
            self.load_balancer,
            "health_snapshot",
        ):
            raise TypeError(
                "load_balancer must provide health_snapshot()"
            )

        snapshot = (
            self.load_balancer
            .health_snapshot()
        )

        if not isinstance(
            snapshot,
            dict,
        ):
            raise TypeError(
                "load balancer health snapshot must be dict"
            )

        service_summaries = {}

        total_instances = 0
        available_instances = 0
        unhealthy_instances = 0
        paused_instances = 0
        active_requests = 0
        total_requests = 0
        failed_requests = 0

        has_zero_available_service = False
        has_partial_service = False

        for service_name in snapshot:
            rows = snapshot[
                service_name
            ]

            service_total = len(
                rows
            )

            service_available = 0
            service_unhealthy = 0
            service_paused = 0
            service_active = 0
            service_requests = 0
            service_failures = 0

            for row in rows:
                healthy = bool(
                    row.get(
                        "healthy",
                        False,
                    )
                )

                accepting = bool(
                    row.get(
                        "accepting_requests",
                        False,
                    )
                )

                available = (
                    healthy
                    and accepting
                )

                if available:
                    service_available += 1

                if not healthy:
                    service_unhealthy += 1

                if healthy and not accepting:
                    service_paused += 1

                service_active += int(
                    row.get(
                        "active_requests",
                        0,
                    )
                )

                service_requests += int(
                    row.get(
                        "total_requests",
                        0,
                    )
                )

                service_failures += int(
                    row.get(
                        "failed_requests",
                        0,
                    )
                )

            if (
                service_total > 0
                and service_available == 0
            ):
                service_status = "unhealthy"
                has_zero_available_service = True

            elif service_available < service_total:
                service_status = "degraded"
                has_partial_service = True

            else:
                service_status = "healthy"

            service_summaries[
                service_name
            ] = {
                "status": service_status,
                "total_instances": service_total,
                "available_instances": service_available,
                "unhealthy_instances": service_unhealthy,
                "paused_instances": service_paused,
                "active_requests": service_active,
                "total_requests": service_requests,
                "failed_requests": service_failures,
                "instances": self._copy(
                    rows
                ),
            }

            total_instances += service_total
            available_instances += service_available
            unhealthy_instances += service_unhealthy
            paused_instances += service_paused
            active_requests += service_active
            total_requests += service_requests
            failed_requests += service_failures

        if has_zero_available_service:
            status = "unhealthy"

        elif has_partial_service:
            status = "degraded"

        else:
            status = "healthy"

        return {
            "attached": True,
            "status": status,
            "services": service_summaries,
            "total_instances": total_instances,
            "available_instances": available_instances,
            "unhealthy_instances": unhealthy_instances,
            "paused_instances": paused_instances,
            "active_requests": active_requests,
            "total_requests": total_requests,
            "failed_requests": failed_requests,
        }

    def health(
        self,
        run_probes=True,
        trace_id=None,
    ):
        if run_probes:
            results = self.run_all(
                trace_id=trace_id
            )
        else:
            results = []

            for probe_id in self._order:
                if probe_id in self._last_results:
                    results.append(
                        self._last_results[
                            probe_id
                        ]
                    )

        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        required_unhealthy = False
        required_degraded = False
        optional_problem = False

        for result in results:
            if result.status == "healthy":
                healthy_count += 1

            elif result.status == "degraded":
                degraded_count += 1

                if result.required:
                    required_degraded = True
                else:
                    optional_problem = True

            else:
                unhealthy_count += 1

                if result.required:
                    required_unhealthy = True
                else:
                    optional_problem = True

        lb = self.load_balancer_status()

        if required_unhealthy:
            overall = "unhealthy"

        elif lb[
            "status"
        ] == "unhealthy":
            overall = "unhealthy"

        elif (
            required_degraded
            or optional_problem
            or lb[
                "status"
            ] == "degraded"
        ):
            overall = "degraded"

        else:
            overall = "healthy"

        return {
            "status": overall,
            "ready": (
                overall
                != "unhealthy"
            ),
            "probe_count": len(
                self._order
            ),
            "executed_probe_count": len(
                results
            ),
            "healthy_probes": healthy_count,
            "degraded_probes": degraded_count,
            "unhealthy_probes": unhealthy_count,
            "probes": [
                result.to_dict()
                for result in results
            ],
            "load_balancer": lb,
        }

    def snapshot(
        self,
        run_probes=True,
        trace_id=None,
    ):
        return self.health(
            run_probes=run_probes,
            trace_id=trace_id,
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}

            for key in value:
                result[key] = self._copy(
                    value[key]
                )

            return result

        if isinstance(value, list):
            return [
                self._copy(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                self._copy(item)
                for item in value
            ]

        return value
