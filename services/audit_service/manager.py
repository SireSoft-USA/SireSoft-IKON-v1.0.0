class AuditManager:
    """
    High-level audit manager.

    Records are append-only in the service API. There is intentionally no
    delete/clear operation. Optional EventBus publication can notify monitoring
    or compliance consumers after an audit record is committed.
    """

    def __init__(
        self,
        ledger=None,
        sanitizer=None,
        persistence=None,
        event_bus=None,
    ):
        self.ledger = (
            AuditLedger()
            if ledger is None
            else ledger
        )

        self.sanitizer = (
            AuditSanitizer()
            if sanitizer is None
            else sanitizer
        )

        self.persistence = (
            AuditPersistence()
            if persistence is None
            else persistence
        )

        self.event_bus = event_bus
        self._sequence = len(
            self.ledger.records()
        )

    def record(
        self,
        timestamp,
        actor_id,
        actor_type,
        action,
        resource,
        outcome="unknown",
        metadata=None,
        trace_id=None,
        correlation_id=None,
        audit_id=None,
    ):
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError(
                "timestamp must be non-negative int"
            )

        sanitized = self.sanitizer.sanitize(
            metadata
        )

        self._sequence += 1

        if audit_id is None:
            audit_id = (
                "audit-"
                + str(self._sequence)
            )

        previous_hash = "0"

        existing = self.ledger.records()

        if len(existing) > 0:
            previous_hash = (
                existing[-1]
                .record_hash
            )

        record = AuditRecord(
            audit_id=audit_id,
            sequence=self._sequence,
            timestamp=timestamp,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource=resource,
            outcome=outcome,
            metadata=sanitized,
            trace_id=trace_id,
            correlation_id=correlation_id,
            previous_hash=previous_hash,
        )

        try:
            self.ledger.append(
                record
            )
        except Exception:
            self._sequence -= 1
            raise

        self._publish_event(
            record
        )

        return record

    def get(
        self,
        audit_id,
    ):
        return self.ledger.get(
            audit_id
        )

    def query(
        self,
        **kwargs
    ):
        return self.ledger.query(
            **kwargs
        )

    def verify(
        self,
    ):
        return self.ledger.verify_integrity()

    def save_state(
        self,
        path,
    ):
        return self.persistence.save(
            path,
            self,
        )

    def load_state_file(
        self,
        path,
    ):
        return self.persistence.load(
            path,
            self,
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMAuditState"
            ),
            "version": 1,
            "sequence": self._sequence,
            "records": [
                record.to_dict()
                for record
                in self.ledger.records()
            ],
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(state, dict):
            raise TypeError(
                "audit manager state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMAuditState":
            raise ValueError(
                "invalid audit state format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported audit state version"
            )

        records = [
            AuditRecord.from_dict(
                value
            )
            for value
            in state.get(
                "records",
                [],
            )
        ]

        staged = AuditLedger()
        staged.replace_records(
            records
        )

        sequence = int(
            state.get(
                "sequence",
                len(records),
            )
        )

        if sequence != len(
            records
        ):
            raise ValueError(
                "audit sequence does not match record count"
            )

        self.ledger = staged
        self._sequence = sequence

        return self

    def status(
        self,
    ):
        integrity = self.verify()

        outcome_counts = {
            "success": 0,
            "failure": 0,
            "denied": 0,
            "unknown": 0,
        }

        for record in self.ledger.records():
            outcome_counts[
                record.outcome
            ] += 1

        return {
            "ready": bool(
                integrity[
                    "valid"
                ]
            ),
            "record_count": len(
                self.ledger.records()
            ),
            "sequence": self._sequence,
            "integrity": integrity,
            "outcomes": (
                outcome_counts
            ),
            "event_bus_attached": (
                self.event_bus
                is not None
            ),
            "integrity_scheme": (
                "fnv1a64_hash_chain"
            ),
        }

    def _publish_event(
        self,
        record,
    ):
        if self.event_bus is None:
            return

        if not hasattr(
            self.event_bus,
            "publish",
        ):
            raise TypeError(
                "event_bus must provide publish()"
            )

        self.event_bus.publish(
            topic="audit.recorded",
            timestamp=(
                record.timestamp
            ),
            payload={
                "audit_id": (
                    record.audit_id
                ),
                "actor_id": (
                    record.actor_id
                ),
                "actor_type": (
                    record.actor_type
                ),
                "action": (
                    record.action
                ),
                "resource": (
                    record.resource
                ),
                "outcome": (
                    record.outcome
                ),
                "record_hash": (
                    record.record_hash
                ),
            },
            source_service=(
                "audit_service"
            ),
            trace_id=(
                record.trace_id
            ),
            correlation_id=(
                record.correlation_id
            ),
        )
