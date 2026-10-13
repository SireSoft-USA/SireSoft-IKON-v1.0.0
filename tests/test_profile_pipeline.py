"""Check that GPU training/RAG assembly honors each isolated model profile.

Mocks subprocess work ONLY; CUDA kernels and trained artifacts have separate
hardware-dependent smoke tests. No filesystem state is changed by this test.
"""
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import run_pipeline as pipeline
from model_profiles import get_profile


def main():
    for name in ('p5000-512', 'p5000-1024'):
        profile = get_profile(name)
        recorded = []
        args = ['run_pipeline.py', '--profile', name, '--device', 'cpu',
                '--skip-preprocessing', '--epochs', '1', '--records-per-dataset',
                '20', '--start-app']
        with patch.object(sys, 'argv', args), \
             patch.object(pipeline, 'prepare_compute'), \
             patch.object(pipeline, 'rebuild_tinystories_if_needed'), \
             patch.object(pipeline, 'verify_canonical_datasets'), \
             patch.object(pipeline, 'verify_artifacts'), \
             patch.object(pipeline, 'run', side_effect=lambda cmd, **kw: recorded.append(cmd) or 0):
            pipeline.main()
        assert len(recorded) == 5, recorded
        tokenizer, train, retrieval, finalize, app = recorded
        assert tokenizer[tokenizer.index('--vocab-size')+1] == str(profile.vocab_size)
        assert tokenizer[tokenizer.index('--output')+1] == profile.tokenizer
        assert train[train.index('--output')+1] == profile.checkpoint
        assert train[train.index('--tokenizer')+1] == profile.tokenizer
        assert train[train.index('--sequence-length')+1] == str(profile.sequence_length)
        assert train[train.index('--d-model')+1] == str(profile.d_model)
        assert train[train.index('--layers')+1] == str(profile.layers)
        assert train[train.index('--heads')+1] == str(profile.heads)
        assert train[train.index('--d-ff')+1] == str(profile.d_ff)
        assert train[train.index('--records-per-dataset')+1] == '20'
        assert retrieval[retrieval.index('--tokenizer')+1] == profile.tokenizer
        assert retrieval[retrieval.index('--output')+1] == profile.retrieval
        assert int(retrieval[retrieval.index('--max-chars')+1]) < 1000
        assert finalize[-2:] == ['--profile', name]
        assert Path(finalize[1]).name == 'finalize_pipeline.py'
        assert app[app.index('--model-profile') + 1] == name
        assert '--require-model' in app
        assert '--device' in app and 'cpu' in app
    print('GPU MODEL TRAINING PIPELINE PROFILE TEST: PASS')


if __name__ == '__main__':
    main()
