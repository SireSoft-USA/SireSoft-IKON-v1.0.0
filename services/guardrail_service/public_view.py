class GuardrailPublicView:
    """
    Redacts original/safe text and matched evidence from decision metadata.

    Forwardable text is returned separately by GuardrailServiceManager only when
    the decision permits it. Blocked text never appears in public responses or
    public audit records.
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

    def audit_record(
        self,
        record,
    ):
        return {
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
        }

    def audit_records(
        self,
        records,
    ):
        return [
            self.audit_record(
                record
            )
            for record in records
        ]

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
