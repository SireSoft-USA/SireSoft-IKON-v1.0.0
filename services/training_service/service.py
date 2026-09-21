class TrainingService:
    SUPPORTED_OPERATIONS = (
        "create_job",
        "list_jobs",
        "status",
        "train_step",
        "train_epoch",
        "evaluate",
        "save_checkpoint",
        "load_checkpoint",
        "complete",
        "remove_job",
    )

    def __init__(self, manager=None):
        self.manager = (
            TrainingJobManager()
            if manager is None
            else manager
        )

    def handle(self, request):
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be ServiceRequest")

        if request.service != "training_service":
            return self._error(
                request,
                "INVALID_REQUEST",
                "Request targeted the wrong service",
            )

        try:
            op = request.operation

            if op == "create_job":
                job = self.manager.create_job(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "config"),
                )
                return self._success(request, {"job": job.summary()})

            if op == "list_jobs":
                jobs = self.manager.list_jobs()
                return self._success(
                    request,
                    {"jobs": jobs, "count": len(jobs)},
                )

            if op == "status":
                job = self.manager.get(
                    self._required(request.payload, "job_id")
                )
                return self._success(request, {"job": job.summary()})

            if op == "train_step":
                metrics = self.manager.train_step(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "sequences"),
                )
                return self._success(request, {"metrics": metrics})

            if op == "train_epoch":
                metrics = self.manager.train_epoch(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "sequence_batches"),
                )
                return self._success(request, {"metrics": metrics})

            if op == "evaluate":
                metrics = self.manager.evaluate(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "sequence_batches"),
                )
                return self._success(request, {"metrics": metrics})

            if op == "save_checkpoint":
                info = self.manager.save_checkpoint(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "path"),
                    metadata=request.payload.get("metadata"),
                )
                return self._success(request, {"checkpoint": info})

            if op == "load_checkpoint":
                info = self.manager.load_checkpoint(
                    self._required(request.payload, "job_id"),
                    self._required(request.payload, "path"),
                )
                return self._success(request, {"checkpoint": info})

            if op == "complete":
                summary = self.manager.complete(
                    self._required(request.payload, "job_id")
                )
                return self._success(request, {"job": summary})

            if op == "remove_job":
                job = self.manager.remove_job(
                    self._required(request.payload, "job_id")
                )
                return self._success(
                    request,
                    {"removed_job_id": job.job_id},
                )

            return self._error(
                request,
                "INVALID_REQUEST",
                "Unsupported training service operation",
            )

        except KeyError as error:
            return self._error(request, "NOT_FOUND", str(error))

        except FileNotFoundError as error:
            return self._error(request, "NOT_FOUND", str(error))

        except RuntimeError as error:
            return self._error(request, "CONFLICT", str(error))

        except (ValueError, TypeError, IndexError) as error:
            return self._error(
                request,
                "INVALID_REQUEST",
                str(error),
            )

    def _required(self, payload, key):
        if key not in payload:
            raise ValueError("payload requires " + key)
        return payload[key]

    def _success(self, request, data):
        return ServiceResponse.success_response(
            request,
            data=data,
        )

    def _error(self, request, code, message):
        return ServiceResponse.error_response(
            request,
            ProtocolError(
                code=code,
                message=message,
                retryable=False,
            ),
        )
