class Job:
    """
    Deterministic queued job state.

    Time is supplied explicitly. The queue core never reads a wall clock and
    never generates random identifiers.
    """

    VALID_STATUSES = (
        "pending",
        "running",
        "completed",
        "failed",
        "dead_letter",
        "cancelled",
    )

    def __init__(
        self,
        job_id,
        queue_name,
        payload,
        sequence,
        created_at,
        priority=0,
        available_at=None,
        max_attempts=3,
        metadata=None,
    ):
        if not isinstance(job_id, str) or job_id == "":
            raise ValueError("job_id must be non-empty str")

        if not isinstance(queue_name, str) or queue_name == "":
            raise ValueError("queue_name must be non-empty str")

        if not isinstance(payload, dict):
            raise TypeError("payload must be dict")

        if not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("sequence must be positive int")

        if not isinstance(created_at, int) or created_at < 0:
            raise ValueError("created_at must be non-negative int")

        if not isinstance(priority, int):
            raise TypeError("priority must be int")

        if available_at is None:
            available_at = created_at

        if not isinstance(available_at, int) or available_at < created_at:
            raise ValueError(
                "available_at must be integer >= created_at"
            )

        if not isinstance(max_attempts, int) or max_attempts <= 0:
            raise ValueError("max_attempts must be positive int")

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        self.job_id = job_id
        self.queue_name = queue_name
        self.payload = self._copy(payload)
        self.sequence = sequence
        self.created_at = created_at
        self.priority = priority
        self.available_at = available_at
        self.max_attempts = max_attempts
        self.metadata = self._copy(metadata)

        self.status = "pending"
        self.attempts = 0
        self.worker_id = None
        self.lease_until = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.last_error = None

    def runnable(self, now):
        self._validate_now(now)

        return (
            self.status == "pending"
            and now >= self.available_at
        )

    def lease_expired(self, now):
        self._validate_now(now)

        return (
            self.status == "running"
            and self.lease_until is not None
            and now >= self.lease_until
        )

    def claim(
        self,
        worker_id,
        now,
        lease_seconds,
    ):
        if not isinstance(worker_id, str) or worker_id == "":
            raise ValueError("worker_id must be non-empty str")

        self._validate_now(now)

        if not isinstance(lease_seconds, int) or lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive int")

        if not self.runnable(now):
            raise RuntimeError("job is not runnable")

        self.status = "running"
        self.worker_id = worker_id
        self.lease_until = now + lease_seconds
        self.started_at = now
        self.attempts += 1

        return self

    def complete(
        self,
        worker_id,
        now,
        result=None,
    ):
        self._validate_owner(worker_id)
        self._validate_now(now)

        self.status = "completed"
        self.completed_at = now
        self.result = self._copy(result)
        self.worker_id = None
        self.lease_until = None
        self.last_error = None

        return self

    def fail(
        self,
        worker_id,
        now,
        error_message,
        retry_delay_seconds=0,
    ):
        self._validate_owner(worker_id)
        self._validate_now(now)

        if not isinstance(error_message, str):
            raise TypeError("error_message must be str")

        if (
            not isinstance(retry_delay_seconds, int)
            or retry_delay_seconds < 0
        ):
            raise ValueError(
                "retry_delay_seconds must be non-negative int"
            )

        self.last_error = error_message
        self.worker_id = None
        self.lease_until = None

        if self.attempts >= self.max_attempts:
            self.status = "dead_letter"
            self.completed_at = now

        else:
            self.status = "pending"
            self.available_at = now + retry_delay_seconds
            self.started_at = None

        return self

    def requeue_expired(
        self,
        now,
        retry_delay_seconds=0,
    ):
        self._validate_now(now)

        if not self.lease_expired(now):
            return False

        if (
            not isinstance(retry_delay_seconds, int)
            or retry_delay_seconds < 0
        ):
            raise ValueError(
                "retry_delay_seconds must be non-negative int"
            )

        self.last_error = "worker lease expired"
        self.worker_id = None
        self.lease_until = None

        if self.attempts >= self.max_attempts:
            self.status = "dead_letter"
            self.completed_at = now
        else:
            self.status = "pending"
            self.available_at = now + retry_delay_seconds
            self.started_at = None

        return True

    def retry(
        self,
        now,
        delay_seconds=0,
        reset_attempts=False,
    ):
        self._validate_now(now)

        if self.status not in (
            "failed",
            "dead_letter",
            "cancelled",
        ):
            raise RuntimeError(
                "only terminal failed/dead/cancelled jobs can be retried"
            )

        if not isinstance(delay_seconds, int) or delay_seconds < 0:
            raise ValueError("delay_seconds must be non-negative int")

        if reset_attempts:
            self.attempts = 0

        self.status = "pending"
        self.available_at = now + delay_seconds
        self.worker_id = None
        self.lease_until = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.last_error = None

        return self

    def cancel(
        self,
        now,
    ):
        self._validate_now(now)

        if self.status in (
            "completed",
            "dead_letter",
            "cancelled",
        ):
            raise RuntimeError("job is already terminal")

        self.status = "cancelled"
        self.completed_at = now
        self.worker_id = None
        self.lease_until = None

        return self

    def public_dict(self):
        return {
            "job_id": self.job_id,
            "queue_name": self.queue_name,
            "payload": self._copy(self.payload),
            "sequence": self.sequence,
            "created_at": self.created_at,
            "priority": self.priority,
            "available_at": self.available_at,
            "max_attempts": self.max_attempts,
            "metadata": self._copy(self.metadata),
            "status": self.status,
            "attempts": self.attempts,
            "worker_id": self.worker_id,
            "lease_until": self.lease_until,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self._copy(self.result),
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(
        cls,
        value,
    ):
        if not isinstance(value, dict):
            raise TypeError("job state must be dict")

        job = cls(
            job_id=value["job_id"],
            queue_name=value["queue_name"],
            payload=value.get("payload", {}),
            sequence=int(value["sequence"]),
            created_at=int(value["created_at"]),
            priority=int(value.get("priority", 0)),
            available_at=int(
                value.get(
                    "available_at",
                    value["created_at"],
                )
            ),
            max_attempts=int(
                value.get(
                    "max_attempts",
                    3,
                )
            ),
            metadata=value.get("metadata", {}),
        )

        status = value.get("status", "pending")

        if status not in cls.VALID_STATUSES:
            raise ValueError("invalid persisted job status")

        job.status = status
        job.attempts = int(value.get("attempts", 0))
        job.worker_id = value.get("worker_id")
        job.lease_until = value.get("lease_until")
        job.started_at = value.get("started_at")
        job.completed_at = value.get("completed_at")
        job.result = job._copy(value.get("result"))
        job.last_error = value.get("last_error")

        return job

    def _validate_owner(
        self,
        worker_id,
    ):
        if self.status != "running":
            raise RuntimeError("job is not running")

        if worker_id != self.worker_id:
            raise PermissionError(
                "worker does not own this job lease"
            )

    def _validate_now(
        self,
        now,
    ):
        if not isinstance(now, int):
            raise TypeError("now must be integer seconds")

        if now < 0:
            raise ValueError("now must be non-negative")

    def _copy(
        self,
        value,
    ):
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
