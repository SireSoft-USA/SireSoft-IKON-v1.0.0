class RuntimeDiagnosticReport:
    def __init__(
        self,
        report_id,
        captured_at,
        snapshot,
        findings,
        redactor=None,
    ):
        if not isinstance(report_id, str) or report_id == "":
            raise ValueError(
                "report_id must be non-empty str"
            )

        if (
            not isinstance(captured_at, int)
            or captured_at < 0
        ):
            raise ValueError(
                "captured_at must be non-negative int"
            )

        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be dict")

        if not isinstance(findings, list):
            raise TypeError("findings must be list")

        for finding in findings:
            if not isinstance(
                finding,
                DiagnosticFinding,
            ):
                raise TypeError(
                    "findings must contain DiagnosticFinding"
                )

        self.report_id = report_id
        self.captured_at = captured_at

        self.redactor = (
            DiagnosticRedactor()
            if redactor is None
            else redactor
        )

        self.snapshot = self.redactor.redact(
            snapshot
        )

        self.findings = [
            self.redactor.redact(
                finding.to_dict()
            )
            for finding in findings
        ]

    def severity_counts(
        self,
    ):
        counts = {
            "info": 0,
            "warning": 0,
            "critical": 0,
        }

        for finding in self.findings:
            severity = finding[
                "severity"
            ]

            if severity in counts:
                counts[severity] += 1

        return counts

    def status(
        self,
    ):
        counts = self.severity_counts()

        if counts["critical"] > 0:
            return "critical"

        if counts["warning"] > 0:
            return "warning"

        return "ok"

    def to_dict(
        self,
    ):
        return {
            "report_id": self.report_id,
            "captured_at": self.captured_at,
            "status": self.status(),
            "severity_counts": (
                self.severity_counts()
            ),
            "findings": [
                dict(finding)
                for finding in self.findings
            ],
            "snapshot": self.redactor.redact(
                self.snapshot
            ),
        }
