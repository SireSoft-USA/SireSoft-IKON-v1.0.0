class DatasetService:
    """
    Protocol-facing dataset catalog/status service.

    Supported operations:
      list_datasets
      get_manifest
      status
      capture_baseline
      verify_immutable

    Raw data remains untouched. No preprocessing occurs in this service.
    """

    def __init__(
        self,
        catalog=None,
        inspector=None,
        tracker=None,
    ):
        self.catalog = (
            build_default_catalog()
            if catalog is None
            else catalog
        )

        self.inspector = (
            RawDatasetInspector()
            if inspector is None
            else inspector
        )

        self.tracker = (
            ImmutableRawTracker()
            if tracker is None
            else tracker
        )

    def handle(
        self,
        request,
    ):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "dataset_service":
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="INVALID_REQUEST",
                    message="Request targeted the wrong service",
                    details={
                        "expected": "dataset_service",
                        "actual": request.service,
                    },
                    retryable=False,
                ),
            )

        try:
            if request.operation == "list_datasets":
                return self._list(
                    request
                )

            if request.operation == "get_manifest":
                return self._manifest(
                    request
                )

            if request.operation == "status":
                return self._status(
                    request
                )

            if request.operation == "capture_baseline":
                return self._capture_baseline(
                    request
                )

            if request.operation == "verify_immutable":
                return self._verify_immutable(
                    request
                )

            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="INVALID_REQUEST",
                    message="Unsupported dataset service operation",
                    details={
                        "operation": request.operation,
                    },
                    retryable=False,
                ),
            )

        except KeyError as error:
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="NOT_FOUND",
                    message=str(
                        error
                    ),
                    retryable=False,
                ),
            )

        except (
            ValueError,
            TypeError,
        ) as error:
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="INVALID_REQUEST",
                    message=str(
                        error
                    ),
                    retryable=False,
                ),
            )

    def _list(self, request):
        return ServiceResponse.success_response(
            request,
            data={
                "datasets": self.catalog.summaries(),
                "count": self.catalog.count(),
            },
        )

    def _manifest(
        self,
        request,
    ):
        dataset_id = self._dataset_id(
            request
        )

        manifest = self.catalog.get(
            dataset_id
        )

        return ServiceResponse.success_response(
            request,
            data={
                "manifest": manifest.to_dict(),
            },
        )

    def _status(
        self,
        request,
    ):
        dataset_id = request.payload.get(
            "dataset_id"
        )

        if dataset_id is not None:
            snapshot = self.inspector.inspect_manifest(
                self.catalog.get(
                    dataset_id
                )
            )

            return ServiceResponse.success_response(
                request,
                data={
                    "snapshot": snapshot.to_dict(),
                },
            )

        snapshots = []

        for manifest in self.catalog.manifests():
            snapshots.append(
                self.inspector.inspect_manifest(
                    manifest
                ).to_dict()
            )

        return ServiceResponse.success_response(
            request,
            data={
                "snapshots": snapshots,
                "count": len(
                    snapshots
                ),
            },
        )

    def _capture_baseline(
        self,
        request,
    ):
        dataset_id = self._dataset_id(
            request
        )

        snapshot = self.inspector.inspect_manifest(
            self.catalog.get(
                dataset_id
            )
        )

        baseline = self.tracker.capture(
            snapshot
        )

        return ServiceResponse.success_response(
            request,
            data={
                "dataset_id": dataset_id,
                "complete": snapshot.complete(),
                "baseline_file_count": len(
                    baseline
                ),
            },
        )

    def _verify_immutable(
        self,
        request,
    ):
        dataset_id = self._dataset_id(
            request
        )

        snapshot = self.inspector.inspect_manifest(
            self.catalog.get(
                dataset_id
            )
        )

        result = self.tracker.verify(
            snapshot
        )

        return ServiceResponse.success_response(
            request,
            data=result,
        )

    def _dataset_id(
        self,
        request,
    ):
        if "dataset_id" not in request.payload:
            raise ValueError(
                "payload requires dataset_id"
            )

        dataset_id = request.payload[
            "dataset_id"
        ]

        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError(
                "dataset_id must be non-empty str"
            )

        return dataset_id
