class DatasetsConfigFactory:
    """
    Builds the immutable raw dataset catalog/service from typed configuration.
    """

    def build_catalog(
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

        DatasetsConfigValidator().require_valid(
            config
        )

        manifests = []

        for dataset in (
            config.enabled_datasets()
        ):
            sources = []

            for source in dataset.sources:
                sources.append(
                    DatasetSource(
                        path=source.path,
                        source_format=(
                            source.source_format
                        ),
                        role=source.role,
                        required=(
                            source.required
                        ),
                        metadata=(
                            source.metadata
                        ),
                    )
                )

            manifests.append(
                DatasetManifest(
                    dataset_id=(
                        dataset.dataset_id
                    ),
                    name=dataset.name,
                    sources=sources,
                    description=(
                        dataset.description
                    ),
                    metadata=(
                        dataset.metadata
                    ),
                )
            )

        return DatasetCatalog(
            manifests
        )

    def build_service(
        self,
        config,
        inspector=None,
        tracker=None,
    ):
        service = DatasetService(
            catalog=(
                self.build_catalog(
                    config
                )
            ),
            inspector=inspector,
            tracker=tracker,
        )

        if (
            config
            .capture_immutable_baselines
        ):
            for manifest in (
                service
                .catalog
                .manifests()
            ):
                snapshot = (
                    service
                    .inspector
                    .inspect_manifest(
                        manifest
                    )
                )

                service.tracker.capture(
                    snapshot
                )

        return service
