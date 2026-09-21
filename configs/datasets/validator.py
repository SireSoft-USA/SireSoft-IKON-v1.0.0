class DatasetsConfigValidator:
    def validate(
        self,
        config,
    ):
        if not isinstance(
            config,
            DatasetsConfig,
        ):
            raise TypeError(
                "config must be DatasetsConfig"
            )

        errors = []
        warnings = []

        enabled = (
            config.enabled_datasets()
        )

        if len(
            enabled
        ) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_DATASETS"
                ),
                "message": (
                    "At least one dataset must be enabled"
                ),
            })

        global_paths = {}

        for dataset in config.datasets:
            required_count = len(
                dataset.required_sources()
            )

            if required_count == 0:
                warnings.append({
                    "code": (
                        "DATASET_WITHOUT_REQUIRED_SOURCE"
                    ),
                    "dataset_id": (
                        dataset.dataset_id
                    ),
                    "message": (
                        "Dataset has no required raw source"
                    ),
                })

            for source in dataset.sources:
                path = source.path

                if (
                    config
                    .enforce_global_source_uniqueness
                    and path in global_paths
                ):
                    errors.append({
                        "code": (
                            "SOURCE_PATH_REUSED"
                        ),
                        "path": path,
                        "dataset_ids": [
                            global_paths[
                                path
                            ],
                            dataset.dataset_id,
                        ],
                        "message": (
                            "Raw source path is declared by multiple datasets"
                        ),
                    })

                else:
                    global_paths[
                        path
                    ] = dataset.dataset_id

                if (
                    source.source_format
                    == "gzip"
                    and source.required
                ):
                    warnings.append({
                        "code": (
                            "REQUIRED_COMPRESSED_SOURCE"
                        ),
                        "dataset_id": (
                            dataset.dataset_id
                        ),
                        "path": path,
                        "message": (
                            "Compressed source is required; ensure downstream preprocessing supports it"
                        ),
                    })

        return {
            "valid": (
                len(
                    errors
                )
                == 0
            ),
            "error_count": len(
                errors
            ),
            "warning_count": len(
                warnings
            ),
            "errors": errors,
            "warnings": warnings,
            "enabled_dataset_count": len(
                enabled
            ),
            "source_count": len(
                global_paths
            ),
        }

    def require_valid(
        self,
        config,
    ):
        result = self.validate(
            config
        )

        if not result[
            "valid"
        ]:
            first = result[
                "errors"
            ][0]

            raise ValueError(
                first[
                    "code"
                ]
                + ": "
                + first[
                    "message"
                ]
            )

        return result
