class RecoveryPlan:
    def __init__(
        self,
        plan_id,
        source_report_id,
        actions=None,
    ):
        if not isinstance(plan_id, str) or plan_id == "":
            raise ValueError(
                "plan_id must be non-empty str"
            )

        if (
            not isinstance(source_report_id, str)
            or source_report_id == ""
        ):
            raise ValueError(
                "source_report_id must be non-empty str"
            )

        if actions is None:
            actions = []

        if not isinstance(actions, list):
            raise TypeError(
                "actions must be list or None"
            )

        self.plan_id = plan_id
        self.source_report_id = source_report_id
        self.actions = []
        self.status = "planned"

        for action in actions:
            self.add(action)

    def add(
        self,
        action,
    ):
        if not isinstance(action, RecoveryAction):
            raise TypeError(
                "action must be RecoveryAction"
            )

        for existing in self.actions:
            if existing.action_id == action.action_id:
                raise ValueError(
                    "duplicate recovery action id: "
                    + action.action_id
                )

        self.actions.append(action)
        return action

    def automatic_actions(self):
        return [
            action
            for action in self.actions
            if action.automatic
        ]

    def manual_actions(self):
        return [
            action
            for action in self.actions
            if not action.automatic
        ]

    def refresh_status(self):
        if len(self.actions) == 0:
            self.status = "empty"
            return self.status

        failed = 0
        pending = 0
        succeeded = 0
        skipped = 0

        for action in self.actions:
            if action.status == "failed":
                failed += 1

            elif action.status in (
                "planned",
                "running",
            ):
                pending += 1

            elif action.status == "succeeded":
                succeeded += 1

            elif action.status == "skipped":
                skipped += 1

        if pending > 0:
            self.status = "in_progress"

        elif failed > 0:
            self.status = "failed"

        elif succeeded > 0 and skipped == 0:
            self.status = "succeeded"

        elif succeeded > 0 or skipped > 0:
            self.status = "partial"

        else:
            self.status = "completed"

        return self.status

    def to_dict(self):
        self.refresh_status()

        return {
            "plan_id": self.plan_id,
            "source_report_id": self.source_report_id,
            "status": self.status,
            "actions": [
                action.to_dict()
                for action in self.actions
            ],
            "automatic_count": len(
                self.automatic_actions()
            ),
            "manual_count": len(
                self.manual_actions()
            ),
        }
