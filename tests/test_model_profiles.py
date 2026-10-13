"""Regression: safe, non-destructive P5000 profile routing and training dry run."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.model_profiles import PROFILES, artifact_paths, get_profile
import app


def main():
    assert set(PROFILES) == {"legacy", "p5000-512", "p5000-1024"}
    for name, profile in PROFILES.items():
        assert profile.sequence_length >= 64
        assert profile.d_model % profile.heads == 0
        assert 1 <= profile.batch_size <= 4
        assert profile.max_new_tokens < profile.sequence_length
        values = list(artifact_paths(name).values())
        assert len(values) == 3 and len(set(values)) == 3
        assert all(not Path(path).is_absolute() for path in values)
        assert profile.checkpoint.endswith('.lbckpt')
        assert profile.tokenizer.endswith('.sltok')
        assert profile.retrieval.endswith('.slretr')
        cmd = [sys.executable, str(ROOT/'tools/run_pipeline.py'),
               '--profile', name, '--dry-run']
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=25)
        assert run.returncode == 0, run.stderr
        assert profile.checkpoint in run.stdout
        assert profile.retrieval in run.stdout
        assert profile.tokenizer in run.stdout
    assert set(artifact_paths('legacy').values()).isdisjoint(
        artifact_paths('p5000-512').values())
    assert set(artifact_paths('p5000-512').values()).isdisjoint(
        artifact_paths('p5000-1024').values())
    assert app.artifact_status('p5000-512').keys() <= artifact_paths('p5000-512').keys()
    assert get_profile('p5000-1024').sequence_length == 1024
    try:
        get_profile('unknown')
    except ValueError:
        pass
    else:
        raise AssertionError('Unknown profile silently accepted')
    print('MODEL PROFILES + DRY RUN TEST: PASS')


if __name__ == '__main__':
    main()
