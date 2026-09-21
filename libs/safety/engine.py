class GuardrailEngine:
    """
    Coordinates input, retrieved-context, and output guardrails and records a
    deterministic audit trail.
    """

    def __init__(
        self,
        input_guard=None,
        context_guard=None,
        output_guard=None,
    ):
        self.input_guard = (
            InputGuard()
            if input_guard is None
            else input_guard
        )

        self.context_guard = (
            ContextGuard()
            if context_guard is None
            else context_guard
        )

        self.output_guard = (
            OutputGuard()
            if output_guard is None
            else output_guard
        )

        self._sequence = 0
        self._audit = []

    def check_input(
        self,
        text,
        metadata=None,
    ):
        decision_id = self._next_id(
            "input"
        )

        decision = self.input_guard.inspect(
            text,
            decision_id=decision_id,
        )

        self._record(
            decision,
            metadata,
        )

        return decision

    def check_context(
        self,
        text,
        metadata=None,
    ):
        decision_id = self._next_id(
            "context"
        )

        decision = self.context_guard.inspect(
            text,
            decision_id=decision_id,
        )

        self._record(
            decision,
            metadata,
        )

        return decision

    def check_output(
        self,
        text,
        metadata=None,
    ):
        decision_id = self._next_id(
            "output"
        )

        decision = self.output_guard.inspect(
            text,
            decision_id=decision_id,
        )

        self._record(
            decision,
            metadata,
        )

        return decision

    def audit_records(self):
        return list(
            self._audit
        )

    def clear_audit(self):
        self._audit = []
        return self

    def _next_id(self, phase):
        return (
            phase
            + "-"
            + str(self._sequence + 1)
        )

    def _record(
        self,
        decision,
        metadata,
    ):
        self._sequence += 1

        self._audit.append(
            AuditRecord(
                sequence=self._sequence,
                decision=decision,
                metadata=metadata,
            )
        )
