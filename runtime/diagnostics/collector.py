class RuntimeDiagnosticCollector:
    """
    Collects evidence only; it never starts or stops runtime components.
    """

    def __init__(
        self,
        runtime_application=None,
        health_manager=None,
        observability_snapshot=None,
        analyzer=None,
        redactor=None,
    ):
        if (
            runtime_application is not None
            and not isinstance(
                runtime_application,
                RuntimeApplication,
            )
        ):
            raise TypeError(
                "runtime_application must be RuntimeApplication or None"
            )

        if (
            health_manager is not None
            and not isinstance(
                health_manager,
                RuntimeHealthManager,
            )
        ):
            raise TypeError(
                "health_manager must be RuntimeHealthManager or None"
            )

        if (
            observability_snapshot is not None
            and not isinstance(
                observability_snapshot,
                ObservabilitySnapshot,
            )
        ):
            raise TypeError(
                "observability_snapshot must be ObservabilitySnapshot or None"
            )

        self.runtime_application = runtime_application
        self.health_manager = health_manager
        self.observability_snapshot = (
            observability_snapshot
        )

        self.analyzer = (
            RuntimeDiagnosticAnalyzer()
            if analyzer is None
            else analyzer
        )

        self.redactor = (
            DiagnosticRedactor()
            if redactor is None
            else redactor
        )

        self._sequence = 0
        self.total_reports = 0

    def collect(
        self,
        captured_at,
        log_limit=20,
        trace_limit=20,
        extra=None,
    ):
        if (
            not isinstance(captured_at, int)
            or captured_at < 0
        ):
            raise ValueError(
                "captured_at must be non-negative int"
            )

        if extra is None:
            extra = {}

        if not isinstance(extra, dict):
            raise TypeError("extra must be dict or None")

        snapshot = {
            "runtime": (
                None
                if self.runtime_application is None
                else self.runtime_application.status()
            ),
            "health": (
                None
                if self.health_manager is None
                else self.health_manager.check()
            ),
            "observability": (
                None
                if self.observability_snapshot is None
                else self.observability_snapshot.capture(
                    log_limit=log_limit,
                    trace_limit=trace_limit,
                    include_health=False,
                )
            ),
            "extra": extra,
        }

        findings = self.analyzer.analyze(
            snapshot
        )

        self._sequence += 1

        report = RuntimeDiagnosticReport(
            report_id=(
                "diagnostic-"
                + str(self._sequence)
            ),
            captured_at=captured_at,
            snapshot=snapshot,
            findings=findings,
            redactor=self.redactor,
        )

        self.total_reports += 1

        return report

    def status(
        self,
    ):
        return {
            "total_reports": (
                self.total_reports
            ),
            "next_report_sequence": (
                self._sequence + 1
            ),
            "sources": {
                "runtime": (
                    self.runtime_application
                    is not None
                ),
                "health": (
                    self.health_manager
                    is not None
                ),
                "observability": (
                    self.observability_snapshot
                    is not None
                ),
            },
        }
