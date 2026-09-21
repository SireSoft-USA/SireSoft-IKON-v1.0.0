class ModelRegistryConfigFactory:
    """
    Builds and bootstraps ModelRegistry from checkpoint declarations.
    """

    def build_registry(
        self,
        config,
        inspector=None,
    ):
        if not isinstance(
            config,
            ModelRegistryConfig,
        ):
            raise TypeError(
                "config must be ModelRegistryConfig"
            )

        ModelRegistryConfigValidator().require_valid(
            config
        )

        registry = ModelRegistry(
            inspector=inspector
        )

        verification = []

        for item in config.enabled_versions():
            registry.register_checkpoint(
                model_id=(
                    item.model_id
                ),
                version=(
                    item.version
                ),
                checkpoint_path=(
                    item.checkpoint_path
                ),
                metadata=(
                    item.metadata
                ),
                stage=(
                    item.stage
                ),
            )

        for item in config.enabled_versions():
            if item.promote:
                registry.promote(
                    item.model_id,
                    item.version,
                )

        for item in config.enabled_versions():
            if (
                config.verify_all
                or item.verify
            ):
                result = registry.verify(
                    item.model_id,
                    item.version,
                )

                verification.append(
                    result
                )

                if (
                    config
                    .fail_on_verification_error
                    and not result[
                        "valid"
                    ]
                ):
                    raise RuntimeError(
                        "model registry verification failed: "
                        + item.key()
                    )

        return {
            "registry": registry,
            "verification": (
                verification
            ),
            "registered_count": len(
                config.enabled_versions()
            ),
        }
