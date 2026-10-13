"""Verify final trained-bundle publishing without GPU or training assets."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from finalize_pipeline import manifest_path, publish_bundle
from model_profiles import get_profile


def main():
    profile = get_profile("p5000-512")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        files = {
            "checkpoint": profile.checkpoint,
            "tokenizer": profile.tokenizer,
            "retrieval_index": profile.retrieval,
        }
        for role, relative in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((role + "-dummy-fixture").encode())

        # All three files must exist before a finalized manifest is published.
        (root / profile.retrieval).unlink()
        try:
            publish_bundle(profile.name, root=root, verify_load=False)
            raise AssertionError("missing RAG index was accepted")
        except FileNotFoundError:
            pass
        output = manifest_path(profile, root)
        assert not output.exists()
        (root / profile.retrieval).write_bytes(b"retrieval-dummy-fixture")

        # Loader is injected only for this offline test. Production uses the
        # real tokenizer, checkpoint and RAG deserializers.
        calls = []
        def pretend_loaded(selected, actual_root):
            calls.append((selected.name, actual_root))
            return {"model": {"max_seq_len": 512}, "retrieval": {"index_entries": 7}}

        target, manifest = publish_bundle(profile.name, root=root, loader=pretend_loaded)
        assert calls == [(profile.name, root)]
        assert target == output and target.is_file()
        assert manifest["profile"] == "p5000-512"
        assert manifest["verified_load"] is True
        assert manifest["context_window"] == 512
        assert manifest["validation"]["retrieval"]["index_entries"] == 7
        assert set(manifest["artifacts"]) == set(files)
        for role, relative in files.items():
            content = (root / relative).read_bytes()
            item = manifest["artifacts"][role]
            assert item["path"] == Path(relative).as_posix()
            assert item["sha256"] == hashlib.sha256(content).hexdigest()
            assert item["bytes"] == len(content)
        assert json.loads(target.read_text()) == manifest
        assert list(target.parent.glob("*.tmp")) == []

        # Failed loading must NOT publish a successful manifest.
        target.unlink()
        def bad_loader(profile, root):
            raise RuntimeError("checkpoint and tokenizer incompatible")
        try:
            publish_bundle(profile.name, root=root, loader=bad_loader)
            raise AssertionError("incompatible artifact loader was accepted")
        except RuntimeError:
            pass
        assert not target.exists()

    # The root entry point must launch the complete dry-run pipeline.
    completed = subprocess.run(
        [sys.executable, str(ROOT / "run_pipeline.py"), "--profile", "p5000-512", "--dry-run"],
        cwd=ROOT, capture_output=True, text=True, timeout=25,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ikon-p5000-512-bundle.json" in completed.stdout
    print("PIPELINE FINALIZATION + MODEL BUNDLE TEST: PASS")


if __name__ == "__main__":
    main()
