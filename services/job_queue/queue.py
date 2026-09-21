class JobQueue:
    """
    Priority + FIFO queue with delayed availability and lease recovery.

    Higher priority wins. Equal-priority jobs are ordered by enqueue sequence.
    """

    def __init__(
        self,
        queue_name,
        default_lease_seconds=30,
        default_max_attempts=3,
    ):
        if not isinstance(queue_name, str) or queue_name == "":
            raise ValueError("queue_name must be non-empty str")

        if (
            not isinstance(default_lease_seconds, int)
            or default_lease_seconds <= 0
        ):
            raise ValueError(
                "default_lease_seconds must be positive int"
            )

        if (
            not isinstance(default_max_attempts, int)
            or default_max_attempts <= 0
        ):
            raise ValueError(
                "default_max_attempts must be positive int"
            )

        self.queue_name = queue_name
        self.default_lease_seconds = default_lease_seconds
        self.default_max_attempts = default_max_attempts

        self._jobs = {}
        self._order = []

        self.enqueued = 0
        self.claimed = 0
        self.completed = 0
        self.failed_attempts = 0
        self.dead_lettered = 0
        self.cancelled = 0
        self.lease_recoveries = 0

    def add_job(
        self,
        job,
    ):
        if not isinstance(job, Job):
            raise TypeError("job must be Job")

        if job.queue_name != self.queue_name:
            raise ValueError("job queue_name mismatch")

        if job.job_id in self._jobs:
            raise ValueError(
                "duplicate job_id in queue: "
                + job.job_id
            )

        self._jobs[job.job_id] = job
        self._order.append(job.job_id)
        self.enqueued += 1

        return job

    def get(
        self,
        job_id,
    ):
        if job_id not in self._jobs:
            raise KeyError(
                "job not found: "
                + str(job_id)
            )

        return self._jobs[job_id]

    def claim(
        self,
        worker_id,
        now,
        lease_seconds=None,
    ):
        self.recover_expired(
            now
        )

        if lease_seconds is None:
            lease_seconds = self.default_lease_seconds

        candidate = None

        for job_id in self._order:
            job = self._jobs[job_id]

            if not job.runnable(now):
                continue

            if candidate is None:
                candidate = job
                continue

            if job.priority > candidate.priority:
                candidate = job

            elif (
                job.priority == candidate.priority
                and job.sequence < candidate.sequence
            ):
                candidate = job

        if candidate is None:
            return None

        candidate.claim(
            worker_id=worker_id,
            now=now,
            lease_seconds=lease_seconds,
        )

        self.claimed += 1

        return candidate

    def complete(
        self,
        job_id,
        worker_id,
        now,
        result=None,
    ):
        job = self.get(job_id)

        job.complete(
            worker_id=worker_id,
            now=now,
            result=result,
        )

        self.completed += 1

        return job

    def fail(
        self,
        job_id,
        worker_id,
        now,
        error_message,
        retry_delay_seconds=0,
    ):
        job = self.get(job_id)

        before = job.status

        job.fail(
            worker_id=worker_id,
            now=now,
            error_message=error_message,
            retry_delay_seconds=(
                retry_delay_seconds
            ),
        )

        self.failed_attempts += 1

        if (
            before == "running"
            and job.status == "dead_letter"
        ):
            self.dead_lettered += 1

        return job

    def cancel(
        self,
        job_id,
        now,
    ):
        job = self.get(job_id)

        job.cancel(
            now
        )

        self.cancelled += 1

        return job

    def retry(
        self,
        job_id,
        now,
        delay_seconds=0,
        reset_attempts=False,
    ):
        job = self.get(job_id)

        return job.retry(
            now=now,
            delay_seconds=delay_seconds,
            reset_attempts=reset_attempts,
        )

    def recover_expired(
        self,
        now,
        retry_delay_seconds=0,
    ):
        recovered = []
        dead = []

        for job_id in self._order:
            job = self._jobs[job_id]

            before = job.status

            if job.requeue_expired(
                now,
                retry_delay_seconds=(
                    retry_delay_seconds
                ),
            ):
                self.lease_recoveries += 1

                if job.status == "dead_letter":
                    self.dead_lettered += 1
                    dead.append(job.job_id)
                else:
                    recovered.append(job.job_id)

        return {
            "recovered_job_ids": recovered,
            "dead_letter_job_ids": dead,
            "recovered_count": len(recovered),
            "dead_letter_count": len(dead),
        }

    def list_jobs(
        self,
        status=None,
        limit=100,
        newest_first=False,
    ):
        if (
            not isinstance(limit, int)
            or limit <= 0
        ):
            raise ValueError("limit must be positive int")

        if status is not None and status not in Job.VALID_STATUSES:
            raise ValueError("invalid job status filter")

        ids = list(self._order)

        if newest_first:
            ids.reverse()

        result = []

        for job_id in ids:
            job = self._jobs[job_id]

            if status is not None and job.status != status:
                continue

            result.append(
                job.public_dict()
            )

            if len(result) >= limit:
                break

        return result

    def purge_terminal(
        self,
    ):
        terminal = (
            "completed",
            "dead_letter",
            "cancelled",
        )

        removed = []

        for job_id in list(self._order):
            job = self._jobs[job_id]

            if job.status in terminal:
                removed.append(job_id)
                del self._jobs[job_id]

        self._order = [
            job_id
            for job_id in self._order
            if job_id in self._jobs
        ]

        return {
            "removed_job_ids": removed,
            "removed_count": len(removed),
        }

    def counts(self):
        counts = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "dead_letter": 0,
            "cancelled": 0,
        }

        for job_id in self._order:
            counts[
                self._jobs[job_id].status
            ] += 1

        return counts

    def status(self):
        return {
            "queue_name": self.queue_name,
            "default_lease_seconds": (
                self.default_lease_seconds
            ),
            "default_max_attempts": (
                self.default_max_attempts
            ),
            "job_count": len(self._order),
            "counts": self.counts(),
            "enqueued": self.enqueued,
            "claimed": self.claimed,
            "completed_total": self.completed,
            "failed_attempts": self.failed_attempts,
            "dead_lettered_total": (
                self.dead_lettered
            ),
            "cancelled_total": self.cancelled,
            "lease_recoveries": (
                self.lease_recoveries
            ),
        }

    def export_state(self):
        return {
            "queue_name": self.queue_name,
            "default_lease_seconds": (
                self.default_lease_seconds
            ),
            "default_max_attempts": (
                self.default_max_attempts
            ),
            "jobs": [
                self._jobs[
                    job_id
                ].public_dict()
                for job_id in self._order
            ],
            "stats": {
                "enqueued": self.enqueued,
                "claimed": self.claimed,
                "completed": self.completed,
                "failed_attempts": (
                    self.failed_attempts
                ),
                "dead_lettered": (
                    self.dead_lettered
                ),
                "cancelled": self.cancelled,
                "lease_recoveries": (
                    self.lease_recoveries
                ),
            },
        }

    @classmethod
    def from_state(
        cls,
        state,
    ):
        if not isinstance(state, dict):
            raise TypeError("queue state must be dict")

        queue = cls(
            queue_name=state["queue_name"],
            default_lease_seconds=int(
                state.get(
                    "default_lease_seconds",
                    30,
                )
            ),
            default_max_attempts=int(
                state.get(
                    "default_max_attempts",
                    3,
                )
            ),
        )

        for job_state in state.get("jobs", []):
            job = Job.from_dict(
                job_state
            )

            if job.job_id in queue._jobs:
                raise ValueError(
                    "duplicate persisted job_id"
                )

            queue._jobs[job.job_id] = job
            queue._order.append(job.job_id)

        stats = state.get("stats", {})

        queue.enqueued = int(
            stats.get(
                "enqueued",
                len(queue._order),
            )
        )
        queue.claimed = int(
            stats.get("claimed", 0)
        )
        queue.completed = int(
            stats.get("completed", 0)
        )
        queue.failed_attempts = int(
            stats.get(
                "failed_attempts",
                0,
            )
        )
        queue.dead_lettered = int(
            stats.get(
                "dead_lettered",
                0,
            )
        )
        queue.cancelled = int(
            stats.get("cancelled", 0)
        )
        queue.lease_recoveries = int(
            stats.get(
                "lease_recoveries",
                0,
            )
        )

        return queue
