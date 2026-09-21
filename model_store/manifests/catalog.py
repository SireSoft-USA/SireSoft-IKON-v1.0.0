class ManifestCatalog:
    """
    Deterministic catalog for stored model manifests.
    """

    def __init__(
        self,
    ):
        self._items = {}
        self._model_order = []
        self._version_order = {}

    def add(
        self,
        manifest,
        manifest_path,
        manifest_checksum,
    ):
        if not isinstance(
            manifest,
            ModelManifest,
        ):
            raise TypeError(
                "manifest must be ModelManifest"
            )

        if not isinstance(
            manifest_path,
            str,
        ) or manifest_path == "":
            raise ValueError(
                "manifest_path must be non-empty str"
            )

        if not isinstance(
            manifest_checksum,
            int,
        ):
            raise TypeError(
                "manifest_checksum must be int"
            )

        model_id = manifest.model_id
        version = manifest.version

        if self.contains(
            model_id,
            version,
        ):
            raise ValueError(
                "manifest already catalogued: "
                + manifest.key()
            )

        if model_id not in self._items:
            self._items[
                model_id
            ] = {}

            self._version_order[
                model_id
            ] = []

            self._model_order.append(
                model_id
            )

        entry = {
            "manifest": manifest,
            "path": manifest_path,
            "checksum": (
                manifest_checksum
            ),
        }

        self._items[
            model_id
        ][
            version
        ] = entry

        self._version_order[
            model_id
        ].append(
            version
        )

        return entry

    def contains(
        self,
        model_id,
        version,
    ):
        return (
            model_id in self._items
            and version
            in self._items[
                model_id
            ]
        )

    def get(
        self,
        model_id,
        version,
    ):
        if not self.contains(
            model_id,
            version,
        ):
            raise KeyError(
                "model manifest not found: "
                + str(
                    model_id
                )
                + "@"
                + str(
                    version
                )
            )

        return self._items[
            model_id
        ][
            version
        ]

    def models(
        self,
    ):
        return [
            {
                "model_id": model_id,
                "versions": list(
                    self._version_order[
                        model_id
                    ]
                ),
                "version_count": len(
                    self._version_order[
                        model_id
                    ]
                ),
            }
            for model_id
            in self._model_order
        ]

    def versions(
        self,
        model_id,
    ):
        if model_id not in self._items:
            return []

        return [
            {
                "manifest": (
                    self._items[
                        model_id
                    ][
                        version
                    ][
                        "manifest"
                    ].to_dict()
                ),
                "path": (
                    self._items[
                        model_id
                    ][
                        version
                    ][
                        "path"
                    ]
                ),
                "checksum": (
                    self._items[
                        model_id
                    ][
                        version
                    ][
                        "checksum"
                    ]
                ),
            }
            for version
            in self._version_order[
                model_id
            ]
        ]

    def count(
        self,
    ):
        total = 0

        for model_id in self._model_order:
            total += len(
                self._version_order[
                    model_id
                ]
            )

        return total
