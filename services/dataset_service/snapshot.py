class RawFileSnapshot:
    """
    Observed state of one declared raw file.
    """

    def __init__(
        self,
        path,
        source_format,
        role,
        required,
        exists,
        size_bytes=0,
        checksum=None,
        sanity_ok=False,
        error=None,
    ):
        self.path = path
        self.source_format = source_format
        self.role = role
        self.required = bool(required)
        self.exists = bool(exists)
        self.size_bytes = int(
            size_bytes
        )
        self.checksum = checksum
        self.sanity_ok = bool(
            sanity_ok
        )
        self.error = error

    def usable(self):
        if not self.exists:
            return not self.required

        return self.sanity_ok

    def fingerprint(self):
        return (
            self.path,
            self.size_bytes,
            self.checksum,
        )

    def to_dict(self):
        return {
            "path": self.path,
            "format": self.source_format,
            "role": self.role,
            "required": self.required,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "sanity_ok": self.sanity_ok,
            "usable": self.usable(),
            "error": self.error,
        }


class DatasetSnapshot:
    """
    Complete observed snapshot for one DatasetManifest.
    """

    def __init__(
        self,
        dataset_id,
        files,
    ):
        if not isinstance(dataset_id, str) or dataset_id == "":
            raise ValueError(
                "dataset_id must be non-empty str"
            )

        self.dataset_id = dataset_id
        self.files = list(files)

    def complete(self):
        for snapshot in self.files:
            if snapshot.required and not snapshot.exists:
                return False

            if snapshot.exists and not snapshot.sanity_ok:
                return False

        return True

    def total_bytes(self):
        total = 0

        for snapshot in self.files:
            total += snapshot.size_bytes

        return total

    def to_dict(self):
        return {
            "dataset_id": self.dataset_id,
            "complete": self.complete(),
            "total_bytes": self.total_bytes(),
            "files": [
                snapshot.to_dict()
                for snapshot in self.files
            ],
        }


class ImmutableRawTracker:
    """
    Stores baseline raw-file fingerprints and detects later mutation.
    """

    def __init__(self):
        self._baselines = {}

    def capture(self, dataset_snapshot):
        if not isinstance(
            dataset_snapshot,
            DatasetSnapshot,
        ):
            raise TypeError(
                "dataset_snapshot must be DatasetSnapshot"
            )

        baseline = {}

        for snapshot in dataset_snapshot.files:
            baseline[
                snapshot.path
            ] = {
                "exists": snapshot.exists,
                "size_bytes": snapshot.size_bytes,
                "checksum": snapshot.checksum,
            }

        self._baselines[
            dataset_snapshot.dataset_id
        ] = baseline

        return baseline

    def has_baseline(self, dataset_id):
        return dataset_id in self._baselines

    def verify(self, dataset_snapshot):
        if not isinstance(
            dataset_snapshot,
            DatasetSnapshot,
        ):
            raise TypeError(
                "dataset_snapshot must be DatasetSnapshot"
            )

        dataset_id = (
            dataset_snapshot.dataset_id
        )

        if dataset_id not in self._baselines:
            raise KeyError(
                "no immutable baseline for dataset: "
                + dataset_id
            )

        baseline = self._baselines[
            dataset_id
        ]

        changes = []

        current_paths = {}

        for snapshot in dataset_snapshot.files:
            current_paths[
                snapshot.path
            ] = True

            if snapshot.path not in baseline:
                changes.append({
                    "path": snapshot.path,
                    "change": "new_source",
                })

                continue

            previous = baseline[
                snapshot.path
            ]

            if (
                snapshot.exists
                != previous["exists"]
            ):
                changes.append({
                    "path": snapshot.path,
                    "change": (
                        "appeared"
                        if snapshot.exists
                        else "missing"
                    ),
                })

                continue

            if snapshot.exists:
                if (
                    snapshot.size_bytes
                    != previous["size_bytes"]
                ):
                    changes.append({
                        "path": snapshot.path,
                        "change": "size_changed",
                        "before": previous["size_bytes"],
                        "after": snapshot.size_bytes,
                    })

                if (
                    snapshot.checksum
                    != previous["checksum"]
                ):
                    changes.append({
                        "path": snapshot.path,
                        "change": "checksum_changed",
                        "before": previous["checksum"],
                        "after": snapshot.checksum,
                    })

        for path in baseline:
            if path not in current_paths:
                changes.append({
                    "path": path,
                    "change": "source_removed_from_manifest",
                })

        return {
            "dataset_id": dataset_id,
            "immutable": (
                len(changes) == 0
            ),
            "changes": changes,
        }
