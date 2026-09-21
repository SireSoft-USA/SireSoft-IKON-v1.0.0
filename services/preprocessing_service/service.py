class PreprocessingService:
    """
    Protocol-facing raw -> canonical preprocessing service.
    """

    SUPPORTED_DATASETS = (
        "dailydialog",
        "dolly",
        "movie-corpus",
        "siresoft",
        "tinystories",
        "openassistant",
    )

    def __init__(self, pipeline):
        if pipeline is None or not hasattr(
            pipeline,
            "process",
        ):
            raise TypeError(
                "pipeline must provide process()"
            )

        self.pipeline = pipeline

    def handle(self, request):
        if not isinstance(
            request,
            ServiceRequest,
        ):
            raise TypeError(
                "request must be ServiceRequest"
            )

        if request.service != "preprocessing_service":
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="INVALID_REQUEST",
                    message=(
                        "Request targeted the wrong service"
                    ),
                    details={
                        "expected": "preprocessing_service",
                        "actual": request.service,
                    },
                    retryable=False,
                ),
            )

        try:
            if request.operation == "supported_datasets":
                return ServiceResponse.success_response(
                    request,
                    data={
                        "datasets": list(
                            self.SUPPORTED_DATASETS
                        ),
                        "count": len(
                            self.SUPPORTED_DATASETS
                        ),
                    },
                )

            if request.operation in (
                "preview",
                "preprocess",
            ):
                return self._process(
                    request
                )

            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="INVALID_REQUEST",
                    message=(
                        "Unsupported preprocessing operation"
                    ),
                    details={
                        "operation": request.operation,
                    },
                    retryable=False,
                ),
            )

        except FileNotFoundError as error:
            return ServiceResponse.error_response(
                request,
                ProtocolError(
                    code="NOT_FOUND",
                    message=str(error),
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
                    message=str(error),
                    retryable=False,
                ),
            )

    def _process(self, request):
        payload = request.payload

        if "dataset_id" not in payload:
            raise ValueError(
                "payload requires dataset_id"
            )

        dataset_id = payload["dataset_id"]

        if dataset_id not in self.SUPPORTED_DATASETS:
            raise ValueError(
                "unsupported dataset_id: "
                + str(dataset_id)
            )

        output_path = payload.get(
            "output_path"
        )

        if request.operation == "preview":
            output_path = None

        result = self.pipeline.process(
            dataset_id=dataset_id,
            sources=payload.get("sources"),
            normalize=payload.get(
                "normalize",
                True,
            ),
            strict=payload.get(
                "strict",
                False,
            ),
            output_path=output_path,
        )

        return ServiceResponse.success_response(
            request,
            data={
                "summary": result.to_summary(),
                "record_ids": [
                    record.record_id
                    for record in result.records
                ],
                "validation_issues": result.validation_issues,
            },
        )


def build_default_preprocessing_pipeline():
    json_parser = JSONParser()

    loader = DatasetLoader(
        json_parser=json_parser,
        jsonl_parser=JSONLParser(
            json_parser
        ),
        text_parser=TextParser(),
        CanonicalRecord=CanonicalRecord,
        dailydialog_adapter=DailyDialogAdapter(
            CanonicalRecord,
            Conversation,
            Message,
        ),
        dolly_adapter=DollyAdapter(
            CanonicalRecord,
            Conversation,
            Message,
        ),
        movie_adapter=MovieCorpusAdapter(
            CanonicalRecord,
            Conversation,
            Message,
        ),
        siresoft_adapter=SireSoftAdapter(
            CanonicalRecord
        ),
        tinystories_adapter=TinyStoriesAdapter(
            CanonicalRecord
        ),
        openassistant_adapter=OpenAssistantAdapter(
            CanonicalRecord,
            Conversation,
            Message,
        ),
    )

    normalizer = CanonicalNormalizer(
        TextNormalizer(
            WhitespaceNormalizer(),
            PunctuationNormalizer(),
            UnicodeRules(),
        )
    )

    return PreprocessingPipeline(
        loader=loader,
        normalizer=normalizer,
        validator=SchemaValidator(),
        writer=CanonicalJSONLWriter(),
        Document=Document,
    )
