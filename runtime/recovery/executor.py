class RecoveryExecutor:
    """
    Executes only exact, pre-registered action handlers.
    """

    def __init__(self):
        self._handlers = {}
        self._order = []

        self.total_executed = 0
        self.total_succeeded = 0
        self.total_failed = 0
        self.total_skipped = 0

    def register(
        self,
        action_type,
        handler,
    ):
        if not isinstance(action_type, str) or action_type == "":
            raise ValueError(
                "action_type must be non-empty str"
            )

        if not callable(handler):
            raise TypeError(
                "handler must be callable"
            )

        if action_type in self._handlers:
            raise ValueError(
                "recovery handler already registered: "
                + action_type
            )

        self._handlers[action_type] = handler
        self._order.append(action_type)

        return handler

    def execute(
        self,
        action,
        dry_run=False,
        allow_manual=False,
    ):
        if not isinstance(action, RecoveryAction):
            raise TypeError(
                "action must be RecoveryAction"
            )

        if action.status != "planned":
            raise RuntimeError(
                "recovery action is not in planned state"
            )

        if dry_run:
            action.mark_skipped("dry-run")
            self.total_skipped += 1
            return action

        if (
            not action.automatic
            and not allow_manual
        ):
            action.mark_skipped(
                "manual approval required"
            )
            self.total_skipped += 1
            return action

        if action.action_type == "manual_review":
            action.mark_skipped(
                "manual review has no automatic execution handler"
            )
            self.total_skipped += 1
            return action

        if action.action_type not in self._handlers:
            action.mark_skipped(
                "no registered recovery handler"
            )
            self.total_skipped += 1
            return action

        action.mark_running()
        self.total_executed += 1

        try:
            result = self._handlers[
                action.action_type
            ](
                action
            )

            action.mark_succeeded(result)
            self.total_succeeded += 1

        except BaseException as error:
            action.mark_failed(error)
            self.total_failed += 1

        return action

    def execute_plan(
        self,
        plan,
        dry_run=False,
        allow_manual=False,
    ):
        if not isinstance(plan, RecoveryPlan):
            raise TypeError(
                "plan must be RecoveryPlan"
            )

        for action in plan.actions:
            if action.status != "planned":
                continue

            self.execute(
                action,
                dry_run=dry_run,
                allow_manual=allow_manual,
            )

        plan.refresh_status()
        return plan

    def status(self):
        return {
            "registered_handlers": list(self._order),
            "total_executed": self.total_executed,
            "total_succeeded": self.total_succeeded,
            "total_failed": self.total_failed,
            "total_skipped": self.total_skipped,
        }
