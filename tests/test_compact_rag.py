"""Exercise real retrieval and the small-checkpoint RAG budgeting path.

No trained production checkpoint, external Python ML packages, or GPU needed.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from real_runtime import load_rag_namespace, enter_project_root


def main():
    enter_project_root()
    ns = load_rag_namespace()
    encoder = ns['ByteEncoder']()
    specials = ns['SpecialTokens']()
    tok_model = ns['BPETrainer'](
        byte_encoder=encoder,
        pair_counter=ns['PairCounter'](),
        vocabulary_factory=ns['Vocabulary'],
        special_tokens=specials,
    ).train([
        'SireSoft builds software applications for clients',
        'SireSoft provides digital transformation and consulting',
        'What is SireSoft? SireSoft creates software.',
    ], vocab_size=512, min_frequency=2)
    tokenizer = ns['BPETokenizer'](tok_model, encoder, specials)
    retrieval = ns['RetrievalManager'](
        tokenizer=tokenizer, Document=ns['Document'],
        dimension=128, min_n=1, max_n=2,
        max_chars=220, overlap_chars=0, min_chunk_chars=0,
    )
    retrieval.index_documents([{
        'document_id': 'company', 'dataset_id': 'siresoft',
        'text': 'SireSoft builds software applications for clients and provides consulting.',
        'metadata': {'kind': 'company'},
        'provenance': {'source_file': 'siresoft.txt'},
    }], mode='replace')
    class Inference:
        loaded = SimpleNamespace(model=SimpleNamespace(max_seq_len=64))
        def ready(self): return True
        def generate(self, **kwargs):
            assert len(kwargs['prompt_ids']) + kwargs['max_new_tokens'] <= 64
            assert kwargs['allow_prompt_truncation'] is False
            return SimpleNamespace(generated_ids=[], stop_reason='eos')
    worker = ns['RAGServiceOrchestrator'](
        tokenizer=tokenizer, retrieval_manager=retrieval,
        inference_runtime=Inference(), max_context_tokens=200,
    )
    preparation = worker.prepare(
        'SireSoft?', max_new_tokens=8, top_k=1, candidate_k=1,
    )
    assert preparation.ready()
    assert len(preparation.prompt_ids) <= 56
    assert preparation.citations() and preparation.citations()[0].document_id == 'company'
    assert '[S1]' in preparation.prompt
    assert 'SireSoft?' in preparation.prompt
    assert 'software' in preparation.citations()[0].text
    answer = worker.answer('SireSoft?', max_new_tokens=8, top_k=1, candidate_k=1)
    assert answer.status == 'ok'
    print('COMPACT RAG REAL RETRIEVAL TEST: PASS')


if __name__ == '__main__':
    main()
