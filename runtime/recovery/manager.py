class RecoveryManager:
    def __init__(
        self,
        policy=None,
        executor=None,
    ):
        self.policy = (
            RecoveryPolicy()
            if policy is None
            else policy
        )

        self.executor = (
            RecoveryExecutor()
            if executor is None
            else executor
        )

        self._plan_sequence = 0
        self.total_plans = 0

    def plan(
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

        self._plan_sequence += 1

        plan = RecoveryPlan(
            plan_id=(
                "recovery-plan-"
                + str(
                    self._plan_sequence
                )
            ),
            source_report_id=report.report_id,
        )

        action_sequence = 0

        public = report.to_dict()

        for finding in public["findings"]:
            action_sequence += 1

            action = self.policy.propose(
                finding,
                action_id=(
                    plan.plan_id
                    + "-action-"
                    + str(action_sequence)
                ),
            )

            if action is not None:
                plan.add(action)

        self.total_plans += 1
        return plan

    def recover(
        self,
        report,
        dry_run=False,
        allow_manual=False,
    ):
        plan = self.plan(report)

        self.executor.execute_plan(
            plan,
            dry_run=dry_run,
            allow_manual=allow_manual,
        )

        return plan

    def status(self):
        return {
            "total_plans": self.total_plans,
            "next_plan_sequence": (
                self._plan_sequence + 1
            ),
            "executor": self.executor.status(),
        }
