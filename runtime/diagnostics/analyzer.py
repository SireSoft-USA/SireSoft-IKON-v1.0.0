class RuntimeDiagnosticAnalyzer:
    def analyze(
        self,
        snapshot,
    ):
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be dict")

        findings = []

        self._analyze_runtime(
            snapshot.get("runtime"),
            findings,
        )

        self._analyze_health(
            snapshot.get("health"),
            findings,
        )

        self._analyze_observability(
            snapshot.get("observability"),
            findings,
        )

        return findings

    def _analyze_runtime(
        self,
        runtime,
        findings,
    ):
        if runtime is None:
            findings.append(
                DiagnosticFinding(
                    code="RUNTIME_STATUS_MISSING",
                    severity="warning",
                    message=(
                        "Runtime application status was not supplied."
                    ),
                    component="runtime",
                )
            )
            return

        if not isinstance(runtime, dict):
            findings.append(
                DiagnosticFinding(
                    code="RUNTIME_STATUS_INVALID",
                    severity="critical",
                    message=(
                        "Runtime application status is not structured."
                    ),
                    component="runtime",
                )
            )
            return

        if runtime.get("stopped", False):
            findings.append(
                DiagnosticFinding(
                    code="RUNTIME_STOPPED",
                    severity="warning",
                    message="Runtime application is stopped.",
                    component="runtime",
                )
            )

        lifecycle = runtime.get("lifecycle")

        if isinstance(lifecycle, dict):
            phase = lifecycle.get("phase")
            failed = lifecycle.get(
                "failed_resources",
                0,
            )

            if phase == "failed":
                findings.append(
                    DiagnosticFinding(
                        code="LIFECYCLE_FAILED",
                        severity="critical",
                        message=(
                            "Runtime lifecycle is in failed state."
                        ),
                        component="lifecycle",
                        details={
                            "failed_resources": failed,
                            "last_error": lifecycle.get(
                                "last_error"
                            ),
                        },
                    )
                )

            elif phase not in (
                "running",
                "stopped",
                "created",
            ):
                findings.append(
                    DiagnosticFinding(
                        code="LIFECYCLE_TRANSITION",
                        severity="info",
                        message=(
                            "Runtime lifecycle is transitioning."
                        ),
                        component="lifecycle",
                        details={
                            "phase": phase,
                        },
                    )
                )

        worker = runtime.get("worker_pool")

        if isinstance(worker, dict):
            if (
                worker.get("started", False)
                and not worker.get("shutdown", False)
                and worker.get("alive_workers", 0) == 0
            ):
                findings.append(
                    DiagnosticFinding(
                        code="WORKERS_UNAVAILABLE",
                        severity="critical",
                        message=(
                            "Worker pool is started but has no live workers."
                        ),
                        component="worker_pool",
                    )
                )

            if worker.get("total_failed", 0) > 0:
                findings.append(
                    DiagnosticFinding(
                        code="WORKER_TASK_FAILURES",
                        severity="warning",
                        message=(
                            "Worker pool has recorded failed tasks."
                        ),
                        component="worker_pool",
                        details={
                            "total_failed": worker.get(
                                "total_failed"
                            ),
                        },
                    )
                )

    def _analyze_health(
        self,
        health,
        findings,
    ):
        if health is None:
            return

        if not isinstance(health, dict):
            findings.append(
                DiagnosticFinding(
                    code="HEALTH_STATUS_INVALID",
                    severity="critical",
                    message=(
                        "Runtime health payload is invalid."
                    ),
                    component="health",
                )
            )
            return

        status = health.get("status")

        if status == "unhealthy":
            findings.append(
                DiagnosticFinding(
                    code="RUNTIME_UNHEALTHY",
                    severity="critical",
                    message=(
                        "Runtime health aggregate is unhealthy."
                    ),
                    component="health",
                    details={
                        "ready": health.get("ready"),
                        "live": health.get("live"),
                    },
                )
            )

        elif status == "degraded":
            findings.append(
                DiagnosticFinding(
                    code="RUNTIME_DEGRADED",
                    severity="warning",
                    message=(
                        "Runtime health aggregate is degraded."
                    ),
                    component="health",
                    details={
                        "ready": health.get("ready"),
                        "live": health.get("live"),
                    },
                )
            )

        probes = health.get(
            "probes",
            [],
        )

        if isinstance(probes, list):
            for probe in probes:
                if not isinstance(probe, dict):
                    continue

                if probe.get("status") == "unhealthy":
                    findings.append(
                        DiagnosticFinding(
                            code="PROBE_UNHEALTHY",
                            severity="warning",
                            message=(
                                "Runtime health probe is unhealthy."
                            ),
                            component=str(
                                probe.get(
                                    "name",
                                    "unknown",
                                )
                            ),
                            details={
                                "error": probe.get(
                                    "error"
                                ),
                            },
                        )
                    )

    def _analyze_observability(
        self,
        observability,
        findings,
    ):
        if observability is None:
            return

        if not isinstance(observability, dict):
            findings.append(
                DiagnosticFinding(
                    code=(
                        "OBSERVABILITY_STATUS_INVALID"
                    ),
                    severity="critical",
                    message=(
                        "Observability payload is invalid."
                    ),
                    component="observability",
                )
            )
            return

        status = observability.get("status")

        if not isinstance(status, dict):
            return

        total_finished = status.get(
            "total_finished",
            0,
        )
        total_error = status.get(
            "total_error",
            0,
        )
        total_exception = status.get(
            "total_exception",
            0,
        )

        if (
            total_error > 0
            or total_exception > 0
        ):
            findings.append(
                DiagnosticFinding(
                    code=(
                        "REQUEST_FAILURES_RECORDED"
                    ),
                    severity="warning",
                    message=(
                        "Runtime observability recorded request failures."
                    ),
                    component="observability",
                    details={
                        "total_finished": total_finished,
                        "total_error": total_error,
                        "total_exception": (
                            total_exception
                        ),
                    },
                )
            )

        active = status.get(
            "active_by_service",
            {},
        )

        if isinstance(active, dict):
            for service in active:
                value = active[service]

                if (
                    isinstance(value, int)
                    and value < 0
                ):
                    findings.append(
                        DiagnosticFinding(
                            code=(
                                "ACTIVE_REQUEST_ACCOUNTING_INVALID"
                            ),
                            severity="critical",
                            message=(
                                "Active-request accounting is negative."
                            ),
                            component="observability",
                            details={
                                "service": service,
                                "value": value,
                            },
                        )
                    )
