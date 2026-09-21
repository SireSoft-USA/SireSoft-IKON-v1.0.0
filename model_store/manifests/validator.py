class ManifestValidator:
    """
    Structural and checkpoint-reference validator.
    """

    def validate(
        self,
        manifest,
    ):
        if not isinstance(
            manifest,
            ModelManifest,
        ):
            raise TypeError(
                "manifest must be ModelManifest"
            )

        checkpoint = (
            manifest.checkpoint
        )

        for key in (
            "path",
            "checksum",
        ):
            if (
                not isinstance(
                    checkpoint[
                        key
                    ],
                    str,
                )
                or checkpoint[
                    key
                ] == ""
            ):
                raise ValueError(
                    "checkpoint "
                    + key
                    + " must be non-empty str"
                )

        for key in (
            "byte_count",
            "parameter_count",
            "parameter_tensors",
        ):
            value = checkpoint[
                key
            ]

            if (
                not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    "checkpoint "
                    + key
                    + " must be non-negative int"
                )

        if checkpoint[
            "byte_count"
        ] <= 0:
            raise ValueError(
                "checkpoint byte_count must be positive"
            )

        return {
            "valid": True,
            "model_id": (
                manifest.model_id
            ),
            "version": (
                manifest.version
            ),
        }

    def compare_checkpoint_artifact(
        self,
        manifest,
        artifact,
    ):
        self.validate(
            manifest
        )

        if not isinstance(
            artifact,
            CheckpointArtifact,
        ):
            raise TypeError(
                "artifact must be CheckpointArtifact"
            )

        checks = {
            "model_id": (
                manifest.model_id
                == artifact.model_id
            ),
            "version": (
                manifest.version
                == artifact.version
            ),
            "path": (
                manifest.checkpoint[
                    "path"
                ]
                == artifact.path
            ),
            "checksum": (
                manifest.checkpoint[
                    "checksum"
                ]
                == artifact.checksum
            ),
            "byte_count": (
                manifest.checkpoint[
                    "byte_count"
                ]
                == artifact.byte_count
            ),
            "parameter_count": (
                manifest.checkpoint[
                    "parameter_count"
                ]
                == artifact.parameter_count
            ),
            "parameter_tensors": (
                manifest.checkpoint[
                    "parameter_tensors"
                ]
                == artifact.parameter_tensors
            ),
        }

        valid = True

        for key in checks:
            if not checks[
                key
            ]:
                valid = False

        return {
            "valid": valid,
            "checks": checks,
        }
