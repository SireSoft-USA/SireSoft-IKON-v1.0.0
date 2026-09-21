class AuditLedger:
    """
    Append-only in-memory audit ledger with a deterministic FNV-1a hash chain.

    This detects accidental or unsophisticated tampering. FNV-1a is not a
    cryptographic signature, so this should not be represented as equivalent
    to a signed/WORM compliance ledger.
    """

    def __init__(self):
        self._records = []
        self._by_id = {}

    def append(self, record):
        if not isinstance(record, AuditRecord):
            raise TypeError("record must be AuditRecord")

        if record.audit_id in self._by_id:
            raise ValueError(
                "duplicate audit_id: "
                + record.audit_id
            )

        expected_sequence = len(self._records) + 1

        if record.sequence != expected_sequence:
            raise ValueError(
                "audit sequence must be contiguous"
            )

        expected_previous = (
            "0"
            if len(self._records) == 0
            else self._records[-1].record_hash
        )

        if record.previous_hash != expected_previous:
            raise ValueError(
                "audit previous_hash mismatch"
            )

        record.record_hash = self._hash_record(
            record
        )

        self._records.append(record)
        self._by_id[
            record.audit_id
        ] = record

        return record

    def get(self, audit_id):
        if audit_id not in self._by_id:
            raise KeyError(
                "audit record not found: "
                + str(audit_id)
            )

        return self._by_id[
            audit_id
        ]

    def records(self):
        return list(self._records)

    def verify_integrity(self):
        previous = "0"
        expected_sequence = 1

        for record in self._records:
            if record.sequence != expected_sequence:
                return {
                    "valid": False,
                    "sequence": record.sequence,
                    "reason": "sequence_gap",
                }

            if record.previous_hash != previous:
                return {
                    "valid": False,
                    "sequence": record.sequence,
                    "reason": "previous_hash_mismatch",
                }

            calculated = self._hash_record(
                record
            )

            if calculated != record.record_hash:
                return {
                    "valid": False,
                    "sequence": record.sequence,
                    "reason": "record_hash_mismatch",
                }

            previous = record.record_hash
            expected_sequence += 1

        return {
            "valid": True,
            "record_count": len(self._records),
            "head_hash": previous,
        }

    def query(
        self,
        actor_id=None,
        actor_type=None,
        action=None,
        resource=None,
        outcome=None,
        trace_id=None,
        correlation_id=None,
        start_timestamp=None,
        end_timestamp=None,
        limit=100,
        newest_first=False,
    ):
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be positive int")

        if (
            outcome is not None
            and outcome not in AuditRecord.OUTCOMES
        ):
            raise ValueError("invalid audit outcome filter")

        records = list(self._records)

        if newest_first:
            records.reverse()

        result = []

        for record in records:
            if actor_id is not None and record.actor_id != actor_id:
                continue

            if actor_type is not None and record.actor_type != actor_type:
                continue

            if action is not None and record.action != action:
                continue

            if resource is not None and record.resource != resource:
                continue

            if outcome is not None and record.outcome != outcome:
                continue

            if trace_id is not None and record.trace_id != trace_id:
                continue

            if (
                correlation_id is not None
                and record.correlation_id != correlation_id
            ):
                continue

            if (
                start_timestamp is not None
                and record.timestamp < start_timestamp
            ):
                continue

            if (
                end_timestamp is not None
                and record.timestamp > end_timestamp
            ):
                continue

            result.append(
                record.to_dict()
            )

            if len(result) >= limit:
                break

        return {
            "records": result,
            "count": len(result),
            "newest_first": bool(newest_first),
        }

    def replace_records(self, records):
        staged = AuditLedger()

        for record in records:
            if not isinstance(record, AuditRecord):
                raise TypeError(
                    "records must contain AuditRecord"
                )

            # append recalculates the hash; ensure persisted hash agrees.
            persisted_hash = record.record_hash
            record.record_hash = None
            staged.append(record)

            if (
                persisted_hash is not None
                and record.record_hash != persisted_hash
            ):
                raise ValueError(
                    "persisted audit record hash mismatch"
                )

        self._records = staged._records
        self._by_id = staged._by_id

        return self

    def _hash_record(self, record):
        canonical = self._canonical(
            record.payload_dict()
        )

        value = fnv1a64(
            canonical.encode("utf-8")
        )

        return self._hex64(
            value
        )

    def _canonical(self, value):
        if value is None:
            return "n"

        if value is True:
            return "b1"

        if value is False:
            return "b0"

        if isinstance(value, int):
            return "i" + str(value)

        if isinstance(value, float):
            return "f" + repr(value)

        if isinstance(value, str):
            return (
                "s"
                + str(len(value))
                + ":"
                + value
            )

        if isinstance(value, list):
            return (
                "l"
                + str(len(value))
                + "["
                + "".join(
                    self._canonical(item)
                    for item in value
                )
                + "]"
            )

        if isinstance(value, tuple):
            return self._canonical(
                list(value)
            )

        if isinstance(value, dict):
            keys = list(value.keys())
            keys.sort()

            output = (
                "d"
                + str(len(keys))
                + "{"
            )

            for key in keys:
                if not isinstance(key, str):
                    raise TypeError(
                        "audit metadata dictionary keys must be strings"
                    )

                output += self._canonical(key)
                output += self._canonical(
                    value[key]
                )

            return output + "}"

        raise TypeError(
            "unsupported audit value type: "
            + type(value).__name__
        )

    def _hex64(self, value):
        digits = "0123456789abcdef"
        output = ""
        shift = 60

        while shift >= 0:
            output += digits[
                (value >> shift)
                & 0x0F
            ]
            shift -= 4

        return output
