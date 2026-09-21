class PublicSafetyView:
    """
    Redacted safety representation for protocol responses.

    GuardrailDecision deliberately retains original/safe text internally for
    auditability. Public RAG responses must not echo blocked model output,
    quarantined context, or matched evidence through safety metadata.
    """

    def decision(
        self,
        decision,
    ):
        if decision is None:
            return None

        findings = []

        for finding in decision.findings:
            findings.append({
                "code": finding.code,
                "category": (
                    finding.category
                ),
                "severity": (
                    finding.severity
                ),
                "message": (
                    finding.message
                ),
                "start": finding.start,
                "end": finding.end,
            })

        return {
            "decision_id": (
                decision.decision_id
            ),
            "phase": decision.phase,
            "action": decision.action,
            "allowed": (
                decision.allowed()
            ),
            "risk_score": (
                decision.risk_score()
            ),
            "max_severity": (
                decision.max_severity()
            ),
            "findings": findings,
        }

    def audit_records(
        self,
        records,
    ):
        result = []

        for record in records:
            result.append({
                "sequence": (
                    record.sequence
                ),
                "decision": (
                    self.decision(
                        record.decision
                    )
                ),
                "metadata": (
                    self._copy(
                        record.metadata
                    )
                ),
            })

        return result

    def _copy(
        self,
        value,
    ):
        if isinstance(
            value,
            dict,
        ):
            result = {}

            for key in value:
                result[
                    key
                ] = self._copy(
                    value[
                        key
                    ]
                )

            return result

        if isinstance(
            value,
            list,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                self._copy(
                    item
                )
                for item in value
            ]

        return value
