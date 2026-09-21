class SireSoftVectorCatalog:
    """
    Deterministic version catalog with one optional active SireSoft snapshot.
    """

    def __init__(
        self,
    ):
        self._snapshots = {}
        self._order = []
        self._active_version = None

    def add(
        self,
        snapshot,
    ):
        if not isinstance(
            snapshot,
            SireSoftVectorSnapshot,
        ):
            raise TypeError(
                "snapshot must be SireSoftVectorSnapshot"
            )

        if snapshot.version in self._snapshots:
            raise ValueError(
                "SireSoft vector snapshot already exists: "
                + snapshot.version
            )

        self._snapshots[
            snapshot.version
        ] = snapshot

        self._order.append(
            snapshot.version
        )

        return snapshot

    def get(
        self,
        version,
    ):
        if version not in self._snapshots:
            raise KeyError(
                "SireSoft vector snapshot not found: "
                + str(
                    version
                )
            )

        return self._snapshots[
            version
        ]

    def contains(
        self,
        version,
    ):
        return (
            version
            in self._snapshots
        )

    def activate(
        self,
        version,
    ):
        self.get(
            version
        )

        self._active_version = (
            version
        )

        return self._snapshots[
            version
        ]

    def active(
        self,
    ):
        if self._active_version is None:
            return None

        return self._snapshots[
            self._active_version
        ]

    def active_version(
        self,
    ):
        return self._active_version

    def list_snapshots(
        self,
    ):
        return [
            self._snapshots[
                version
            ].to_dict()
            for version
            in self._order
        ]

    def count(
        self,
    ):
        return len(
            self._order
        )

    def export_state(
        self,
    ):
        return {
            "format": (
                "SireLLMVectorSireSoftCatalog"
            ),
            "version": 1,
            "active_version": (
                self._active_version
            ),
            "snapshots": (
                self.list_snapshots()
            ),
        }

    def load_state(
        self,
        state,
    ):
        if not isinstance(
            state,
            dict,
        ):
            raise TypeError(
                "SireSoft vector catalog state must be dict"
            )

        if state.get(
            "format"
        ) != "SireLLMVectorSireSoftCatalog":
            raise ValueError(
                "invalid SireSoft vector catalog format"
            )

        if int(
            state.get(
                "version",
                0,
            )
        ) != 1:
            raise ValueError(
                "unsupported SireSoft vector catalog version"
            )

        staged = (
            SireSoftVectorCatalog()
        )

        for item in state.get(
            "snapshots",
            [],
        ):
            staged.add(
                SireSoftVectorSnapshot
                .from_dict(
                    item
                )
            )

        active = state.get(
            "active_version"
        )

        if active is not None:
            staged.activate(
                active
            )

        self._snapshots = (
            staged._snapshots
        )
        self._order = (
            staged._order
        )
        self._active_version = (
            staged._active_version
        )

        return self
