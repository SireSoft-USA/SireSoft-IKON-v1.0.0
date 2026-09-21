class SafetyFinding:
    """
    Structured guardrail finding.

    severity:
      1 -> informational
      2 -> low
      3 -> medium
      4 -> high
    """

    def __init__(
        self,
        code,
        category,
        severity,
        message,
        start=None,
        end=None,
        evidence=None,
    ):
        if not isinstance(code, str) or code == "":
            raise ValueError("code must be non-empty str")

        if not isinstance(category, str) or category == "":
            raise ValueError("category must be non-empty str")

        if not isinstance(severity, int) or severity < 1 or severity > 4:
            raise ValueError("severity must be int in range 1..4")

        if not isinstance(message, str) or message == "":
            raise ValueError("message must be non-empty str")

        if start is not None:
            if not isinstance(start, int) or start < 0:
                raise ValueError("start must be non-negative int or None")

        if end is not None:
            if not isinstance(end, int) or end < 0:
                raise ValueError("end must be non-negative int or None")

        if (
            start is not None
            and end is not None
            and end < start
        ):
            raise ValueError("end cannot precede start")

        self.code = code
        self.category = category
        self.severity = severity
        self.message = message
        self.start = start
        self.end = end
        self.evidence = evidence

    def to_dict(self):
        return {
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "start": self.start,
            "end": self.end,
            "evidence": self.evidence,
        }


class GuardrailDecision:
    """
    Final decision for one guardrail phase.

    action:
      allow
      warn
      sanitize
      block
    """

    VALID_ACTIONS = (
        "allow",
        "warn",
        "sanitize",
        "block",
    )

    def __init__(
        self,
        decision_id,
        phase,
        action,
        findings=None,
        original_text=None,
        safe_text=None,
    ):
        if not isinstance(decision_id, str) or decision_id == "":
            raise ValueError("decision_id must be non-empty str")

        if not isinstance(phase, str) or phase == "":
            raise ValueError("phase must be non-empty str")

        if action not in self.VALID_ACTIONS:
            raise ValueError("invalid guardrail action")

        self.decision_id = decision_id
        self.phase = phase
        self.action = action
        self.findings = (
            []
            if findings is None
            else list(findings)
        )

        self.original_text = original_text
        self.safe_text = safe_text

    def allowed(self):
        return self.action != "block"

    def max_severity(self):
        highest = 0

        for finding in self.findings:
            if finding.severity > highest:
                highest = finding.severity

        return highest

    def risk_score(self):
        if len(self.findings) == 0:
            return 0

        total = 0

        for finding in self.findings:
            total += finding.severity

        # Bound to 100 for easy service-layer reporting later.
        score = total * 10

        if score > 100:
            score = 100

        return score

    def to_dict(self):
        return {
            "decision_id": self.decision_id,
            "phase": self.phase,
            "action": self.action,
            "allowed": self.allowed(),
            "risk_score": self.risk_score(),
            "max_severity": self.max_severity(),
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "original_text": self.original_text,
            "safe_text": self.safe_text,
        }


class AuditRecord:
    """
    Deterministic in-memory audit record.

    Timestamping is intentionally deferred to the runtime/service layer because
    this safety core contains no imports or OS dependencies.
    """

    def __init__(
        self,
        sequence,
        decision,
        metadata=None,
    ):
        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("sequence must be positive int")

        if not isinstance(decision, GuardrailDecision):
            raise TypeError("decision must be GuardrailDecision")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict")

        self.sequence = sequence
        self.decision = decision
        self.metadata = dict(metadata)

    def to_dict(self):
        return {
            "sequence": self.sequence,
            "decision": self.decision.to_dict(),
            "metadata": dict(self.metadata),
        }
