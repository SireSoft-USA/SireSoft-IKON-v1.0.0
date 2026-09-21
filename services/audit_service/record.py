class AuditRecord:
    """
    Immutable-style audit record envelope.

    The record_hash is calculated by AuditLedger after all public fields are
    finalized. previous_hash links records into a tamper-evident chain.
    """

    OUTCOMES = (
        "success",
        "failure",
        "denied",
        "unknown",
    )

    def __init__(
        self,
        audit_id,
        sequence,
        timestamp,
        actor_id,
        actor_type,
        action,
        resource,
        outcome,
        metadata=None,
        trace_id=None,
        correlation_id=None,
        previous_hash="0",
        record_hash=None,
    ):
        if not isinstance(audit_id, str) or audit_id == "":
            raise ValueError("audit_id must be non-empty str")

        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("sequence must be positive int")

        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamp must be non-negative int")

        for name, value in (
            ("actor_id", actor_id),
            ("actor_type", actor_type),
            ("action", action),
            ("resource", resource),
        ):
            if not isinstance(value, str) or value == "":
                raise ValueError(
                    name + " must be non-empty str"
                )

        if outcome not in self.OUTCOMES:
            raise ValueError("invalid audit outcome")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        if not isinstance(previous_hash, str) or previous_hash == "":
            raise ValueError("previous_hash must be non-empty str")

        if record_hash is not None and not isinstance(record_hash, str):
            raise TypeError("record_hash must be str or None")

        self.audit_id = audit_id
        self.sequence = sequence
        self.timestamp = timestamp
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.action = action
        self.resource = resource
        self.outcome = outcome
        self.metadata = self._copy(metadata)
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.previous_hash = previous_hash
        self.record_hash = record_hash

    def payload_dict(self):
        return {
            "audit_id": self.audit_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "metadata": self._copy(self.metadata),
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "previous_hash": self.previous_hash,
        }

    def to_dict(self):
        value = self.payload_dict()
        value["record_hash"] = self.record_hash
        return value

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict):
            raise TypeError("audit record state must be dict")

        return cls(
            audit_id=value["audit_id"],
            sequence=int(value["sequence"]),
            timestamp=int(value["timestamp"]),
            actor_id=value["actor_id"],
            actor_type=value["actor_type"],
            action=value["action"],
            resource=value["resource"],
            outcome=value["outcome"],
            metadata=value.get("metadata", {}),
            trace_id=value.get("trace_id"),
            correlation_id=value.get("correlation_id"),
            previous_hash=value.get("previous_hash", "0"),
            record_hash=value.get("record_hash"),
        )

    def _copy(self, value):
        if isinstance(value, dict):
            result = {}
            for key in value:
                result[key] = self._copy(value[key])
            return result

        if isinstance(value, list):
            return [self._copy(item) for item in value]

        if isinstance(value, tuple):
            return [self._copy(item) for item in value]

        return value
