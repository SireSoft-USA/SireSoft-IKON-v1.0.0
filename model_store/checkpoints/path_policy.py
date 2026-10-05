import os


class CheckpointPathPolicy:
    """Creates deterministic, traversal-safe checkpoint paths."""

    def __init__(self, root_path):
        if not isinstance(root_path, str) or root_path == "":
            raise ValueError("root_path must be non-empty str")
        self.root_path = root_path.rstrip("/\\")

    def segment(self, value, field_name):
        if not isinstance(value, str) or value == "":
            raise ValueError(field_name + " must be non-empty str")
        if value in (".", "..") or "/" in value or "\\" in value or os.path.sep in value:
            raise ValueError(field_name + " contains unsafe path characters")
        if os.path.altsep and os.path.altsep in value:
            raise ValueError(field_name + " contains unsafe path characters")
        return value

    def model_directory(self, model_id):
        model_id = self.segment(model_id, "model_id")
        return os.path.join(self.root_path, model_id)

    def checkpoint_path(self, model_id, version):
        model_id = self.segment(model_id, "model_id")
        version = self.segment(version, "version")
        return os.path.join(self.root_path, model_id, version + ".lbckpt")
