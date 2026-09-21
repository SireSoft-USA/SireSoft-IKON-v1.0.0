class RecoveryPolicy:
    """
    Conservative mapping from concrete diagnostic findings to recovery actions.
    """

    def __init__(
        self,
        automatic_codes=None,
    ):
        if automatic_codes is None:
            automatic_codes = (
                "PROBE_UNHEALTHY",
                "WORKER_TASK_FAILURES",
            )

        if not isinstance(
            automatic_codes,
            (list, tuple),
        ):
            raise TypeError(
                "automatic_codes must be list/tuple or None"
            )

        self._automatic = {}

        for code in automatic_codes:
            if not isinstance(code, str) or code == "":
                raise ValueError(
                    "automatic recovery codes must be non-empty strings"
                )

            self._automatic[code] = True

    def propose(
        self,
        finding,
        action_id,
    ):
        if not isinstance(finding, dict):
            raise TypeError(
                "finding must be dict"
            )

        code = finding.get("code")
        component = finding.get(
            "component",
            "runtime",
        )

        automatic = code in self._automatic

        if code == "PROBE_UNHEALTHY":
            return RecoveryAction(
                action_id=action_id,
                action_type="mark_component_healthy",
                target=str(component),
                reason_code=code,
                automatic=automatic,
            )

        if code == "WORKER_TASK_FAILURES":
            return RecoveryAction(
                action_id=action_id,
                action_type="clear_transient_failure_state",
                target=str(component),
                reason_code=code,
                automatic=automatic,
                parameters={
                    "note": (
                        "non-destructive bookkeeping recovery only"
                    ),
                },
            )

        if code in (
            "LIFECYCLE_FAILED",
            "WORKERS_UNAVAILABLE",
            "RUNTIME_UNHEALTHY",
            "RUNTIME_DEGRADED",
            "RUNTIME_STOPPED",
            "REQUEST_FAILURES_RECORDED",
            "ACTIVE_REQUEST_ACCOUNTING_INVALID",
        ):
            return RecoveryAction(
                action_id=action_id,
                action_type="manual_review",
                target=str(component),
                reason_code=code,
                automatic=False,
                parameters={
                    "severity": finding.get("severity"),
                    "message": finding.get("message"),
                },
            )

        return None
