class PreprocessingConfigFactory:
    def build_pipeline(self, config):
        if not isinstance(
            config,
            PreprocessingConfig,
        ):
            raise TypeError(
                "config must be PreprocessingConfig"
            )

        PreprocessingConfigValidator().require_valid(
            config
        )

        return build_default_preprocessing_pipeline()

    def build_service(self, config):
        return PreprocessingService(
            self.build_pipeline(config)
        )

    def process_dataset(
        self,
        pipeline,
        config,
        dataset_id,
        output_override=None,
    ):
        if not isinstance(
            pipeline,
            PreprocessingPipeline,
        ):
            raise TypeError(
                "pipeline must be PreprocessingPipeline"
            )

        if not isinstance(
            config,
            PreprocessingConfig,
        ):
            raise TypeError(
                "config must be PreprocessingConfig"
            )

        mapping = config.dataset_map()

        if dataset_id not in mapping:
            raise KeyError(
                "dataset not configured: "
                + dataset_id
            )

        item = mapping[dataset_id]

        if not item.enabled:
            raise ValueError(
                "dataset is disabled: "
                + dataset_id
            )

        sources = (
            item.sources
            if len(item.sources) > 0
            else None
        )

        output_path = (
            item.output_path
            if output_override is None
            else output_override
        )

        return pipeline.process(
            dataset_id=dataset_id,
            sources=sources,
            normalize=item.normalize,
            strict=item.strict,
            output_path=output_path,
        )

    def process_all(
        self,
        config,
        pipeline=None,
    ):
        if not isinstance(
            config,
            PreprocessingConfig,
        ):
            raise TypeError(
                "config must be PreprocessingConfig"
            )

        PreprocessingConfigValidator().require_valid(
            config
        )

        if pipeline is None:
            pipeline = self.build_pipeline(
                config
            )

        results = []
        total_records = 0
        total_documents = 0
        all_valid = True

        for item in config.enabled_datasets():
            result = self.process_dataset(
                pipeline,
                config,
                item.dataset_id,
            )

            results.append(result)
            total_records += len(
                result.records
            )
            total_documents += len(
                result.documents
            )

            if not result.valid():
                all_valid = False

        return {
            "results": results,
            "dataset_count": len(results),
            "record_count": total_records,
            "document_count": (
                total_documents
            ),
            "valid": all_valid,
        }
