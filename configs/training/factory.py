class TrainingConfigFactory:
    """
    Integrates typed configuration with the existing TrainingFactory and
    TrainingJobManager.
    """

    def build_factory_dict(
        self,
        config,
    ):
        if not isinstance(
            config,
            TrainingJobConfig,
        ):
            raise TypeError(
                "config must be TrainingJobConfig"
            )

        TrainingConfigValidator().require_valid(
            config
        )

        return (
            config.to_factory_dict()
        )

    def create_job(
        self,
        job_id,
        config,
        training_factory=None,
    ):
        if not isinstance(
            job_id,
            str,
        ) or job_id == "":
            raise ValueError(
                "job_id must be non-empty str"
            )

        if training_factory is None:
            training_factory = (
                TrainingFactory()
            )

        return training_factory.create(
            job_id,
            self.build_factory_dict(
                config
            ),
        )

    def create_manager_job(
        self,
        manager,
        job_id,
        config,
    ):
        if not isinstance(
            manager,
            TrainingJobManager,
        ):
            raise TypeError(
                "manager must be TrainingJobManager"
            )

        return manager.create_job(
            job_id,
            self.build_factory_dict(
                config
            ),
        )
