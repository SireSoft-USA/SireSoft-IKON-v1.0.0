"""CPU-only contracts for bounded conversation prompts and RAG budgets.

Mock inference here is intentional: real generation is covered separately by
unit and live model tests. No checkpoint is overwritten.
"""
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ikon_django import core
from ikon_django.contracts import FrontendChatRequest, FrontendMessage


class Tokenizer:
    def encode(self, text):
        return text.split()
    def decode(self, ids):
        return "ok"


class Inference:
    def __init__(self, window):
        self.loaded = SimpleNamespace(model=SimpleNamespace(max_seq_len=window))
        self.calls = []
    def generate(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs['max_new_tokens'] < self.loaded.model.max_seq_len
        assert len(kwargs['prompt_ids']) <= self.loaded.model.max_seq_len
        return SimpleNamespace(generated_ids=[1], to_dict=lambda: {})


class Orchestrator:
    def __init__(self):
        self.calls = []
    def answer(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(to_dict=lambda: {'answer_text': 'ok', 'citations': []})


def main():
    request = FrontendChatRequest(conversation_id='test', messages=[
        FrontendMessage('user', 'hello'),
        FrontendMessage('assistant', 'some prior response ' * 400),
        FrontendMessage('user', 'What do you do?'),
    ])
    tok = Tokenizer()
    for window, expected_max in [(64, 8), (512, 128), (1024, 128)]:
        inference = Inference(window)
        orchestration = Orchestrator()
        stack = {'tokenizer_manager': SimpleNamespace(tokenizer=tok),
                 'inference': inference, 'orchestrator': orchestration}
        with patch.object(core, '_require_stack', return_value=stack), \
             patch.object(core, '_special_token_ids', return_value=(1, 0)), \
             patch.object(core, 'DEFAULT_MAX_NEW_TOKENS', 128):
            base = core._run_base_frontend_chat(request)
            assert base['text'] == 'ok'
            call = inference.calls[0]
            assert call['max_new_tokens'] == expected_max
            assert 'What' in ' '.join(call['prompt_ids'])
            assert len(call['prompt_ids']) + call['max_new_tokens'] <= window
            rag = core._run_rag_frontend_chat(request)
            assert rag['text'] == 'ok'
            assert orchestration.calls[0]['max_new_tokens'] == expected_max
    print('CONVERSATION + RAG CONTEXT BUDGET TEST: PASS')


if __name__ == '__main__':
    main()
