class PreprocessingConfigValidator:
    def validate(self, config):
        if not isinstance(
            config,
            PreprocessingConfig,
        ):
            raise TypeError(
                "config must be PreprocessingConfig"
            )

        errors = []
        warnings = []

        enabled = config.enabled_datasets()

        if len(enabled) == 0:
            errors.append({
                "code": (
                    "NO_ENABLED_PREPROCESSING_DATASETS"
                ),
                "message": (
                    "At least one preprocessing dataset must be enabled"
                ),
            })

        output_paths = {}

        for item in config.datasets:
            for role in item.required_roles():
                if (
                    role not in item.sources
                    and not config.allow_default_sources
                ):
                    errors.append({
                        "code": (
                            "MISSING_REQUIRED_SOURCE_ROLE"
                        ),
                        "dataset_id": (
                            item.dataset_id
                        ),
                        "role": role,
                        "message": (
                            "Required source role is missing and default sources are disabled"
                        ),
                    })

            if (
                config.require_canonical_outputs
                and item.enabled
                and item.output_path is None
            ):
                errors.append({
                    "code": (
                        "MISSING_CANONICAL_OUTPUT_PATH"
                    ),
                    "dataset_id": item.dataset_id,
                    "message": (
                        "Enabled preprocessing dataset requires canonical output_path"
                    ),
                })

            if item.output_path is not None:
                normalized = (
                    item.output_path
                    .replace("\\", "/")
                    .lower()
                )

                if (
                    normalized.startswith(
                        "datasets/raw/"
                    )
                    or "/datasets/raw/"
                    in normalized
                ):
                    errors.append({
                        "code": (
                            "RAW_LAYER_OUTPUT_FORBIDDEN"
                        ),
                        "dataset_id": item.dataset_id,
                        "path": item.output_path,
                        "message": (
                            "Preprocessing output cannot overwrite the immutable raw layer"
                        ),
                    })

                if item.output_path in output_paths:
                    errors.append({
                        "code": "OUTPUT_PATH_REUSED",
                        "dataset_ids": [
                            output_paths[
                                item.output_path
                            ],
                            item.dataset_id,
                        ],
                        "message": (
                            "Two preprocessing jobs share the same output path"
                        ),
                    })
                else:
                    output_paths[
                        item.output_path
                    ] = item.dataset_id

            if (
                not item.normalize
                and item.enabled
            ):
                warnings.append({
                    "code": (
                        "NORMALIZATION_DISABLED"
                    ),
                    "dataset_id": item.dataset_id,
                    "message": (
                        "Model-facing text normalization is disabled"
                    ),
                })

            if (
                not item.strict
                and item.enabled
            ):
                warnings.append({
                    "code": (
                        "NON_STRICT_CANONICAL_VALIDATION"
                    ),
                    "dataset_id": item.dataset_id,
                    "message": (
                        "Canonical validation errors will not abort preprocessing"
                    ),
                })

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "enabled_dataset_count": len(
                enabled
            ),
        }

    def require_valid(self, config):
        result = self.validate(config)

        if not result["valid"]:
            first = result["errors"][0]
            raise ValueError(
                first["code"]
                + ": "
                + first["message"]
            )

        return result
