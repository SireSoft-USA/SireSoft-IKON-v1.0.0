class RuntimeControlPlane:
    """
    Safe orchestration surface over runtime operations.

    Important boundaries:
      - no shell, eval, or dynamic module execution
      - no implicit wall-clock reads
      - diagnostics are read-only
      - recovery is dry-run by default
      - manual recovery requires explicit allow_manual=True
      - shutdown only records intent through ShutdownCoordinator
    """

    def __init__(
        self,
        runtime_application,
        diagnostic_collector,
        recovery_manager,
        maintenance_manager,
        shutdown_coordinator,
    ):
        if not isinstance(
            runtime_application,
            RuntimeApplication,
        ):
            raise TypeError(
                "runtime_application must be RuntimeApplication"
            )

        if not isinstance(
            diagnostic_collector,
            RuntimeDiagnosticCollector,
        ):
            raise TypeError(
                "diagnostic_collector must be RuntimeDiagnosticCollector"
            )

        if not isinstance(
            recovery_manager,
            RecoveryManager,
        ):
            raise TypeError(
                "recovery_manager must be RecoveryManager"
            )

        if not isinstance(
            maintenance_manager,
            RuntimeMaintenanceManager,
        ):
            raise TypeError(
                "maintenance_manager must be RuntimeMaintenanceManager"
            )

        if not isinstance(
            shutdown_coordinator,
            ShutdownCoordinator,
        ):
            raise TypeError(
                "shutdown_coordinator must be ShutdownCoordinator"
            )

        self.runtime_application = (
            runtime_application
        )
        self.diagnostic_collector = (
            diagnostic_collector
        )
        self.recovery_manager = (
            recovery_manager
        )
        self.maintenance_manager = (
            maintenance_manager
        )
        self.shutdown_coordinator = (
            shutdown_coordinator
        )

        self.total_operations = 0
        self.total_mutations = 0
        self.last_diagnostic_report = None

    def status(
        self,
    ):
        self.total_operations += 1

        return ControlPlaneResult(
            operation="status",
            data={
                "runtime": (
                    self.runtime_application
                    .status()
                ),
                "maintenance": (
                    self.maintenance_manager
                    .status()
                ),
                "shutdown": (
                    self.shutdown_coordinator
                    .status()
                ),
                "recovery": (
                    self.recovery_manager
                    .status()
                ),
                "control": (
                    self._control_status()
                ),
            },
            changed=False,
        )

    def diagnostics(
        self,
        captured_at,
        log_limit=20,
        trace_limit=20,
        extra=None,
    ):
        self._validate_now(
            captured_at,
            "captured_at",
        )

        report = (
            self.diagnostic_collector
            .collect(
                captured_at=(
                    captured_at
                ),
                log_limit=(
                    log_limit
                ),
                trace_limit=(
                    trace_limit
                ),
                extra=extra,
            )
        )

        self.last_diagnostic_report = report
        self.total_operations += 1

        return ControlPlaneResult(
            operation="diagnostics",
            data={
                "report": (
                    report.to_dict()
                ),
            },
            changed=False,
        )

    def recovery_plan(
        self,
        report,
    ):
        if not isinstance(
            report,
            RuntimeDiagnosticReport,
        ):
            raise TypeError(
                "report must be RuntimeDiagnosticReport"
            )

        plan = (
            self.recovery_manager
            .plan(
                report
            )
        )

        self.total_operations += 1

        return ControlPlaneResult(
            operation=(
                "recovery_plan"
            ),
            data={
                "plan": plan.to_dict(),
            },
            changed=False,
        )

    def recover(
        self,
        report,
        dry_run=True,
        allow_manual=False,
    ):
        if not isinstance(
            report,
            RuntimeDiagnosticReport,
        ):
            raise TypeError(
                "report must be RuntimeDiagnosticReport"
            )

        plan = (
            self.recovery_manager
            .recover(
                report,
                dry_run=bool(
                    dry_run
                ),
                allow_manual=bool(
                    allow_manual
                ),
            )
        )

        changed = False

        for action in plan.actions:
            if action.status == "succeeded":
                changed = True
                break

        self.total_operations += 1

        if changed:
            self.total_mutations += 1

        return ControlPlaneResult(
            operation="recover",
            data={
                "dry_run": bool(
                    dry_run
                ),
                "allow_manual": bool(
                    allow_manual
                ),
                "plan": plan.to_dict(),
            },
            changed=changed,
        )

    def begin_maintenance(
        self,
        now,
        reason="maintenance",
    ):
        self._validate_now(
            now,
            "now",
        )

        before = (
            self.maintenance_manager
            .state
            .mode
        )

        status = (
            self.maintenance_manager
            .begin_draining(
                now,
                reason=reason,
            )
        )

        changed = (
            before
            != status[
                "mode"
            ]
        )

        self.total_operations += 1

        if changed:
            self.total_mutations += 1

        return ControlPlaneResult(
            operation=(
                "begin_maintenance"
            ),
            data={
                "maintenance": status,
            },
            changed=changed,
        )

    def advance_maintenance(
        self,
        now,
    ):
        self._validate_now(
            now,
            "now",
        )

        before = (
            self.maintenance_manager
            .state
            .mode
        )

        status = (
            self.maintenance_manager
            .advance(
                now
            )
        )

        changed = (
            before
            != status[
                "mode"
            ]
        )

        self.total_operations += 1

        if changed:
            self.total_mutations += 1

        return ControlPlaneResult(
            operation=(
                "advance_maintenance"
            ),
            data={
                "maintenance": status,
            },
            changed=changed,
        )

    def exit_maintenance(
        self,
        now,
    ):
        self._validate_now(
            now,
            "now",
        )

        before = (
            self.maintenance_manager
            .state
            .mode
        )

        status = (
            self.maintenance_manager
            .exit(
                now
            )
        )

        changed = (
            before
            != status[
                "mode"
            ]
        )

        self.total_operations += 1

        if changed:
            self.total_mutations += 1

        return ControlPlaneResult(
            operation=(
                "exit_maintenance"
            ),
            data={
                "maintenance": status,
            },
            changed=changed,
        )

    def request_shutdown(
        self,
        reason,
        metadata=None,
    ):
        before = (
            self.shutdown_coordinator
            .requested()
        )

        event = (
            self.shutdown_coordinator
            .request(
                reason=reason,
                metadata=metadata,
            )
        )

        changed = not before

        self.total_operations += 1

        if changed:
            self.total_mutations += 1

        return ControlPlaneResult(
            operation=(
                "request_shutdown"
            ),
            data={
                "shutdown": (
                    self.shutdown_coordinator
                    .status()
                ),
                "event": (
                    event.to_dict()
                ),
            },
            changed=changed,
        )

    def _control_status(
        self,
    ):
        return {
            "total_operations": (
                self.total_operations
            ),
            "total_mutations": (
                self.total_mutations
            ),
        }

    def _validate_now(
        self,
        value,
        field_name,
    ):
        if (
            not isinstance(
                value,
                int,
            )
            or value < 0
        ):
            raise ValueError(
                field_name
                + " must be non-negative int"
            )
