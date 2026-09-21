class GuardrailServiceManager:
    """
    Service-layer wrapper around GuardrailEngine.

    Public inspection results contain:
      - redacted structured decision metadata
      - forwardable/sanitized text only when action permits it

    Blocked text is intentionally omitted.
    """

    def __init__(
        self,
        engine=None,
        public_view=None,
    ):
        self.engine = (
            GuardrailEngine()
            if engine is None
            else engine
        )

        self.public_view = (
            GuardrailPublicView()
            if public_view is None
            else public_view
        )

        self.policy = (
            GuardrailPolicyStatus(
                self.engine
            )
        )

    def inspect_input(
        self,
        text,
        metadata=None,
    ):
        decision = (
            self.engine
            .check_input(
                text,
                metadata=metadata,
            )
        )

        return self._result(
            decision,
            forward_key="safe_input",
        )

    def inspect_context(
        self,
        text,
        metadata=None,
    ):
        decision = (
            self.engine
            .check_context(
                text,
                metadata=metadata,
            )
        )

        return self._result(
            decision,
            forward_key=(
                "sanitized_context"
            ),
        )

    def inspect_output(
        self,
        text,
        metadata=None,
    ):
        decision = (
            self.engine
            .check_output(
                text,
                metadata=metadata,
            )
        )

        return self._result(
            decision,
            forward_key="safe_output",
        )

    def policy_status(
        self,
    ):
        return self.policy.to_dict()

    def audit_summary(
        self,
    ):
        return (
            self.public_view
            .audit_records(
                self.engine
                .audit_records()
            )
        )

    def clear_audit(
        self,
    ):
        before = len(
            self.engine
            .audit_records()
        )

        self.engine.clear_audit()

        return {
            "cleared": before,
            "remaining": 0,
        }

    def status(
        self,
    ):
        return {
            "ready": True,
            "audit_records": len(
                self.engine
                .audit_records()
            ),
            "policy": (
                self.policy_status()
            ),
        }

    def _result(
        self,
        decision,
        forward_key,
    ):
        result = {
            "decision": (
                self.public_view
                .decision(
                    decision
                )
            ),
            forward_key: None,
        }

        if decision.allowed():
            result[
                forward_key
            ] = decision.safe_text

        return result
